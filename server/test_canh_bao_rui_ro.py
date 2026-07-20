"""Cảnh báo rủi ro của connector phải HIỆN LÚC NGƯỜI DÙNG QUYẾT ĐỊNH, không nằm im trong file.

    cd server && ../.venv/Scripts/python.exe test_canh_bao_rui_ro.py

Không cần pytest, không chạm mạng.

Bối cảnh: trường `risk` trong mcp-catalog.json trước đây CHỈ được vẽ ở luồng QR (openQrFlow) và ở
hộp thoại đổi quyền. 15/16 connector có cảnh báo thì không bao giờ hiện cảnh báo lúc bấm Kết nối,
gồm cả facebook-personal (dán cookie tài khoản thật) và google-keep (token toàn quyền tài khoản
Google). Test này giữ cho lỗi đó không quay lại.
"""
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(os.path.dirname(os.path.abspath(__file__))).parent
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

_fails = []


def check(name, cond):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        _fails.append(name)


js = (ROOT / "dashboard" / "console.js").read_text(encoding="utf-8")


def than_ham(ten):
    """Cắt thân một hàm JS theo dấu ngoặc nhọn cân bằng."""
    i = js.index(f"function {ten}(")
    k = js.index("{", i)
    depth = 0
    for m in range(k, len(js)):
        if js[m] == "{":
            depth += 1
        elif js[m] == "}":
            depth -= 1
            if depth == 0:
                return js[k:m + 1]
    raise AssertionError(f"không cắt được thân hàm {ten}")


# ---- cả 3 luồng đấu nối đều phải vẽ cảnh báo ----
for ten in ("openApikeyFlow", "openOauthFlow", "openQrFlow"):
    than = than_ham(ten)
    check(f"{ten} có vẽ khối cảnh báo rủi ro (conn-risk)", "conn-risk" in than)
    check(f"{ten} chỉ vẽ khi connector THẬT SỰ có cảnh báo (không hiện hộp rỗng)",
          re.search(r"con\.risk\s*\?", than) is not None)

# ---- catalog: mọi connector rủi ro cao phải có cảnh báo ----
cat = json.loads((ROOT / "system" / "mcp-catalog.json").read_text(encoding="utf-8"))
by_id = {c["id"]: c for c in cat["connectors"]}

for cid in ("google-keep", "facebook-personal", "zalo"):
    check(f"{cid} có khai risk", bool((by_id.get(cid) or {}).get("risk")))

# ---- google-keep: mô tả trên THẺ phải nói rõ bán kính thiệt hại ----
# Người dùng thấy mô tả này TỪ NGOÀI danh sách, trước khi bấm vào. Tên connector là "Google Keep"
# nên mô tả đúng NĂNG LỰC, nhưng token lại có toàn quyền tài khoản - phải nói ra.
keep = by_id.get("google-keep") or {}
mota = keep.get("description", "")
check("mô tả thẻ google-keep cảnh báo token toàn quyền tài khoản",
      "toàn quyền" in mota.lower() and "google" in mota.lower())
check("mô tả thẻ nói rõ KHÔNG phải OAuth giới hạn phạm vi",
      "oauth" in mota.lower() or "phạm vi" in mota.lower())

# Javis chỉ LÀM được đúng Keep - đây là điểm trấn an, phải giữ đúng.
tm = keep.get("tool_meta") or {}
tat_ca = (tm.get("read") or []) + (tm.get("write") or []) + (tm.get("danger") or [])
check("google-keep vẫn chỉ khai tool Keep, không lan sang Gmail/Drive",
      tat_ca and not any(t.startswith(("gmail", "drive", "mail_", "file_")) for t in tat_ca))

# ---- CANARY: chứng minh phép cắt thân hàm có quyền lực thật ----
_than_qr = than_ham("openQrFlow")
check("CANARY: thân openQrFlow cắt ra phải NGẮN hơn cả file rất nhiều "
      "-> tức đang soi đúng một hàm chứ không phải quét cả console.js",
      0 < len(_than_qr) < len(js) / 4)

if _fails:
    print(f"\nFAIL - test_canh_bao_rui_ro: {len(_fails)} lỗi: {_fails}")
    sys.exit(1)
print("\nOK - test_canh_bao_rui_ro: tất cả pass")
