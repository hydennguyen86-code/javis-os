"""
usage_parsers.py - Ham parse THUAN cho dashboard token. Khong phu thuoc config/DB,
chi nhan dict/path -> tra ve UsageEvent (dict) da chuan hoa. De unit-test doc lap.

UsageEvent = {
  ts:int(epoch), day:'YYYY-MM-DD'(gio dia phuong UTC+7), provider:'claude'|'codex'|'api',
  engine:str, model:str, project:str, session_id:str,
  source:'javis'|'manual', activity:'chat'|'background'|'subagent'|'manual',
  input:int, output:int, cache_read:int, cache_create:int,
}
billable_in = input + cache_read + cache_create.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone, timedelta

_TZ = timezone(timedelta(hours=7))  # Asia/Ho_Chi_Minh


def _parse_ts(s: str):
    """ISO (co the hau to Z) -> (epoch:int, day-local:str). None neu khong parse duoc."""
    if not s:
        return None
    try:
        dt = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return int(dt.timestamp()), dt.astimezone(_TZ).strftime("%Y-%m-%d")
    except Exception:
        return None


def _basename(path: str) -> str:
    if not path:
        return "(unknown)"
    p = str(path).replace("\\", "/").rstrip("/")
    return p.rsplit("/", 1)[-1] or "(unknown)"


def parse_claude_line(obj: dict, chat_sessions: set) -> dict | None:
    """Mot dong JSONL da json.loads cua Claude Code -> UsageEvent hoac None.

    Bo qua: khong phai type=assistant, model synthetic/thieu, khong co usage, tong token = 0.
    """
    if not isinstance(obj, dict) or obj.get("type") != "assistant":
        return None
    msg = obj.get("message") or {}
    model = msg.get("model")
    if not model or model == "<synthetic>":
        return None
    usage = msg.get("usage")
    if not isinstance(usage, dict):
        return None
    inp = int(usage.get("input_tokens") or 0)
    out = int(usage.get("output_tokens") or 0)
    cread = int(usage.get("cache_read_input_tokens") or 0)
    ccreate = int(usage.get("cache_creation_input_tokens") or 0)
    if inp + out + cread + ccreate <= 0:
        return None

    entrypoint = obj.get("entrypoint") or ""
    source = "javis" if entrypoint.startswith("sdk") else "manual"
    session_id = obj.get("sessionId") or ""

    if obj.get("isSidechain"):
        activity = "subagent"
    elif source == "manual":
        activity = "manual"
    elif session_id in chat_sessions:
        activity = "chat"
    else:
        activity = "background"

    parsed = _parse_ts(obj.get("timestamp"))
    ts, day = parsed if parsed else (0, "")

    return {
        "ts": ts, "day": day, "provider": "claude",
        "engine": entrypoint or "claude", "model": model,
        "project": _basename(obj.get("cwd") or ""), "session_id": session_id,
        "source": source, "activity": activity,
        "input": inp, "output": out, "cache_read": cread, "cache_create": ccreate,
    }
