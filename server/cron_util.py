"""
cron_util.py - Bộ đọc & tính lịch cron 5 trường cho Javis (KHÔNG phụ thuộc thư viện ngoài).

Vì project giữ dependency tối giản (không có croniter), module này tự parse biểu thức cron
chuẩn 5 trường "phút giờ ngày-tháng tháng thứ" và tính LẦN CHẠY KẾ TIẾP sau một mốc thời gian.
Dùng cho nhắc hẹn/job định kỳ (reminders.py): mỗi lần fire xong tính due_at kế tiếp qua cron_next.

Hỗ trợ mỗi trường: '*'  '*/n'  'a'  'a-b'  'a-b/n'  'a,b,c' (kết hợp). Tên tháng (jan..dec) và
thứ (sun..sat) chấp nhận. dow: 0=Chủ nhật..6=Thứ bảy (7 cũng = Chủ nhật). Macro: @hourly @daily
@midnight @weekly @monthly @yearly/@annually. Ngữ nghĩa Vixie: nếu CẢ ngày-tháng lẫn thứ đều
bị giới hạn (khác '*') thì 1 ngày khớp khi khớp MỘT trong hai (OR).

Tính theo timezone truyền vào (Javis dùng giờ VN UTC+7 - offset cố định, không DST nên số học
datetime an toàn).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone, tzinfo
from typing import Optional, Set, Tuple

_MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], start=1)}
_DOWS = {d: i for i, d in enumerate(
    ["sun", "mon", "tue", "wed", "thu", "fri", "sat"], start=0)}

_MACROS = {
    "@hourly": "0 * * * *",
    "@daily": "0 0 * * *",
    "@midnight": "0 0 * * *",
    "@weekly": "0 0 * * 0",
    "@monthly": "0 0 1 * *",
    "@yearly": "0 0 1 1 *",
    "@annually": "0 0 1 1 *",
}

# (lo, hi) hợp lệ cho từng trường: minute, hour, dom, month, dow
_BOUNDS = [(0, 59), (0, 23), (1, 31), (1, 12), (0, 7)]

_MAX_YEARS_AHEAD = 5   # cron không chạy trong 5 năm coi như bất khả thi → lỗi


def _parse_atom(atom: str, lo: int, hi: int, names: dict) -> Tuple[Set[int], bool]:
    """1 phần (giữa các dấu phẩy). Trả (tập giá trị, is_star). Trường cron không có số âm."""
    atom = atom.strip().lower()
    if atom == "":
        raise ValueError("trường cron rỗng")
    step = 1
    if "/" in atom:                       # tách bước /n
        base, _, s = atom.partition("/")
        if not s.isdigit() or int(s) < 1:
            raise ValueError(f"bước cron không hợp lệ: {atom}")
        step = int(s)
        atom = base.strip() or "*"

    def _num(tok: str) -> int:
        tok = tok.strip().lower()
        if tok in names:
            return names[tok]
        if not tok.isdigit():
            raise ValueError(f"giá trị cron không hiểu: {tok}")
        return int(tok)

    if atom == "*":
        start, end, is_star = lo, hi, (step == 1)
    elif "-" in atom:
        a, _, b = atom.partition("-")
        start, end, is_star = _num(a), _num(b), False
    else:
        v = _num(atom)
        start, end, is_star = v, (hi if step != 1 else v), False   # "n/step" = n..hi bước step
    if start > end:
        raise ValueError(f"khoảng cron ngược: {atom}")
    vals = {v for v in range(start, end + 1, step) if lo <= v <= hi}
    if not vals:
        raise ValueError(f"trường cron không có giá trị hợp lệ: {atom}")
    return vals, is_star


def _parse_field(spec: str, lo: int, hi: int, names: dict) -> Tuple[Set[int], bool]:
    """Cả trường (có thể nhiều phần ngăn bởi ','). is_star = True chỉ khi trường phủ '*'."""
    out: Set[int] = set()
    is_star = False
    for part in (spec.strip().lower() or "*").split(","):
        vals, st = _parse_atom(part, lo, hi, names)
        out |= vals
        is_star = is_star or st
    return out, is_star


class CronExpr:
    __slots__ = ("minutes", "hours", "doms", "months", "dows", "dom_star", "dow_star", "raw")

    def __init__(self, expr: str):
        self.raw = expr.strip()
        s = self.raw.lower()
        if s in _MACROS:
            s = _MACROS[s]
        fields = s.split()
        if len(fields) != 5:
            raise ValueError("cron phải có 5 trường (phút giờ ngày tháng thứ) hoặc macro @daily...")
        self.minutes, _ = _parse_field(fields[0], 0, 59, {})
        self.hours, _ = _parse_field(fields[1], 0, 23, {})
        self.doms, self.dom_star = _parse_field(fields[2], 1, 31, {})
        self.months, _ = _parse_field(fields[3], 1, 12, _MONTHS)
        dows, self.dow_star = _parse_field(fields[4], 0, 7, _DOWS)
        self.dows = {0 if d == 7 else d for d in dows}   # 7 → 0 (Chủ nhật)

    def _day_ok(self, dt: datetime) -> bool:
        cron_dow = (dt.weekday() + 1) % 7   # Python: Mon=0..Sun=6 → cron: Sun=0..Sat=6
        dom_hit = dt.day in self.doms
        dow_hit = cron_dow in self.dows
        if not self.dom_star and not self.dow_star:
            return dom_hit or dow_hit      # ngữ nghĩa Vixie: cả hai giới hạn → OR
        if not self.dom_star:
            return dom_hit
        if not self.dow_star:
            return dow_hit
        return True

    def next_after(self, after: datetime) -> datetime:
        """Lần khớp đầu tiên STRICTLY sau 'after' (đã có tzinfo)."""
        dt = (after + timedelta(minutes=1)).replace(second=0, microsecond=0)
        limit_year = after.year + _MAX_YEARS_AHEAD
        while dt.year <= limit_year:
            if dt.month not in self.months:
                dt = _first_of_next_month(dt)
                continue
            if not self._day_ok(dt):
                dt = (dt + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
                continue
            if dt.hour not in self.hours:
                dt = (dt + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
                continue
            if dt.minute not in self.minutes:
                dt = (dt + timedelta(minutes=1)).replace(second=0, microsecond=0)
                continue
            return dt
        raise ValueError(f"cron '{self.raw}' không có lần chạy nào trong {_MAX_YEARS_AHEAD} năm tới")


def _first_of_next_month(dt: datetime) -> datetime:
    y, m = (dt.year + 1, 1) if dt.month == 12 else (dt.year, dt.month + 1)
    return dt.replace(year=y, month=m, day=1, hour=0, minute=0, second=0, microsecond=0)


def validate_cron(expr: str) -> str:
    """Parse + thử tính 1 lần chạy để bắt biểu thức bất khả thi. Trả biểu thức đã chuẩn hoá
    (hạ chữ thường). Ném ValueError nếu sai."""
    ce = CronExpr(expr)
    ce.next_after(datetime(2000, 1, 1, tzinfo=timezone.utc))
    return ce.raw.lower()


def cron_next(expr: str, after_epoch: float, tz: tzinfo) -> float:
    """Epoch (giây) của lần chạy kế tiếp sau 'after_epoch', tính theo timezone tz."""
    after = datetime.fromtimestamp(float(after_epoch), tz)
    return CronExpr(expr).next_after(after).timestamp()
