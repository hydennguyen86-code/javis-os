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


_PRICING_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "usage_pricing.json")


def load_prices(path: str = None) -> dict:
    """Doc bang gia usage_pricing.json -> dict {tien_to_model: {in,out,cache_read,cache_write}}.
    Loi/thieu file -> {} (chi phi se = 0, khong chan)."""
    try:
        with open(path or _PRICING_PATH, "r", encoding="utf-8") as fh:
            return (json.load(fh) or {}).get("prices", {}) or {}
    except Exception:
        return {}


def estimate_cost(ev: dict, prices: dict) -> float:
    """Chi phi quy doi USD cho 1 UsageEvent theo bang gia (USD/1M token).
    Khop model theo tien to DAI NHAT; khong khop -> 0."""
    model = ev.get("model") or ""
    best_key = ""
    for key in prices:
        if model.startswith(key) and len(key) > len(best_key):
            best_key = key
    if not best_key:
        return 0.0
    p = prices[best_key]
    cost = (int(ev.get("input") or 0) * float(p.get("in") or 0)
            + int(ev.get("output") or 0) * float(p.get("out") or 0)
            + int(ev.get("cache_read") or 0) * float(p.get("cache_read") or 0)
            + int(ev.get("cache_create") or 0) * float(p.get("cache_write") or 0))
    return cost / 1_000_000.0


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


def parse_codex_file(path: str) -> dict | None:
    """Mot file rollout Codex (~/.codex/sessions/**/rollout-*.jsonl) -> mot UsageEvent
    la TONG CA PHIEN, hoac None neu khong tim thay token_count.

    total_token_usage la CONG DON theo phien: lay ban ghi co total_tokens LON NHAT
    (= trang thai cuoi) lam tong. input_tokens da GOM cached, nen input moi = input - cached.
    Codex la engine phu: source='javis', activity='chat' (best-effort, chua tach nen).
    """
    cwd = ""
    model = "codex"
    best = None            # (total_tokens, info_dict, ts_line)
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except Exception:
                    continue
                if not isinstance(obj, dict):
                    continue
                payload = obj.get("payload") if isinstance(obj.get("payload"), dict) else {}
                if obj.get("type") == "session_meta":
                    cwd = payload.get("cwd") or cwd
                m = obj.get("model") or payload.get("model")
                if m:
                    model = m
                if payload.get("type") == "token_count":
                    info = payload.get("info") or {}
                    ttu = info.get("total_token_usage") or {}
                    tot = int(ttu.get("total_tokens") or 0)
                    if ttu and (best is None or tot >= best[0]):
                        best = (tot, ttu, obj.get("timestamp"))
    except Exception:
        return None
    if best is None:
        return None
    _, ttu, ts_line = best
    inp_all = int(ttu.get("input_tokens") or 0)
    cread = int(ttu.get("cached_input_tokens") or 0)
    out = int(ttu.get("output_tokens") or 0)
    inp = max(0, inp_all - cread)
    if inp + out + cread <= 0:
        return None
    parsed = _parse_ts(ts_line)
    ts, day = parsed if parsed else (0, "")
    session_id = _basename(path).rsplit(".", 1)[0]
    return {
        "ts": ts, "day": day, "provider": "codex",
        "engine": "codex", "model": model,
        "project": _basename(cwd), "session_id": session_id,
        "source": "javis", "activity": "chat",
        "input": inp, "output": out, "cache_read": cread, "cache_create": 0,
    }
