"""Test tích hợp: xóa não lan sang máy khác qua sync (remote file:// cục bộ). Chạy:
    cd server && ../.venv/Scripts/python.exe test_brain_delete_sync.py
Cần git trong PATH. KHÔNG mạng thật."""
import os, sys, time, tempfile, subprocess
from pathlib import Path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import git_brain as gb  # noqa: E402

_fails = []
def check(name, cond):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: _fails.append(name)

if not gb.has_git():
    print("SKIP: máy không có git"); sys.exit(0)

ROOT = Path(tempfile.mkdtemp(prefix="jv-delsync-")).resolve()
REMOTE = ROOT / "remote.git"
subprocess.run(["git", "init", "--bare", str(REMOTE)], capture_output=True)
URL = "file:///" + str(REMOTE).replace("\\", "/").lstrip("/")
TOKEN = "x"  # file:// không dùng token nhưng sync_brains yêu cầu non-empty

def machine(tag):
    b = ROOT / tag / "brains"; m = ROOT / tag / "mirror"; t = ROOT / tag / "trash"
    b.mkdir(parents=True, exist_ok=True)
    return str(b), str(m), str(t)

def seed(brains, name, text="hi"):
    d = Path(brains) / name; d.mkdir(parents=True, exist_ok=True)
    (d / "note.md").write_text(text, encoding="utf-8")

def sync(brains, mirror, trash):
    return gb.sync_brains(brains, mirror, URL, TOKEN, "main",
                          trash_dir=trash, protected_names={"Brain Default"})

# --- Dựng: A tạo Foo, đẩy lên; B kéo về -> cả hai + remote đều có Foo ---
Ab, Am, At = machine("A"); Bb, Bm, Bt = machine("B")
seed(Ab, "Foo"); sync(Ab, Am, At)
sync(Bb, Bm, Bt)
check("B nhận được Foo từ remote", (Path(Bb) / "Foo" / "note.md").exists())

# --- A xóa Foo (move trash + tombstone) rồi sync ---
gb.move_to_trash(str(Path(Ab) / "Foo"), At, "Foo")
gb.write_tombstone(Ab, "Foo")
r = sync(Ab, Am, At)
check("A: sync sau xóa ok", r.get("ok"))
check("A: Foo không còn trong brains", not (Path(Ab) / "Foo").exists())

# --- B sync -> Foo bị xóa ở B + vào thùng rác B, remote sạch ---
r2 = sync(Bb, Bm, Bt)
check("B: sync ok", r2.get("ok"))
check("B: Foo bị xóa khỏi brains", not (Path(Bb) / "Foo").exists())
trashed = list(Path(Bt).glob("Foo__*")) if Path(Bt).is_dir() else []
check("B: Foo nằm trong thùng rác B", len(trashed) == 1 and (trashed[0] / "note.md").exists())

# --- Chốt thời gian: tạo LẠI Foo mới ở A (mtime mới) rồi sync -> KHÔNG bị xóa, tombstone gỡ ---
seed(Ab, "Foo", "moi")
os.utime(Path(Ab) / "Foo" / "note.md", None)  # mtime = bây giờ > deleted_at
r3 = sync(Ab, Am, At)
check("A: Foo dựng lại KHÔNG bị xóa (chốt thời gian)", (Path(Ab) / "Foo" / "note.md").exists())
check("A: tombstone Foo đã gỡ", not (Path(Ab) / gb.TOMBSTONE_DIR / "Foo.json").exists())

# --- Bảo vệ khi KHÔNG tombstone: xóa tay Bar khỏi brains B -> sync khôi phục, không mất ---
Cb, Cm, Ct = machine("C")
seed(Cb, "Bar"); sync(Cb, Cm, Ct)   # đẩy Bar lên remote
Db, Dm, Dt = machine("D"); sync(Db, Dm, Dt)  # D kéo Bar về
import shutil as _sh; _sh.rmtree(str(Path(Db) / "Bar"))  # xóa TAY, KHÔNG tombstone
sync(Db, Dm, Dt)
check("Bảo vệ: Bar biến mất không tombstone -> được khôi phục", (Path(Db) / "Bar").exists())

# --- Não mặc định miễn nhiễm: tombstone giả trỏ 'Brain Default' -> không bị xóa ---
Eb, Em, Et = machine("E")
seed(Eb, "Brain Default"); gb.write_tombstone(Eb, "Brain Default")
sync(Eb, Em, Et)
check("Não mặc định miễn nhiễm tombstone", (Path(Eb) / "Brain Default").exists())

print(); print("TẤT CẢ PASS" if not _fails else f"{len(_fails)} FAIL: {_fails}")
sys.exit(1 if _fails else 0)
