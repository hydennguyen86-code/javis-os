"""Plugin bundled: quản lý Trang/Fanpage Facebook qua Graph API.

Gọi THẲNG graph.facebook.com bằng user access token của kết nối "facebook-pages" (BYO app -
user tự tạo Facebook App, OAuth do oauth_mcp lo, token tự gia hạn ~60 ngày). Đọc danh sách Trang
qua /me/accounts, mỗi Trang có access_token RIÊNG - mọi thao tác trên một Trang (đăng bài, đọc/
trả lời bình luận) đều dùng token của chính Trang đó, KHÔNG dùng token cá nhân.

Tool đọc (fb_pages_list/fb_page_posts/fb_page_comments) = readonly. Tool ghi công khai
(fb_page_post/fb_page_reply) = min_mode full → không bao giờ tự chạy ở chế độ suggest/auto,
phải mức Toàn quyền + kết nối đã ở mức đó.
"""
from __future__ import annotations

import json

GRAPH = "https://graph.facebook.com/v25.0"
CONNECTOR_ID = "facebook-pages"


def _connected_id():
    """id kết nối facebook-pages ĐÃ đăng nhập (None nếu chưa). Import lười để load không phụ thuộc."""
    try:
        import mcp_store
        import oauth_mcp
    except Exception:
        return None
    for c in mcp_store.list_connections():
        if c.get("connector_id") == CONNECTOR_ID and oauth_mcp.status(c["id"]).get("connected"):
            return c["id"]
    return None


def _check():
    if not _connected_id():
        return ("Chưa kết nối Facebook Trang. Vào trang Kết nối, chọn 'Facebook Trang (tự tạo app - "
                "Graph API)', làm theo hướng dẫn tạo Facebook App rồi đăng nhập (nhớ tick chọn Trang). "
                "Sau đó gọi lại tool này.")
    return None


async def _token():
    import oauth_mcp
    cid = _connected_id()
    if not cid:
        return None
    hdr = await oauth_mcp.auth_headers(cid)      # tự refresh token ~60 ngày khi sắp hết hạn
    return (hdr.get("Authorization", "") or "").replace("Bearer ", "").strip() or None


async def _get(path, params, token):
    import httpx
    try:
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.get(f"{GRAPH}/{str(path).lstrip('/')}",
                            params={**(params or {}), "access_token": token})
        try:
            return r.json()
        except Exception:
            return {"error": {"message": f"HTTP {r.status_code}: {r.text[:200]}"}}
    except Exception as e:
        return {"error": {"message": f"{type(e).__name__}: {e}"}}


async def _post(path, data, token):
    import httpx
    try:
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.post(f"{GRAPH}/{str(path).lstrip('/')}",
                             data={**(data or {}), "access_token": token})
        try:
            return r.json()
        except Exception:
            return {"error": {"message": f"HTTP {r.status_code}: {r.text[:200]}"}}
    except Exception as e:
        return {"error": {"message": f"{type(e).__name__}: {e}"}}


def _fmt(d):
    if isinstance(d, dict) and d.get("error"):
        e = d["error"]
        return "ERROR: Facebook API: " + (e.get("message") if isinstance(e, dict) else str(e))
    return json.dumps(d, ensure_ascii=False, default=str)


async def _pages(user_token):
    """Danh sách Trang user quản lý, mỗi Trang kèm access_token RIÊNG. Trả (list, err)."""
    d = await _get("me/accounts", {"fields": "id,name,category,access_token,tasks", "limit": 200}, user_token)
    if isinstance(d, dict) and d.get("error"):
        return None, _fmt(d)
    return (d or {}).get("data") or [], None


async def _resolve_page(args, user_token):
    """Chọn Trang thao tác. Trả (page_id, page_token, page_name, err).
    - page_id / page (tên) trong args → khớp; nếu bỏ trống mà chỉ có 1 Trang → tự lấy;
    - nhiều Trang mà không chỉ rõ → lỗi kèm danh sách Trang để user chọn."""
    pages, err = await _pages(user_token)
    if err:
        return None, None, None, err
    if not pages:
        return None, None, None, ("ERROR: Không thấy Trang nào bạn quản lý. Kiểm tra: bạn là Admin của Trang, "
                                  "và khi đăng nhập Facebook đã TICK chọn Trang đó cho app.")
    ref = str((args or {}).get("page_id") or (args or {}).get("page") or "").strip()
    if ref:
        rl = ref.lower()
        for p in pages:
            if str(p.get("id")) == ref or rl in str(p.get("name", "")).lower():
                return p.get("id"), p.get("access_token"), p.get("name"), None
        avail = ", ".join(f"{p.get('name')} ({p.get('id')})" for p in pages)
        return None, None, None, f"ERROR: Không khớp Trang '{ref}'. Trang bạn có: {avail}"
    if len(pages) == 1:
        p = pages[0]
        return p.get("id"), p.get("access_token"), p.get("name"), None
    avail = ", ".join(f"{p.get('name')} ({p.get('id')})" for p in pages)
    return None, None, None, f"ERROR: Bạn có nhiều Trang, cần chỉ rõ page_id hoặc page (tên). Trang: {avail}"


async def _list(args, ctx):
    token = await _token()
    if not token:
        return "ERROR: " + (_check() or "chưa kết nối")
    pages, err = await _pages(token)
    if err:
        return err
    # KHÔNG lộ access_token của Trang ra output.
    safe = [{"id": p.get("id"), "name": p.get("name"), "category": p.get("category"),
             "tasks": p.get("tasks")} for p in pages]
    return json.dumps(safe, ensure_ascii=False, default=str)


async def _posts(args, ctx):
    token = await _token()
    if not token:
        return "ERROR: " + (_check() or "chưa kết nối")
    pid, ptok, pname, err = await _resolve_page(args, token)
    if err:
        return err
    args = args or {}
    try:
        limit = max(1, min(100, int(args.get("limit") or 10)))
    except (TypeError, ValueError):
        limit = 10
    d = await _get(f"{pid}/feed",
                   {"fields": "id,message,story,created_time,permalink_url,comments.summary(true).limit(0)",
                    "limit": limit}, ptok)
    return _fmt(d)


async def _comments(args, ctx):
    token = await _token()
    if not token:
        return "ERROR: " + (_check() or "chưa kết nối")
    args = args or {}
    obj = str(args.get("post_id") or args.get("object_id") or "").strip()
    if not obj:
        return "ERROR: thiếu 'post_id' (id bài cần đọc bình luận; lấy từ fb_page_posts)."
    # post_id dạng {pageid}_{postid}: tự suy Trang khi user không chỉ rõ.
    if not (args.get("page_id") or args.get("page")) and "_" in obj:
        args = {**args, "page_id": obj.split("_", 1)[0]}
    pid, ptok, pname, err = await _resolve_page(args, token)
    if err:
        return err
    try:
        limit = max(1, min(100, int(args.get("limit") or 25)))
    except (TypeError, ValueError):
        limit = 25
    d = await _get(f"{obj}/comments",
                   {"fields": "id,from,message,created_time,like_count",
                    "order": "reverse_chronological", "limit": limit}, ptok)
    return _fmt(d)


async def _publish(args, ctx):
    token = await _token()
    if not token:
        return "ERROR: " + (_check() or "chưa kết nối")
    args = args or {}
    msg = str(args.get("message") or "").strip()
    link = str(args.get("link") or "").strip()
    if not msg and not link:
        return "ERROR: cần 'message' (nội dung bài) hoặc 'link'."
    pid, ptok, pname, err = await _resolve_page(args, token)
    if err:
        return err
    data = {}
    if msg:
        data["message"] = msg
    if link:
        data["link"] = link
    d = await _post(f"{pid}/feed", data, ptok)
    if isinstance(d, dict) and d.get("error"):
        return _fmt(d)
    return json.dumps({"ok": True, "page": pname,
                       "post_id": d.get("id") if isinstance(d, dict) else None},
                      ensure_ascii=False, default=str)


async def _reply(args, ctx):
    token = await _token()
    if not token:
        return "ERROR: " + (_check() or "chưa kết nối")
    args = args or {}
    target = str(args.get("comment_id") or args.get("object_id") or args.get("post_id") or "").strip()
    msg = str(args.get("message") or "").strip()
    if not target:
        return "ERROR: thiếu 'comment_id' (bình luận cần trả lời) hoặc 'post_id' (để bình luận vào bài)."
    if not msg:
        return "ERROR: thiếu 'message' (nội dung trả lời)."
    pid, ptok, pname, err = await _resolve_page(args, token)
    if err:
        return err
    d = await _post(f"{target}/comments", {"message": msg}, ptok)
    if isinstance(d, dict) and d.get("error"):
        return _fmt(d)
    return json.dumps({"ok": True, "page": pname,
                       "reply_id": d.get("id") if isinstance(d, dict) else None},
                      ensure_ascii=False, default=str)


def register(ctx):
    ctx.register_tool(
        name="fb_pages_list", min_mode="readonly", check_fn=_check, handler=_list,
        description=("Liệt kê các Trang/Fanpage Facebook bạn quản lý (id, tên, hạng mục, quyền). Gọi đầu "
                     "tiên để lấy id/tên Trang cho các tool khác. KHÔNG lộ token của Trang."),
        schema={"type": "object", "properties": {}},
    )
    ctx.register_tool(
        name="fb_page_posts", min_mode="readonly", check_fn=_check, handler=_posts,
        description=("Đọc các bài GẦN ĐÂY trên một Trang của bạn (id bài, nội dung, thời gian, link, số bình "
                     "luận). Bỏ trống page nếu chỉ có 1 Trang; nhiều Trang thì truyền page_id hoặc page (tên)."),
        schema={"type": "object", "properties": {
            "page_id": {"type": "string", "description": "id Trang (bỏ trống nếu chỉ có 1 Trang)"},
            "page": {"type": "string", "description": "tên Trang (thay cho page_id)"},
            "limit": {"type": "integer", "description": "Số bài tối đa (mặc định 10)"}}},
    )
    ctx.register_tool(
        name="fb_page_comments", min_mode="readonly", check_fn=_check, handler=_comments,
        description=("Đọc bình luận của MỘT bài trên Trang (người bình luận, nội dung, thời gian). Cần post_id "
                     "lấy từ fb_page_posts. Trang tự suy từ post_id; nhiều Trang thì truyền thêm page_id/page nếu cần."),
        schema={"type": "object", "properties": {
            "post_id": {"type": "string", "description": "id bài cần đọc bình luận (từ fb_page_posts)"},
            "page_id": {"type": "string", "description": "id Trang (thường không cần, suy từ post_id)"},
            "page": {"type": "string", "description": "tên Trang (tuỳ chọn)"},
            "limit": {"type": "integer", "description": "Số bình luận tối đa (mặc định 25)"}},
            "required": ["post_id"]},
    )
    ctx.register_tool(
        name="fb_page_post", min_mode="full", check_fn=_check, handler=_publish,
        description=("ĐĂNG một bài lên Trang của bạn - hành động THẬT, công khai. Cần message (nội dung) và/hoặc "
                     "link. Bỏ trống page nếu chỉ có 1 Trang; nhiều Trang thì truyền page_id/page."),
        schema={"type": "object", "properties": {
            "message": {"type": "string", "description": "Nội dung bài đăng"},
            "link": {"type": "string", "description": "Link đính kèm (tuỳ chọn)"},
            "page_id": {"type": "string", "description": "id Trang (bỏ trống nếu chỉ có 1 Trang)"},
            "page": {"type": "string", "description": "tên Trang (thay cho page_id)"}}},
    )
    ctx.register_tool(
        name="fb_page_reply", min_mode="full", check_fn=_check, handler=_reply,
        description=("TRẢ LỜI một bình luận, hoặc bình luận vào một bài - hành động THẬT, công khai. Cần message "
                     "và comment_id (trả lời bình luận) HOẶC post_id (bình luận vào bài). Nhiều Trang thì truyền "
                     "page_id/page."),
        schema={"type": "object", "properties": {
            "message": {"type": "string", "description": "Nội dung trả lời"},
            "comment_id": {"type": "string", "description": "id bình luận cần trả lời"},
            "post_id": {"type": "string", "description": "id bài (bình luận thẳng vào bài thay vì trả lời 1 comment)"},
            "page_id": {"type": "string", "description": "id Trang (khi có nhiều Trang)"},
            "page": {"type": "string", "description": "tên Trang (khi có nhiều Trang)"}},
            "required": ["message"]},
    )
