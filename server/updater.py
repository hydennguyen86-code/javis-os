#!/usr/bin/env python
"""Updater tách rời của Javis cho bản GIT checkout (Windows + native Linux). Server spawn DETACHED:

    python updater.py --old-sha <sha> --old-version <v> --target <v> --port <p>

Chuỗi: stop server -> git pull (stash nếu cây bẩn) -> pip install -> start -> chờ /health ~90s.
/health không lên → git reset --hard <old-sha> -> pip -> start (rollback tự động).
Chỉ dùng stdlib (chạy được cả khi bản mới hỏng dependency)."""
import argparse
import datetime
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "server"))
import update_state as us  # noqa: E402


def _now():
    return datetime.datetime.now().isoformat(timespec="seconds")


def log(msg):
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    try:
        with open(us.STATE_DIR / "update.log", "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def run(cmd):
    log("$ " + " ".join(cmd))
    r = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    if r.returncode != 0:
        log(f"  (rc={r.returncode}) " + (r.stderr or r.stdout or "").strip()[:500])
    return r


def venv_python():
    p = ROOT / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    return str(p) if p.exists() else sys.executable


def has_systemd():
    try:
        r = subprocess.run(["systemctl", "list-unit-files"], capture_output=True, text=True)
        return r.returncode == 0 and "javis.service" in (r.stdout or "")
    except Exception:
        return False


def stop_server():
    if os.name == "nt":
        run(["cmd", "/c", str(ROOT / "stop-javis.bat")])
    else:
        subprocess.run(["systemctl", "stop", "javis"], capture_output=True, text=True)


def start_server():
    if os.name == "nt":
        subprocess.Popen(["wscript.exe", "//nologo", str(ROOT / "start-javis.vbs")],
                         cwd=str(ROOT), creationflags=0x00000008)  # DETACHED_PROCESS
    else:
        subprocess.run(["systemctl", "start", "javis"], capture_output=True, text=True)


def git_dirty():
    r = run(["git", "status", "--porcelain", "--untracked-files=no"])
    return bool((r.stdout or "").strip())


def pip_install():
    return run([venv_python(), "-m", "pip", "install", "-r", "requirements.txt", "-q"])


def read_current_version():
    try:
        return (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    except Exception:
        return "0.0.0"


def poll_health(port, timeout_s=90):
    url = f"http://127.0.0.1:{port}/health"
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=4) as r:
                if r.status == 200:
                    return True
        except Exception:
            pass
        time.sleep(3)
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--old-sha", default="")
    ap.add_argument("--old-version", default="")
    ap.add_argument("--target", default="")
    ap.add_argument("--port", default=os.getenv("JAVIS_PORT", "7777"))
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    if a.dry_run:
        print(f"PLAN: stop -> pull(stash nếu bẩn) -> pip -> start -> health({a.port}) "
              f"-> rollback(reset {a.old_sha or '?'}) nếu không lên")
        return 0

    target = a.target or None
    us.write_state({"phase": "preparing", "started_at": _now(), "finished_at": None,
                    "result": None, "error": None, "old_sha": a.old_sha,
                    "old_version": a.old_version, "target_version": target, "stashed": False})

    if os.name != "nt" and not has_systemd():
        log("Không thấy systemd service 'javis' → không tự khởi động lại được. Hãy restart tay.")
        us.write_state({"phase": "error", "result": "error",
                        "error": "Không có systemd service 'javis' để tự khởi động lại.",
                        "finished_at": _now()})
        return 1

    log("Dừng server cũ…")
    stop_server()
    time.sleep(2)

    us.write_state({"phase": "pulling"})
    if git_dirty():
        log("Cây git có sửa đổi cục bộ → git stash (giữ lại, không mất).")
        run(["git", "stash"])
        us.write_state({"stashed": True})
    pull = run(["git", "pull", "--ff-only"])
    if pull.returncode != 0:
        log("git pull LỖI:\n" + (pull.stderr or pull.stdout or ""))
        start_server()
        us.write_state({"phase": "error", "result": "pull_failed",
                        "error": (pull.stderr or "git pull thất bại")[:500], "finished_at": _now()})
        return 1

    us.write_state({"phase": "installing"})
    log("Cài thư viện…")
    pip_install()

    us.write_state({"phase": "restarting"})
    log("Khởi động bản mới…")
    start_server()

    us.write_state({"phase": "health_check"})
    log("Kiểm tra sức khoẻ…")
    healthy = poll_health(a.port, 90)
    current = read_current_version()
    outcome = us.update_outcome(healthy, current, a.old_version, target)
    log(f"health={healthy} current={current} → {outcome}")

    if outcome == "success":
        us.record_boot_version(current)
        us.write_state({"phase": "done", "result": "success", "finished_at": _now()})
        return 0
    if outcome == "version_mismatch":
        us.write_state({"phase": "done", "result": "error",
                        "error": "Server lên nhưng phiên bản chưa đổi (pull chưa áp?). Xem update.log.",
                        "finished_at": _now()})
        return 1

    # need_rollback
    log("Bản mới KHÔNG lên được → tự lùi về bản cũ…")
    us.write_state({"phase": "rolling_back"})
    if not a.old_sha:
        us.write_state({"phase": "error", "result": "rollback_failed",
                        "error": "Không có commit cũ để lùi.", "finished_at": _now()})
        return 1
    run(["git", "reset", "--hard", a.old_sha])
    pip_install()
    start_server()
    if poll_health(a.port, 90):
        us.write_state({"phase": "done", "result": "rolled_back",
                        "error": "Bản mới lỗi, đã tự quay về bản cũ.", "finished_at": _now()})
        return 0
    us.write_state({"phase": "error", "result": "rollback_failed",
                    "error": "Bản mới lỗi và lùi bản cũng chưa lên. Xem update.log.", "finished_at": _now()})
    return 1


if __name__ == "__main__":
    sys.exit(main())
