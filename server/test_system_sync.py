"""Test mirror_skills: copy cả cây con + cổng chữ ký stat. Chạy tay / CI:

    cd server && ../.venv/Scripts/python.exe test_system_sync.py

Không cần pytest, không chạm mạng. Tự dựng brain giả trong thư mục tạm.
Phủ: copy thư mục con (references/ scripts/), file phụ ngang hàng đổi thì mirror nhận
(bug CÓ SẴN), bỏ qua .disabled, add-only không xoá file lạ, không đổi gì thì KHÔNG copy
lại lần nào và KHÔNG còn đọc-và-băm SKILL.md, hai luồng đồng thời không treo, file nhị phân
qua nguyên vẹn. Phần đồng thời (ép bằng Event, KHÔNG sleep) tách bạch hai thứ khác nhau:
re-check bên trong khoá (luồng tới sau khi luồng trước đã xong thì không copy lặp) và BẢN
THÂN cái khoá (2 luồng không copy đè nhau cùng lúc - check này tắt khi gỡ khoá). Cuối cùng
phủ 2 bẫy của cache chữ ký: nguồn đổi GIỮA CHỪNG lượt copy không được mất cập nhật, và skill
copy lỗi không được cache thành công (lượt sau phải thử lại).
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

# ---- RE-CHECK trong khoá: luồng tới SAU khi luồng trước đã xong thì KHÔNG copy lặp ----
# TÊN CHECK NÀY NÓI ĐÚNG THỨ NÓ CHỨNG MINH: nó phủ lần kiểm THỨ HAI (re-check bên trong khoá)
# của mẫu double-checked locking, KHÔNG phủ bản thân cái khoá. Gỡ hẳn khoá đi mà giữ re-check
# thì check này VẪN xanh - đã thử. Việc chứng minh khoá có tác dụng là của check kế tiếp.
# Khe hở được ép: luồng T2 đọc chữ ký (thấy cây đã đổi, cache còn cũ) RỒI mới xin khoá - nếu
# đúng lúc đó T1 đã copy xong + cập nhật cache + NHẢ khoá, T2 xin khoá THÀNH CÔNG (khoá đang
# rảnh) và nếu không kiểm lại chữ ký sau khi cầm khoá thì T2 copy LẶP một lượt vô ích.
# Ép thứ tự bằng threading.Event (không sleep nên không phập phù): brain fresh (lần gọi ĐẦU
# nên cache chắc chắn trống -> "cây đã đổi" với MỌI luồng), giữ T2 đứng tại _mirror_lock
# (patch tạm hàm này) cho tới khi T1 chạy xong TOÀN BỘ (join thật, không đoán), rồi mới thả
# T2 ra xin khoá. Skill chỉ 1 file nên đếm copy2 = đếm số LƯỢT copy: đúng phải ra 1, bug ra 2.
_R3 = Path(tempfile.mkdtemp(prefix="javis-mirrorrace-"))
_sk3 = _R3 / "skills" / "chi-1-file"
_sk3.mkdir(parents=True)
(_sk3 / "SKILL.md").write_text("---\nname: Chỉ 1 file\ndescription: Test đua khoá.\n---\nthân\n",
                               encoding="utf-8")

_t2_reached_lock = threading.Event()   # T2 đã đọc chữ ký (thấy lệch) và vừa gọi tới _mirror_lock
_t1_fully_done = threading.Event()     # T1 đã join xong thật sự (copy xong + đã nhả khoá)
_orig_mirror_lock = system_sync._mirror_lock


def _lock_hook(key):
    if threading.current_thread().name == "T2":
        _t2_reached_lock.set()
        if not _t1_fully_done.wait(timeout=10):
            print("CẢNH BÁO: T1 không xong trong 10s - test đua có thể treo")
    return _orig_mirror_lock(key)


_race_copies = []
_orig_copy2_race = shutil.copy2


def _spy_copy2_race(src, dst, *a, **kw):
    _race_copies.append(str(dst))
    return _orig_copy2_race(src, dst, *a, **kw)


system_sync._mirror_lock = _lock_hook
shutil.copy2 = _spy_copy2_race
try:
    _t2 = threading.Thread(target=lambda: system_sync.mirror_skills(_R3), name="T2")
    _t2.start()
    _t2_reached_lock.wait(timeout=10)   # đảm bảo T2 đã kẹt đúng tại cửa xin khoá

    _t1 = threading.Thread(target=lambda: system_sync.mirror_skills(_R3), name="T1")
    _t1.start()
    _t1.join(timeout=10)                # T1 chạy TỰ DO, không bị chặn -> copy xong, nhả khoá
    _t1_fully_done.set()                # báo T2: giờ mới được xin khoá (chắc chắn khoá đã rảnh)

    _t2.join(timeout=10)
finally:
    shutil.copy2 = _orig_copy2_race
    system_sync._mirror_lock = _orig_mirror_lock

# BẮT BUỘC: nếu T2 chết trước khi tới hook thì số copy vẫn là 1 và check dưới xanh mà KHÔNG
# chứng minh gì cả. Phải khẳng định T2 đã thật sự tới đúng khe hở mình định ép.
check("T2 đã tới cửa xin khoá (khe hở được ép thật)", _t2_reached_lock.is_set())
check(f"re-check trong khoá: luồng tới sau khi luồng trước XONG -> không copy lặp "
      f"(đếm được {len(_race_copies)})", len(_race_copies) == 1)

# ---- KHOÁ tự thân: 2 luồng KHÔNG được copy2 ĐÈ NHAU cùng lúc lên cùng đường dẫn đích ----
# Đây mới là check TẮT khi gỡ khoá (đã kiểm: có khoá B copy 0 lần, gỡ khoá B copy 1 lần).
# Lý do khoá tồn tại: 2 luồng cùng copy2 lên CÙNG file đích = nguy cơ file rách (torn write).
# Ép xác định: giữ A ĐỨNG YÊN BÊN TRONG vòng copy (hook copy2 của A chờ tại đó => A chắc chắn
# đang GIỮ khoá), rồi mới thả B chạy. Có khoá: B trượt acquire(blocking=False) -> về luôn, B
# copy 0 lần. Không khoá: B chui thẳng vào vòng copy (re-check vẫn thấy cache cũ vì A chưa kịp
# ghi) -> B copy đè lên A. Không sleep, chỉ Event.
_R4 = Path(tempfile.mkdtemp(prefix="javis-mirrorlock-"))
_sk4 = _R4 / "skills" / "chi-1-file"
_sk4.mkdir(parents=True)
(_sk4 / "SKILL.md").write_text("---\nname: Chỉ 1 file\ndescription: Test khoá.\n---\nthân\n",
                               encoding="utf-8")

_a_inside_copy = threading.Event()   # A đang Ở TRONG vòng copy => A đang giữ khoá
_b_finished = threading.Event()      # B đã chạy xong trọn vẹn
_lock_copies = {"A": 0, "B": 0}
_orig_copy2_lock = shutil.copy2
_a_has_waited = {"done": False}


def _spy_copy2_lock(src, dst, *a, **kw):
    _name = threading.current_thread().name
    if _name in _lock_copies:
        _lock_copies[_name] += 1
    if _name == "A" and not _a_has_waited["done"]:
        _a_has_waited["done"] = True
        _a_inside_copy.set()          # A đã vào trong vòng copy, đang giữ khoá
        if not _b_finished.wait(timeout=10):
            print("CẢNH BÁO: B không xong trong 10s - test khoá có thể treo")
    return _orig_copy2_lock(src, dst, *a, **kw)


shutil.copy2 = _spy_copy2_lock
try:
    _ta = threading.Thread(target=lambda: system_sync.mirror_skills(_R4), name="A")
    _ta.start()
    _a_reached = _a_inside_copy.wait(timeout=10)

    _tb = threading.Thread(target=lambda: system_sync.mirror_skills(_R4), name="B")
    _tb.start()
    _tb.join(timeout=10)     # B chạy trọn vẹn TRONG LÚC A vẫn đang kẹt giữa vòng copy
    _b_finished.set()
    _ta.join(timeout=10)
finally:
    shutil.copy2 = _orig_copy2_lock

check("A đã kẹt trong vòng copy (khe hở được ép thật)", _a_reached)
check(f"khoá: B KHÔNG copy đè khi A đang copy dở (B copy {_lock_copies['B']} lần)",
      _lock_copies["B"] == 0)

# ---- nguồn ĐỔI GIỮA CHỪNG lượt copy -> KHÔNG được mất cập nhật ----
# Cache phải ghi chữ ký ẢNH CHỤP mà lượt copy dựa vào, KHÔNG phải chữ ký tính lại sau khi
# copy xong. POST /skills ghi skill giữa phiên là kịch bản CÓ THẬT của đường nóng này. Nếu
# tính lại: ta vừa chép nội dung CŨ nhưng cache lại ghi chữ ký MỚI -> cache nói dối -> tầng 1
# thoát vĩnh viễn -> mirror kẹt ở bản cũ mãi. Ép bằng hook copy2: chép xong file đầu tiên thì
# ghi đè nguồn bằng nội dung mới, đúng như một ghi ngoài xen vào giữa lượt.
_R5 = Path(tempfile.mkdtemp(prefix="javis-mirrormid-"))
_sk5 = _R5 / "skills" / "skill-x"
_sk5.mkdir(parents=True)
_src5 = _sk5 / "SKILL.md"
_src5.write_text("v1", encoding="utf-8")
_mir5 = _R5 / ".claude" / "skills" / "skill-x" / "SKILL.md"

_orig_copy2_mid = shutil.copy2
_mid_injected = {"done": False}


def _spy_copy2_mid(src, dst, *a, **kw):
    _r = _orig_copy2_mid(src, dst, *a, **kw)
    if not _mid_injected["done"]:      # mô phỏng POST /skills ghi xen GIỮA lượt copy
        _mid_injected["done"] = True
        _src5.write_text("v2-bản-mới", encoding="utf-8")
        os.utime(_src5, (1, 1))        # ép mtime khác hẳn để chữ ký chắc chắn đổi
    return _r


shutil.copy2 = _spy_copy2_mid
try:
    system_sync.mirror_skills(_R5)     # lượt 1: chép v1, rồi nguồn nhảy sang v2 giữa chừng
finally:
    shutil.copy2 = _orig_copy2_mid

system_sync.mirror_skills(_R5)         # lượt 2: PHẢI nhận ra nguồn còn mới hơn -> chép lại
check("nguồn đổi GIỮA CHỪNG lượt copy -> lượt sau vẫn bắt kịp, không mất cập nhật",
      _mir5.is_file() and _mir5.read_text(encoding="utf-8") == "v2-bản-mới")

# ---- 1 skill copy LỖI -> KHÔNG cache thành công, lượt sau phải THỬ LẠI ----
# Lỗi tạm thời (AV quét / handle đang mở trên Windows - đúng hazard mà chính comment trong
# _mirror_signature cảnh báo) không được biến thành "skill vắng mặt vĩnh viễn tới khi restart".
_R6 = Path(tempfile.mkdtemp(prefix="javis-mirrorerr-"))
for _n in ("skill-a", "skill-b"):
    _d6 = _R6 / "skills" / _n
    _d6.mkdir(parents=True)
    (_d6 / "SKILL.md").write_text(f"nội dung {_n}", encoding="utf-8")
_mir6 = _R6 / ".claude" / "skills"

_orig_copy2_err = shutil.copy2
_boom = {"fired": False}


def _spy_copy2_err(src, dst, *a, **kw):
    if not _boom["fired"] and "skill-a" in str(src):
        _boom["fired"] = True          # hỏng ĐÚNG MỘT LẦN rồi thôi
        raise PermissionError("giả lập AV quét đang giữ file")
    return _orig_copy2_err(src, dst, *a, **kw)


shutil.copy2 = _spy_copy2_err
try:
    system_sync.mirror_skills(_R6)     # lượt 1: skill-a lỗi, skill-b vẫn phải qua
finally:
    shutil.copy2 = _orig_copy2_err

check("1 skill lỗi KHÔNG chặn skill khác", (_mir6 / "skill-b" / "SKILL.md").is_file())
system_sync.mirror_skills(_R6)         # lượt 2: lỗi đã hết -> PHẢI thử lại skill-a
check("skill copy lỗi -> lượt sau THỬ LẠI (không bị cache là đã xong)",
      (_mir6 / "skill-a" / "SKILL.md").is_file())

# ---- dọn ----
for _d in (_ROOT, _R2, _R3, _R4, _R5, _R6):
    shutil.rmtree(_d, ignore_errors=True)

if _fails:
    print(f"\nFAIL - test_system_sync: {len(_fails)} lỗi: {_fails}")
    sys.exit(1)
print("\nOK - test_system_sync: tất cả pass")
