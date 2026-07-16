"""Test trần description skill + hằng số router. Chạy tay / CI:

    cd server && ../.venv/Scripts/python.exe test_skill_caps.py

Không cần pytest, không chạm mạng.
Phủ: hằng số SKILL_DESC_MAX/SKILL_LIST_MAX, validate_description (quá dài, boilerplate,
hợp lệ, rỗng), fallback _meta_of dùng chung trần.
"""
import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("JAVIS_STATE_DIR", tempfile.mkdtemp(prefix="javis-capstest-"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import skill_router  # noqa: E402

_fails = []


def check(name, cond):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        _fails.append(name)


# ---- hằng số ----
check("SKILL_DESC_MAX = 150", getattr(skill_router, "SKILL_DESC_MAX", None) == 150)
check("SKILL_LIST_MAX = 20", getattr(skill_router, "SKILL_LIST_MAX", None) == 20)

# ---- validate_description ----
v = skill_router.validate_description
check("description hợp lệ -> None", v("Chuyển HTML sang file Webcake .pke.") is None)
check("description rỗng -> None (body-fallback lo)", v("") is None)
check("description None -> None", v(None) is None)

long_desc = "x" * 151
r = v(long_desc)
check("description 151 ký tự -> bị từ chối", isinstance(r, str))
check("lý do từ chối có nêu số ký tự thật", r is not None and "151" in r)
check("lý do từ chối có nêu trần", r is not None and "150" in r)
check("description đúng 150 ký tự -> lọt", v("x" * 150) is None)

check("bắt boilerplate 'Kích hoạt khi'",
      isinstance(v("Kích hoạt khi người dùng muốn tạo ảnh"), str))
check("bắt boilerplate 'Sử dụng skill này khi'",
      isinstance(v("Sử dụng skill này khi cần vẽ"), str))
check("KHÔNG bắt 'Dùng khi cần' (mở đầu hợp lệ, ngắn)",
      v("Dùng khi cần tạo ảnh minh hoạ phong cách flat 2D") is None)

# ---- _meta_of fallback dùng chung trần ----
tmp = Path(tempfile.mkdtemp(prefix="javis-capsbrain-"))
d = tmp / "skills" / "khong-co-desc"
d.mkdir(parents=True)
(d / "SKILL.md").write_text("---\nname: Không mô tả\n---\n" + ("y" * 400) + "\n",
                            encoding="utf-8")
metas = skill_router.list_enabled_meta(tmp)
got = next((m for m in metas if m["slug"] == "khong-co-desc"), None)
check("_meta_of fallback trả về skill", got is not None)
check("fallback cắt theo SKILL_DESC_MAX chứ không phải 140",
      got is not None and len(got["description"]) == skill_router.SKILL_DESC_MAX)

if _fails:
    print(f"\nFAIL - test_skill_caps: {len(_fails)} lỗi: {_fails}")
    sys.exit(1)
print("\nOK - test_skill_caps: tất cả pass")
