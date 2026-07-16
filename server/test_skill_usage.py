"""Test sidecar telemetry skill (skill_usage). Chạy tay / CI:

    cd server && ../.venv/Scripts/python.exe test_skill_usage.py

Không cần pytest, không chạm mạng. Tự cô lập sang thư mục tạm.
Phủ: bump tăng đúng, ghi atomic, file thiếu, file JSON hỏng, gọi song song,
is_stale (pinned / có use_count / chưa đủ già / đủ già).
"""
import json
import os
import sys
import tempfile
import time
from pathlib import Path

os.environ.setdefault("JAVIS_STATE_DIR", tempfile.mkdtemp(prefix="javis-usagetest-"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import skill_usage  # noqa: E402

_fails = []


def check(name, cond):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        _fails.append(name)


_ROOT = Path(tempfile.mkdtemp(prefix="javis-usagebrain-"))

# ---- file thiếu ----
check("brain chưa có sidecar → read_usage trả {}", skill_usage.read_usage(_ROOT) == {})

# ---- bump ----
skill_usage.bump(_ROOT, "viet-email")
u = skill_usage.read_usage(_ROOT)
check("bump lần 1 tạo bản ghi", "viet-email" in u)
check("bump lần 1 → use_count = 1", u.get("viet-email", {}).get("use_count") == 1)
check("bump lần 1 đặt created_at", u.get("viet-email", {}).get("created_at"))
check("bump lần 1 đặt first_used_at", u.get("viet-email", {}).get("first_used_at"))

skill_usage.bump(_ROOT, "viet-email")
u = skill_usage.read_usage(_ROOT)
check("bump lần 2 → use_count = 2", u.get("viet-email", {}).get("use_count") == 2)

skill_usage.bump(_ROOT, "skill-khac")
u = skill_usage.read_usage(_ROOT)
check("bump slug khác không đè slug cũ", u.get("viet-email", {}).get("use_count") == 2)
check("bump slug khác tạo bản ghi riêng", u.get("skill-khac", {}).get("use_count") == 1)

# ---- đúng vị trí ----
check("sidecar nằm ở Javis/skill-usage.json",
      skill_usage.usage_path(_ROOT) == _ROOT / "Javis" / "skill-usage.json")
check("sidecar thật sự tồn tại trên đĩa", skill_usage.usage_path(_ROOT).is_file())

# ---- file hỏng: KHÔNG được làm gãy ----
skill_usage.usage_path(_ROOT).write_text("{ day khong phai json", encoding="utf-8")
check("sidecar hỏng → read_usage trả {} chứ không raise", skill_usage.read_usage(_ROOT) == {})
try:
    skill_usage.bump(_ROOT, "viet-email")
    check("sidecar hỏng → bump không raise", True)
except Exception as e:
    check(f"sidecar hỏng → bump không raise (raised {e!r})", False)

# ---- không có quyền ghi / đường dẫn vô lý: vẫn không raise ----
try:
    skill_usage.bump(Path("/khong/ton/tai/o/dau/ca"), "x")
    check("brain không tồn tại → bump không raise", True)
except Exception as e:
    check(f"brain không tồn tại → bump không raise (raised {e!r})", False)

# ---- gọi song song ----
import threading  # noqa: E402

_R2 = Path(tempfile.mkdtemp(prefix="javis-usagepar-"))


def _hammer():
    for _ in range(20):
        skill_usage.bump(_R2, "dua-xe")


_ts = [threading.Thread(target=_hammer) for _ in range(4)]
[t.start() for t in _ts]
[t.join() for t in _ts]
_n = skill_usage.read_usage(_R2).get("dua-xe", {}).get("use_count", 0)
check(f"4 luồng x 20 bump → sidecar còn đọc được, use_count={_n} (>0, <=80)", 0 < _n <= 80)

# ---- is_stale ----
_now = time.time()
_old = _now - 40 * 86400
_new = _now - 3 * 86400

check("pinned → không bao giờ stale",
      skill_usage.is_stale({"use_count": 0, "created_at": _old, "pinned": True}, None, _now) is False)
check("có use_count > 0 → không bao giờ stale",
      skill_usage.is_stale({"use_count": 5, "created_at": _old, "pinned": False}, None, _now) is False)
check("use=0 nhưng mới tạo → chưa stale",
      skill_usage.is_stale({"use_count": 0, "created_at": _new, "pinned": False}, None, _now) is False)
check("use=0 + đủ già → stale",
      skill_usage.is_stale({"use_count": 0, "created_at": _old, "pinned": False}, None, _now) is True)
check("không có bản ghi + mtime cũ → stale (fallback mtime)",
      skill_usage.is_stale({}, _old, _now) is True)
check("không có bản ghi + mtime mới → chưa stale",
      skill_usage.is_stale({}, _new, _now) is False)
check("không có bản ghi + không có mtime → không stale (không đủ căn cứ)",
      skill_usage.is_stale({}, None, _now) is False)

if _fails:
    print(f"\nFAIL - test_skill_usage: {len(_fails)} lỗi: {_fails}")
    sys.exit(1)
print("\nOK - test_skill_usage: tất cả pass")
