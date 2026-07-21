"""Test connector + plugin Facebook cá nhân (cookie/mbasic). Chạy tay / CI:

    cd server && python test_fb_personal.py

KHÔNG mạng (giả cookie + giả _get/_post + _client). Phủ: catalog connector hợp lệ (apikey,
field cookie, risk cảnh báo khoá tài khoản), plugin nạp đủ 3 tool + đúng min_mode (đọc readonly,
đăng/bình luận full), gate chưa-có-cookie, bóc fb_dtsg + tìm form soạn bài/bình luận, đọc feed
(text + link, chặn khi bị đẩy về login), đăng bài + bình luận build đúng POST, và validate_connection
cho connector ẢO (không URL) qua cửa mà không dial MCP.
"""
import asyncio
import importlib.util
import json
import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("JAVIS_STATE_DIR", tempfile.mkdtemp(prefix="javis-fbpersonal-"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

_fails = []
def check(n, c):
    print(("ok  " if c else "FAIL ") + n)
    if not c: _fails.append(n)


# ---- 1. Catalog connector ----
cat = json.load(open(Path(__file__).parent.parent / "system" / "mcp-catalog.json", encoding="utf-8"))
fp = next((x for x in cat["connectors"] if x["id"] == "facebook-personal"), None)
check("catalog: có connector facebook-personal", fp is not None)
check("catalog: auth apikey + field cookie", fp["auth"].get("type") == "apikey"
      and any(f["key"] == "cookie" for f in fp["auth"]["fields"]))
check("catalog: field cookie multiline", any(f["key"] == "cookie" and f.get("multiline") for f in fp["auth"]["fields"]))
check("catalog: default_perm readonly", fp["default_perm"] == "readonly")
check("catalog: risk cảnh báo khoá tài khoản", "KHO" in (fp.get("risk") or "").upper() and "cá nhân" in fp["risk"].lower())
check("catalog: tool ghi ở danger", set(fp["tool_meta"].get("danger") or []) == {"fb_personal_post", "fb_personal_comment"})
import mcp_catalog  # noqa: E402
check("mcp_catalog.get load được", mcp_catalog.get("facebook-personal") is not None)


# ---- 2. validate_connection: connector ẢO (không URL) qua cửa không dial ----
import mcp_hub, mcp_store  # noqa: E402


async def virtual_validate_test():
    orig = mcp_store.resolved
    mcp_store.resolved = lambda enabled_only=False: [{
        "id": "cfp", "url": "", "command": "",
        "connector": {"tool_meta": {"read": ["fb_feed_read"], "danger": ["fb_personal_post", "fb_personal_comment"]}},
    }]
    try:
        r = await mcp_hub.validate_connection("cfp")
        check("validate_connection: connector ẢO ok + đếm 3 tool, KHÔNG dial MCP",
              r.get("ok") and r.get("tools") == 3)
    finally:
        mcp_store.resolved = orig

asyncio.run(virtual_validate_test())


# ---- 3. Plugin nạp + min_mode ----
spec = importlib.util.spec_from_file_location(
    "fb_personal_test", str(Path(__file__).parent.parent / "system" / "plugins" / "fb-personal" / "plugin.py"))
plug = importlib.util.module_from_spec(spec)
spec.loader.exec_module(plug)


class _Ctx:
    def __init__(self): self.tools = []
    def register_tool(self, name, description, handler, schema=None, min_mode="readonly", check_fn=None, **k):
        self.tools.append({"name": name, "handler": handler, "min_mode": min_mode})


ctx = _Ctx()
plug.register(ctx)
byname = {t["name"]: t for t in ctx.tools}
check("plugin: đủ 3 tool", set(byname) == {"fb_feed_read", "fb_personal_post", "fb_personal_comment"})
check("plugin: fb_feed_read readonly", byname["fb_feed_read"]["min_mode"] == "readonly")
check("plugin: đăng + bình luận full",
      byname["fb_personal_post"]["min_mode"] == "full" and byname["fb_personal_comment"]["min_mode"] == "full")

# gate: chưa có cookie
plug._connected_id = lambda: None
check("plugin: _check chặn khi chưa có cookie", "Chưa kết nối" in (plug._check() or ""))


# ---- 4. Helper thuần: fb_dtsg, find_form, strip ----
HOME = ('<html><body>'
        '<form method="post" action="/composer/mbasic/?csid=1">'
        '<input type="hidden" name="fb_dtsg" value="AbC123">'
        '<textarea name="xc_message"></textarea>'
        '<input type="submit" name="view_post" value="Đăng"></form>'
        '<div class="story"><h3>Nguyen Van A</h3><p>Hôm nay trời đẹp quá</p>'
        '<a href="/story.php?story_fbid=111&id=222">Chi tiết</a></div>'
        '<div class="story"><h3>Shop B</h3><p>Giảm giá 50 phần trăm</p>'
        '<a href="/story.php?story_fbid=333&id=444">Chi tiết</a></div>'
        '</body></html>')
POSTPAGE = ('<html><body><div><h3>Nguyen Van A</h3><p>Hôm nay trời đẹp quá</p></div>'
            '<form method="post" action="/a/comment.php?ctoken=xyz">'
            '<input type="hidden" name="fb_dtsg" value="Cmt99">'
            '<textarea name="comment_text"></textarea>'
            '<input type="submit" name="submit" value="Bình luận"></form></body></html>')

check("_fb_dtsg: bóc được token", plug._fb_dtsg(HOME) == "AbC123")
a, hid, ta = plug._find_form(HOME, ["xc_message", "status"])
check("_find_form: form soạn bài (action + fb_dtsg + textarea)",
      a == "/composer/mbasic/?csid=1" and hid.get("fb_dtsg") == "AbC123" and ta == "xc_message")
ac, hic, tc = plug._find_form(POSTPAGE, ["comment_text", "comment"])
check("_find_form: form bình luận", ac == "/a/comment.php?ctoken=xyz" and hic.get("fb_dtsg") == "Cmt99" and tc == "comment_text")
check("_strip: bỏ tag, còn chữ", "trời đẹp quá" in plug._strip(HOME) and "<" not in plug._strip(HOME))


# ---- 5. Handler (giả cookie + _client + _get/_post) ----
async def handler_tests():
    plug._connected_id = lambda: "cfp"
    plug._cookie = lambda: "c_user=1; xs=abc"

    class _FakeClient:
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
    plug._client = lambda ck, ua=None: _FakeClient()

    state = {"page": HOME, "url": BASE_HOME, "posted": None}
    async def _fake_get(client, url):
        return state["page"], state["url"]
    async def _fake_post(client, action, data):
        state["posted"] = (action, data)
        return "<html>ok</html>", state["url"]
    plug._get = _fake_get
    plug._post = _fake_post

    # feed: text + link, không bị chặn
    r_feed = await plug._feed({"max_chars": 500}, None)
    d = json.loads(r_feed)
    check("fb_feed_read: có feed_text + post_links",
          "trời đẹp" in d["feed_text"] and any("story_fbid=111" in u for u in d["post_links"]))

    # feed bị đẩy về login → ERROR
    state["url"] = "https://mbasic.facebook.com/login.php?next=..."
    r_block = await plug._feed({}, None)
    check("fb_feed_read: cookie hỏng (login) → ERROR", r_block.startswith("ERROR") and "cookie" in r_block.lower())
    state["url"] = BASE_HOME

    # post: POST đúng form action + xc_message + fb_dtsg
    r_post = await plug._publish({"message": "Xin chao ca nha"}, None)
    check("fb_personal_post: POST composer + message + fb_dtsg",
          state["posted"][0] == "/composer/mbasic/?csid=1"
          and state["posted"][1].get("xc_message") == "Xin chao ca nha"
          and state["posted"][1].get("fb_dtsg") == "AbC123"
          and '"ok": true' in r_post.lower())
    r_post_empty = await plug._publish({}, None)
    check("fb_personal_post: thiếu message → ERROR", r_post_empty.startswith("ERROR"))

    # comment: nạp trang bài rồi POST comment_text
    state["page"] = POSTPAGE
    r_cmt = await plug._comment({"post_url": "/story.php?story_fbid=111", "message": "Dep qua"}, None)
    check("fb_personal_comment: POST comment form + comment_text + fb_dtsg",
          state["posted"][0] == "/a/comment.php?ctoken=xyz"
          and state["posted"][1].get("comment_text") == "Dep qua"
          and state["posted"][1].get("fb_dtsg") == "Cmt99"
          and '"ok": true' in r_cmt.lower())
    r_cmt_nopost = await plug._comment({"message": "hi"}, None)
    check("fb_personal_comment: thiếu post_url/post_id → ERROR", r_cmt_nopost.startswith("ERROR"))
    r_cmt_nomsg = await plug._comment({"post_url": "/x"}, None)
    check("fb_personal_comment: thiếu message → ERROR", r_cmt_nomsg.startswith("ERROR"))

BASE_HOME = "https://mbasic.facebook.com/"
asyncio.run(handler_tests())


# ---- 6. Lớp fetch: phát hiện trang 'không hỗ trợ' + tự đổi UA + ô UA override ----
UNSUPPORTED = ('<html><body><h2>Trình duyệt này không hỗ trợ Facebook, hãy tải Facebook Lite</h2>'
               '</body></html>')
check("_unsupported: bắt trang 'không hỗ trợ / Facebook Lite'",
      plug._unsupported(UNSUPPORTED) and not plug._unsupported(HOME))
LOGINPAGE = ('<html><body><form method="post" action="/login/device-based/regular/login/">'
             '<input name="email" type="text"><input name="pass" type="password">'
             '<input name="login" value="Đăng nhập"></form></body></html>')
check("_is_login: bắt trang đăng nhập (email+pass)", plug._is_login(LOGINPAGE) and not plug._is_login(HOME))


async def fetch_tests():
    plug._connected_id = lambda: "cfp"
    plug._cookie = lambda: "c_user=1; xs=abc"

    class _FakeClient:
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
    plug._client = lambda ck, ua: _FakeClient()

    # UA override: field user_agent → đứng đầu danh sách UA thử
    import mcp_store
    orig = mcp_store.connection_secrets
    mcp_store.connection_secrets = lambda cid: {"cookie": "c=1", "user_agent": "MyUA/1.0"}
    try:
        check("_uas: UA user khai đứng đầu + còn UA mặc định",
              plug._uas()[0] == "MyUA/1.0" and len(plug._uas()) >= 2)
    finally:
        mcp_store.connection_secrets = orig

    # mọi UA bị chê → trả lỗi hướng dẫn đổi UA (KHÔNG trả rác)
    async def _get_bad(client, url):
        return UNSUPPORTED, BASE_HOME
    plug._get = _get_bad
    _p, _u, _ua, err = await plug._fetch("c=1", "/")
    check("_fetch: mọi UA bị chê → ERROR hướng dẫn đổi UA", bool(err) and err.startswith("ERROR") and "User-Agent" in err)
    r_feed_bad = await plug._feed({}, None)
    check("fb_feed_read: trang 'không hỗ trợ' → ERROR rõ (không trả rác)",
          r_feed_bad.startswith("ERROR") and "User-Agent" in r_feed_bad)

    # UA đầu bị chê, UA sau OK → tự chuyển, trả trang tốt
    calls = {"n": 0}
    async def _get_flaky(client, url):
        calls["n"] += 1
        return (UNSUPPORTED, BASE_HOME) if calls["n"] == 1 else (HOME, BASE_HOME)
    plug._get = _get_flaky
    page, _url, _ua2, err2 = await plug._fetch("c=1", "/")
    check("_fetch: UA đầu bị chê thì tự thử UA sau và qua được",
          err2 is None and "xc_message" in page and calls["n"] == 2)

    # trang đăng nhập theo NỘI DUNG (url vẫn mbasic, không /login) → báo cookie bị từ chối, KHÔNG đổi UA vô ích
    async def _get_login(client, url):
        return LOGINPAGE, BASE_HOME
    plug._get = _get_login
    _p3, _u3, _ua3, err3 = await plug._fetch("c=1", "/")
    check("_fetch: trang đăng nhập (nội dung) → ERROR cookie bị từ chối", bool(err3) and "từ chối" in err3)
    r_feed_login = await plug._feed({}, None)
    check("fb_feed_read: cookie bị từ chối → ERROR rõ (không đọc login thành feed)",
          r_feed_login.startswith("ERROR") and "ĐĂNG NHẬP" in r_feed_login)

asyncio.run(fetch_tests())

if _fails:
    print(f"\nFAIL - {len(_fails)} test: {_fails}")
    sys.exit(1)
print("\nOK - test_fb_personal: tất cả pass")
