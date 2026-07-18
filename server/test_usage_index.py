"""Test usage_index (indexer SQLite + query). Chay tay:

    cd server && ../.venv/Scripts/python.exe test_usage_index.py

Tu co lap: JAVIS_STATE_DIR + thu muc nguon (Claude/Codex) tro vao temp. Khong mang.
Exit code != 0 neu fail.
"""
import json
import os
import sys
import tempfile
from pathlib import Path

_TMP = Path(tempfile.mkdtemp(prefix="javis-uidx-"))
os.environ["JAVIS_STATE_DIR"] = str(_TMP / "state")
os.environ["JAVIS_CLAUDE_PROJECTS_DIR"] = str(_TMP / "claude")
os.environ["JAVIS_CODEX_SESSIONS_DIR"] = str(_TMP / "codex")
(_TMP / "state").mkdir(parents=True, exist_ok=True)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import usage_index as ui  # noqa: E402

_fails = []


def check(name, cond):
    print(("OK   " if cond else "FAIL ") + name)
    if not cond:
        _fails.append(name)


def _write_lines(path: Path, lines):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(x) for x in lines), encoding="utf-8")


# --- nguon Claude: 1 file, 2 dong (background + subagent, cung session S1) ---
_claude_file = _TMP / "claude" / "D--Project-Demo" / "sess.jsonl"
_line_bg = {"type": "assistant", "entrypoint": "sdk-cli", "isSidechain": False, "sessionId": "S1",
            "cwd": "D:/Project/Demo", "timestamp": "2026-07-05T03:00:00.000Z",
            "message": {"model": "claude-opus-4-8", "usage": {"input_tokens": 100, "output_tokens": 200}}}
_line_sub = {"type": "assistant", "entrypoint": "sdk-cli", "isSidechain": True, "sessionId": "S1",
             "cwd": "D:/Project/Demo", "timestamp": "2026-07-05T03:05:00.000Z",
             "message": {"model": "claude-opus-4-8", "usage": {"input_tokens": 50, "output_tokens": 80}}}
_write_lines(_claude_file, [_line_bg, _line_sub])

# --- nguon Codex: 1 rollout ---
_codex_file = _TMP / "codex" / "2026" / "07" / "05" / "rollout-2026-07-05T03-00-00-x.jsonl"
_write_lines(_codex_file, [
    {"timestamp": "2026-07-05T03:00:00.000Z", "type": "session_meta", "payload": {"cwd": "D:/Project/Demo"}},
    {"timestamp": "2026-07-05T03:00:05.000Z", "type": "turn_context", "payload": {"model": "gpt-5.5"}},
    {"timestamp": "2026-07-05T03:10:00.000Z", "type": "event_msg", "payload": {"type": "token_count",
     "info": {"total_token_usage": {"input_tokens": 3000, "cached_input_tokens": 800, "output_tokens": 150, "total_tokens": 3150}}}},
])

# --- refresh lan 1 ---
r1 = ui.refresh()
check("refresh: co xu ly file claude", r1["claude_files"] >= 1)
check("refresh: co xu ly file codex", r1["codex_files"] >= 1)

by_act = ui.totals_by("activity")
check("activity: background = dong khong sidechain", by_act.get("background", {}).get("input") == 100 and by_act["background"]["output"] == 200)
check("activity: subagent = dong sidechain", by_act.get("subagent", {}).get("input") == 50 and by_act["subagent"]["output"] == 80)
check("activity: chat = codex", by_act.get("chat", {}).get("input") == 2200 and by_act["chat"]["cache_read"] == 800)

by_prov = ui.totals_by("provider")
check("provider: claude gop 2 dong", by_prov["claude"]["input"] == 150 and by_prov["claude"]["output"] == 280)
check("provider: claude 1 phien (1 file)", by_prov["claude"]["sessions"] == 1)
check("provider: codex", by_prov["codex"]["input"] == 2200 and by_prov["codex"]["output"] == 150)

# --- refresh lan 2: idempotent (khong file nao xu ly lai, tong khong doi) ---
r2 = ui.refresh()
check("refresh2: khong xu ly lai claude (idempotent)", r2["claude_files"] == 0)
check("refresh2: khong xu ly lai codex (idempotent)", r2["codex_files"] == 0)
check("refresh2: tong claude khong doi", ui.totals_by("provider")["claude"]["input"] == 150)

# --- file doi (append 1 dong) -> chi cong phan moi ---
_write_lines(_claude_file, [_line_bg, _line_sub,
             {"type": "assistant", "entrypoint": "sdk-cli", "isSidechain": False, "sessionId": "S1",
              "cwd": "D:/Project/Demo", "timestamp": "2026-07-05T04:00:00.000Z",
              "message": {"model": "claude-opus-4-8", "usage": {"input_tokens": 10, "output_tokens": 20}}}])
r3 = ui.refresh()
check("refresh3: file doi duoc xu ly lai", r3["claude_files"] == 1)
check("refresh3: claude tang dung phan moi (150+10)", ui.totals_by("provider")["claude"]["input"] == 160)
check("refresh3: van 1 phien (cung file)", ui.totals_by("provider")["claude"]["sessions"] == 1)


# ============================================================
# Task 5: usage_store forward-log + nap nhanh API (khong dem trung)
# ============================================================
import usage_store  # noqa: E402  (dung chung JAVIS_STATE_DIR temp)

_evp = Path(os.environ["JAVIS_STATE_DIR"]) / "usage-events.jsonl"
usage_store.record("openrouter", "deepseek/x", 100, 50, 0)
check("events: record ghi 1 dong usage-events.jsonl", _evp.exists() and len(_evp.read_text(encoding="utf-8").strip().splitlines()) >= 1)

r_api = ui.refresh()
_api = ui.totals_by("provider").get("api", {})
check("api: xuat hien sau refresh (100/50)", _api.get("input") == 100 and _api.get("output") == 50)
check("api: refresh dem api_events", r_api["api_events"] >= 1)

usage_store.record("openrouter", "deepseek/x", 10, 5, 0)
ui.refresh()
_api2 = ui.totals_by("provider")["api"]
check("api: chi cong phan moi (110/55)", _api2["input"] == 110 and _api2["output"] == 55)

ui.refresh()
check("api: idempotent (offset khong nap lai)", ui.totals_by("provider")["api"]["input"] == 110)

# dong codex trong events KHONG duoc dem vao api (da co log tho codex -> tranh double count)
usage_store.record("codex", "gpt-5.5", 999, 999, 0)
ui.refresh()
check("api: dong codex trong events bi bo qua", ui.totals_by("provider")["api"]["input"] == 110)


if _fails:
    print("\n%d FAIL" % len(_fails))
    sys.exit(1)
print("\nALL PASS")
