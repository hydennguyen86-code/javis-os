"""
zalo_rules.py - Chính sách theo TỪNG cuộc chat Zalo.

Thay cho bộ lọc thông báo toàn cục của bản listener đầu: mỗi cuộc chat một file luật
`<brain>/Javis/zalo/<slug>.md`, đặt bằng lời qua chat, giao diện chỉ hiển thị.
Nhất quán với loop/agent/skill (đều là .md do chat sinh ra), có git nên lần lại được.

Bốn chế độ:
    im-lang    chỉ ghi nhận, không báo
    bao-het    mọi tin đều báo Telegram
    tu-khoa    báo khi tin chứa từ khoá
    nhac-quen  khách nhắn mà quá N phút không ai đáp thì báo

KHÔNG chế độ nào gọi engine đọc nội dung khách: cả bốn chỉ báo về Telegram cho chủ, nên
nội dung do người lạ soạn KHÔNG bao giờ chạm engine. Javis KHÔNG tự trả lời khách trên
Zalo - mọi tin gửi đi đều do chủ yêu cầu trực tiếp (xem zalo_listener.send_from_chat).

Module này CỐ Ý chỉ có hàm thuần + đọc ghi file: không engine, không mạng, không MCP.
"""
from __future__ import annotations

import os
import re
import time
import unicodedata
from pathlib import Path

import skill_router   # dùng lại split_frontmatter, khỏi đẻ thêm một bộ bóc YAML nữa

MODES = ("im-lang", "bao-het", "tu-khoa", "nhac-quen")
DEFAULT_MODE = "im-lang"
MAX_SCRIPT = 8000          # trần độ dài phần thân file luật (chú thích chủ ghi tay)

# Hành động trả về từ decide()
BO, BAO, CHO = "bo", "bao", "cho"


def _fold(s) -> str:
    """Bỏ dấu + hạ chữ thường: khách gõ 'gia' vẫn khớp từ khoá 'giá'."""
    s = unicodedata.normalize("NFD", str(s or ""))
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    return s.replace("đ", "d").replace("Đ", "D").lower()


def slugify(s) -> str:
    s = _fold(s)
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s[:48] or "cuoc-chat"


def rules_dir(brain_root) -> Path:
    return Path(brain_root) / "Javis" / "zalo"


# ============================================================
# Đọc / ghi file luật
# ============================================================
def _norm(meta: dict, body: str, path=None) -> dict:
    mode = str(meta.get("mode") or DEFAULT_MODE).strip()
    if mode not in MODES:
        mode = DEFAULT_MODE
    kws = meta.get("keywords") or []
    if isinstance(kws, str):
        kws = [k.strip() for k in kws.split(",")]
    try:
        after = int(meta.get("escalate_after_min") or 30)
    except (TypeError, ValueError):
        after = 30
    return {
        "thread_id": str(meta.get("thread_id") or "").strip(),
        "thread_name": str(meta.get("thread_name") or "").strip(),
        # Loại nhóm/khách, để dựng đúng nhãn "(nhóm)" và gửi đúng thread_type kể cả sau khi
        # khởi động lại (lúc sổ cuộc chat còn rỗng, chưa học lại được từ webhook).
        "thread_type": str(meta.get("thread_type") or "").strip(),
        "mode": mode,
        "enabled": bool(meta.get("enabled")),
        "keywords": [str(k).strip() for k in kws if str(k).strip()],
        "escalate_after_min": max(1, after),
        "owner_uid": str(meta.get("owner_uid") or "").strip(),
        "updated": str(meta.get("updated") or ""),
        "script": (body or "").strip()[:MAX_SCRIPT],
        "path": str(path or ""),
        "slug": Path(path).stem if path else "",
    }


def parse_rule(text: str, path=None) -> dict:
    meta, body = skill_router.split_frontmatter(text or "")
    return _norm(meta if isinstance(meta, dict) else {}, body, path)


def dump_rule(rule: dict) -> str:
    """Sinh lại file .md. Kịch bản nằm ở THÂN file, không nhét vào frontmatter (nó dài
    và nhiều dòng, nhồi vào YAML là hỏng)."""
    def q(v):
        return '"' + str(v).replace('"', "'") + '"'
    lines = ["---", "type: zalo-rule",
             f"thread_id: {q(rule.get('thread_id', ''))}",
             f"thread_name: {q(rule.get('thread_name', ''))}"]
    if rule.get("thread_type"):
        lines.append(f"thread_type: {rule.get('thread_type')}")
    lines += [f"mode: {rule.get('mode') or DEFAULT_MODE}",
              f"enabled: {'true' if rule.get('enabled') else 'false'}"]
    if rule.get("keywords"):
        lines.append("keywords: [" + ", ".join(q(k) for k in rule["keywords"]) + "]")
    if rule.get("mode") == "nhac-quen":
        lines.append(f"escalate_after_min: {rule.get('escalate_after_min') or 30}")
    if rule.get("owner_uid"):
        lines.append(f"owner_uid: {q(rule['owner_uid'])}")
    lines += [f"updated: {rule.get('updated') or time.strftime('%Y-%m-%d')}", "---", "",
              (rule.get("script") or "").strip(), ""]
    return "\n".join(lines)


def list_rules(brain_root) -> list:
    d = rules_dir(brain_root)
    out = []
    try:
        files = sorted(d.glob("*.md"))
    except OSError:
        return out
    for f in files:
        try:
            out.append(parse_rule(f.read_text(encoding="utf-8", errors="replace"), f))
        except OSError:
            continue
    return out


def slug_for(rule: dict) -> str:
    """Tên file DUY NHẤT theo thread_id, để hai cuộc chat TRÙNG TÊN không ghi đè lên nhau.

    Sổ cuộc chat CỐ Ý đặt tên trùng cho nhóm chưa biết tên (lấy tên người gửi gần nhất), nên
    nếu chỉ slug theo tên thì hai nhóm khác nhau cùng ghi vào MỘT file - lưu cái sau xoá mất
    luật cái trước, và tick của nó biến mất khi tải lại. Gắn thẳng thread_id vào tên file để
    ánh xạ 1-1 với thread_id. Cắt phần tên ngắn lại rồi mới nối id, để id không bị cắt cụt."""
    tid = re.sub(r"[^a-z0-9]+", "-", str(rule.get("thread_id") or "").lower()).strip("-")
    nm = slugify(rule.get("thread_name") or "")[:32]
    if tid:
        return (nm + "-" + tid).strip("-") if nm else tid
    return nm or "cuoc-chat"


def save_rule(brain_root, rule: dict) -> str:
    d = rules_dir(brain_root)
    d.mkdir(parents=True, exist_ok=True)
    slug = rule.get("slug") or slug_for(rule)
    p = d / f"{slug}.md"
    # Tên tạm kèm pid để hai lần lưu đồng thời (chủ tick nhanh) không giẫm lên tmp của nhau.
    tmp = d / f".{slug}.{os.getpid()}.md.tmp"
    tmp.write_text(dump_rule(rule), encoding="utf-8")
    os.replace(tmp, p)     # ghi nguyên tử: đọc giữa chừng không bao giờ thấy file cụt
    return str(p)


def rule_for(rules: list, thread_id: str):
    tid = str(thread_id or "")
    return next((r for r in rules if r.get("thread_id") == tid), None) if tid else None


def match_threads(candidates: list, query: str) -> list:
    """Khớp cuộc chat theo TÊN (chủ nói 'nhóm Kim Khí' chứ không đọc id bao giờ).

    Trả về DANH SÁCH ứng viên. Người gọi phải tự xử khi có nhiều hơn một: đoán bừa là
    gắn kịch bản nhầm nhóm rồi bot đi trả lời khách của nhóm khác.
    candidates: [{id, name}] (sổ cuộc chat đã thấy hoặc luật đang có).
    """
    q = _fold(query).strip()
    if not q:
        return []
    exact_id = [c for c in candidates if str(c.get("id")) == str(query).strip()]
    if exact_id:
        return exact_id
    exact = [c for c in candidates if _fold(c.get("name")) == q]
    if exact:
        return exact
    return [c for c in candidates if q in _fold(c.get("name"))]


# ============================================================
# Quyết định (thuần)
# ============================================================
def decide(rule: dict, ev: dict) -> tuple:
    """Sự kiện này thì làm gì. Trả (hành_động, lý_do_bỏ).

    Không đụng giờ im lặng ở đây - cái đó áp lúc SẮP báo Telegram, để mốc chờ của
    nhac-quen vẫn cập nhật trong giờ im lặng (im lặng chỉ là hoãn báo cho CHỦ ngủ).
    """
    if not rule:
        return BO, "chưa có luật cho cuộc chat này"
    if not rule.get("enabled"):
        return BO, "luật đang tắt"
    kind = str(ev.get("kind") or "message").lower()
    if "message" not in kind or kind.startswith("old") or "seen" in kind or "delivered" in kind:
        return BO, "không phải tin nhắn"
    if ev.get("is_self"):
        return BO, "tin của chính tài khoản Javis"
    mode = rule.get("mode")
    if mode == "bao-het":
        return BAO, ""
    if mode == "tu-khoa":
        kws = rule.get("keywords") or []
        if not kws:
            return BAO, ""
        body = _fold(ev.get("text"))
        return (BAO, "") if any(_fold(k) in body for k in kws) else (BO, "không khớp từ khoá")
    if mode == "nhac-quen":
        return CHO, ""
    return BO, "chế độ im lặng"


def pending_action(rule: dict, ev: dict) -> str:
    """Chế độ nhac-quen: sự kiện này ĐẶT mốc chờ hay XOÁ mốc. Trả 'dat' | 'xoa' | ''.

    Chủ trả lời khách bằng TÀI KHOẢN RIÊNG của mình, nên trong nhóm chủ là một thành
    viên khác và tin của chủ về đầy đủ qua webhook - đó là cách biết chủ đã trả lời.
    """
    if not rule or rule.get("mode") != "nhac-quen" or not rule.get("enabled"):
        return ""
    if ev.get("is_self"):
        return ""
    owner = rule.get("owner_uid")
    if owner and str(ev.get("sender_uid") or "") == str(owner):
        return "xoa"
    return "dat"


def due_reminders(rules: list, pending: dict, now=None) -> list:
    """Mốc chờ nào đã quá hạn. Trả [(thread_id, rule, moc)]. Người gọi tự xoá mốc sau
    khi báo - báo một lần rồi thôi, không nhắc lặp mỗi nhịp."""
    now = time.time() if now is None else float(now)
    out = []
    for tid, p in list(pending.items()):
        r = rule_for(rules, tid)
        if not r or r.get("mode") != "nhac-quen" or not r.get("enabled"):
            continue
        if now - float(p.get("since") or 0) >= r["escalate_after_min"] * 60:
            out.append((tid, r, p))
    return out
