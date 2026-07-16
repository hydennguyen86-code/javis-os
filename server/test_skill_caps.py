"""Test trần description skill + hằng số router. Chạy tay / CI:

    cd server && ../.venv/Scripts/python.exe test_skill_caps.py

Không cần pytest, không chạm mạng.
Phủ: hằng số SKILL_DESC_MAX/SKILL_LIST_MAX, validate_description (quá dài, boilerplate,
hợp lệ, rỗng), fallback _meta_of dùng chung trần.
"""
import ast
import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("JAVIS_STATE_DIR", tempfile.mkdtemp(prefix="javis-capstest-"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import skill_router  # noqa: E402
import system_sync  # noqa: E402

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

# ---- không còn hằng số cắt nào nằm rải rác (chống mọc lại 'thước thứ hai') ----
_SRC = Path(os.path.dirname(os.path.abspath(__file__)))


def _region(path, start_marker, end_marker):
    """Lấy đoạn mã giữa hai mốc để chỉ soi đúng vùng render router."""
    text = (_SRC / path).read_text(encoding="utf-8")
    i = text.index(start_marker)
    j = text.index(end_marker, i)
    return text[i:j]


hub = _region("mcp_hub.py", "metas = skill_router.list_enabled_meta(vault_root)",
              'add("javis_use_skill"')
check("mcp_hub không còn literal [:60]", "[:60]" not in hub)
check("mcp_hub không còn literal 20", "20" not in hub)
check("mcp_hub dùng SKILL_DESC_MAX", "SKILL_DESC_MAX" in hub)
check("mcp_hub dùng SKILL_LIST_MAX", "SKILL_LIST_MAX" in hub)

blk = _region("main.py", "def _skill_router_block", "@app.get(\"/javis/index\")")
check("main không còn literal [:100]", "[:100]" not in blk)
check("main không còn literal 15", "15" not in blk)
check("main dùng SKILL_DESC_MAX", "SKILL_DESC_MAX" in blk)
check("main dùng SKILL_LIST_MAX", "SKILL_LIST_MAX" in blk)

# ---- LINT: mọi skill HỆ THỐNG phải lọt trần + sạch boilerplate ----
# Đây là rào chặn tái phát: bug cắt cụt description không được quay lại qua skill ship kèm app.
# Dùng system_sync.SYSTEM_SKILLS_DIR chứ không hardcode đường dẫn; và KHÔNG rglob toàn repo
# (sẽ dính bản mirror trong brains/ và .claude/worktrees/).
_sys_dir = system_sync.SYSTEM_SKILLS_DIR
check("tìm thấy thư mục skill hệ thống", _sys_dir.is_dir())
for _slug in sorted(system_sync.system_skill_slugs()):
    _f = _sys_dir / _slug / "SKILL.md"
    _meta, _ = skill_router.split_frontmatter(_f.read_text(encoding="utf-8"))
    _desc = _meta.get("description", "")
    # Bẫy dấu hai chấm làm hỏng frontmatter theo HAI đường khác nhau - phải chặn CẢ HAI
    # TRƯỚC khi gọi validate_description:
    #  1) 'description: {a: b}' hoặc block lồng nhau -> YAML ra DICT. validate_description làm
    #     (desc or "").strip(); dict là truthy nên lọt qua 'or' rồi nổ AttributeError, giết
    #     luôn vòng lặp -> các skill xếp sau KHÔNG được chấm nữa. Đúng cái kiểu hỏng mà
    #     check()/_fails sinh ra để tránh. Chặn bằng isinstance, báo như 1 FAIL bình thường.
    #  2) 'description: Foo: bar' (không bọc nháy) -> YAML NÉM LỖI, split_frontmatter tha lỗi
    #     trả {} -> description RỖNG. validate_description coi rỗng là hợp lệ (POST /skills có
    #     body-fallback lo) nên lint sẽ XANH dù skill vừa mất sạch mô tả. Với skill HỆ THỐNG
    #     thì rỗng = hỏng thật, phải bắt riêng - không thì lint mù đúng bug nó sinh ra để canh.
    if not isinstance(_desc, str):
        check(f"skill hệ thống '{_slug}' description phải là chuỗi (YAML trả về "
              f"{type(_desc).__name__} -> frontmatter vỡ, skill mất mô tả lúc chạy; "
              "bọc cả giá trị trong nháy kép)", False)
        continue
    # Hỏng thì DỪNG ở đây (continue), đừng chấm tiếp: validate_description coi rỗng là hợp lệ
    # nên nó sẽ in thêm 'ok ... description hợp lệ (0 ký tự)' ngay dưới dòng FAIL - lint tự mâu
    # thuẫn với chính mình là lint người ta học cách phớt lờ.
    _co_desc = bool(_desc.strip())
    check(f"skill hệ thống '{_slug}' có description không rỗng (rỗng = frontmatter vỡ "
          "hoặc thiếu description; skill hệ thống bắt buộc có mô tả để route được)",
          _co_desc)
    if not _co_desc:
        continue
    _err = skill_router.validate_description(_desc)
    check(f"skill hệ thống '{_slug}' description hợp lệ ({len(_desc)} ký tự)"
          + (f" → {_err}" if _err else ""), _err is None)

# ---- POST /skills phải ép trần TRƯỚC khi tạo thư mục ----
# Canh tính chất: request có description sai bị TỪ CHỐI và KHÔNG để lại folder skill rỗng
# trên đĩa. Lint CI (Task 3) chỉ phủ skill HỆ THỐNG nên không có gì khác trong bộ test bắt
# được nếu chốt chặn ở đường API rơi mất.
#
# ĐỌC MÃ NGUỒN, KHÔNG import - cố ý: gọi save_skill thật đòi import main.py, tức kéo cả app
# FastAPI vào bộ test (nặng + rủi ro tác dụng phụ lúc import). ast.parse đọc file dưới dạng
# văn bản y như quét chuỗi, KHÔNG dựng app và KHÔNG chạy dòng mã nào của nó.
#
# VÌ SAO AST CHỨ KHÔNG PHẢI SO CHUỖI (đừng "đơn giản hoá" ngược lại): so chuỗi không phân
# biệt nổi MÃ với CHÚ THÍCH. Chốt chặn bị comment lại vẫn còn nguyên chữ 'if desc_err' và
# 'status_code=400' trong nguồn nên check kiểu `"if desc_err" in _guard` vẫn XANH trong khi
# chốt đã chết - đúng bằng regression cần chặn. Thêm bao nhiêu chuỗi cũng không vá được, vì
# lỗi nằm ở tầng: phải soi cây cú pháp. AST cũng miễn nhiễm cái bẫy `_save.index(...)` lấy
# lần xuất hiện ĐẦU TIÊN của tên hàm (một docstring nhắc tên là vùng quét lệch ngay).
#
# CHỐT CHẶN ĐẢO (`if not desc_err: return ...`) bị CỐ Ý coi là HỎNG, không phải chấp nhận:
# nó nhận description sai và từ chối cái đúng. Test đòi test của If là tham chiếu TRẦN
# `desc_err`, nên bản đảo không khớp -> không tìm thấy chốt -> FAIL. Đó là chủ ý.
#
# GIỚI HẠN (nói thẳng để không ai tưởng đây là bất khả xâm phạm): đây là kiểm tra CẤU TRÚC
# tĩnh. Nó chứng minh chốt chặn TỒN TẠI dưới dạng mã sống, rẽ nhánh trên kết quả
# validate_description, trả 400, và đứng trước mkdir. Nó KHÔNG chạy endpoint nên không
# chứng minh hành vi lúc chạy (vd validate_description bị mock/đổi ngữ nghĩa, hay có đường
# ghi đĩa khác trước đó). Hành vi của chính validate_description do các check ở trên phủ.
_main_tree = ast.parse((_SRC / "main.py").read_text(encoding="utf-8"))
_save_node = next((n for n in ast.walk(_main_tree)
                   if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                   and n.name == "save_skill"), None)
check("tìm thấy hàm save_skill trong main.py (AST)", _save_node is not None)


def _returns_400(if_node):
    """Thân nhánh có return JSONResponse(..., status_code=400) không."""
    for stmt in if_node.body:
        for n in ast.walk(stmt):
            if not isinstance(n, ast.Return) or not isinstance(n.value, ast.Call):
                continue
            for kw in n.value.keywords:
                if (kw.arg == "status_code" and isinstance(kw.value, ast.Constant)
                        and kw.value.value == 400):
                    return True
    return False


if _save_node is not None:
    # Lời gọi validate_description phải được GÁN vào desc_err - buộc chốt chặn dưới đây
    # đúng là đang rẽ trên kết quả kiểm tra, chứ không phải một biến trùng tên nào khác.
    _vd_assign = [n for n in ast.walk(_save_node)
                  if isinstance(n, ast.Assign) and isinstance(n.value, ast.Call)
                  and isinstance(n.value.func, ast.Attribute)
                  and n.value.func.attr == "validate_description"
                  and any(isinstance(t, ast.Name) and t.id == "desc_err" for t in n.targets)]
    check("POST /skills gọi validate_description và gán vào desc_err (AST, không tính "
          "chú thích)", bool(_vd_assign))
    # Chốt chặn: `if desc_err:` (tham chiếu TRẦN, bản đảo `if not desc_err` cố ý KHÔNG khớp)
    # + thân có return 400.
    _guards = [n for n in ast.walk(_save_node)
               if isinstance(n, ast.If) and isinstance(n.test, ast.Name)
               and n.test.id == "desc_err" and _returns_400(n)]
    check("POST /skills có chốt chặn SỐNG 'if desc_err: return ...400' (AST - chốt bị "
          "comment lại hoặc đảo thành 'if not desc_err' sẽ trượt check này)",
          bool(_guards))
    _mkdirs = [n.lineno for n in ast.walk(_save_node)
               if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
               and n.func.attr == "mkdir"]
    check("tìm thấy lời gọi mkdir trong save_skill (AST)", bool(_mkdirs))
    if _guards and _mkdirs and _vd_assign:
        check("POST /skills chặn TRƯỚC mọi mkdir (request bị từ chối không để lại folder "
              "skill rỗng trên đĩa)",
              min(g.lineno for g in _guards) < min(_mkdirs))
        check("chốt chặn nằm SAU lời gọi validate_description (rẽ nhánh trên biến đã gán)",
              min(a.lineno for a in _vd_assign) < min(g.lineno for g in _guards))

if _fails:
    print(f"\nFAIL - test_skill_caps: {len(_fails)} lỗi: {_fails}")
    sys.exit(1)
print("\nOK - test_skill_caps: tất cả pass")
