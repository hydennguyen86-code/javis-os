"""
usage_index.py - Indexer + query cho dashboard token.

Quet log THO Claude (~/.claude/projects/**/*.jsonl) + Codex (~/.codex/sessions/**/rollout-*.jsonl),
parse TANG DAN (bo file chua doi theo size+mtime), phan loai hoat dong (chat vs nen) bang join
conversations.db, gop vao SQLite STATE_DIR/usage_index.db.

Nhanh API (openrouter/openai/anthropic) khong co log tho -> doc tu STATE_DIR/usage-events.jsonl
ma usage_store.record() ghi them (Task 5). Query: summary()/insights() (Task 6-7).

Grain luu: 1 file = 1 phien. Moi file dong gop nhieu dong file_daily theo
(day, provider, source, activity, model, project). File doi -> XOA het dong cu cua file roi
parse lai (idempotent, khong can offset). Rieng usage-events.jsonl la append-only nen dung offset.
"""
from __future__ import annotations

import glob
import json
import os
import sqlite3
from pathlib import Path

from config import STATE_DIR
import usage_parsers as up

DB_PATH = STATE_DIR / "usage_index.db"
_EVENTS_PATH = STATE_DIR / "usage-events.jsonl"

_DIMS = {"provider", "source", "activity", "model", "project", "day"}
# provider API (chi nhung nay lay tu usage-events.jsonl; claude/codex lay tu log tho)
_API_PROVIDERS = {"openrouter", "openai", "anthropic", "anthropic-api", "oauth"}


def _claude_dir() -> str:
    return os.getenv("JAVIS_CLAUDE_PROJECTS_DIR") or os.path.expanduser("~/.claude/projects")


def _codex_dir() -> str:
    return os.getenv("JAVIS_CODEX_SESSIONS_DIR") or os.path.expanduser("~/.codex/sessions")


def _conversations_db() -> Path:
    return STATE_DIR / "conversations.db"


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("CREATE TABLE IF NOT EXISTS files_seen("
                 "path TEXT PRIMARY KEY, size INTEGER, mtime REAL, offset INTEGER DEFAULT 0)")
    conn.execute("CREATE TABLE IF NOT EXISTS file_daily("
                 "path TEXT, day TEXT, provider TEXT, source TEXT, activity TEXT, model TEXT, project TEXT,"
                 "input INTEGER, output INTEGER, cache_read INTEGER, cache_create INTEGER)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_fd_day ON file_daily(day)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_fd_path ON file_daily(path)")
    return conn


def _chat_sessions() -> set:
    """Tap cli_session_id trong conversations.db = cac phien do NGUOI DUNG mo (chat).
    Thieu file / loi -> set() (khong chan)."""
    p = _conversations_db()
    out = set()
    try:
        if p.exists():
            c = sqlite3.connect("file:%s?mode=ro" % p, uri=True)
            try:
                for (sid,) in c.execute(
                        "SELECT cli_session_id FROM sessions WHERE cli_session_id IS NOT NULL AND cli_session_id<>''"):
                    if sid:
                        out.add(sid)
            finally:
                c.close()
    except Exception:
        pass
    return out


def _unchanged(conn, path, size, mtime) -> bool:
    row = conn.execute("SELECT size, mtime FROM files_seen WHERE path=?", (path,)).fetchone()
    return bool(row) and row[0] == size and abs((row[1] or 0) - mtime) < 1e-6


def _mark(conn, path, size, mtime, offset=0) -> None:
    conn.execute("INSERT INTO files_seen(path,size,mtime,offset) VALUES(?,?,?,?) "
                 "ON CONFLICT(path) DO UPDATE SET size=excluded.size, mtime=excluded.mtime, offset=excluded.offset",
                 (path, size, mtime, offset))


def _clear_file(conn, path) -> None:
    conn.execute("DELETE FROM file_daily WHERE path=?", (path,))


def _insert_events(conn, path, events) -> None:
    """Gop events cua 1 file theo khoa (day,provider,source,activity,model,project) roi insert."""
    groups = {}
    for ev in events:
        k = (ev.get("day") or "", ev["provider"], ev["source"], ev["activity"], ev["model"], ev["project"])
        g = groups.setdefault(k, [0, 0, 0, 0])
        g[0] += ev["input"]
        g[1] += ev["output"]
        g[2] += ev["cache_read"]
        g[3] += ev["cache_create"]
    if groups:
        conn.executemany(
            "INSERT INTO file_daily(path,day,provider,source,activity,model,project,input,output,cache_read,cache_create)"
            " VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            [(path,) + k + tuple(g) for k, g in groups.items()])


def _scan_claude(conn, chat) -> int:
    n = 0
    for path in glob.glob(os.path.join(_claude_dir(), "**", "*.jsonl"), recursive=True):
        try:
            st = os.stat(path)
        except OSError:
            continue
        if _unchanged(conn, path, st.st_size, st.st_mtime):
            continue
        _clear_file(conn, path)
        events = []
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
                    ev = up.parse_claude_line(obj, chat)
                    if ev:
                        events.append(ev)
        except OSError:
            continue
        _insert_events(conn, path, events)
        _mark(conn, path, st.st_size, st.st_mtime)
        n += 1
    return n


def _scan_codex(conn) -> int:
    n = 0
    for path in glob.glob(os.path.join(_codex_dir(), "**", "rollout-*.jsonl"), recursive=True):
        try:
            st = os.stat(path)
        except OSError:
            continue
        if _unchanged(conn, path, st.st_size, st.st_mtime):
            continue
        _clear_file(conn, path)
        ev = up.parse_codex_file(path)
        if ev:
            _insert_events(conn, path, [ev])
        _mark(conn, path, st.st_size, st.st_mtime)
        n += 1
    return n


def _ingest_api_events(conn) -> int:
    """Nap nhanh API tu usage-events.jsonl (append-only). Doc tu offset (so DONG da nap,
    luu trong files_seen.offset). CHI lay provider API (openrouter/openai/anthropic) - dong
    claude/codex bi bo qua vi da co log tho (tranh dem trung). Tra so event API moi nap."""
    path = str(_EVENTS_PATH)
    if not _EVENTS_PATH.exists():
        return 0
    try:
        raw = _EVENTS_PATH.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return 0
    lines = raw.splitlines()
    complete = len(lines)
    if raw and not raw.endswith("\n"):
        complete -= 1                       # dong cuoi con dang ghi do -> de lan sau

    row = conn.execute("SELECT offset FROM files_seen WHERE path=?", (path,)).fetchone()
    start = row[0] if row else 0
    if start > complete:                    # file bi cat/xoay -> nap lai tu dau
        conn.execute("DELETE FROM file_daily WHERE path=?", (path,))
        start = 0

    events = []
    for ln in lines[start:complete]:
        ln = ln.strip()
        if not ln:
            continue
        try:
            e = json.loads(ln)
        except Exception:
            continue
        prov = (e.get("provider") or "").lower()
        if prov not in _API_PROVIDERS:
            continue
        tin = int(e.get("in") or 0)
        tout = int(e.get("out") or 0)
        if tin + tout <= 0:
            continue
        events.append({"day": e.get("day") or "", "provider": "api", "source": "javis",
                       "activity": "chat", "model": e.get("model") or "?", "project": "(api)",
                       "input": tin, "output": tout, "cache_read": 0, "cache_create": 0})
    if events:
        _insert_events(conn, path, events)
    conn.execute("INSERT INTO files_seen(path,size,mtime,offset) VALUES(?,?,?,?) "
                 "ON CONFLICT(path) DO UPDATE SET offset=excluded.offset",
                 (path, 0, 0, complete))
    return len(events)


def refresh() -> dict:
    """Quet tang dan ca 3 nguon. Tra so file/event thuc su xu ly lan nay."""
    res = {"claude_files": 0, "codex_files": 0, "api_events": 0}
    conn = _connect()
    try:
        chat = _chat_sessions()
        res["claude_files"] = _scan_claude(conn, chat)
        res["codex_files"] = _scan_codex(conn)
        res["api_events"] = _ingest_api_events(conn)
        conn.commit()
    finally:
        conn.close()
    return res


def totals_by(dim: str, provider: str = None) -> dict:
    """Tong token theo mot chieu (khong loc ky), dung cho kiem thu + breakdown tho.
    Tra {gia_tri: {input,output,cache_read,cache_create,sessions}}."""
    if dim not in _DIMS:
        raise ValueError("dim khong hop le: %s" % dim)
    conn = _connect()
    try:
        where, args = "", []
        if provider:
            where, args = "WHERE provider=?", [provider]
        rows = conn.execute(
            "SELECT %s, SUM(input), SUM(output), SUM(cache_read), SUM(cache_create), COUNT(DISTINCT path) "
            "FROM file_daily %s GROUP BY %s" % (dim, where, dim), args).fetchall()
    finally:
        conn.close()
    return {r[0]: {"input": r[1] or 0, "output": r[2] or 0, "cache_read": r[3] or 0,
                   "cache_create": r[4] or 0, "sessions": r[5] or 0} for r in rows}
