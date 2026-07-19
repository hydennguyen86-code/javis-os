"""Plugin bundled (THỬ NGHIỆM): tự động hoá Facebook CÁ NHÂN bằng cookie phiên.

Facebook đã đóng API cho tài khoản cá nhân (đọc feed, đăng tường) từ lâu, nên đi đường cookie:
gọi mbasic.facebook.com (bản HTML nhẹ) bằng httpx + cookie phiên của kết nối "facebook-personal".
Chạy được headless trên VPS (chỉ cần cookie, KHÔNG cần mở trình duyệt / Chromium).

QUAN TRỌNG - User-Agent: mbasic là site cho TRÌNH DUYỆT DI ĐỘNG thật; gửi UA lạ (desktop, hoặc
Firefox mobile) sẽ bị đẩy sang trang "Trình duyệt không hỗ trợ, tải Facebook Lite" thay vì feed.
Nên mặc định dùng UA iPhone Safari, tự thử vài UA di động nếu bị chê, và cho user dán UA riêng
(khớp UA với trình duyệt nơi lấy cookie là chắc nhất) qua field 'user_agent' của kết nối.

CẢNH BÁO: vi phạm điều khoản Facebook, RỦI RO KHOÁ TÀI KHOẢN. Cookie = chìa khoá toàn quyền tài
khoản (lưu mã hoá). Tool đọc feed = readonly; đăng bài + bình luận = min_mode full nên không tự
chạy ở chế độ suggest/auto. mbasic có thể bị Facebook đổi/đóng → bộ tìm form là BEST-EFFORT.
"""
from __future__ import annotations

import html as _html
import json
import re

BASE = "https://mbasic.facebook.com"
CONNECTOR_ID = "facebook-personal"

# mbasic chỉ nhả HTML cho UA di động thật. iPhone Safari là UA nhận được mbasic ổn nhất; kèm
# vài UA dự phòng để tự đổi khi bị chê. User có thể ghi đè bằng field user_agent của kết nối.
_DEFAULT_UAS = [
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
]


def _secrets():
    try:
        import mcp_store
    except Exception:
        return {}
    cid = _connected_id()
    if not cid:
        return {}
    return mcp_store.connection_secrets(cid) or {}


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
    ck = (_secrets().get("cookie") or "").strip()
    if ck.lower().startswith("cookie:"):
        ck = ck.split(":", 1)[1].strip()
    return ck or None


def _uas():
    """UA để thử, theo thứ tự: UA user tự khai (nếu có) rồi tới các UA mặc định."""
    lst = []
    override = (_secrets().get("user_agent") or "").strip()
    if override:
        lst.append(override)
    for u in _DEFAULT_UAS:
        if u not in lst:
            lst.append(u)
    return lst


def _check():
    if not _cookie():
        return ("Chưa kết nối Facebook cá nhân. Vào trang Kết nối, chọn 'Facebook cá nhân (cookie)', "
                "dán cookie phiên theo hướng dẫn. Sau đó gọi lại tool này.")
    return None


def _client(cookie, ua):
    import httpx
    return httpx.AsyncClient(timeout=30, follow_redirects=True,
                             headers={"Cookie": cookie, "User-Agent": ua,
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


def _blocked(url):
    u = (url or "").lower()
    return "login" in u or "checkpoint" in u


def _unsupported(page):
    """Trang 'Trình duyệt không hỗ trợ, tải Facebook Lite' mà mbasic trả khi chê UA."""
    return bool(re.search(r"không hỗ trợ|browser is not supported|isn'?t compatible|"
                          r"tải Facebook Lite|Get Facebook Lite|Nâng cấp trình duyệt|Update your browser",
                          page or "", re.I))


def _is_login(page):
    """mbasic trả trang ĐĂNG NHẬP (cookie bị từ chối) - có cả ô email lẫn ô mật khẩu."""
    p = page or ""
    return (bool(re.search(r'<input[^>]*name="email"', p, re.I))
            and bool(re.search(r'<input[^>]*name="(pass|encpass)"', p, re.I)))


_COOKIE_HELP = ("ERROR: Facebook trả trang ĐĂNG NHẬP - cookie đang bị từ chối, không đọc được feed. "
                "Thường do: (1) cookie đã hết hạn / bạn đã đăng xuất trình duyệt gốc - đừng logout sau khi "
                "copy, và lấy cookie MỚI ngay trước khi thử; (2) Javis đang chạy ở IP/máy KHÁC nơi bạn đăng "
                "nhập (VPS, khác nước) nên Facebook chặn phiên vì 'đăng nhập lạ' - chạy Javis cùng máy/mạng "
                "nơi đăng nhập, hoặc đăng nhập Facebook từ chính IP của VPS; (3) tài khoản đang bị checkpoint - "
                "mở trình duyệt xác minh xong rồi lấy lại cookie. Kiểm tra cookie có đủ cả c_user và xs.")


_UA_HELP = ("mbasic chê trình duyệt ('không hỗ trợ, tải Facebook Lite') với mọi User-Agent thử. "
            "Cách sửa: mở kết nối Facebook cá nhân, dán vào ô 'User-Agent' đúng UA của trình duyệt "
            "nơi bạn lấy cookie (tra 'my user agent' trên trình duyệt đó). Tốt nhất lấy cookie từ "
            "trình duyệt DI ĐỘNG (điện thoại) rồi dán cả UA di động đó.")


async def _fetch(cookie, url):
    """GET url, tự đổi UA nếu mbasic chê. Trả (page, final_url, ua_dùng, err_str)."""
    last_url = ""
    for ua in _uas():
        try:
            async with _client(cookie, ua) as c:
                page, furl = await _get(c, url)
        except Exception as e:
            return None, "", ua, f"ERROR: không tải được ({type(e).__name__}: {e})."
        if _blocked(furl) or _is_login(page):
            return None, furl, ua, _COOKIE_HELP     # cookie bị từ chối - đổi UA không cứu được
        if _unsupported(page):
            last_url = furl
            continue                      # thử UA kế tiếp
        return page, furl, ua, None
    return None, last_url, None, "ERROR: " + _UA_HELP


async def _feed(args, ctx):
    ck = _cookie()
    if not ck:
        return "ERROR: " + (_check() or "chưa kết nối")
    args = args or {}
    try:
        limit = max(500, min(20000, int(args.get("max_chars") or 6000)))
    except (TypeError, ValueError):
        limit = 6000
    page, url, _ua, err = await _fetch(ck, "/")
    if err:
        return err
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
    home, _url, ua, err = await _fetch(ck, "/")
    if err:
        return err
    action, fields, ta = _find_form(home, ["xc_message", "status", "text"])
    if not action or not ta:
        return ("ERROR: Không tìm thấy ô soạn bài trên mbasic (Facebook có thể đã đổi/đóng mbasic). "
                "Cần chỉnh lại selector trong plugin fb-personal.")
    try:
        async with _client(ck, ua) as c:
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
    page, _url, ua, err = await _fetch(ck, post)
    if err:
        return err
    action, fields, ta = _find_form(page, ["comment_text", "comment"])
    if not action or not ta:
        return ("ERROR: Không tìm thấy ô bình luận trên bài này (mbasic đổi/đóng, hoặc bài không cho "
                "bình luận). Cần chỉnh lại selector trong plugin fb-personal.")
    try:
        async with _client(ck, ua) as c:
            _res, rurl = await _post(c, action, {**fields, ta: msg})
    except Exception as e:
        return f"ERROR: bình luận lỗi ({type(e).__name__}: {e})."
    if _blocked(rurl):
        return "ERROR: Bị chặn khi bình luận (login/checkpoint)."
    return json.dumps({"ok": True, "action": "comment",
                       "note": "Đã gửi bình luận. Kiểm tra lại bài để chắc chắn."}, ensure_ascii=False)


# ---- Bóc dữ liệu HTML (BEST-EFFORT: chỉnh khi Facebook đổi mbasic) ----
def _fb_dtsg(page):
    m = (re.search(r'name="fb_dtsg"\s+value="([^"]+)"', page)
         or re.search(r"name='fb_dtsg'\s+value='([^']+)'", page))
    return m.group(1) if m else ""


def _find_form(page, textarea_names):
    """Tìm <form> chứa <textarea name=...> khớp một trong textarea_names.
    Trả (action, hidden_dict, ta_name) hoặc (None, {}, None)."""
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
