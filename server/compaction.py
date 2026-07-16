"""
Nén hội thoại dài cho engine API (openrouter / openai / anthropic-api / gemini).

Vấn đề: engine API resend toàn bộ lịch sử mỗi lượt. Trước đây _trim_history chỉ CẮT BỎ
phần cũ quá cửa sổ 12 message - model quên sạch những gì đã bàn trước đó trong phiên dài.

Cách nén (port ý tưởng session_memory_compaction của anthropics/claude-cookbooks):
- Sau mỗi lượt, nếu phần lịch sử NẰM NGOÀI cửa sổ mà chưa được nén đủ lớn (>= MIN_CHUNK
  message) → gọi nền 1 request tóm tắt GỘP (tóm tắt cũ + đoạn mới → tóm tắt mới),
  lưu vào sessions.compact_summary + compact_count (số message đầu đã phủ).
- Lượt sau seed lại lịch sử: bỏ qua compact_count message đầu, chèn tóm tắt làm system
  message thứ 2 → model vẫn "nhớ" mạch cũ mà payload không phình.
- Engine CLI (Claude Code) tự quản context nên KHÔNG đi qua đây.
"""
import sys

MAX_HISTORY_MSGS = 12   # cửa sổ message gần nhất giữ NGUYÊN VẸN (≈6 lượt hỏi-đáp)
MIN_CHUNK = 6           # phần cũ chưa nén phải >= N message mới đáng tốn 1 request tóm tắt
MAX_SUMMARY_CHARS = 6000
_MSG_CLIP = 1500        # mỗi message đưa vào prompt tóm tắt cắt còn ~1500 ký tự
# Đuôi hội thoại CHƯA nén dài quá ngưỡng này → nén ĐỒNG BỘ ngay trong lượt trước khi gửi,
# để phần cũ vào tóm tắt thay vì bị cắt câm. Hay xảy ra khi đổi từ engine Claude (CLI - không
# tạo tóm tắt) sang engine API giữa chừng, hoặc nén nền chưa kịp bắt đầu.
SYNC_COMPACT_TAIL = 24

SUMMARY_HEADER = ("[Tóm tắt phần đầu hội thoại - đã nén để tiết kiệm context. "
                  "Coi đây là ký ức về những gì hai bên đã trao đổi trước đó:]\n")


def trim_history(messages, max_msgs: int = MAX_HISTORY_MSGS):
    """Giữ RUN system message dẫn đầu (system prompt + tóm tắt nén) + max_msgs message
    gần nhất. Bỏ assistant dẫn đầu phần tail vì Anthropic yêu cầu message đầu (sau system)
    phải là role=user. Trả về list mới; không mutate input."""
    if not messages:
        return messages
    n_head = 0
    while n_head < len(messages) and messages[n_head].get("role") == "system":
        n_head += 1
    if len(messages) - n_head <= max_msgs:
        return messages
    head = messages[:n_head]
    tail = messages[len(messages) - max_msgs:]
    while tail and tail[0].get("role") == "assistant":
        tail = tail[1:]
    return head + tail


def seed_messages(store, conv_sid, raw_msgs):
    """Lịch sử để seed lại 1 lượt chat: phần đầu đã nén thay bằng tóm tắt (system message).
    raw_msgs = list {role, content} user/assistant theo thứ tự thời gian (đã lọc rỗng)."""
    sess = store.get_session(conv_sid) or {}
    summary = (sess.get("compact_summary") or "").strip()
    count = int(sess.get("compact_count") or 0)
    if not summary or count <= 0:
        return raw_msgs
    tail = raw_msgs[count:] if count < len(raw_msgs) else []
    return [{"role": "system", "content": SUMMARY_HEADER + summary}] + tail


async def prepare_history(head, store, conv_sid, raw_msgs, prov, api_key, model, api_stream,
                          keep: int = MAX_HISTORY_MSGS, sync_tail: int = SYNC_COMPACT_TAIL):
    """Ghép payload lịch sử cho 1 lượt engine API mà KHÔNG bao giờ bỏ CÂM ngữ cảnh.

    head = các system message dẫn đầu (system prompt + dòng khai model). raw_msgs = lịch sử
    user/assistant theo thứ tự thời gian, ĐÃ bỏ câu user hiện tại (lượt gọi sẽ tự append sau).

    Trả về: head + [tóm tắt nén nếu có] + đuôi hội thoại CHƯA nén. Khác trim_history cũ (giữ
    cứng 12 message gần nhất, CẮT BỎ phần cũ hơn kể cả khi chưa có tóm tắt → mất trí nhớ khi
    phiên dài hoặc vừa đổi từ engine Claude/CLI sang API): ở đây phần cũ CHỈ rời payload khi
    đã nằm trong tóm tắt. Nếu đuôi chưa nén quá dài thì nén ĐỒNG BỘ ngay (1 request, chặn lượt
    một nhịp) để gấp phần cũ vào tóm tắt trước khi gửi - hiếm khi chạm, chủ yếu ở lượt API đầu
    tiên sau một mạch chat bằng Claude Code."""
    sess = store.get_session(conv_sid) or {}
    count = int(sess.get("compact_count") or 0)
    uncompacted = max(0, len(raw_msgs) - count)
    if uncompacted > sync_tail:
        # min_chunk=1: buộc nén ngay cả phần cũ nhỏ, miễn có gì để gấp vào tóm tắt.
        await maybe_compact(store, conv_sid, prov, api_key, model, api_stream,
                            keep=keep, min_chunk=1)
    return list(head) + seed_messages(store, conv_sid, raw_msgs)


async def _summarize(old, chunk, prov, api_key, model, api_stream):
    """Gọi provider tóm tắt GỘP `old` (tóm tắt cũ, có thể rỗng) + `chunk` (list message
    user/assistant) → chuỗi tóm tắt mới (đã strip + clip MAX_SUMMARY_CHARS).
    Trả '' nếu provider lỗi hoặc ra rỗng - caller tự quyết fallback."""
    lines = []
    for m in chunk:
        c = m.get("content") or ""
        if len(c) > _MSG_CLIP:
            c = c[:_MSG_CLIP] + " (...)"
        lines.append(("User: " if m.get("role") == "user" else "Javis: ") + c)
    prompt = (
        "Bạn đang nén lịch sử hội thoại giữa User và trợ lý Javis để tiết kiệm context.\n\n"
        f"TÓM TẮT HIỆN CÓ (các phần trước đó nữa):\n{old or '(chưa có)'}\n\n"
        "ĐOẠN HỘI THOẠI MỚI CẦN GỘP THÊM:\n" + "\n\n".join(lines) + "\n\n"
        "Viết TÓM TẮT MỚI gộp cả hai (tối đa ~350 từ), giữ lại: chủ đề chính, quyết định đã chốt, "
        "con số/tên riêng/đường dẫn quan trọng, việc đang dang dở, sở thích hay yêu cầu User đã nêu. "
        "Bỏ chào hỏi xã giao. Viết gọn dạng gạch đầu dòng '- '. CHỈ in tóm tắt, không mở bài."
    )
    text = ""
    async for ev in api_stream(prov, api_key, model, [{"role": "user", "content": prompt}], "off"):
        t = ev.get("type")
        if t == "text":
            text += ev.get("content") or ""
        elif t == "error":
            print(f"[compact] provider lỗi: {ev.get('content')}", file=sys.stderr)
            return ""
    return text.strip()[:MAX_SUMMARY_CHARS]


async def maybe_compact(store, conv_sid, prov, api_key, model, api_stream,
                        keep: int = MAX_HISTORY_MSGS, min_chunk: int = MIN_CHUNK):
    """Chạy NỀN sau 1 lượt chat: nén phần lịch sử cũ sắp rơi khỏi cửa sổ vào compact_summary.
    api_stream = main._api_stream (inject để test không cần mạng). Trả True nếu có nén.
    Lỗi ở đây KHÔNG được phá lượt chat - nuốt + log, lượt sau còn nguyên fallback trim."""
    try:
        msgs = [m for m in store.get_messages(conv_sid)
                if m.get("role") in ("user", "assistant") and (m.get("content") or "").strip()]
        sess = store.get_session(conv_sid) or {}
        count = int(sess.get("compact_count") or 0)
        old = (sess.get("compact_summary") or "").strip()
        cut = len(msgs) - keep
        if cut - count < min_chunk:
            return False
        text = await _summarize(old, msgs[count:cut], prov, api_key, model, api_stream)
        if not text:
            return False
        store.set_compact(conv_sid, text, cut)
        return True
    except Exception as e:
        print(f"[compact] {type(e).__name__}: {e}", file=sys.stderr)
        return False


def _split_mem(msgs):
    """Tách list lịch sử IN-MEMORY thành (head, prev_summary, convo):
      head        = các system message CỐ ĐỊNH dẫn đầu (system prompt + dòng khai model),
      prev_summary= nội dung system 'tóm tắt nén' cũ nếu có (đã bỏ SUMMARY_HEADER),
      convo       = message user/assistant còn nội dung, theo thứ tự thời gian.
    Phân biệt system tóm tắt với system cố định bằng SUMMARY_HEADER ở đầu content."""
    head, prev_summary, i = [], "", 0
    while i < len(msgs) and msgs[i].get("role") == "system":
        c = msgs[i].get("content") or ""
        if c.startswith(SUMMARY_HEADER):
            prev_summary = c[len(SUMMARY_HEADER):].strip()
        else:
            head.append(msgs[i])
        i += 1
    convo = [m for m in msgs[i:]
             if m.get("role") in ("user", "assistant") and (m.get("content") or "").strip()]
    return head, prev_summary, convo


async def compact_mem(msgs, prov, api_key, model, api_stream,
                      keep: int = MAX_HISTORY_MSGS, min_chunk: int = MIN_CHUNK):
    """Nén danh sách lịch sử GIỮ TRONG RAM - dành cho phiên Telegram (giữ sess['or'] in-memory,
    KHÔNG rebuild từ SQLite mỗi lượt như dashboard). Thay cho trim_history cứng: phần cũ rơi
    khỏi cửa sổ được TÓM TẮT (gộp cả tóm tắt cũ) rồi chèn làm system message ngay sau phần đầu,
    thay vì bị CẮT CÂM - phiên Telegram dài / vừa đổi từ engine Claude sang API không còn mất
    trí nhớ phần đầu (cùng lớp lỗi đã vá cho dashboard).

    msgs vào/ra cùng dạng: [system cố định...] (+ [system tóm tắt cũ]) + user/assistant...
    Trả về LIST MỚI (không mutate input). Chưa đủ phần cũ để đáng 1 request tóm tắt → giữ
    nguyên. Nén hỏng (provider lỗi) → fallback trim_history để payload vẫn bị chặn kích thước."""
    try:
        head, prev_summary, convo = _split_mem(msgs)
        cut = len(convo) - keep
        if cut < min_chunk:
            return list(msgs)
        new_summary = await _summarize(prev_summary, convo[:cut], prov, api_key, model, api_stream)
        if not new_summary:
            return trim_history(msgs, keep)
        tail = convo[cut:]
        while tail and tail[0].get("role") == "assistant":
            tail = tail[1:]   # message đầu sau system phải là user (yêu cầu Anthropic)
        summary_msg = {"role": "system", "content": SUMMARY_HEADER + new_summary}
        return list(head) + [summary_msg] + tail
    except Exception as e:
        print(f"[compact_mem] {type(e).__name__}: {e}", file=sys.stderr)
        return trim_history(msgs, keep)
