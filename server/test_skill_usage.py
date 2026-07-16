"""Test sidecar telemetry skill (skill_usage). Chạy tay / CI:

    cd server && ../.venv/Scripts/python.exe test_skill_usage.py

Không cần pytest, không chạm mạng. Tự cô lập sang thư mục tạm, KHÔNG để lại rác
ngoài thư mục tạm.
Phủ: bump tăng đúng, ghi atomic, file thiếu, file JSON hỏng, brain root không ghi được,
gọi song song (không mất bump), is_stale (pinned / có use_count / chưa đủ già / đủ già).
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

# ---- brain root KHÔNG ghi được: vẫn không raise ----
# Mẹo: lấy một FILE thường rồi truyền vào như thể nó là brain root. _write_atomic sẽ
# mkdir("<file>/Javis") → OS ném NotADirectoryError/FileExistsError trên MỌI nền tảng.
# KHÔNG dùng đường dẫn kiểu "/khong/ton/tai": trên Windows "/" resolve theo ổ đĩa hiện
# tại nên mkdir THÀNH CÔNG, nhánh except không bao giờ chạy (test rởm) và còn ghi rác ra
# đĩa thật. CI ở đây là win32 nên đây là lỗi thật, không phải khác biệt lý thuyết.
_fd_bogus, _bogus_file = tempfile.mkstemp(prefix="javis-usagebogus-")
os.close(_fd_bogus)
_BOGUS_ROOT = Path(_bogus_file)
try:
    skill_usage.bump(_BOGUS_ROOT, "x")
    check("brain root không ghi được → bump nuốt lỗi, không raise", True)
except Exception as e:
    check(f"brain root không ghi được → bump nuốt lỗi, không raise (raised {e!r})", False)
check("brain root không ghi được → read_usage trả {}", skill_usage.read_usage(_BOGUS_ROOT) == {})
check("brain root không ghi được → không có gì được tạo dưới file đó",
      _BOGUS_ROOT.is_file() and not (_BOGUS_ROOT / "Javis").exists())
os.unlink(_bogus_file)

# ---- gọi song song: _LOCK phải serialize read-modify-write, KHÔNG được mất bump nào ----
# Khẳng định ĐÚNG BẰNG 80, không phải khoảng. bump chạy 1 process, _LOCK bọc trọn vòng
# đọc-sửa-ghi nên kết quả duy nhất đúng là 80. Nếu để khoảng (0 < n <= 80) thì gỡ _LOCK ra
# test vẫn xanh dù bump bị nuốt do race - tức là chỉ chứng minh "không sập", đúng thứ mà
# test này KHÔNG có nhiệm vụ chứng minh.
import threading  # noqa: E402

_R2 = Path(tempfile.mkdtemp(prefix="javis-usagepar-"))


def _hammer():
    for _ in range(20):
        skill_usage.bump(_R2, "dua-xe")


_ts = [threading.Thread(target=_hammer) for _ in range(4)]
[t.start() for t in _ts]
[t.join() for t in _ts]
_n = skill_usage.read_usage(_R2).get("dua-xe", {}).get("use_count", 0)
check(f"4 luồng x 20 bump → không mất bump nào, use_count={_n} (phải đúng 80)", _n == 80)

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
