"""Test tool javis_schedule (plugin bundled). Chạy tay / CI:

    cd server && python test_javis_schedule.py

Bối cảnh: trước tool này, chat muốn tạo việc định kỳ phải TỰ GÕ YAML frontmatter vào
Javis/loops/<slug>.md, hoặc shell ra curl POST /reminders (reminders.py:17). Tool gói cả hai
lại và tự route: nhắc/cron/một-lần -> kho reminders; việc lặp + bền -> file .md.

KHÔNG chạm mạng: mọi test đều gọi hàm thuần hoặc ghi file trong thư mục tạm.

Phủ:
- _route_kind: phân loại đúng lịch -> kho nào.
- _slugify_vn: tên tiếng Việt -> slug ascii, không đụng file đã có.
- op=create việc lặp -> ghi .md đúng chỗ, frontmatter đọc lại được, enabled=false.
- op=create nhắc -> KHÔNG ghi .md (phải đi đường reminders).
- Tool đăng ký đúng tên + min_mode.
"""
import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("JAVIS_STATE_DIR", tempfile.mkdtemp(prefix="javis-schedtest-"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, str(Path(__file__).parent.parent / "system" / "plugins" / "javis-schedule"))

import plugin as sched  # noqa: E402

_fails = []


def check(name, cond):
    print(("ok  " if cond else "FAIL ") + name)
    if not cond:
        _fails.append(name)


# ---- 1. Route: lịch nào về kho nào ----
check("route: '120m' -> loop (lặp, bền)", sched._route_kind("120m", False) == "loop")
check("route: 'mỗi 2 tiếng' -> loop", sched._route_kind("mỗi 2 tiếng", False) == "loop")
check("route: '0 7 * * *' -> reminder (cron, reminders đã có sẵn)",
      sched._route_kind("0 7 * * *", False) == "reminder")
check("route: '30 phút nữa' -> reminder (một lần)", sched._route_kind("30 phút nữa", False) == "reminder")
check("route: notify_only ép về reminder dù lịch lặp",
      sched._route_kind("120m", True) == "reminder")

# ---- 2. Slug ----
check("slug: bỏ dấu tiếng Việt", sched._slugify_vn("Đọc source mỗi 2 tiếng") == "doc-source-moi-2-tieng")
check("slug: không rỗng khi tên toàn ký tự lạ", sched._slugify_vn("!!!") != "")

# ---- 3. Tạo việc lặp -> ghi .md ----
_vault = tempfile.mkdtemp(prefix="javis-vault-")
res = sched._create_loop_file(_vault, name="Quét đơn mỗi 2 tiếng",
                              prompt="Mỗi vòng đọc số đơn hôm nay qua MCP POS rồi ghi nháp.",
                              schedule="120m", owner_chat="123")
f = Path(_vault) / "Javis" / "loops" / "quet-don-moi-2-tieng.md"
check("loop: ghi đúng <vault>/Javis/loops/<slug>.md", f.is_file())
body = f.read_text(encoding="utf-8") if f.is_file() else ""
check("loop: frontmatter có type: loop", "type: loop" in body)
check("loop: MẶC ĐỊNH enabled: false (luật an toàn CLAUDE.md)", "enabled: false" in body)
check("loop: MẶC ĐỊNH mode: suggest (không bao giờ tự đặt full)", "mode: suggest" in body)
check("loop: interval_min từ '120m'", "interval_min: 120" in body)
check("loop: giữ owner_chat để báo đúng người", 'owner_chat: "123"' in body)
check("loop: thân file LÀ prompt (tự đủ, không phụ thuộc chat)", "MCP POS" in body)
check("loop: trả về đường dẫn cho model biết đã ghi đâu", "quet-don-moi-2-tieng" in str(res))

# ---- 4. Không ghi đè loop đã có bằng bản ascii song song ----
# self_improve.py:273 lấy ĐỊNH DANH theo TÊN FILE. Tạo trùng slug -> phải báo, không âm thầm fork.
res2 = sched._create_loop_file(_vault, name="Quét đơn mỗi 2 tiếng", prompt="khác", schedule="60m")
check("loop: trùng slug -> báo lỗi rõ, không đẻ bản sao",
      str(res2).startswith("ERROR:") or "đã có" in str(res2).lower())

# ---- 5. Tool đăng ký đúng ----
_regs = []


class _FakeCtx:
    # data_dir là @property trên PluginContext thật (plugins_host.py:223) nên KHÔNG gán được;
    # fake ctx chỉ cần thứ handler thật sự đọc.
    vault_root = _vault
    slug = "javis-schedule"

    def register_tool(self, **kw):
        _regs.append(kw)

    def register_hook(self, *a, **k):
        pass


sched.register(_FakeCtx())
check("đăng ký: đúng 1 tool", len(_regs) == 1)
check("đăng ký: tên javis_schedule", _regs and _regs[0].get("name") == "javis_schedule")
check("đăng ký: min_mode=safe (tạo việc là GHI, chặn ở suggest)",
      _regs and _regs[0].get("min_mode") == "safe")
desc = (_regs[0].get("description") or "") if _regs else ""
check("đăng ký: mô tả nói rõ KHI NÀO gọi", len(desc) > 60 and "op" in desc)
props = ((_regs[0].get("schema") or {}).get("properties") or {}) if _regs else {}
check("đăng ký: schema có op/name/schedule/prompt",
      {"op", "name", "schedule", "prompt"}.issubset(set(props)))


if _fails:
    print(f"\nFAIL - test_javis_schedule: {len(_fails)} lỗi: {_fails}")
    sys.exit(1)
print("\nOK - test_javis_schedule: tất cả pass")
