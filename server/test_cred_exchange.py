"""Test bước ĐỔI CREDENTIAL trên UI (server/cred_exchange.py). Chạy tay / CI:

    cd server && ../.venv/Scripts/python.exe test_cred_exchange.py

Không cần pytest, KHÔNG chạm mạng (handler thật được thay bằng handler giả).

Bất biến quan trọng nhất được phủ ở đây: App Password NGƯỜI DÙNG NHẬP KHÔNG BAO GIỜ ĐƯỢC LƯU.
Nó chỉ dùng một lần để đổi lấy master token rồi bị xoá khỏi dữ liệu trước khi ghi xuống đĩa.
"""
import os
import sys
import tempfile

os.environ.setdefault("JAVIS_STATE_DIR", tempfile.mkdtemp(prefix="javis-credtest-"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cred_exchange  # noqa: E402
import mcp_catalog  # noqa: E402

_fails = []


def check(name, cond):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        _fails.append(name)


CON = {
    "id": "thu-nghiem",
    "auth": {
        "fields": [
            {"key": "email", "env": "EMAIL"},
            {"key": "app_password", "optional": True},          # KHÔNG có env - chỉ là đầu vào
            {"key": "token", "env": "TOKEN", "optional": True},
        ],
        "exchange": {
            "handler": "gia_lap",
            "inputs": ["email", "app_password"],
            "output": "token",
            "drop": ["app_password"],
        },
    },
}

_goi = []


def _handler_gia(fields):
    _goi.append(dict(fields))
    if fields.get("app_password") == "sai":
        return None, "Mật khẩu ứng dụng không đúng."
    return "TOKEN-MOI-" + fields.get("email", ""), ""


cred_exchange.HANDLERS["gia_lap"] = _handler_gia

# ---- đổi thành công ----
_goi.clear()
out, err = cred_exchange.run(CON, {"email": "a@gmail.com", "app_password": "dung", "token": ""})
check("đổi thành công -> không lỗi", err == "")
check("đổi thành công -> token được điền", out.get("token") == "TOKEN-MOI-a@gmail.com")
check("BẢO MẬT: app_password bị XOÁ khỏi dữ liệu lưu", "app_password" not in out)
check("email vẫn được giữ", out.get("email") == "a@gmail.com")
check("handler nhận đúng đầu vào", _goi and _goi[0].get("app_password") == "dung")

# ---- đổi thất bại ----
out2, err2 = cred_exchange.run(CON, {"email": "a@gmail.com", "app_password": "sai", "token": ""})
check("đổi thất bại -> có lỗi tiếng Việt", "không đúng" in (err2 or ""))
check("BẢO MẬT: đổi thất bại thì app_password VẪN bị xoá", "app_password" not in (out2 or {}))
check("đổi thất bại -> token vẫn rỗng", not (out2 or {}).get("token"))

# ---- đã có token sẵn thì BỎ QUA đổi (đường lui thủ công) ----
_goi.clear()
out3, err3 = cred_exchange.run(CON, {"email": "a@gmail.com", "app_password": "dung",
                                     "token": "aas_et/co-san"})
check("đã dán sẵn token -> KHÔNG gọi handler", not _goi)
check("đã dán sẵn token -> giữ nguyên token người dùng nhập",
      out3.get("token") == "aas_et/co-san")
check("BẢO MẬT: đã dán sẵn token thì app_password vẫn bị xoá", "app_password" not in out3)
check("đã dán sẵn token -> không lỗi", err3 == "")

# ---- thiếu đầu vào ----
out4, err4 = cred_exchange.run(CON, {"email": "a@gmail.com", "app_password": "", "token": ""})
check("thiếu app_password và token -> báo lỗi rõ", bool(err4))
check("thiếu đầu vào -> KHÔNG gọi handler", len(_goi) == 0)

# ---- connector không khai exchange thì đi qua không đổi gì ----
out5, err5 = cred_exchange.run({"id": "khac", "auth": {"fields": []}},
                               {"api_key": "abc"})
check("connector không khai exchange -> giữ nguyên dữ liệu", out5 == {"api_key": "abc"})
check("connector không khai exchange -> không lỗi", err5 == "")

# ---- handler lạ (catalog KHÔNG được chỉ định mã tuỳ ý) ----
CON_LA = {"id": "la", "auth": {"fields": [], "exchange": {
    "handler": "khong_ton_tai", "inputs": ["a"], "output": "b", "drop": []}}}
out6, err6 = cred_exchange.run(CON_LA, {"a": "x"})
check("handler không có trong registry -> báo lỗi, không nổ", bool(err6))

# ---- google-keep trong catalog thật phải khai đúng ----
keep = mcp_catalog.get("google-keep")
ex = ((keep or {}).get("auth") or {}).get("exchange") or {}
check("google-keep khai exchange", ex.get("handler") == "google_master_token")
check("google-keep đổi ra master_token", ex.get("output") == "master_token")
check("BẢO MẬT: google-keep khai drop app_password", "app_password" in (ex.get("drop") or []))

fields = {f["key"]: f for f in ((keep or {}).get("auth") or {}).get("fields") or []}
check("google-keep có ô app_password", "app_password" in fields)
check("BẢO MẬT: ô app_password KHÔNG map ra env (không thể lọt vào tiến trình con)",
      not fields.get("app_password", {}).get("env"))
check("ô app_password là tuỳ chọn (còn đường lui dán token tay)",
      bool(fields.get("app_password", {}).get("optional")))
check("ô master_token thành tuỳ chọn (vì đã có đường app password)",
      bool(fields.get("master_token", {}).get("optional")))

env = mcp_catalog.build_env(keep, {"google_email": "a@gmail.com", "app_password": "SIEU-BI-MAT",
                                   "master_token": "aas_et/x"})
check("BẢO MẬT: app_password KHÔNG xuất hiện trong env dù có bị truyền nhầm vào",
      "SIEU-BI-MAT" not in str(env))

# ---- nút mở trang App Password của Google ----
links = (((keep or {}).get("auth") or {}).get("setup") or {}).get("links") or []
check("google-keep có nút mở trang tạo App Password",
      any("apppasswords" in (l.get("url") or "") for l in links))

# ---- ĐẦU-CUỐI: app_password có bao giờ chạm tới ĐĨA không? ----
# Đi đúng đường của endpoint /connect/add: cred_exchange.run -> mcp_store.add_connection,
# rồi đọc THẲNG file trên đĩa xem chuỗi bí mật có lọt ra không.
import json as _json  # noqa: E402
from pathlib import Path as _Path  # noqa: E402

import mcp_store  # noqa: E402

_BI_MAT = "ZZZbimatZZZ1234"          # 16 ký tự, dễ tìm trong file
cred_exchange.HANDLERS["google_master_token"] = lambda f: ("aas_et/gia-lap", "")
_fields, _err = cred_exchange.run(mcp_catalog.get("google-keep"), {
    "google_email": "a@gmail.com", "app_password": _BI_MAT, "master_token": "", "unsafe_mode": ""})
check("đầu-cuối: đổi không lỗi", _err == "")
check("đầu-cuối: master_token được điền từ handler", _fields.get("master_token") == "aas_et/gia-lap")

_cid, _e2 = mcp_store.add_connection("google-keep", {"label": "thử", "fields": _fields})
check("đầu-cuối: lưu được kết nối", bool(_cid) and not _e2)

_store = _Path(os.environ["JAVIS_STATE_DIR"]) / "mcp_servers.json"
_raw = _store.read_text(encoding="utf-8") if _store.exists() else ""
check("BẢO MẬT đầu-cuối: chuỗi App Password KHÔNG có trong file lưu trên đĩa",
      bool(_raw) and _BI_MAT not in _raw)

_conn = mcp_store.get_connection(_cid) or {}
check("BẢO MẬT đầu-cuối: không có khoá 'app_password' trong secrets đã lưu",
      "app_password" not in (_conn.get("secrets") or {}))

_res = next((c for c in mcp_store.resolved(enabled_only=False) if c["id"] == _cid), None)
check("BẢO MẬT đầu-cuối: app_password KHÔNG lọt vào env của tiến trình con",
      _res is not None and _BI_MAT not in str(_res.get("env") or {}))
check("đầu-cuối: master token ĐƯỢC truyền vào env cho keep-mcp",
      (_res or {}).get("env", {}).get("GOOGLE_MASTER_TOKEN") == "aas_et/gia-lap")

# ---- CANARY: chứng minh check 'app_password bị xoá' có quyền lực thật ----
CON_XAU = {"id": "xau", "auth": {"fields": [], "exchange": {
    "handler": "gia_lap", "inputs": ["email", "app_password"], "output": "token",
    "drop": []}}}          # CỐ Ý quên drop
out7, _ = cred_exchange.run(CON_XAU, {"email": "a@gmail.com", "app_password": "dung", "token": ""})
check("CANARY: cấu hình QUÊN drop thì app_password PHẢI còn lại -> tức check ở trên "
      "thật sự đang đo việc xoá, không phải luôn-xanh", "app_password" in out7)

if _fails:
    print(f"\nFAIL - test_cred_exchange: {len(_fails)} lỗi: {_fails}")
    sys.exit(1)
print("\nOK - test_cred_exchange: tất cả pass")
