"""Plugin bundled (THỬ NGHIỆM): tự động hoá Facebook CÁ NHÂN bằng cookie phiên.

Facebook đã đóng API cho tài khoản cá nhân (đọc feed, đăng tường) từ lâu, nên đi đường cookie:
gọi mbasic.facebook.com (bản HTML nhẹ) bằng httpx + cookie phiên của kết nối "facebook-personal".
Chạy được headless trên VPS (chỉ cần cookie, KHÔNG cần mở trình duyệt / Chromium).

CẢNH BÁO: vi phạm điều khoản Facebook, RỦI RO KHOÁ TÀI KHOẢN. Cookie = chìa khoá toàn quyền
tài khoản (lưu mã hoá). Tool đọc feed = readonly; đăng bài + bình luận = min_mode full nên không
tự chạy ở chế độ suggest/auto. mbasic là bản HTML Facebook có thể đổi/đóng bất thường → coi các
bộ tìm form/selector ở đây là BEST-EFFORT, cần chỉnh lại khi Facebook thay đổi.
"""
from __future__ import annotations

import html as _html
import json
import re

BASE = "https://mbasic.facebook.com"
CONNECTOR_ID = "facebook-personal"
_UA = "Mozilla/5.0 (Android 10; Mobile; rv:120.0) Gecko/120.0 Firefox/120.0"


def _connected_id():
    try:
        import mcp_store
    except Exception:
        return None
    for c in mcp_store.list_connections():
        if c.get("connector_id") == CONNECTOR_ID:
            return c["id"]
    return None


def _cookie():
    try:
        import mcp_store
    except Exception:
        return None
    cid = _connected_id()
    if not cid:
        return None
    ck = ((mcp_store.connection_secrets(cid) or {}).get("cookie") or "").strip()
    if ck.lower().startswith("cookie:"):
        ck = ck.split(":", 1)[1].strip()
    return ck or None


def _check():
    if not _cookie():
        return ("Chưa kết nối Facebook cá nhân. Vào trang Kết nối, chọn 'Facebook cá nhân (cookie)', "
                "dán cookie phiên theo hướng dẫn. Sau đó gọi lại tool này.")
    return None


def _client(cookie):
    import httpx
    return httpx.AsyncClient(timeout=30, follow_redirects=True,
                             headers={"Cookie": cookie, "User-Agent": _UA,
                                      "Accept-Language": "vi-VN,vi;q=0.9,en;q=0.8"})


def _abs(u):
    if u.startswith("http"):
        return u
    return BASE + ("" if u.startswith("/") else "/") + u


async def _get(client, url):
    r = await client.get(_abs(url))
    return r.text, str(r.url)


async def _post(client, action, data):
    r = await client.post(_abs(action), data=data)
    return r.text, str(r.url)


def _fb_dtsg(page):
    m = (re.search(r'name="fb_dtsg"\s+value="([^"]+)"', page)
         or re.search(r"name='fb_dtsg'\s+value='([^']+)'", page))
    return m.group(1) if m else ""


def _find_form(page, textarea_names):
    """Tìm <form> chứa <textarea name=...> khớp một trong textarea_names.
    Trả (action, hidden_dict, ta_name) hoặc (None, {}, None). BEST-EFFORT (mbasic đổi thì chỉnh đây)."""
    for fm in re.findall(r"<form[^>]*>.*?</form>", page, re.S | re.I):
        ta = next((n for n in textarea_names
                   if re.search(r'<textarea[^>]*name="' + re.escape(n) + r'"', fm, re.I)), None)
        if not ta:
            continue
        am = re.search(r'<form[^>]*\baction="([^"]*)"', fm, re.I)
        action = _html.unescape(am.group(1)) if am else ""
        fields = {}
        for nm, val in re.findall(r'<input[^>]*name="([^"]*)"[^>]*value="([^"]*)"', fm, re.I):
            fields[_html.unescape(nm)] = _html.unescape(val)
        return (action or None), fields, ta
    return None, {}, None


_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"[ \t\r\f\v]+")


def _strip(page):
    page = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", page, flags=re.S | re.I)
    page = re.sub(r"<br\s*/?>|</p>|</div>|</li>|</h\d>", "\n", page, flags=re.I)
    txt = _html.unescape(_TAG.sub(" ", page))
    lines = [_WS.sub(" ", ln).strip() for ln in txt.split("\n")]
    return "\n".join(ln for ln in lines if ln)


def _blocked(url):
    u = (url or "").lower()
    return "login" in u or "checkpoint" in u


async def _feed(args, ctx):
    ck = _cookie()
    if not ck:
        return "ERROR: " + (_check() or "chưa kết nối")
    args = args or {}
    try:
        limit = max(500, min(20000, int(args.get("max_chars") or 6000)))
    except (TypeError, ValueError):
        limit = 6000
    try:
        async with _client(ck) as c:
            page, url = await _get(c, "/")
    except Exception as e:
        return f"ERROR: không tải được feed ({type(e).__name__}: {e})."
    if _blocked(url):
        return ("ERROR: Cookie không đăng nhập được (bị đẩy về login/checkpoint). Cookie có thể hết hạn "
                "hoặc tài khoản bị chặn - lấy lại cookie mới.")
    links = []
    for href in re.findall(r'href="(/story\.php\?[^"]+|/[^"]*permalink[^"]*|/[^"]*\?story_fbid=[^"]+)"', page):
        u = _html.unescape(href)
        if u not in links:
            links.append(u)
        if len(links) >= 25:
            break
    text = _strip(page)
    if len(text) > limit:
        text = text[:limit] + "…"
    return json.dumps({"feed_text": text, "post_links": links, "source": url}, ensure_ascii=False)


async def _publish(args, ctx):
    ck = _cookie()
    if not ck:
        return "ERROR: " + (_check() or "chưa kết nối")
    msg = str((args or {}).get("message") or "").strip()
    if not msg:
        return "ERROR: thiếu 'message' (nội dung bài đăng)."
    try:
        async with _client(ck) as c:
            home, url = await _get(c, "/")
            if _blocked(url):
                return "ERROR: Cookie không đăng nhập được (login/checkpoint). Lấy lại cookie mới."
            action, fields, ta = _find_form(home, ["xc_message", "status", "text"])
            if not action or not ta:
                return ("ERROR: Không tìm thấy ô soạn bài trên mbasic (Facebook có thể đã đổi/đóng mbasic). "
                        "Cần chỉnh lại selector trong plugin fb-personal.")
            _res, rurl = await _post(c, action, {**fields, ta: msg})
    except Exception as e:
        return f"ERROR: đăng bài lỗi ({type(e).__name__}: {e})."
    if _blocked(rurl):
        return "ERROR: Bị chặn khi đăng (login/checkpoint) - cookie yếu hoặc bị nghi tự động."
    return json.dumps({"ok": True, "action": "post",
                       "note": "Đã gửi yêu cầu đăng lên tường. Kiểm tra lại trang cá nhân để chắc chắn."},
                      ensure_ascii=False)


async def _comment(args, ctx):
    ck = _cookie()
    if not ck:
        return "ERROR: " + (_check() or "chưa kết nối")
    args = args or {}
    msg = str(args.get("message") or "").strip()
    post = str(args.get("post_url") or args.get("post_id") or "").strip()
    if not msg:
        return "ERROR: thiếu 'message' (nội dung bình luận)."
    if not post:
        return "ERROR: thiếu 'post_url' (link bài mbasic, lấy từ fb_feed_read) hoặc 'post_id'."
    if post.isdigit():
        post = f"/story.php?story_fbid={post}"
    try:
        async with _client(ck) as c:
            page, url = await _get(c, post)
            if _blocked(url):
                return "ERROR: Cookie không đăng nhập được (login/checkpoint). Lấy lại cookie mới."
            action, fields, ta = _find_form(page, ["comment_text", "comment"])
            if not action or not ta:
                return ("ERROR: Không tìm thấy ô bình luận trên bài này (mbasic đổi/đóng, hoặc bài không "
                        "cho bình luận). Cần chỉnh lại selector trong plugin fb-personal.")
            _res, rurl = await _post(c, action, {**fields, ta: msg})
    except Exception as e:
        return f"ERROR: bình luận lỗi ({type(e).__name__}: {e})."
    if _blocked(rurl):
        return "ERROR: Bị chặn khi bình luận (login/checkpoint)."
    return json.dumps({"ok": True, "action": "comment",
                       "note": "Đã gửi bình luận. Kiểm tra lại bài để chắc chắn."}, ensure_ascii=False)


def register(ctx):
    ctx.register_tool(
        name="fb_feed_read", min_mode="readonly", check_fn=_check, handler=_feed,
        description=("Đọc/lướt feed Facebook CÁ NHÂN của bạn qua cookie (mbasic). Trả văn bản feed đã làm "
                     "sạch + danh sách link bài để Javis tóm tắt/tìm thông tin. max_chars giới hạn độ dài "
                     "(mặc định 6000)."),
        schema={"type": "object", "properties": {
            "max_chars": {"type": "integer", "description": "Số ký tự tối đa của feed_text (mặc định 6000)"}}},
    )
    ctx.register_tool(
        name="fb_personal_post", min_mode="full", check_fn=_check, handler=_publish,
        description=("ĐĂNG một bài lên tường Facebook CÁ NHÂN của bạn - hành động THẬT bằng tài khoản cá nhân "
                     "(rủi ro khoá tài khoản). Cần message."),
        schema={"type": "object", "properties": {
            "message": {"type": "string", "description": "Nội dung bài đăng"}},
            "required": ["message"]},
    )
    ctx.register_tool(
        name="fb_personal_comment", min_mode="full", check_fn=_check, handler=_comment,
        description=("BÌNH LUẬN vào một bài trên Facebook bằng tài khoản CÁ NHÂN - hành động THẬT. Cần message "
                     "và post_url (link bài mbasic từ fb_feed_read) hoặc post_id."),
        schema={"type": "object", "properties": {
            "message": {"type": "string", "description": "Nội dung bình luận"},
            "post_url": {"type": "string", "description": "Link bài trên mbasic (từ fb_feed_read)"},
            "post_id": {"type": "string", "description": "ID bài (thay cho post_url)"}},
            "required": ["message"]},
    )
