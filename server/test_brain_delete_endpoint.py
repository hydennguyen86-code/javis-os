"""Test endpoint /brains/delete + /brains/new (tombstone). Chạy:
    cd server && ../.venv/Scripts/python.exe test_brain_delete_endpoint.py"""
import os, sys, asyncio, tempfile
from pathlib import Path
os.environ.setdefault("JAVIS_STATE_DIR", tempfile.mkdtemp(prefix="jv-del-state-"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import main  # noqa: E402
import git_brain as gb  # noqa: E402

_fails = []
def check(name, cond):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: _fails.append(name)

BR = Path(tempfile.mkdtemp(prefix="jv-del-brains-")).resolve()
main.BRAINS_DIR = str(BR)
(BR / "Brain Default").mkdir(parents=True)         # não mặc định (không xóa được)
foo = BR / "Foo"; foo.mkdir(parents=True); (foo / "n.md").write_text("hi", encoding="utf-8")

# Xóa Foo hợp lệ (confirm khớp) -> vào thùng rác + tombstone, không còn trong brains
r = asyncio.run(main.delete_brain(name="Foo", confirm="Foo"))
ok = getattr(r, "body", None) is None  # JSONResponse lỗi mới có .body; dict thành công thì không
check("xóa Foo trả ok", isinstance(r, dict) and r.get("ok"))
check("Foo biến khỏi brains", not foo.exists())
check("tombstone Foo được ghi", (BR / gb.TOMBSTONE_DIR / "Foo.json").exists())
import config as cfgmod
trash = Path(cfgmod.STATE_DIR) / "brain-trash"
check("Foo nằm trong thùng rác", trash.is_dir() and len(list(trash.glob("Foo__*"))) == 1)

# Chặn xóa não mặc định
r2 = asyncio.run(main.delete_brain(name="Brain Default", confirm="Brain Default"))
check("chặn xóa não mặc định", hasattr(r2, "status_code") and r2.status_code == 400)

# confirm sai -> chặn
bar = BR / "Bar"; bar.mkdir(parents=True)
r3 = asyncio.run(main.delete_brain(name="Bar", confirm="sai"))
check("confirm sai -> chặn, Bar còn nguyên", hasattr(r3, "status_code") and bar.exists())

# /brains/new gỡ tombstone cùng tên (dựng lại Foo)
gb.write_tombstone(str(BR), "Foo")
r4 = asyncio.run(main.new_brain(name="Foo"))
check("tạo lại Foo -> gỡ tombstone Foo", not (BR / gb.TOMBSTONE_DIR / "Foo.json").exists())

print(); print("TẤT CẢ PASS" if not _fails else f"{len(_fails)} FAIL: {_fails}")
sys.exit(1 if _fails else 0)
