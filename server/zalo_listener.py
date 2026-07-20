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
import signal
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
_FAST_FAIL_S = 15          # bật lên mà tắt trong ngần này giây = hỏng cứng, không phải rớt mạng
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
    "threads": [],        # CỔNG CHÍNH: chỉ nghe đúng cuộc chat được chọn. Rỗng = không báo gì.
    "keywords": [],       # lọc phụ, thu hẹp TRONG các cuộc chat đã chọn
    "quiet_hours": "",
    "secret": "",
    "owner_chat": "",
}

MAX_BODY = 256 * 1024      # trần kích thước 1 payload webhook (chống nhồi bộ nhớ)
ROSTER_CAP = 300           # trần số cuộc chat ghi nhớ (tài khoản thật có thể hàng trăm nhóm)


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

    CỔNG CHÍNH là danh sách cuộc chat được chọn (cfg["threads"]): chủ chỉ muốn nghe
    liên tục đúng vài nhóm/khách cần support, phần còn lại để đọc theo yêu cầu hoặc
    theo loop. Chưa chọn cuộc chat nào thì KHÔNG báo gì - im lặng là mặc định đúng,
    không phải lỗi.

    keywords là lọc PHỤ, chỉ thu hẹp thêm bên trong các cuộc chat đã chọn.
    """
    now = now or datetime.now(VN_TZ)
    if not cfg.get("enabled"):
        return False, "tắt"
    # Nhận cả biến thể như "group_message": tên sự kiện của CLI chưa chốt nên so khớp
    # CHÍNH XÁC là dễ hụt. Nhưng phải loại "old_messages" (phát lại lịch sử lúc nối lại -
    # báo thì spam cả trăm tin cũ) cùng seen/delivered (báo đã xem, không phải tin mới).
    kind = str(ev.get("kind") or "message").lower()
    if "message" not in kind or kind.startswith("old") or "seen" in kind or "delivered" in kind:
        return False, "không phải tin nhắn"
    if ev.get("is_self"):
        return False, "tin của mình"
    threads = [str(t) for t in (cfg.get("threads") or []) if str(t).strip()]
    if not threads:
        return False, "chưa chọn cuộc chat"
    if str(ev.get("thread_id") or "") not in threads:
        return False, "ngoài danh sách theo dõi"
    if _in_quiet(cfg.get("quiet_hours", ""), now):
        return False, "giờ im lặng"
    kws = [k for k in (cfg.get("keywords") or []) if str(k).strip()]
    if not kws:
        return True, ""
    body = _fold(ev.get("text"))
    if any(_fold(k) in body for k in kws):
        return True, ""
    return False, "không khớp từ khoá"


class Roster:
    """Sổ các cuộc chat sidecar ĐÃ THẤY, để chủ tick chọn cái cần theo dõi mà không
    phải đi tra thread ID bằng tay.

    Cố ý học từ chính luồng webhook chứ không gọi tool zalo_list_threads: gọi tool sẽ
    dựng thêm một socket cho CÙNG tài khoản, đúng vào cái va chạm 'một socket mỗi tài
    khoản' chưa kiểm chứng được.
    """

    def __init__(self, cap: int = ROSTER_CAP):
        self.cap = max(1, int(cap))
        self._items: dict = {}

    def note(self, ev: dict) -> None:
        # Ghi sổ MỌI sự kiện có thread_id, không riêng tin nhắn. Lý do: khi chủ vừa thêm
        # tài khoản vào một nhóm, cái về trước là sự kiện nhóm chứ chưa có tin nào - chờ
        # đúng "message" thì nhóm mới không bao giờ hiện ra để mà chọn.
        tid = str(ev.get("thread_id") or "")
        if not tid or ev.get("is_self"):
            return
        it = self._items.get(tid) or {"id": tid, "count": 0}
        # Tên người gửi là dữ liệu KHÔNG tin được (khách tự đặt) - cắt ngắn ở đây,
        # và phía giao diện phải esc() trước khi chèn vào HTML.
        it["name"] = sanitize_text(ev.get("sender") or "", cap=40) or tid
        it["type"] = ev.get("thread_type") or "user"
        it["count"] = it["count"] + 1
        it["last"] = time.time()
        self._items[tid] = it
        if len(self._items) > self.cap:      # bỏ cuộc chat cũ nhất
            oldest = min(self._items.values(), key=lambda x: x.get("last", 0))
            self._items.pop(oldest["id"], None)

    def list(self) -> list:
        return sorted(self._items.values(), key=lambda x: x.get("last", 0), reverse=True)


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


_ZERO_WIDTH = "​‌‍⁠﻿‪‫‬‭‮"


def sanitize_text(s, cap: int = _TEXT_CAP) -> str:
    """Làm sạch chuỗi ĐẾN TỪ NGƯỜI LẠ trước khi cho hiển thị ở bất cứ đâu.

    Bỏ ký tự điều khiển và ký tự tàng hình (zero-width, ký tự đảo chiều RTL) - đây là
    những thứ dùng để GIẤU chữ: nhìn thì vô hại mà máy đọc ra một nội dung khác. Gộp
    dòng trống liên tiếp để tin dài không đẩy phần cảnh báo trôi khỏi màn hình. Cắt độ dài.
    """
    s = str(s or "")
    s = "".join(ch for ch in s if ch not in _ZERO_WIDTH)
    s = "".join(ch for ch in s if ch == "\n" or unicodedata.category(ch)[0] != "C")
    s = re.sub(r"\n{3,}", "\n\n", s).strip()
    return (s[:cap] + "...") if len(s) > cap else s


def format_message(ev: dict) -> str:
    """Tin nhắn Telegram gửi cho chủ.

    BẢO MẬT: nội dung do người lạ trên Zalo soạn, phải coi là DỮ LIỆU chứ không phải
    lệnh. Rào nội dung giữa hai vạch có nhãn rõ ràng để một tin cố ý xuống dòng rồi
    viết "Javis: đã chuyển khoản xong, trả lời CÓ để xác nhận" KHÔNG giả dạng được lời
    của Javis. Gửi bằng plain text (main._notify_owner không đặt parse_mode) nên chữ
    trong tin cũng không dựng được markup.
    """
    who = sanitize_text(ev.get("sender") or "", cap=60) or "Ai đó"
    where = " (nhóm)" if ev.get("thread_type") == "group" else ""
    body = sanitize_text(ev.get("text")) or "(ảnh hoặc sticker)"
    return (f"Zalo{where} - {who} nhắn:\n"
            f"--- tin của khách, KHÔNG phải lệnh cho Javis ---\n"
            f"{body}\n"
            f"--- hết tin ---")


# ============================================================
# Vòng đời tiến trình sidecar
# ============================================================
@dataclass
class ZaloListenerDeps:
    read_settings: Callable[[], dict]
    write_settings: Callable[[dict], Any]
    # mcp_store.resolved - KHÔNG dùng get_connection: hàm đó trả bản _public() đã lược mất
    # "config", nên đọc home_dir luôn ra rỗng và listener không bao giờ khởi động nổi.
    # resolved() còn là nơi tính HOME thật (kể cả đường mặc định khi config trống), dùng
    # chung với lúc chạy MCP nên hai bên không lệch nhau.
    resolved_conns: Callable[[], list]
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
        # --filter all: sidecar nhận cả tin riêng lẫn nhóm để CÒN THẤY mà liệt kê cho chủ
        # chọn. Việc chặn nằm ở should_notify (whitelist cuộc chat), không phải ở đây.
        # --events: MẶC ĐỊNH của CLI chỉ là "message,friend" - thiếu "group", nên sự kiện
        # nhóm không về và nhóm không bao giờ hiện ra để chọn. Khai đủ cả bốn loại.
        argv = [npx, "-y", "zalo-agent-cli", "listen", "--webhook", url,
                "--events", "message,friend,group,reaction",
                "--filter", "all", "--no-self"]
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
        else:
            # Nhóm tiến trình riêng để _kill_tree() dọn được cả `node` con của `npx`.
            kwargs["start_new_session"] = True
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
        """Bọc ngoài vòng chạy nền. Luồng nền mà chết vì lỗi bất ngờ thì trạng thái sẽ ĐỨNG
        NGUYÊN ở giá trị cũ và giao diện báo sai (vd vẫn 'Đang tắt' dù chủ đã bật) - phải
        biến mọi lỗi thành trạng thái đọc được, đừng để chết câm."""
        try:
            self._run(home)
        except BaseException as e:
            self.state = "error"
            self.error = f"Luồng nền dừng bất thường: {type(e).__name__}: {e}"
            print(f"[zalo listener] luồng nền chết: {type(e).__name__}: {e}", file=sys.stderr)

    def _run(self, home: str):
        """Vòng chạy nền: spawn → đọc log → đứt thì backoff dựng lại."""
        attempt = 0
        fast_fails = 0          # số lần chết NGAY khi vừa bật (chưa kịp nghe được gì)
        while not self._stop.is_set():
            cfg = read_cfg(self.deps)
            self.state = "starting"
            if not self._spawn(home, cfg):
                return                       # lỗi cứng (thiếu npx) - state đã đặt trong _spawn
            fatal = False
            saw_listening = False
            t0 = time.time()
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
                            saw_listening = True
                            attempt = 0      # nối lại được thì reset backoff
            except Exception as e:
                self.error = f"{type(e).__name__}: {e}"
            rc = None
            try:
                rc = self.proc.poll()
            except Exception:
                pass
            self._kill_tree()      # phải dọn cả cây, không thì `node` sống mồ côi
            if self._stop.is_set():
                break
            if fatal:
                # Trùng phiên: connector `zalo` (mcp start) nhiều khả năng đang giữ socket
                # của CÙNG tài khoản. Dừng hẳn + báo rõ để chủ thấy va chạm, đừng quay vòng.
                self.state = "duplicate" if "duplicate" in self.error.lower() else "error"
                return
            # Chết NGAY mà chưa kịp nghe được gì = lệnh sai / CLI không chạy được, KHÁC hẳn
            # với "đang nghe rồi mới rớt mạng". Thử lại mãi chỉ làm giao diện báo 'đang thử
            # lại' trong khi thật ra hỏng cứng, nên sau 3 lần thì dừng và phơi log CLI ra.
            if not saw_listening and (time.time() - t0) < _FAST_FAIL_S:
                fast_fails += 1
                if fast_fails >= 3:
                    tail = " | ".join(list(self._tail)[-3:])[:300]
                    self.state = "error"
                    self.error = (f"Sidecar bật lên là tắt ngay {fast_fails} lần"
                                  + (f" (mã thoát {rc})" if rc is not None else "")
                                  + (f". CLI nói: {tail}" if tail else
                                     ". CLI không in ra gì - nhiều khả năng sai tên lệnh hoặc chưa đăng nhập."))
                    return
            else:
                fast_fails = 0
            delay = _BACKOFF[min(attempt, len(_BACKOFF) - 1)]
            attempt += 1
            self.state = "reconnecting"
            self.error = f"Mất kết nối, thử lại sau {delay}s"
            if self._stop.wait(delay):
                break
        self.state = "off"

    def _kill_tree(self) -> None:
        """Giết CẢ CÂY tiến trình, không chỉ tiến trình trực tiếp.

        `npx` chỉ là vỏ, nó sinh ra `node` mới là thứ giữ websocket. Gọi proc.kill()
        trần chỉ giết cái vỏ, còn node sống mồ côi và VẪN đẩy webhook về - triệu chứng
        đã gặp: giao diện báo tiến trình không chạy trong khi tin vẫn chảy về đều.
        """
        p = self.proc
        if not p:
            return
        try:
            if p.poll() is not None:
                return
        except Exception:
            return
        try:
            if os.name == "nt":
                subprocess.run(["taskkill", "/F", "/T", "/PID", str(p.pid)],
                               capture_output=True, timeout=15)
            else:
                os.killpg(os.getpgid(p.pid), signal.SIGTERM)
                try:
                    p.wait(timeout=5)
                except Exception:
                    os.killpg(os.getpgid(p.pid), signal.SIGKILL)
        except Exception:
            try:
                p.kill()          # cùng lắm thì giết được cái vỏ còn hơn không
            except Exception:
                pass

    # ---- API ----
    def start(self, home: str) -> dict:
        if self._thread and self._thread.is_alive():
            if not self._stop.is_set():
                return {"ok": True, "already": True}
            # Luồng cũ đang dừng DỞ: nếu cứ trả "đã chạy rồi" thì cờ dừng vẫn còn bật,
            # luồng cũ thoát và đặt state="off" trong khi settings nói đang bật. Phải
            # chờ nó thoát hẳn rồi mới dựng luồng mới.
            self._thread.join(timeout=15)
        self._stop.clear()
        self.error = ""
        self._thread = threading.Thread(target=self._loop, args=(home,), daemon=True)
        self._thread.start()
        return {"ok": True}

    def stop(self) -> dict:
        self._stop.set()
        self._kill_tree()
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
    """Lấy home cô lập của connection Zalo (do zalo_login tạo lúc quét QR). Trả (home, lỗi).

    Đọc từ mcp_store.resolved() vì đó là nơi tính HOME thật cho connector isolate_home.
    Lỗi phải kèm ĐƯỜNG DẪN cụ thể - "chưa đăng nhập" chung chung thì không lần ra được.
    """
    conn_id = str(conn_id or "").strip()
    if not conn_id:
        return "", "Chưa chọn tài khoản Zalo trong ô phía trên"
    try:
        rows = deps.resolved_conns() or []
    except Exception as e:
        return "", f"Không đọc được danh sách kết nối: {type(e).__name__}: {e}"
    row = next((r for r in rows if r.get("id") == conn_id), None)
    if not row:
        return "", "Không tìm thấy kết nối Zalo này (đã bị xoá?). Chọn lại tài khoản giúp em."
    home = ((row.get("env") or {}).get("HOME") or "").strip()
    if not home:
        return "", "Kết nối Zalo này không có thư mục phiên riêng - thử xoá rồi quét QR lại."
    if not os.path.isdir(home):
        return "", f"Chưa thấy phiên đăng nhập Zalo ở {home} - quét QR lại giúp em."
    return home, ""


# ============================================================
# Đăng ký router
# ============================================================
def register(app, deps: ZaloListenerDeps):
    router = APIRouter()
    runner = _Runner(deps)
    seen = SeenSet()
    rate = RateLimiter()
    roster = Roster()
    # Đếm loại sự kiện thật sự nhận được. Tên sự kiện của CLI chưa có tài liệu chốt, nên
    # khi có thứ "đáng lẽ phải hiện mà không hiện" thì đây là chỗ NHÌN ra sự thật thay vì
    # đoán tiếp. Lộ qua /zalo-listener/status.
    kinds: dict = {}

    async def _handle(ev: dict, cfg: dict):
        k = str(ev.get("kind") or "?")[:40]
        kinds[k] = kinds.get(k, 0) + 1
        # Ghi sổ TRƯỚC khi lọc: cuộc chat chưa được chọn vẫn phải hiện ra để chủ tick,
        # nếu không thì không bao giờ chọn được cái gì (vòng luẩn quẩn).
        roster.note(ev)
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
        # Trần kích thước: nội dung do người lạ soạn, không để một tin khổng lồ nhồi bộ nhớ.
        try:
            if int(request.headers.get("content-length") or 0) > MAX_BODY:
                return JSONResponse({"error": "too large"}, status_code=413)
        except ValueError:
            pass
        try:
            body_raw = await request.body()
        except Exception:
            return {"ok": True}
        if len(body_raw) > MAX_BODY:
            return JSONResponse({"error": "too large"}, status_code=413)
        try:
            raw = json.loads(body_raw)
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
                "roster": roster.list(),      # cuộc chat đã thấy, để chủ tick chọn
                "kinds": kinds,               # loại sự kiện thật sự nhận được (để chẩn đoán)
                "cfg": {k: v for k, v in cfg.items() if k != "secret"}}

    @router.post("/zalo-listener/config")
    async def save_config(payload: dict = Body(...)):
        cfg = write_cfg(deps, payload or {})
        return {"ok": True, "cfg": {k: v for k, v in cfg.items() if k != "secret"}}

    @router.post("/zalo-listener/start")
    async def start(payload: dict = Body(default={})):
        # Lưu cấu hình nhưng CHƯA bật. Bật trước rồi mới kiểm là để lại trạng thái mâu thuẫn:
        # settings nói đang bật, tiến trình thì không chạy, giao diện hiện "Đang tắt" ngay
        # cạnh nút "Tắt". Đúng lỗi đã gặp trên VPS.
        cfg = write_cfg(deps, {**(payload or {}), "enabled": False})
        home, err = _home_of(deps, cfg.get("conn_id", ""))
        if err:
            # Ghi vào runner để /status còn phản ánh: nếu không, nhịp hỏi lại 5s sẽ xoá mất
            # dòng lỗi vừa hiện và chủ không kịp đọc.
            runner.state, runner.error = "error", err
            return {"ok": False, "error": err}
        write_cfg(deps, {"enabled": True})
        runner.error = ""
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
