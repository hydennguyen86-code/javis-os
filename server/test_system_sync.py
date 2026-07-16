"""Test mirror_skills: copy cả cây con + cổng chữ ký stat. Chạy tay / CI:

    cd server && ../.venv/Scripts/python.exe test_system_sync.py

Không cần pytest, không chạm mạng. Tự dựng brain giả trong thư mục tạm.
Phủ: copy thư mục con (references/ scripts/), file phụ ngang hàng đổi thì mirror nhận
(bug CÓ SẴN), bỏ qua .disabled, add-only không xoá file lạ, không đổi gì thì KHÔNG copy
lại lần nào và KHÔNG còn đọc-và-băm SKILL.md, hai luồng đồng thời không treo, file nhị phân
qua nguyên vẹn.
"""
import os
import shutil
import sys
import tempfile
import threading
from pathlib import Path

os.environ.setdefault("JAVIS_STATE_DIR", tempfile.mkdtemp(prefix="javis-synctest-"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import system_sync  # noqa: E402

_fails = []


def check(name, cond):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        _fails.append(name)


def _mk_brain(prefix):
    """Brain giả: 1 skill có cây con + 1 skill đã tắt. Trả (root, skill_dir, mirror_dir)."""
    root = Path(tempfile.mkdtemp(prefix=prefix))
    sk = root / "skills" / "co-tai-lieu"
    (sk / "references").mkdir(parents=True)
    (sk / "scripts").mkdir(parents=True)
    (sk / "SKILL.md").write_text("---\nname: Có tài liệu\ndescription: Thử cây con.\n---\nthân\n",
                                 encoding="utf-8")
    (sk / "references" / "chi-tiet.md").write_text("chi tiết v1\n", encoding="utf-8")
    (sk / "scripts" / "chay.py").write_text("print('hi')\n", encoding="utf-8")
    (sk / "anh.png").write_bytes(b"\x89PNG\r\n\x1a\n binary")
    dis = root / "skills" / ".disabled" / "da-tat"
    dis.mkdir(parents=True)
    (dis / "SKILL.md").write_text("---\nname: Đã tắt\n---\nx\n", encoding="utf-8")
    return root, sk, root / ".claude" / "skills" / "co-tai-lieu"


# ---- copy đệ quy ----
_ROOT, _SK, _MIR = _mk_brain("javis-mirror-")
system_sync.mirror_skills(_ROOT)
check("mirror có SKILL.md", (_MIR / "SKILL.md").is_file())
check("mirror có references/chi-tiet.md", (_MIR / "references" / "chi-tiet.md").is_file())
check("mirror có scripts/chay.py", (_MIR / "scripts" / "chay.py").is_file())
check("mirror giữ nguyên byte của file nhị phân",
      (_MIR / "anh.png").is_file()
      and (_MIR / "anh.png").read_bytes() == b"\x89PNG\r\n\x1a\n binary")
check("KHÔNG mirror skill đã tắt", not (_ROOT / ".claude" / "skills" / "da-tat").exists())

# ---- đổi references/ mà SKILL.md không đổi -> mirror PHẢI nhận (bug CÓ SẴN) ----
(_SK / "references" / "chi-tiet.md").write_text("chi tiết v2\n", encoding="utf-8")
system_sync.mirror_skills(_ROOT)
try:
    actual = (_MIR / "references" / "chi-tiet.md").read_text(encoding="utf-8")
    check("đổi references/ (SKILL.md không đổi) -> mirror nhận bản mới",
          actual == "chi tiết v2\n")
except FileNotFoundError:
    check("đổi references/ (SKILL.md không đổi) -> mirror nhận bản mới", False)

# ---- đổi file phụ NGANG HÀNG mà SKILL.md không đổi -> mirror PHẢI nhận (bug CÓ SẴN) ----
(_SK / "anh.png").write_bytes(b"\x89PNG\r\n\x1a\n DOI ROI")
system_sync.mirror_skills(_ROOT)
try:
    actual = (_MIR / "anh.png").read_bytes()
    check("đổi file phụ ngang hàng (SKILL.md không đổi) -> mirror nhận bản mới",
          actual == b"\x89PNG\r\n\x1a\n DOI ROI")
except FileNotFoundError:
    check("đổi file phụ ngang hàng (SKILL.md không đổi) -> mirror nhận bản mới", False)

# ---- add-only: file lạ trong mirror KHÔNG bị xoá ----
(_MIR / "nguoi-dung-them.md").write_text("giữ tôi lại\n", encoding="utf-8")
(_SK / "SKILL.md").write_text("---\nname: Có tài liệu\ndescription: Đổi để ép copy.\n---\nthân 2\n",
                              encoding="utf-8")
system_sync.mirror_skills(_ROOT)
check("add-only: không xoá file lạ ở mirror", (_MIR / "nguoi-dung-them.md").is_file())

# ---- không đổi gì -> KHÔNG copy lại lần nào ----
# KHÔNG kiểm bằng mtime: shutil.copy2 giữ nguyên mtime của NGUỒN nên đích luôn cùng mtime
# dù có copy lại hay không -> test kiểu đó xanh cả khi code sai. Phải ĐẾM copy2 thật sự.
_copies = []
_orig_copy2 = shutil.copy2


def _spy_copy2(src, dst, *a, **kw):
    _copies.append(str(dst))
    return _orig_copy2(src, dst, *a, **kw)


shutil.copy2 = _spy_copy2
try:
    system_sync.mirror_skills(_ROOT)
    system_sync.mirror_skills(_ROOT)
finally:
    shutil.copy2 = _orig_copy2
check(f"không đổi gì -> KHÔNG copy lại lần nào (đếm được {len(_copies)})", len(_copies) == 0)

# ---- không đổi gì -> KHÔNG còn đọc-và-băm SKILL.md như bản cũ ----
# CHÍNH XÁC ĐIỀU NÀY CHỨNG MINH: bản cũ đọc SKILL.md qua Path.read_text để băm, mỗi skill
# hai lần (nguồn + đích), mỗi lượt gọi - đó là 52ms. Spy này bắt đúng đường đó biến mất.
# ĐIỀU NÓ *KHÔNG* CHỨNG MINH: "không đọc file nào cả". shutil.copy2 đọc bằng open() chứ
# không qua Path.read_text, nên nếu copy vẫn chạy thì spy này VẪN im. Việc chứng minh không
# copy là của check _copies ở trên. Hai check bù nhau, đừng gộp.
_reads = []
_orig_rt = Path.read_text
_orig_rb = Path.read_bytes


def _spy_rt(self, *a, **kw):
    _reads.append(str(self))
    return _orig_rt(self, *a, **kw)


def _spy_rb(self, *a, **kw):
    _reads.append(str(self))
    return _orig_rb(self, *a, **kw)


Path.read_text = _spy_rt
Path.read_bytes = _spy_rb
try:
    system_sync.mirror_skills(_ROOT)
finally:
    Path.read_text = _orig_rt
    Path.read_bytes = _orig_rb
check(f"không đổi gì -> KHÔNG còn đọc-và-băm SKILL.md (đếm được {len(_reads)} lượt read_text/read_bytes)",
      len(_reads) == 0)

# ---- hai luồng đồng thời trên cùng root -> không treo ----
_R2, _SK2, _MIR2 = _mk_brain("javis-mirrorpar-")
_done = []


def _race():
    system_sync.mirror_skills(_R2)
    _done.append(1)


_ts = [threading.Thread(target=_race) for _ in range(4)]
[t.start() for t in _ts]
[t.join(timeout=20) for t in _ts]
check("4 luồng đồng thời -> không treo, cả 4 xong", len(_done) == 4)
check("4 luồng đồng thời -> mirror vẫn đúng", (_MIR2 / "references" / "chi-tiet.md").is_file())

# ---- dọn ----
for _d in (_ROOT, _R2):
    shutil.rmtree(_d, ignore_errors=True)

if _fails:
    print(f"\nFAIL - test_system_sync: {len(_fails)} lỗi: {_fails}")
    sys.exit(1)
print("\nOK - test_system_sync: tất cả pass")
