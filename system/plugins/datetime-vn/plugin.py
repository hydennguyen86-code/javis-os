"""Plugin bundled: thời gian & ngày theo Việt Nam. Thuần stdlib, readonly.

Ví dụ MẪU cho tool plugin đơn giản nhất: register 2 tool đọc, không hook, không state.
Handler dạng handler(args: dict, ctx) -> str. ctx là PluginContext (slug, vault_root, data_dir, ...).
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

# Asia/Ho_Chi_Minh cố định UTC+7 (VN không có DST) → không phụ thuộc tzdata.
_TZ = timezone(timedelta(hours=7))
_WD = ["Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu", "Thứ Bảy", "Chủ Nhật"]


def _now(args, ctx):
    n = datetime.now(_TZ)
    return json.dumps({
        "iso": n.isoformat(timespec="seconds"),
        "date": n.strftime("%Y-%m-%d"),
        "time": n.strftime("%H:%M:%S"),
        "weekday": _WD[n.weekday()],
        "tz": "Asia/Ho_Chi_Minh (UTC+7)",
    }, ensure_ascii=False)


def _date_add(args, ctx):
    args = args or {}
    try:
        days = int(args.get("days", 0))
    except (TypeError, ValueError):
        return "ERROR: 'days' phải là số nguyên (âm = lùi về trước)."
    base_s = args.get("from")
    if base_s:
        try:
            base = datetime.strptime(str(base_s), "%Y-%m-%d").replace(tzinfo=_TZ)
        except ValueError:
            return "ERROR: 'from' phải dạng YYYY-MM-DD."
    else:
        base = datetime.now(_TZ)
    d = base + timedelta(days=days)
    return json.dumps({"date": d.strftime("%Y-%m-%d"), "weekday": _WD[d.weekday()]}, ensure_ascii=False)


def register(ctx):
    ctx.register_tool(
        name="javis_now",
        description=("Ngày giờ hiện tại theo múi giờ Việt Nam (UTC+7): iso, date, time, thứ trong tuần. "
                     "Dùng khi cần biết 'hôm nay', 'bây giờ mấy giờ', đặt nhắc hẹn, hay đóng dấu thời gian báo cáo."),
        handler=_now, min_mode="readonly",
        schema={"type": "object", "properties": {}},
    )
    ctx.register_tool(
        name="javis_date_add",
        description=("Tính ngày cách hôm nay (hoặc cách ngày 'from') N ngày. Tham số: days (số nguyên, "
                     "âm = trước), from (YYYY-MM-DD, tuỳ chọn). Dùng cho 'ngày mai', '3 ngày nữa', 'tuần trước'."),
        handler=_date_add, min_mode="readonly",
        schema={"type": "object",
                "properties": {"days": {"type": "integer", "description": "Số ngày cộng thêm (âm = lùi)"},
                               "from": {"type": "string", "description": "Ngày gốc YYYY-MM-DD (bỏ trống = hôm nay)"}},
                "required": ["days"]},
    )
