"""
usage_store.py - Kho đếm token/chi phí do CHÍNH JAVIS đo (đa nhà cung cấp).

Vì Javis nhìn thấy token in/out trong mọi phản hồi (Claude Code CLI, Codex, OpenRouter, OpenAI,
Anthropic), đây là con số usage đồng nhất - KHÔNG phụ thuộc provider có lộ hạn mức hay không.
KHÁC với "hạn mức tài khoản" (gói thuê bao) mà đa số provider không cho lấy qua API.

Lưu STATE_DIR/usage.json: { "days": { "YYYY-MM-DD": { "<provider>|<model>": {in,out,turns,cost} } },
                            "total": { "<provider>|<model>": {in,out,turns,cost} } }
- Gộp theo NGÀY (giữ 30 ngày gần nhất) + TỔNG tích luỹ.
- cost chỉ ghi khi provider trả về chi phí thật (vd Claude Code CLI total_cost_usd); còn lại 0
  (chỉ đếm token) - KHÔNG tự đoán giá vì bảng giá mỗi model khác nhau, dễ sai.
"""
from __future__ import annotations

import json
import threading
from datetime import datetime, timezone, timedelta

from config import STATE_DIR

_PATH = STATE_DIR / "usage.json"
_LOCK = threading.Lock()
_KEEP_DAYS = 30


def _today() -> str:
    return datetime.now(timezone(timedelta(hours=7))).strftime("%Y-%m-%d")


def _load() -> dict:
    try:
        if _PATH.exists():
            d = json.loads(_PATH.read_text(encoding="utf-8"))
            if isinstance(d, dict):
                d.setdefault("days", {})
                d.setdefault("total", {})
                return d
    except Exception:
        pass
    return {"days": {}, "total": {}}


def _save(d: dict) -> None:
    try:
        tmp = _PATH.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
        tmp.replace(_PATH)
    except Exception:
        pass


def record(provider: str, model: str, tin=0, tout=0, cost=0.0) -> None:
    """Cộng dồn 1 lượt vào ngày hôm nay + tổng. Bỏ qua nếu không có token nào (lượt lỗi)."""
    tin, tout = int(tin or 0), int(tout or 0)
    cost = float(cost or 0.0)
    if tin <= 0 and tout <= 0 and cost <= 0:
        return
    key = f"{provider or '?'}|{model or '?'}"
    with _LOCK:
        d = _load()
        day = _today()
        for bucket in (d["days"].setdefault(day, {}), d["total"]):
            e = bucket.setdefault(key, {"in": 0, "out": 0, "turns": 0, "cost": 0.0})
            e["in"] += tin
            e["out"] += tout
            e["turns"] += 1
            e["cost"] += cost
        for old in sorted(d["days"])[:-_KEEP_DAYS]:   # dọn ngày cũ
            d["days"].pop(old, None)
        _save(d)


def _rollup(bucket: dict) -> dict:
    """Gộp các key <provider>|<model> thành list + tổng cộng."""
    items, tot = [], {"in": 0, "out": 0, "turns": 0, "cost": 0.0}
    for key, e in sorted(bucket.items(), key=lambda kv: -(kv[1]["in"] + kv[1]["out"])):
        prov, _, model = key.partition("|")
        items.append({"provider": prov, "model": model, **e})
        for k in tot:
            tot[k] += e.get(k, 0)
    return {"items": items, "total": tot}


def summary() -> dict:
    d = _load()
    day = _today()
    return {"day": day,
            "today": _rollup(d["days"].get(day, {})),
            "all_time": _rollup(d.get("total", {}))}
