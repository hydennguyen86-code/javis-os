"""Test connector Facebook Trang (Graph API) BYO app (v0.9.90). Chạy tay / CI:

    cd server && python test_meta_pages.py

KHÔNG mạng (giả _get/_post). Phủ: catalog connector hợp lệ (provider meta, scope Trang, guide
localhost), plugin nạp đủ 5 tool + đúng min_mode (đọc readonly, đăng/trả lời full), gate chưa-kết-
nối, chọn Trang (1 Trang tự lấy, nhiều Trang bắt chỉ rõ), đăng bài dùng token Trang, trả lời
bình luận, đọc bình luận suy Trang từ post_id, và fb_pages_list KHÔNG lộ access_token của Trang.
"""
import asyncio
import importlib.util
import json
import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("JAVIS_STATE_DIR", tempfile.mkdtemp(prefix="javis-metapages-"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

_fails = []
def check(n, c):
    print(("ok  " if c else "FAIL ") + n)
    if not c: _fails.append(n)


# ---- 1. Catalog connector ----
cat = json.load(open(Path(__file__).parent.parent / "system" / "mcp-catalog.json", encoding="utf-8"))
fp = next((x for x in cat["connectors"] if x["id"] == "facebook-pages"), None)
check("catalog: có connector facebook-pages", fp is not None)
check("catalog: provider=meta + explicit authorize/token url", fp["auth"].get("provider") == "meta"
      and fp["auth"].get("authorize_url") and fp["auth"].get("token_url"))
check("catalog: scope có pages_manage_posts + pages_manage_engagement + pages_show_list",
      {"pages_manage_posts", "pages_manage_engagement", "pages_show_list"} <= set(fp["auth"]["scopes"]))
check("catalog: có fields client_id + client_secret",
      {f["key"] for f in fp["auth"]["fields"]} == {"client_id", "client_secret"})
check("catalog: default_perm readonly + guide dùng localhost",
      fp["default_perm"] == "readonly" and "localhost" in fp["auth"]["guide"])
check("catalog: tool ghi khai ở danger", set(fp["tool_meta"].get("danger") or []) == {"fb_page_post", "fb_page_reply"})
import mcp_catalog  # noqa: E402
check("mcp_catalog.get load được", mcp_catalog.get("facebook-pages") is not None)


# ---- 2. Plugin nạp + min_mode ----
spec = importlib.util.spec_from_file_location(
    "meta_pages_graph_test", str(Path(__file__).parent.parent / "system" / "plugins" / "meta-pages-graph" / "plugin.py"))
plug = importlib.util.module_from_spec(spec)
spec.loader.exec_module(plug)


class _Ctx:
    def __init__(self): self.tools = []
    def register_tool(self, name, description, handler, schema=None, min_mode="readonly", check_fn=None, **k):
        self.tools.append({"name": name, "handler": handler, "min_mode": min_mode, "check_fn": check_fn})


ctx = _Ctx()
plug.register(ctx)
byname = {t["name"]: t for t in ctx.tools}
check("plugin: đủ 5 tool", set(byname) == {"fb_pages_list", "fb_page_posts", "fb_page_comments",
                                            "fb_page_post", "fb_page_reply"})
check("plugin: tool đọc = readonly",
      all(byname[n]["min_mode"] == "readonly" for n in ("fb_pages_list", "fb_page_posts", "fb_page_comments")))
check("plugin: tool ghi (đăng/trả lời) = full",
      byname["fb_page_post"]["min_mode"] == "full" and byname["fb_page_reply"]["min_mode"] == "full")

# chưa kết nối → _check chặn
plug._connected_id = lambda: None
check("plugin: _check chặn khi chưa kết nối", "Chưa kết nối" in (plug._check() or ""))


# ---- 3. Handler (giả token + _get/_post, không mạng) ----
async def handler_tests():
    plug._connected_id = lambda: "cfbp"
    async def _fake_token(): return "USERTOK"
    plug._token = _fake_token

    calls = {}
    pages_data = {"data": [{"id": "P1", "name": "Shop A", "category": "Retail",
                            "access_token": "PTOKA", "tasks": ["MANAGE", "CREATE_CONTENT"]}]}

    async def _fake_get(path, params, token):
        calls["get"] = (path, params, token)
        if path == "me/accounts":
            return pages_data
        if path.endswith("/feed"):
            return {"data": [{"id": "P1_10", "message": "hi", "permalink_url": "http://x"}]}
        if path.endswith("/comments"):
            return {"data": [{"id": "c1", "message": "hay qua", "from": {"name": "Khach"}}]}
        return {"data": []}

    async def _fake_post(path, data, token):
        calls["post"] = (path, data, token)
        return {"id": "NEWID"}

    plug._get = _fake_get
    plug._post = _fake_post

    # fb_pages_list: KHÔNG lộ access_token của Trang
    r_list = await plug._list({}, None)
    check("fb_pages_list: có tên Trang", "Shop A" in r_list)
    check("fb_pages_list: KHÔNG lộ page access_token", "PTOKA" not in r_list)

    # _resolve_page: 1 Trang → tự lấy, dùng token Trang
    pid, ptok, pname, err = await plug._resolve_page({}, "USERTOK")
    check("_resolve_page: 1 Trang tự lấy + token Trang", pid == "P1" and ptok == "PTOKA" and err is None)

    # fb_page_posts: gọi feed bằng TOKEN TRANG (không phải token cá nhân)
    await plug._posts({}, None)
    check("fb_page_posts: dùng token Trang gọi P1/feed",
          calls["get"][0] == "P1/feed" and calls["get"][2] == "PTOKA")

    # fb_page_comments: suy Trang từ post_id P1_10, đọc P1_10/comments
    await plug._comments({"post_id": "P1_10"}, None)
    check("fb_page_comments: đọc {post}/comments bằng token Trang",
          calls["get"][0] == "P1_10/comments" and calls["get"][2] == "PTOKA")
    r_noid = await plug._comments({}, None)
    check("fb_page_comments: thiếu post_id → ERROR", r_noid.startswith("ERROR"))

    # fb_page_post: POST P1/feed bằng token Trang, có message
    r_pub = await plug._publish({"message": "Xin chao ca nha"}, None)
    check("fb_page_post: POST P1/feed + token Trang + message",
          calls["post"][0] == "P1/feed" and calls["post"][2] == "PTOKA"
          and calls["post"][1].get("message") == "Xin chao ca nha")
    check("fb_page_post: trả ok + post_id", '"ok": true' in r_pub.lower() and "NEWID" in r_pub)
    r_pub_empty = await plug._publish({}, None)
    check("fb_page_post: thiếu message/link → ERROR", r_pub_empty.startswith("ERROR"))

    # fb_page_reply: POST {comment}/comments
    r_rep = await plug._reply({"comment_id": "c1", "message": "Cam on ban"}, None)
    check("fb_page_reply: POST c1/comments + token Trang",
          calls["post"][0] == "c1/comments" and calls["post"][2] == "PTOKA"
          and calls["post"][1].get("message") == "Cam on ban")
    check("fb_page_reply: trả ok + reply_id", '"ok": true' in r_rep.lower() and "NEWID" in r_rep)
    r_rep_nomsg = await plug._reply({"comment_id": "c1"}, None)
    check("fb_page_reply: thiếu message → ERROR", r_rep_nomsg.startswith("ERROR"))
    r_rep_notarget = await plug._reply({"message": "hi"}, None)
    check("fb_page_reply: thiếu comment_id/post_id → ERROR", r_rep_notarget.startswith("ERROR"))

    # Nhiều Trang: không chỉ rõ → lỗi kèm danh sách; chỉ rõ tên → chọn đúng
    pages_data["data"].append({"id": "P2", "name": "Shop B", "category": "Retail", "access_token": "PTOKB"})
    _, _, _, err_multi = await plug._resolve_page({}, "USERTOK")
    check("_resolve_page: nhiều Trang mà không chỉ rõ → ERROR liệt kê Trang",
          err_multi and err_multi.startswith("ERROR") and "Shop A" in err_multi and "Shop B" in err_multi)
    pid2, ptok2, _, err2 = await plug._resolve_page({"page": "Shop B"}, "USERTOK")
    check("_resolve_page: khớp theo tên Trang", pid2 == "P2" and ptok2 == "PTOKB" and err2 is None)

    # format lỗi Graph
    check("_fmt: lỗi Graph → ERROR message",
          plug._fmt({"error": {"message": "boom"}}).startswith("ERROR: Facebook API: boom"))

asyncio.run(handler_tests())

if _fails:
    print(f"\nFAIL - {len(_fails)} test: {_fails}")
    sys.exit(1)
print("\nOK - test_meta_pages: tất cả pass")
