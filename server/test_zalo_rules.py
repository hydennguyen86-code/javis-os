"""Test chính sách Zalo theo từng cuộc chat. Chạy tay / CI:

    cd server && python test_zalo_rules.py

KHÔNG mạng, KHÔNG engine, KHÔNG spawn gì. Phủ: đọc ghi file luật (vòng tròn), khớp
tên nhóm nhập nhằng, năm chế độ quyết định đúng, mốc chờ của nhac-quen, và bất biến
"bốn chế độ đầu không đụng engine".
"""
import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("JAVIS_STATE_DIR", tempfile.mkdtemp(prefix="javis-zrule-"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

_fails = []
def check(n, c):
    print(("ok  " if c else "FAIL ") + n)
    if not c: _fails.append(n)


import zalo_rules as zr  # noqa: E402

BRAIN = tempfile.mkdtemp(prefix="javis-zbrain-")


def ev(**kw):
    base = {"kind": "message", "msg_id": "m1", "thread_id": "t1", "thread_type": "group",
            "text": "cho hỏi giá cái này", "sender": "Khách", "sender_uid": "u9", "is_self": False}
    base.update(kw)
    return base


# ---- 1. Ghi rồi đọc lại phải ra đúng cái đã ghi ----
r = {"thread_id": "t1", "thread_name": "Nhóm Kim Khí Hà Lộc", "mode": "chatbot",
     "enabled": True, "owner_uid": "uOwner", "max_reply_per_hour": 5,
     "script": "Bot trả lời về giờ mở cửa.\nGặp khiếu nại thì đẩy cho chủ."}
p = zr.save_rule(BRAIN, r)
check("file: ghi ra đúng <brain>/Javis/zalo/<slug>.md",
      Path(p).parent == zr.rules_dir(BRAIN) and Path(p).name == "nhom-kim-khi-ha-loc.md")

back = zr.parse_rule(Path(p).read_text(encoding="utf-8"), p)
check("vòng tròn: thread_id giữ nguyên", back["thread_id"] == "t1")
check("vòng tròn: mode giữ nguyên", back["mode"] == "chatbot")
check("vòng tròn: enabled giữ nguyên", back["enabled"] is True)
check("vòng tròn: kịch bản nhiều dòng không vỡ", "khiếu nại" in back["script"]
      and back["script"].count("\n") == 1)
check("vòng tròn: trần tin mỗi giờ giữ nguyên", back["max_reply_per_hour"] == 5)
check("kịch bản nằm ở THÂN file, không nhồi vào YAML",
      Path(p).read_text(encoding="utf-8").split("---")[2].strip().startswith("Bot trả lời"))

check("liệt kê: thấy luật vừa ghi", len(zr.list_rules(BRAIN)) == 1)
check("brain chưa có thư mục luật thì trả rỗng, không nổ",
      zr.list_rules(tempfile.mkdtemp(prefix="javis-trong-")) == [])

# Mode lạ (gõ sai tay) phải rơi về im lặng, KHÔNG được coi như chatbot
odd = zr.parse_rule("---\nmode: tu-tra-loi-het\nenabled: true\n---\nx")
check("an toàn: mode lạ rơi về im-lang chứ không đoán thành chatbot",
      odd["mode"] == "im-lang")


# ---- 2. Khớp tên nhóm: nhập nhằng thì KHÔNG được đoán ----
cands = [{"id": "t1", "name": "Nhóm Kim Khí Hà Lộc"},
         {"id": "t2", "name": "Nhóm Kim Khí Bán Lẻ"},
         {"id": "t3", "name": "Khách lẻ Minh"}]
check("khớp tên: gõ đúng id thì trúng ngay", [c["id"] for c in zr.match_threads(cands, "t2")] == ["t2"])
check("khớp tên: gõ đủ tên thì trúng đúng một",
      [c["id"] for c in zr.match_threads(cands, "nhóm kim khí hà lộc")] == ["t1"])
check("khớp tên: gõ thiếu dấu vẫn trúng",
      [c["id"] for c in zr.match_threads(cands, "nhom kim khi ha loc")] == ["t1"])
check("khớp tên: mơ hồ thì trả CẢ HAI để hỏi lại, không tự chọn",
      len(zr.match_threads(cands, "kim khí")) == 2)
check("khớp tên: không có gì khớp thì rỗng", zr.match_threads(cands, "zzz") == [])
check("khớp tên: chuỗi rỗng thì rỗng (không quét trúng tất cả)", zr.match_threads(cands, "  ") == [])


# ---- 3. Năm chế độ ----
def rule(**kw):
    base = {"thread_id": "t1", "mode": "bao-het", "enabled": True, "keywords": [],
            "escalate_after_min": 30, "owner_uid": "uOwner"}
    base.update(kw)
    return base

check("chưa có luật thì không làm gì", zr.decide(None, ev())[0] == zr.BO)
check("luật tắt thì không làm gì", zr.decide(rule(enabled=False), ev())[1] == "luật đang tắt")
check("im-lang: chỉ ghi nhận", zr.decide(rule(mode="im-lang"), ev())[0] == zr.BO)
check("bao-het: mọi tin đều báo", zr.decide(rule(mode="bao-het"), ev())[0] == zr.BAO)
check("tu-khoa: khớp thì báo",
      zr.decide(rule(mode="tu-khoa", keywords=["giá"]), ev())[0] == zr.BAO)
check("tu-khoa: không khớp thì thôi",
      zr.decide(rule(mode="tu-khoa", keywords=["ship"]), ev())[0] == zr.BO)
check("tu-khoa: khớp bỏ dấu",
      zr.decide(rule(mode="tu-khoa", keywords=["giá"]), ev(text="GIA BAO NHIEU"))[0] == zr.BAO)
check("nhac-quen: đặt mốc chờ chứ không báo ngay",
      zr.decide(rule(mode="nhac-quen"), ev())[0] == zr.CHO)
check("chatbot: chuyển cho bot", zr.decide(rule(mode="chatbot"), ev())[0] == zr.BOT)
check("tin của chính tài khoản Javis thì bỏ (không tự nói chuyện với mình)",
      zr.decide(rule(), ev(is_self=True))[0] == zr.BO)
for k in ("old_messages", "seen_messages", "delivered_messages"):
    check(f"'{k}' không kích hoạt gì (tránh dội tin cũ lúc nối lại)",
          zr.decide(rule(), ev(kind=k))[0] == zr.BO)


# ---- 4. Mốc chờ của nhac-quen ----
nq = rule(mode="nhac-quen", escalate_after_min=30)
check("mốc: khách nhắn thì đặt mốc", zr.pending_action(nq, ev()) == "dat")
check("mốc: CHỦ trả lời thì xoá mốc (chủ là thành viên khác trong nhóm)",
      zr.pending_action(nq, ev(sender_uid="uOwner")) == "xoa")
check("mốc: chưa khai owner_uid thì tin nào cũng chỉ đặt mốc (sẽ nhắc nhầm - phải cảnh báo)",
      zr.pending_action(rule(mode="nhac-quen", owner_uid=""), ev(sender_uid="uOwner")) == "dat")
check("mốc: chế độ khác thì không dính gì tới mốc", zr.pending_action(rule(), ev()) == "")

rules = [nq]
now = 1000000.0
check("quá hạn: chưa đủ 30 phút thì im",
      zr.due_reminders(rules, {"t1": {"since": now - 600}}, now=now) == [])
due = zr.due_reminders(rules, {"t1": {"since": now - 1900}}, now=now)
check("quá hạn: đủ 30 phút thì tới lượt báo", len(due) == 1 and due[0][0] == "t1")
check("quá hạn: mốc của cuộc chat KHÔNG có luật thì bỏ qua",
      zr.due_reminders(rules, {"tXX": {"since": now - 9999}}, now=now) == [])
check("quá hạn: luật đã tắt thì không nhắc nữa",
      zr.due_reminders([rule(mode="nhac-quen", enabled=False)],
                       {"t1": {"since": now - 9999}}, now=now) == [])


# ---- 5. Bất biến: module luật KHÔNG được chạm engine ----
src = open("zalo_rules.py", encoding="utf-8").read()
check("bất biến: module luật không gọi engine / mạng / MCP",
      not any(k in src for k in ("claude_engine", "claude_sdk", "httpx", "requests",
                                 "subprocess", "mcp_client", "mcp_hub")))


# ---- 6. Plugin javis_zalo_rule: chủ đặt luật bằng LỜI, không có form nhập ----
import importlib.util  # noqa: E402
import types  # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "zrp", str(Path(__file__).resolve().parents[1] / "system" / "plugins" / "zalo-rule" / "plugin.py"))
zp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(zp)
zp._roster = lambda: [{"id": "g1", "name": "Nhom Kim Khi Ha Loc"},
                      {"id": "g2", "name": "Nhom Kim Khi Ban Le"}]
B2 = tempfile.mkdtemp(prefix="javis-zplug-")
ctx = types.SimpleNamespace(vault_root=B2, data_dir=B2, slug="zalo-rule")

out = zp._handler({"op": "set", "thread": "kim khi", "mode": "bao-het"}, ctx)
check("plugin: tên mơ hồ thì TỪ CHỐI kèm danh sách, không tự chọn (gắn nhầm nhóm là bot "
      "đi trả lời khách nhóm khác)",
      out.startswith("ERROR") and "g1" in out and "g2" in out)
check("plugin: luật KHÔNG được tạo khi tên mơ hồ", zr.list_rules(B2) == [])

out = zp._handler({"op": "set", "thread": "g2", "mode": "chatbot", "script": "Giờ mở cửa 7h-19h."}, ctx)
r2 = zr.rule_for(zr.list_rules(B2), "g2")
check("plugin: chatbot LUÔN tạo ở trạng thái TẮT (nó nhắn thẳng cho khách thật)",
      r2 and r2["mode"] == "chatbot" and r2["enabled"] is False)
check("plugin: dặn engine đọc lại kịch bản cho chủ nghe rồi mới bật", "bật không" in out)
check("plugin: kịch bản được ghi xuống", "7h-19h" in (r2 or {}).get("script", ""))

zp._handler({"op": "set", "thread": "g1", "mode": "nhac-quen", "escalate_after_min": 30}, ctx)
r1 = zr.rule_for(zr.list_rules(B2), "g1")
check("plugin: bốn chế độ không-chatbot thì bật ngay được", r1 and r1["enabled"] is True)
out = zp._handler({"op": "show", "thread": "g1"}, ctx)
check("plugin: thiếu owner_uid thì CẢNH BÁO là sẽ nhắc cả khi chủ đã trả lời",
      "CHƯA khai owner_uid" in out)

out = zp._handler({"op": "set", "thread": "g1", "mode": "khong-co-che-do-nay"}, ctx)
check("plugin: chế độ lạ thì từ chối, không ghi bừa", out.startswith("ERROR"))

zp._handler({"op": "off", "thread": "g1"}, ctx)
check("plugin: tắt được luật", zr.rule_for(zr.list_rules(B2), "g1")["enabled"] is False)

out = zp._handler({"op": "set", "thread": "zzz", "mode": "bao-het"}, ctx)
check("plugin: không khớp tên thì nói rõ đang thấy những cuộc chat nào",
      out.startswith("ERROR") and "Nhom Kim Khi" in out)


print("\n" + ("TAT CA OK" if not _fails else f"{len(_fails)} FAIL: {_fails}"))
sys.exit(1 if _fails else 0)
