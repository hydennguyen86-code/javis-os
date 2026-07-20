"""Plugin bundled: gửi tin Zalo AN TOÀN theo yêu cầu chủ trong chat.

Vá lỗi gửi nhầm người (Minh Quý -> Đặng Vũ). Xem điều tra: workflow trace ngày 2026-07-20.

Gốc lỗi cũ: khi bật nghe tài khoản "Javis Vũ", listener tự tắt connector Zalo của tài khoản
đó, nên engine dùng tool Zalo THÔ (zalo_send_message) lại lặng lẽ rơi sang connector Zalo
KHÁC đang bật, tra tên trong danh bạ tài khoản sai rồi gửi nhầm - không có bước xác nhận.

Tool này thay tool thô: gọi thẳng zalo_listener.send_from_chat() - khoá CỨNG bằng cấu trúc:
  1. Luôn gửi TỪ tài khoản đang nghe (không rơi sang tài khoản khác).
  2. Người nhận PHẢI nằm trong danh sách cuộc chat đang theo dõi -> không thể ra người lạ.
  3. Tên khớp nhiều thì TỪ CHỐI, bắt hỏi lại - không đoán.

min_mode: safe -> loop nền (readonly/suggest) KHÔNG gọi được; chỉ chủ yêu cầu trực tiếp
trong chat (mode full) mới gửi. Đúng nguyên tắc "Javis chỉ gửi khi chủ yêu cầu trực tiếp".
"""
from __future__ import annotations


async def _handler(args, ctx):
    args = args or {}
    thread = str(args.get("thread") or "").strip()
    text = str(args.get("text") or "").strip()
    if not thread:
        return "ERROR: thiếu 'thread' (tên cuộc chat hoặc thread_id đang theo dõi)."
    if not text:
        return "ERROR: thiếu 'text' (nội dung tin cần gửi)."
    try:
        import main
        res = await main.zalo_listener_feature.send_from_chat(thread, text)
    except Exception as e:
        return f"ERROR: không gửi được ({type(e).__name__}: {e})."
    if not res.get("ok"):
        return "ERROR: " + str(res.get("error") or "gửi không được")
    return f"Đã gửi cho {res.get('sent_to')} (thread {res.get('thread_id')})."


def register(ctx):
    ctx.register_tool(
        name="javis_zalo_send",
        description=(
            "Gửi tin nhắn Zalo cho MỘT cuộc chat mà Javis ĐANG NGHE. DÙNG TOOL NÀY thay vì "
            "tool zalo_send_message thô - tool thô có thể gửi nhầm tài khoản/nhầm người. "
            "Tool này khoá cứng vào tài khoản đang nghe và chỉ gửi được cho cuộc chat trong "
            "danh sách đang theo dõi, nên an toàn. "
            "thread = TÊN cuộc chat (vd 'Minh Quý') hoặc thread_id. Khớp nhiều hơn một thì "
            "tool báo lỗi kèm danh sách - phải hỏi lại chủ đúng cái nào, ĐỪNG đoán. Không có "
            "trong danh sách theo dõi thì tool từ chối. text = nội dung tin."
        ),
        handler=_handler, min_mode="safe",
        schema={
            "type": "object",
            "properties": {
                "thread": {"type": "string", "description": "Tên cuộc chat đang nghe hoặc thread_id"},
                "text": {"type": "string", "description": "Nội dung tin gửi"},
            },
            "required": ["thread", "text"],
        },
    )
