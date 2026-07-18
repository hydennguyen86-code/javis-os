"""Test tầng cập nhật: update_state (thuần) + endpoint /update/status + updater dry-run.
Chạy:  cd server && .venv\\Scripts\\python.exe test_update.py    (KHÔNG mạng)."""
import os, sys, tempfile
os.environ["JAVIS_STATE_DIR"] = tempfile.mkdtemp(prefix="javis-update-test-")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

_fails = []
def check(name, cond):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        _fails.append(name)

import update_state as us  # noqa: E402

# --- version compare ---
check("ver_newer 0.9.79 > 0.9.78", us.ver_newer("0.9.79", "0.9.78") is True)
check("ver_newer bằng nhau - False", us.ver_newer("1.0.0", "1.0.0") is False)
check("ver_newer local ahead - False", us.ver_newer("0.9.78", "0.9.79") is False)
check("ver_tuple rác - coi như (0,0,0), không crash", us.ver_tuple("abc") == (0, 0, 0))

# --- state round-trip ---
us.write_state({"phase": "installing", "old_version": "0.9.78"})
st = us.read_state()
check("write/read state giữ phase", st.get("phase") == "installing")
check("write/read state giữ old_version", st.get("old_version") == "0.9.78")
us.write_state({"phase": "done"})
check("write_state merge (không mất field cũ)", us.read_state().get("old_version") == "0.9.78")

# --- record_boot_version ---
us.STATE_FILE.unlink(missing_ok=True)
us.record_boot_version("0.9.78")
check("boot lần đầu: last_good = current", us.read_state().get("last_good_version") == "0.9.78")
check("boot lần đầu: chưa có previous", us.read_state().get("previous_version") is None)
us.record_boot_version("0.9.79")
check("boot lên bản mới: last_good cập nhật", us.read_state().get("last_good_version") == "0.9.79")
check("boot lên bản mới: previous = bản cũ", us.read_state().get("previous_version") == "0.9.78")

# --- update_outcome ---
check("health đỏ - need_rollback", us.update_outcome(False, "0.9.79", "0.9.78", "0.9.79") == "need_rollback")
check("health xanh + đúng target - success", us.update_outcome(True, "0.9.79", "0.9.78", "0.9.79") == "success")
check("health xanh + version tiến (target rỗng) - success", us.update_outcome(True, "0.9.79", "0.9.78", None) == "success")
check("health xanh nhưng version chưa đổi - version_mismatch", us.update_outcome(True, "0.9.78", "0.9.78", "0.9.79") == "version_mismatch")

# --- update_state: phủ thêm hợp đồng hàm ---
check("ver_tuple số hợp lệ -> tuple 3 phần", us.ver_tuple("1.2.3") == (1, 2, 3))
check("ver_tuple bỏ tiền tố v", us.ver_tuple("v2.0.0") == (2, 0, 0))
# health xanh + version tiến qua old nhưng CHƯA tới target (main nhích trong lúc pull):
# vẫn coi là success - KHÔNG rollback một bản đang chạy khoẻ chỉ vì chưa phải bản mới nhất.
check("outcome: khoẻ + tiến qua old dù chưa tới target -> success",
      us.update_outcome(True, "0.9.79", "0.9.78", "0.9.80") == "success")
us.STATE_FILE.unlink(missing_ok=True)
us.record_boot_version("1.0.0")
us.record_boot_version("1.0.0")
check("boot lại cùng phiên bản -> không đặt previous", us.read_state().get("previous_version") is None)
us.STATE_FILE.write_text("{khong-phai-json", encoding="utf-8")
check("read_state gặp JSON hỏng -> trả {}", us.read_state() == {})
us.STATE_FILE.unlink(missing_ok=True)

# --- main.py dùng update_state + /version có previous_version ---
import asyncio  # noqa: E402
import main  # noqa: E402
check("main alias _ver_newer chạy", main._ver_newer("0.9.79", "0.9.78") is True)
us.STATE_FILE.unlink(missing_ok=True)
us.write_state({"previous_version": "0.9.77"})
_v = asyncio.run(main.version_info())
check("/version có khoá previous_version", "previous_version" in _v)
check("/version previous_version đúng giá trị", _v.get("previous_version") == "0.9.77")

print()
if _fails:
    print(f"{len(_fails)} FAIL: {_fails}"); sys.exit(1)
print("TẤT CẢ PASS")
