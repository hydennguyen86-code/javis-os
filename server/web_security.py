"""
web_security.py - Chống CSRF + DNS-rebinding cho web API cục bộ của Javis.

Vì sao cần: dashboard nghe ở localhost:7777. Khi CHƯA đặt mật khẩu (chạy cá nhân trên máy),
một trang web độc bất kỳ trong trình duyệt của user có thể:
  1. fetch/POST tới http://localhost:7777/... → server VẪN xử lý (CORS chỉ chặn ĐỌC kết quả,
     không chặn request chạy) → hành động có side-effect vẫn xảy ra (CSRF-to-localhost).
  2. Trỏ một tên miền của kẻ tấn công về 127.0.0.1 (DNS-rebinding) để lách kiểm tra origin.

Lớp phòng thủ (tách khỏi main.py để test được mà không nạp cả app):
  - Request GHI (POST/PUT/DELETE/PATCH) có Origin CHÉO (khác Host, không thuộc allowlist) → chặn 403.
    Cùng-origin (Origin==Host) và client không-trình-duyệt (không gửi Origin, vd Claude CLI, curl)
    KHÔNG bị ảnh hưởng → 0 rủi ro khoá nhầm.
  - Khi CHƯA có cổng đăng nhập (no-auth): Host phải là localhost / IP / tên miền cấu hình - tên
    miền lạ (dấu hiệu DNS-rebinding) bị chặn. Khi ĐÃ bật auth thì bỏ qua bước Host (tránh khoá nhầm
    deploy sau reverse-proxy tên miền chưa khai) - lúc đó cookie + Origin-check đã đủ.

Allowlist: localhost/127.0.0.1/::1 + tên miền custom (settings.domain.custom) + env JAVIS_ALLOWED_HOSTS.
"""
from __future__ import annotations

import ipaddress
import os
import time

import config as cfgmod

_LOCALHOST = {"localhost", "127.0.0.1", "::1", "0.0.0.0"}
MUTATING = {"POST", "PUT", "DELETE", "PATCH"}

_cache = {"hosts": None, "ts": 0.0}
_CACHE_TTL = 5.0


def host_only(v) -> str:
    """Bóc hostname (bỏ scheme + path + port). Giữ IPv6 trong ngoặc: '[::1]:7777' → '::1'."""
    v = (v or "").strip().lower()
    if "://" in v:
        v = v.split("://", 1)[1]
    v = v.split("/", 1)[0]
    if v.startswith("["):            # [::1]:7777 hoặc [::1]
        return v[1:].split("]", 1)[0]
    if v.count(":") == 1:            # host:port
        return v.split(":", 1)[0]
    return v                          # bare host / bare IPv6 (hiếm)


def _is_ip(h: str) -> bool:
    try:
        ipaddress.ip_address(h)
        return True
    except ValueError:
        return False


def _compute_hosts() -> set:
    hosts = set(_LOCALHOST)
    try:
        dom = ((cfgmod.read_settings().get("domain") or {}).get("custom") or "").strip().lower()
        dom = host_only(dom)
        if dom:
            hosts.add(dom)
    except Exception:
        pass
    for h in (os.getenv("JAVIS_ALLOWED_HOSTS", "") or "").split(","):
        h = host_only(h)
        if h:
            hosts.add(h)
    return hosts


def allowed_web_hosts(_now=None) -> set:
    """Allowlist hostname (cache ngắn để khỏi đọc settings mỗi request)."""
    now = _now if _now is not None else time.time()
    if _cache["hosts"] is None or (now - _cache["ts"]) > _CACHE_TTL:
        _cache["hosts"] = _compute_hosts()
        _cache["ts"] = now
    return _cache["hosts"]


def invalidate():
    _cache["hosts"] = None


def csrf_decision(method: str, host_header: str, origin_header, gate_active: bool):
    """Trả None nếu CHO QUA, hoặc (status_code, message) nếu CHẶN. Hàm THUẦN - dễ test."""
    host = host_only(host_header)
    allowed = None
    # 1) CSRF: ghi + có Origin chéo (khác host, ngoài allowlist) → chặn.
    if method.upper() in MUTATING and origin_header:
        oh = host_only(origin_header)
        if oh != host:
            allowed = allowed_web_hosts()
            if oh not in allowed:
                return 403, "cross-origin request bị chặn"
    # 2) DNS-rebinding: chỉ siết Host khi CHƯA có cổng đăng nhập (trường hợp hở thật sự).
    if not gate_active and host:
        if not _is_ip(host):
            if allowed is None:
                allowed = allowed_web_hosts()
            if host not in allowed:
                return 403, "host không được phép"
    return None
