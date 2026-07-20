"""
zalo_listener.py - Nghe tin Zalo LIÊN TỤC bằng tiến trình sidecar.

Vá đúng lỗ hổng: connector `zalo` (zalo-agent-cli qua MCP) là PULL-ONLY, phải gọi
tool mới biết có tin, mà mcp_client._IDLE_TTL=600 lại giết subprocess sau 10 phút
không dùng → websocket + ring buffer của `mcp start` không sống sót. Nên muốn nghe
liên tục thì phải có tiến trình sống ĐỘC LẬP với pool MCP.

Luồng:
    npx zalo-agent-cli listen --webhook http://127.0.0.1:<port>/hook/zalo
        (HOME = home cô lập của connection đã quét QR, xem zalo_login.py)
      → mỗi sự kiện POST 1 JSON về Javis
      → lọc (từ khoá / thread theo dõi / dm_only / giờ im lặng) + khử trùng msgId
      → báo Telegram cho chủ.

KHÔNG gọi model ở khâu nào → listener chạy cả ngày không tốn token.
KHÔNG tự trả lời khách: Javis chỉ gửi tin Zalo khi chủ yêu cầu trực tiếp trong chat.

Điều CHƯA kiểm chứng (xem spec 2026-07-20-zalo-listener-design): Zalo chỉ cho MỘT
socket mỗi tài khoản, nên connector `zalo` (mcp start) và sidecar này có thể đá
nhau. Thiết kế chọn làm va chạm HIỆN RÕ (bắt chuỗi trùng phiên trong stdout → đẩy
lên UI, dừng hẳn thay vì quay vòng vô ích) chứ không đoán trước cách né.

Module KHÔNG import main (tránh vòng lặp import): helper tiêm qua ZaloListenerDeps.
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import secrets as _secrets
import shutil
import subprocess
import sys
import threading
import time
import unicodedata
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Optional
from urllib.parse import quote

from fastapi import APIRouter, Body, Request
from fastapi.responses import JSONResponse

VN_TZ = timezone(timedelta(hours=7))

HOOK_PATH = "/hook/zalo"
SECRET_HEADER = "x-javis-zalo-secret"

# Backoff dựng lại khi socket đứt. Trùng phiên / lỗi xác thực thì KHÔNG quay vòng.
_BACKOFF = (5, 30, 120, 300)
_TEXT_CAP = 400            # trần ký tự nội dung tin đẩy vào Telegram
_SEEN_CAP = 2000
_RATE_LIMIT = 20           # trần số thông báo ...
_RATE_WINDOW_S = 600       # ... trong 10 phút (nhóm đông không làm nổ Telegram)

# Chuỗi trong stdout/stderr của CLI báo hiệu ĐỪNG thử lại nữa.
_FATAL_MARKS = ("duplicate", "trùng phiên", "another session", "already running",
                "login required", "not logged in", "chưa đăng nhập", "unauthorized")

DEFAULT_CFG = {
    "enabled": False,
    "conn_id": "",
    "keywords": [],
    "threads": [],
    "dm_only": True,
    "quiet_hours": "",
    "secret": "",
    "owner_chat": "",
}


# ============================================================
# Hàm THUẦN - test được không cần tiến trình thật
# ============================================================
def _fold(s) -> str:
    """Bỏ dấu + hạ chữ thường: khách gõ 'gia' vẫn khớp từ khoá 'giá'."""
    s = unicodedata.normalize("NFD", str(s or ""))
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    return s.replace("đ", "d").replace("Đ", "D").lower()


def _text_of(v) -> str:
    """Bóc nội dung tin: CLI khi thì trả chuỗi, khi thì object {title|text|content}."""
    if isinstance(v, str):
        return v
    if isinstance(v, dict):
        for k in ("title", "text", "content", "caption", "description"):
            got = v.get(k)
            if isinstance(got, str) and got.strip():
                return got
    return ""


def normalize_event(raw) -> dict:
    """Chuẩn hoá 1 sự kiện webhook về khuôn Javis dùng.

    Payload của zalo-agent-cli CHƯA chốt (dạng phẳng lẫn dạng {event, data}, camelCase
    lẫn snake_case) nên hàm này cố tình nhận nhiều biến thể và không bao giờ nổ - rác
    vào thì trả khuôn rỗng để bộ lọc tự loại.
    """
    if not isinstance(raw, dict):
        raw = {}
    kind = raw.get("event")
    if not isinstance(kind, str):
        kind = raw.get("type") if isinstance(raw.get("type"), str) else ""
    data = raw.get("data") if isinstance(raw.get("data"), dict) else raw

    def pick(*keys):
        for k in keys:
            v = data.get(k)
            if v not in (None, ""):
                return v
        return ""

    # threadType: chữ ("group") hoặc số theo ThreadType của zca-js (0=riêng, 1=nhóm).
    tt = data.get("threadType")
    if tt in (None, ""):
        tt = data.get("type") if isinstance(data.get("type"), int) else None
    if isinstance(tt, str):
        thread_type = "group" if "group" in tt.lower() else "user"
    elif isinstance(tt, int):
        thread_type = "group" if tt == 1 else "user"
    else:
        thread_type = "user"

    text = _text_of(pick("content", "text", "message", "body"))
    return {
        "kind": (kind or "message").lower(),
        "msg_id": str(pick("msgId", "msg_id", "messageId", "message_id", "id") or ""),
        "thread_id": str(pick("threadId", "thread_id", "uidFrom", "groupId") or ""),
        "thread_type": thread_type,
        "text": text,
        "sender": str(pick("dName", "displayName", "senderName", "fromName", "name") or ""),
        "is_self": bool(data.get("isSelf") or data.get("is_self") or data.get("self") or False),
    }


def _in_quiet(quiet: str, now: datetime) -> bool:
    """quiet dạng '23-07'. Sai định dạng thì coi như KHÔNG có giờ im lặng."""
    m = re.match(r"^\s*(\d{1,2})\s*-\s*(\d{1,2})\s*$", str(quiet or ""))
    if not m:
        return False
    a, b = int(m.group(1)), int(m.group(2))
    if not (0 <= a <= 23 and 0 <= b <= 23):
        return False
    h = now.hour
    return (a <= h < b) if a <= b else (h >= a or h < b)


def should_notify(ev: dict, cfg: dict, now: Optional[datetime] = None) -> tuple:
    """Có nên bắn Telegram cho sự kiện này không. Trả (bool, lý_do_bỏ_qua).

    Mặc định CHẶT: chỉ tin nhắn riêng có chứa từ khoá. Nới ra sau khi dùng thấy sót
    thì an toàn hơn là mặc định báo hết rồi phải tắt bớt.
    """
    now = now or datetime.now(VN_TZ)
    if not cfg.get("enabled"):
        return False, "tắt"
    if (ev.get("kind") or "message") != "message":
        return False, "không phải tin nhắn"
    if ev.get("is_self"):
        return False, "tin của mình"
    if cfg.get("dm_only", True) and ev.get("thread_type") == "group":
        return False, "nhóm"
    if _in_quiet(cfg.get("quiet_hours", ""), now):
        return False, "giờ im lặng"
    # Thread đang theo dõi thì báo bất kể nội dung (khách quen, đơn đang chạy...).
    threads = [str(t) for t in (cfg.get("threads") or [])]
    if threads and str(ev.get("thread_id") or "") in threads:
        return True, ""
    kws = [k for k in (cfg.get("keywords") or []) if str(k).strip()]
    if not kws:
        return True, ""
    body = _fold(ev.get("text"))
    if any(_fold(k) in body for k in kws):
        return True, ""
    return False, "không khớp từ khoá"


class SeenSet:
    """Khử trùng msgId: CLI gửi lại sau khi nối lại là chuyện thường, không được
    bắn Telegram hai lần. msgId rỗng thì luôn cho qua (gộp lại sẽ nuốt nhầm tin khác)."""

    def __init__(self, cap: int = _SEEN_CAP):
        self.cap = max(2, int(cap))
        self._seen: dict = {}

    def is_new(self, msg_id) -> bool:
        key = str(msg_id or "")
        if not key:
            return True
        if key in self._seen:
            return False
        if len(self._seen) >= self.cap:      # đầy thì bỏ nửa cũ, không phình vô hạn
            for k in list(self._seen)[: self.cap // 2]:
                self._seen.pop(k, None)
        self._seen[key] = True
        return True


class RateLimiter:
    """Trần số thông báo trong một cửa sổ thời gian - một nhóm đông không được
    làm nổ Telegram của chủ."""

    def __init__(self, limit: int = _RATE_LIMIT, window_s: int = _RATE_WINDOW_S):
        self.limit = max(1, int(limit))
        self.window_s = max(1, int(window_s))
        self._hits: deque = deque()

    def allow(self, now: Optional[float] = None) -> bool:
        now = time.time() if now is None else float(now)
        while self._hits and now - self._hits[0] > self.window_s:
            self._hits.popleft()
        if len(self._hits) >= self.limit:
            return False
        self._hits.append(now)
        return True


def format_message(ev: dict) -> str:
    """Tin nhắn Telegram gửi cho chủ. Ngắn, đọc là biết ai nhắn gì."""
    who = ev.get("sender") or "Ai đó"
    where = " (nhóm)" if ev.get("thread_type") == "group" else ""
    body = (ev.get("text") or "").strip() or "(ảnh hoặc sticker)"
    if len(body) > _TEXT_CAP:
        body = body[:_TEXT_CAP] + "..."
    return f"Zalo{where} - {who}:\n{body}"


# ============================================================
# Vòng đời tiến trình sidecar
# ============================================================
@dataclass
class ZaloListenerDeps:
    read_settings: Callable[[], dict]
    write_settings: Callable[[dict], Any]
    get_connection: Callable[[str], Any]     # mcp_store.get_connection
    notify: Callable                          # async (owner_chat, text) -> (ok, err)
    port: Callable[[], int]                   # cổng Javis đang nghe


class _Runner:
    """Quản 1 tiến trình `zalo-agent-cli listen`. Đọc stdout để biết trạng thái thật,
    tự dựng lại khi đứt, nhưng DỪNG HẲN khi trùng phiên / chưa đăng nhập (thử lại chỉ
    tốn công và làm Zalo nghi ngờ thêm)."""

    def __init__(self, deps: ZaloListenerDeps):
        self.deps = deps
        self.proc = None
        self.state = "off"          # off | starting | listening | reconnecting | duplicate | error
        self.error = ""
        self.last_event_ts = 0.0
        self.started_ts = 0.0
        self._stop = threading.Event()
        self._thread = None
        self._tail = deque(maxlen=15)

    # ---- argv ----
    def _argv(self, cfg: dict) -> Optional[list]:
        npx = shutil.which("npx")
        if not npx:
            return None
        # Secret đi trong QUERY chứ không phải header: `zalo-agent-cli --webhook <url>` chỉ POST
        # JSON trần, KHÔNG có cờ nào đặt header tuỳ ý → gác bằng header là chặn sạch tin, tính
        # năng chết ngay. Kênh này chỉ chạy trên loopback nên đánh đổi chấp nhận được: rào chính
        # là _AUTH_LOCAL_EXACT + loopback, secret chỉ là tầng hai chặn tiến trình KHÁC cùng máy.
        # Endpoint vẫn nhận cả header (SECRET_HEADER) cho ai tự dựng nguồn đẩy khác.
        url = f"http://127.0.0.1:{self.deps.port()}{HOOK_PATH}?k={quote(cfg.get('secret', ''))}"
        argv = [npx, "-y", "zalo-agent-cli", "listen", "--webhook", url,
                "--filter", "dm" if cfg.get("dm_only", True) else "all", "--no-self"]
        if str(npx).lower().endswith((".cmd", ".bat")):
            argv = ["cmd.exe", "/c"] + argv
        return argv

    def _spawn(self, home: str, cfg: dict) -> bool:
        argv = self._argv(cfg)
        if not argv:
            self.state, self.error = "error", "Cần Node.js 20+ (lệnh npx) trên máy chạy Javis"
            return False
        env = dict(os.environ)
        env["HOME"] = home          # home cô lập = tài khoản Zalo đã quét QR (xem zalo_login.py)
        env["USERPROFILE"] = home
        kwargs = {}
        if os.name == "nt":
            kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        try:
            self.proc = subprocess.Popen(
                argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL, text=True, encoding="utf-8",
                errors="replace", env=env, **kwargs)
        except OSError as e:
            self.state, self.error = "error", f"Không chạy được npx: {e}"
            return False
        self.started_ts = time.time()
        return True

    def _scan_line(self, line: str) -> Optional[str]:
        """Đọc 1 dòng log CLI → trạng thái mới (nếu có). Trả 'fatal' nếu đừng thử lại."""
        low = line.lower()
        if any(m in low for m in _FATAL_MARKS):
            self.error = line.strip()[:200]
            return "fatal"
        if "connected" in low or "listening" in low or "đang nghe" in low:
            return "listening"
        if "disconnect" in low or "closed" in low or "reconnect" in low:
            return "reconnecting"
        return None

    def _loop(self, home: str):
        """Vòng chạy nền: spawn → đọc log → đứt thì backoff dựng lại."""
        attempt = 0
        while not self._stop.is_set():
            cfg = read_cfg(self.deps)
            self.state = "starting"
            if not self._spawn(home, cfg):
                return                       # lỗi cứng (thiếu npx) - state đã đặt trong _spawn
            fatal = False
            try:
                for raw in iter(self.proc.stdout.readline, ""):
                    if self._stop.is_set():
                        break
                    line = (raw or "").rstrip()
                    if not line:
                        continue
                    self._tail.append(line[:200])
                    st = self._scan_line(line)
                    if st == "fatal":
                        fatal = True
                        break
                    if st:
                        self.state = st
                        if st == "listening":
                            attempt = 0      # nối lại được thì reset backoff
            except Exception as e:
                self.error = f"{type(e).__name__}: {e}"
            try:
                if self.proc and self.proc.poll() is None:
                    self.proc.kill()
            except Exception:
                pass
            if self._stop.is_set():
                break
            if fatal:
                # Trùng phiên: connector `zalo` (mcp start) nhiều khả năng đang giữ socket
                # của CÙNG tài khoản. Dừng hẳn + báo rõ để chủ thấy va chạm, đừng quay vòng.
                self.state = "duplicate" if "duplicate" in self.error.lower() else "error"
                return
            delay = _BACKOFF[min(attempt, len(_BACKOFF) - 1)]
            attempt += 1
            self.state = "reconnecting"
            self.error = f"Mất kết nối, thử lại sau {delay}s"
            if self._stop.wait(delay):
                break
        self.state = "off"

    # ---- API ----
    def start(self, home: str) -> dict:
        if self._thread and self._thread.is_alive():
            return {"ok": True, "already": True}
        self._stop.clear()
        self.error = ""
        self._thread = threading.Thread(target=self._loop, args=(home,), daemon=True)
        self._thread.start()
        return {"ok": True}

    def stop(self) -> dict:
        self._stop.set()
        try:
            if self.proc and self.proc.poll() is None:
                self.proc.kill()
        except Exception:
            pass
        self.state = "off"
        return {"ok": True}

    def status(self) -> dict:
        return {"state": self.state, "error": self.error,
                "last_event": self.last_event_ts, "started": self.started_ts,
                "log": list(self._tail)[-5:]}


# ============================================================
# Cấu hình
# ============================================================
def read_cfg(deps: ZaloListenerDeps) -> dict:
    cfg = dict(DEFAULT_CFG)
    try:
        cfg.update(deps.read_settings().get("zalo_listener") or {})
    except Exception:
        pass
    return cfg


def write_cfg(deps: ZaloListenerDeps, patch: dict) -> dict:
    s = deps.read_settings()
    cur = dict(DEFAULT_CFG)
    cur.update(s.get("zalo_listener") or {})
    for k in DEFAULT_CFG:
        if k in patch and patch[k] is not None:
            cur[k] = patch[k]
    if not cur.get("secret"):
        cur["secret"] = _secrets.token_urlsafe(24)
    s["zalo_listener"] = cur
    deps.write_settings(s)
    return cur


def _home_of(deps: ZaloListenerDeps, conn_id: str) -> tuple:
    """Lấy home cô lập của connection Zalo (do zalo_login tạo lúc quét QR)."""
    try:
        c = deps.get_connection(conn_id) or {}
    except Exception:
        c = {}
    if not c:
        return "", "Chưa chọn tài khoản Zalo (hoặc kết nối đã bị xoá)"
    home = ((c.get("config") or {}).get("home_dir") or "").strip()
    if not home or not os.path.isdir(home):
        return "", "Kết nối Zalo này chưa có phiên đăng nhập, quét QR lại giúp em"
    return home, ""


# ============================================================
# Đăng ký router
# ============================================================
def register(app, deps: ZaloListenerDeps):
    router = APIRouter()
    runner = _Runner(deps)
    seen = SeenSet()
    rate = RateLimiter()

    async def _handle(ev: dict, cfg: dict):
        ok, _why = should_notify(ev, cfg)
        if not ok:
            return
        if not seen.is_new(ev.get("msg_id")):
            return
        if not rate.allow():
            return
        try:
            await deps.notify(cfg.get("owner_chat", ""), format_message(ev))
        except Exception as e:
            print(f"[zalo listener] báo Telegram lỗi: {e}", file=sys.stderr)

    @router.post(HOOK_PATH)
    async def hook(request: Request):
        """Sidecar POST mỗi sự kiện vào đây. PHẢI trả 200 ngay: CLI chỉ chờ 5 giây
        rồi bỏ qua âm thầm, xử lý đồng bộ là mất tin."""
        cfg = read_cfg(deps)
        want = cfg.get("secret") or ""
        # Nhận secret từ query (đường sidecar dùng - CLI không đặt header được) HOẶC header.
        got = request.query_params.get("k") or request.headers.get(SECRET_HEADER, "")
        if want and not _secrets.compare_digest(str(got), str(want)):
            return JSONResponse({"error": "forbidden"}, status_code=403)
        try:
            raw = await request.json()
        except Exception:
            return {"ok": True}
        runner.last_event_ts = time.time()
        for item in (raw if isinstance(raw, list) else [raw]):
            ev = normalize_event(item)
            asyncio.create_task(_handle(ev, cfg))
        return {"ok": True}

    @router.get("/zalo-listener/status")
    async def status():
        cfg = read_cfg(deps)
        return {**runner.status(), "enabled": bool(cfg.get("enabled")),
                "conn_id": cfg.get("conn_id", ""),
                "cfg": {k: v for k, v in cfg.items() if k != "secret"}}

    @router.post("/zalo-listener/config")
    async def save_config(payload: dict = Body(...)):
        cfg = write_cfg(deps, payload or {})
        return {"ok": True, "cfg": {k: v for k, v in cfg.items() if k != "secret"}}

    @router.post("/zalo-listener/start")
    async def start(payload: dict = Body(default={})):
        cfg = write_cfg(deps, {**(payload or {}), "enabled": True})
        home, err = _home_of(deps, cfg.get("conn_id", ""))
        if err:
            return {"ok": False, "error": err}
        return {**runner.start(home), "state": runner.state}

    @router.post("/zalo-listener/stop")
    async def stop():
        write_cfg(deps, {"enabled": False})
        return runner.stop()

    app.include_router(router)

    async def autostart():
        """Bật lại listener sau khi Javis khởi động, nếu chủ đã bật trước đó."""
        cfg = read_cfg(deps)
        if not cfg.get("enabled"):
            return
        home, err = _home_of(deps, cfg.get("conn_id", ""))
        if err:
            runner.state, runner.error = "error", err
            return
        runner.start(home)

    return type("ZaloListenerFeature", (), {
        "runner": runner, "autostart": staticmethod(autostart),
        "read_cfg": staticmethod(lambda: read_cfg(deps)),
        # Lộ ra để test được CẢ chuỗi lọc → khử trùng → rate → báo, không chỉ vỏ HTTP
        # (endpoint đẩy việc qua create_task nên test qua HTTP không chờ được kết quả).
        "handle_event": staticmethod(_handle),
    })()
