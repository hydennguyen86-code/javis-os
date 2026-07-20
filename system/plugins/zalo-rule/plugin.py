"""Plugin bundled: đặt LUẬT cho từng cuộc chat Zalo ngay từ chat.

Chủ nói bằng lời ("nhóm Kim Khí, 30 phút anh chưa trả lời thì nhắc anh"), engine gọi
tool này, tool ghi ra `<brain>/Javis/zalo/<slug>.md`. Giao diện trang Kết nối chỉ HIỂN
THỊ luật, không có form nhập - đúng như chủ yêu cầu.

Nhất quán với cách loop/agent/skill được tạo: đều là file .md do chat sinh ra, nằm trong
brain nên có git, sửa tay được.

An toàn: cả bốn chế độ đều chỉ BÁO về Telegram cho chủ, không tự nhắn cho khách. Javis
KHÔNG tự trả lời trên Zalo - muốn gửi tin cho khách thì chủ yêu cầu trực tiếp và Javis
dùng tool javis_zalo_send. Sai luật cũng chỉ phiền chủ chứ không lỡ tay nhắn ra ngoài.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "server"))

import zalo_rules as zr   # noqa: E402


def _brain(ctx):
    return getattr(ctx, "vault_root", None) or "."


def _roster():
    """Sổ cuộc chat sidecar đã thấy - để khớp TÊN nhóm chủ nói sang thread_id.

    Listener chạy trong CÙNG tiến trình server nên lấy thẳng được. Chưa bật listener thì
    sổ rỗng, và tool sẽ báo rõ điều đó thay vì im lặng không tìm thấy gì.
    """
    try:
        import main
        return list(main.zalo_listener_feature.roster_list() or [])
    except Exception:
        return []


def _candidates(brain):
    """Ứng viên để khớp tên: sổ cuộc chat đã thấy + các luật đã có."""
    out = {c.get("id"): {"id": c.get("id"), "name": c.get("name")} for c in _roster() if c.get("id")}
    for r in zr.list_rules(brain):
        if r.get("thread_id"):
            out.setdefault(r["thread_id"], {"id": r["thread_id"], "name": r.get("thread_name") or ""})
    return list(out.values())


def _fmt(r):
    bits = [f"{r['thread_name'] or r['thread_id']} [{r['mode']}]",
            "đang chạy" if r["enabled"] else "đang TẮT"]
    if r["mode"] == "tu-khoa" and r["keywords"]:
        bits.append("từ khoá: " + ", ".join(r["keywords"]))
    if r["mode"] == "nhac-quen":
        bits.append(f"nhắc sau {r['escalate_after_min']} phút")
        if not r["owner_uid"]:
            bits.append("CHƯA khai owner_uid nên sẽ nhắc cả khi chủ đã trả lời")
    return " - ".join(bits)


def _handler(args, ctx):
    args = args or {}
    op = str(args.get("op") or "list").strip().lower()
    brain = _brain(ctx)

    if op == "list":
        rules = zr.list_rules(brain)
        if not rules:
            return ("Chưa có luật Zalo nào. Nói cho tôi biết nhóm nào cần làm gì, "
                    "ví dụ: nhóm Kim Khí nếu 30 phút chưa ai trả lời thì nhắc.")
        return "\n".join("- " + _fmt(r) for r in rules)

    thread = str(args.get("thread") or "").strip()
    if not thread:
        return "ERROR: thiếu 'thread' (tên nhóm hoặc thread_id)."

    cands = _candidates(brain)
    hits = zr.match_threads(cands, thread)
    if not hits:
        seen = ", ".join((c.get("name") or c.get("id")) for c in cands[:12]) or "(chưa thấy cuộc chat nào)"
        return (f"ERROR: không tìm thấy cuộc chat nào tên '{thread}'. "
                f"Các cuộc chat đang thấy: {seen}. "
                f"Listener phải đang bật và đã có tin đi qua thì cuộc chat mới hiện ra.")
    if len(hits) > 1:
        ds = "; ".join(f"{h.get('name')} (id {h.get('id')})" for h in hits[:8])
        # KHÔNG đoán: gắn luật nhầm nhóm là báo/im nhầm cuộc chat của chủ.
        return (f"ERROR: '{thread}' khớp {len(hits)} cuộc chat: {ds}. "
                f"Hỏi lại chủ xem là cái nào rồi gọi lại với thread_id chính xác.")
    hit = hits[0]
    rules = zr.list_rules(brain)
    cur = zr.rule_for(rules, hit["id"])

    if op == "show":
        if not cur:
            return f"Cuộc chat '{hit.get('name')}' chưa có luật nào."
        return _fmt(cur)

    if op == "off":
        if not cur:
            return f"Cuộc chat '{hit.get('name')}' vốn chưa có luật, không cần tắt."
        cur["enabled"] = False
        cur["updated"] = time.strftime("%Y-%m-%d")
        zr.save_rule(brain, cur)
        return f"Đã tắt luật cho {cur['thread_name'] or cur['thread_id']}."

    if op != "set":
        return "ERROR: 'op' phải là list | show | set | off."

    mode = str(args.get("mode") or "").strip()
    if mode not in zr.MODES:
        return f"ERROR: 'mode' phải là một trong: {', '.join(zr.MODES)}."

    r = cur or {"thread_id": hit["id"], "thread_name": hit.get("name") or hit["id"],
                "keywords": [], "escalate_after_min": 30, "owner_uid": "", "script": ""}
    r["mode"] = mode
    if args.get("keywords") is not None:
        kw = args["keywords"]
        r["keywords"] = [k.strip() for k in (kw.split(",") if isinstance(kw, str) else kw) if str(k).strip()]
    if args.get("escalate_after_min") is not None:
        try:
            r["escalate_after_min"] = int(args["escalate_after_min"])
        except (TypeError, ValueError):
            return "ERROR: 'escalate_after_min' phải là số."
    if args.get("owner_uid") is not None:
        r["owner_uid"] = str(args["owner_uid"]).strip()

    r["enabled"] = bool(args.get("enabled", True))
    r["updated"] = time.strftime("%Y-%m-%d")
    path = zr.save_rule(brain, r)

    msg = f"Đã đặt luật cho {r['thread_name']}: {_fmt(r)}. Ghi ở {path}."
    if mode == "nhac-quen" and not r["owner_uid"]:
        msg += (" Chưa khai owner_uid nên Javis không biết chủ đã trả lời hay chưa và sẽ "
                "nhắc cả khi chủ đã trả lời rồi. Hỏi chủ tên hiển thị của chủ trong nhóm "
                "để lấy uid rồi đặt lại.")
    return msg


def register(ctx):
    ctx.register_tool(
        name="javis_zalo_rule",
        description=(
            "Đặt luật cho MỘT cuộc chat Zalo (nhóm hoặc khách). GỌI TOOL NÀY, đừng chỉ ghi "
            "vào Memory: ghi nhớ KHÔNG đổi hành vi của listener, phải có file luật thì Javis "
            "mới thật sự im lặng hay báo. Javis chỉ ĐỌC và BÁO trên Zalo, KHÔNG tự trả lời khách. "
            "Gọi khi chủ nói kiểu: 'nhóm X đừng báo telegram nữa' (mode=im-lang), "
            "'im lặng thôi' (im-lang), 'nhóm X báo hết tin cho anh' (bao-het), "
            "'có tin gì về giá thì báo' (tu-khoa + keywords), "
            "'30 phút chưa ai trả lời thì nhắc anh' (nhac-quen). "
            "op=list xem tất cả | op=show xem một | op=set đặt hoặc sửa | op=off tắt. "
            "thread nhận TÊN nhóm hoặc thread_id; khớp nhiều hơn một thì tool báo lỗi kèm "
            "danh sách, phải hỏi lại chủ chứ đừng đoán. "
            "mode: im-lang (chỉ ghi nhận) | bao-het (mọi tin đều báo Telegram) | "
            "tu-khoa (báo khi tin chứa từ khoá) | nhac-quen (nhắc khi quá N phút chưa ai "
            "trả lời). Muốn Javis GỬI tin cho khách thì chủ yêu cầu trực tiếp - dùng tool "
            "javis_zalo_send, KHÔNG có chế độ tự trả lời."
        ),
        handler=_handler, min_mode="safe",
        schema={
            "type": "object",
            "properties": {
                "op": {"type": "string", "enum": ["list", "show", "set", "off"]},
                "thread": {"type": "string", "description": "Tên nhóm hoặc thread_id"},
                "mode": {"type": "string", "enum": list(zr.MODES)},
                "keywords": {"type": "string", "description": "Từ khoá, cách nhau bằng dấu phẩy"},
                "escalate_after_min": {"type": "integer"},
                "owner_uid": {"type": "string", "description": "uid Zalo của chủ trong nhóm"},
                "enabled": {"type": "boolean"},
            },
            "required": ["op"],
        },
    )
