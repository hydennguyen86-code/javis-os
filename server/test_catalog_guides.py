"""Lint cách TRÌNH BÀY hướng dẫn connector trong system/mcp-catalog.json. Chạy tay / CI:

    cd server && ../.venv/Scripts/python.exe test_catalog_guides.py

Không cần pytest, không chạm mạng.

Vì sao có file này: guide được render vào <div class="conn-guide"> với CSS `white-space: pre-line`,
nghĩa là xuống dòng trong JSON hiện đúng thành xuống dòng trên giao diện. Trước đây cả 23 guide
đều là MỘT đoạn chạy dài không ngắt, đọc trên modal hẹp rất mệt và các bước (1)(2)(3) chen ngang
giữa dòng. Test này giữ cho lỗi đó không quay lại.
"""
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(os.path.dirname(os.path.abspath(__file__))).parent
CATALOG = ROOT / "system" / "mcp-catalog.json"

# Guide dài hơn ngần này mà không có dòng nào thì chắc chắn khó đọc trên modal.
LEN_CAN_XUONG_DONG = 200
# Một dòng dài hơn ngần này là đang nhồi quá nhiều ý vào một hơi.
DAI_TOI_DA_MOI_DONG = 200

_fails = []


def check(name, cond):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        _fails.append(name)


data = json.loads(CATALOG.read_text(encoding="utf-8"))
connectors = data["connectors"]
check(f"đọc được catalog ({len(connectors)} connector)", len(connectors) > 0)

# ---- cấm em dash / en dash ở MỌI chuỗi hiển thị cho user ----
# Quy tắc cứng của người dùng: em dash làm giọng đọc TTS bị khựng.
raw = CATALOG.read_text(encoding="utf-8")
check("cả file không có em dash (U+2014)", "—" not in raw)
check("cả file không có en dash (U+2013)", "–" not in raw)

# ---- trình bày guide ----
thieu_xuong_dong = []
dong_qua_dai = []
buoc_khong_dau_dong = []
guide_rong = []

for c in connectors:
    cid = c["id"]
    guide = ((c.get("auth") or {}).get("guide") or "")
    if not guide.strip():
        guide_rong.append(cid)
        continue

    if len(guide) > LEN_CAN_XUONG_DONG and "\n" not in guide:
        thieu_xuong_dong.append(f"{cid}({len(guide)} ký tự, 0 xuống dòng)")

    for line in guide.split("\n"):
        if len(line) > DAI_TOI_DA_MOI_DONG:
            dong_qua_dai.append(f"{cid}({len(line)} ký tự)")
            break

    # Bước đánh số phải MỞ ĐẦU một dòng, không chen ngang giữa câu.
    # Bỏ qua "1." đứng sau chữ số (vd "1.40", "0.9.110") và mốc thời gian.
    for m in re.finditer(r"(?<![\d,.])(\(\d\)|\b\d\.)\s", guide):
        truoc = guide[:m.start()]
        dau_dong = (not truoc) or truoc.endswith("\n")
        if not dau_dong:
            buoc_khong_dau_dong.append(f"{cid}(…{guide[max(0, m.start() - 25):m.end() + 12]!r})")
            break

check("mọi guide dài đều có xuống dòng: " + (", ".join(thieu_xuong_dong) or "đạt"),
      not thieu_xuong_dong)
check("không dòng nào quá dài: " + (", ".join(dong_qua_dai) or "đạt"),
      not dong_qua_dai)
check("bước đánh số luôn mở đầu một dòng: " + (", ".join(buoc_khong_dau_dong) or "đạt"),
      not buoc_khong_dau_dong)
check("mọi connector đều có guide: " + (", ".join(guide_rong) or "đạt"), not guide_rong)

# ---- CSS phải thật sự tôn trọng xuống dòng, nếu không guide nhiều dòng là vô nghĩa ----
css = (ROOT / "dashboard" / "console.css").read_text(encoding="utf-8")
khoi = ""
for i, line in enumerate(css.split("\n")):
    if line.strip().startswith(".conn-guide"):
        khoi = "\n".join(css.split("\n")[i:i + 4])
        break
check("CSS .conn-guide giữ xuống dòng (white-space: pre-line)", "pre-line" in khoi)
check("CSS .conn-guide bẻ được chuỗi dài không khoảng trắng (overflow-wrap)",
      "overflow-wrap" in khoi or "word-break" in khoi)

# ---- CANARY: chứng minh luật 'bước phải đầu dòng' thật sự bắt được, không phải luôn-xanh ----
_xau = "Làm 1 lần: (1) mở trang (2) lấy key."
_bat_duoc = False
for m in re.finditer(r"(?<![\d,.])(\(\d\)|\b\d\.)\s", _xau):
    truoc = _xau[:m.start()]
    if truoc and not truoc.endswith("\n"):
        _bat_duoc = True
        break
check("CANARY: chuỗi kiểu cũ 'Làm 1 lần: (1) ... (2) ...' PHẢI bị luật bắt "
      "-> tức luật có quyền lực thật", _bat_duoc)

if _fails:
    print(f"\nFAIL - test_catalog_guides: {len(_fails)} lỗi: {_fails}")
    sys.exit(1)
print("\nOK - test_catalog_guides: tất cả pass")
