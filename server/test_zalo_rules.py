"""Test chính sách Zalo theo từng cuộc chat. Chạy tay / CI:

    cd server && python test_zalo_rules.py

KHÔNG mạng, KHÔNG engine, KHÔNG spawn gì. Phủ: đọc ghi file luật (vòng tròn), khớp
tên nhóm nhập nhằng, bốn chế độ quyết định đúng, mốc chờ của nhac-quen, và bất biến
"module luật không đụng engine". Không còn chế độ chatbot: Javis chỉ đọc và báo.
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
r = {"thread_id": "t1", "thread_name": "Nhóm Kim Khí Hà Lộc", "mode": "nhac-quen",
     "enabled": True, "owner_uid": "uOwner", "escalate_after_min": 45, "thread_type": "group",
     "script": "Ghi chú của chủ về nhóm.\nDòng thứ hai."}
p = zr.save_rule(BRAIN, r)
check("file: ghi ra đúng <brain>/Javis/zalo/<slug>.md, tên file GẮN thread_id (chống trùng)",
      Path(p).parent == zr.rules_dir(BRAIN) and Path(p).name == "nhom-kim-khi-ha-loc-t1.md")

back = zr.parse_rule(Path(p).read_text(encoding="utf-8"), p)
check("vòng tròn: thread_id giữ nguyên", back["thread_id"] == "t1")
check("vòng tròn: mode giữ nguyên", back["mode"] == "nhac-quen")
check("vòng tròn: enabled giữ nguyên", back["enabled"] is True)
check("vòng tròn: thread_type giữ nguyên (để dựng đúng nhãn nhóm sau khi khởi động lại)",
      back["thread_type"] == "group")
check("vòng tròn: phần thân nhiều dòng không vỡ", "thứ hai" in back["script"]
      and back["script"].count("\n") == 1)
check("vòng tròn: escalate_after_min giữ nguyên", back["escalate_after_min"] == 45)
check("phần thân nằm ở THÂN file, không nhồi vào YAML",
      Path(p).read_text(encoding="utf-8").split("---")[2].strip().startswith("Ghi chú"))

check("liệt kê: thấy luật vừa ghi", len(zr.list_rules(BRAIN)) == 1)
check("brain chưa có thư mục luật thì trả rỗng, không nổ",
      zr.list_rules(tempfile.mkdtemp(prefix="javis-trong-")) == [])

# CHỐNG TRÙNG FILE: hai cuộc chat KHÁC id nhưng CÙNG tên (sổ cố ý đặt tên trùng cho nhóm
# chưa biết tên) phải ra HAI file khác nhau. Trước đây slug theo tên -> cùng file -> lưu
# cái sau xoá luật cái trước -> tick của nó biến mất khi tải lại.
BC = tempfile.mkdtemp(prefix="javis-collide-")
pa = zr.save_rule(BC, {"thread_id": "g111", "thread_name": "Minh Quý", "mode": "im-lang", "enabled": True})
pb = zr.save_rule(BC, {"thread_id": "g222", "thread_name": "Minh Quý", "mode": "im-lang", "enabled": True})
check("chống trùng: hai chat cùng TÊN khác ID ra HAI file riêng", pa != pb)
check("chống trùng: cả hai luật cùng tồn tại, không cái nào bị ghi đè",
      len(zr.list_rules(BC)) == 2
      and {x["thread_id"] for x in zr.list_rules(BC)} == {"g111", "g222"})

# Mode lạ (gõ sai tay) phải rơi về im lặng, KHÔNG được đoán thành chế độ nào khác
odd = zr.parse_rule("---\nmode: tu-tra-loi-het\nenabled: true\n---\nx")
check("an toàn: mode lạ rơi về im-lang", odd["mode"] == "im-lang")
# File luật CŨ có mode=chatbot (đã bỏ) phải tự hạ về im-lang: im lặng, KHÔNG tự trả lời.
old_bot = zr.parse_rule("---\nmode: chatbot\nenabled: true\n---\nx")
check("an toàn: luật chatbot cũ tự hạ về im-lang (bỏ tính năng tự trả lời)",
      old_bot["mode"] == "im-lang")


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


# ---- 3. Bốn chế độ ----
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
check("bỏ chatbot: không còn hằng BOT trong module", not hasattr(zr, "BOT"))
check("bỏ chatbot: mode 'chatbot' cũ (nếu còn sót) coi như im lặng, KHÔNG trả lời",
      zr.decide(rule(mode="chatbot"), ev())[0] == zr.BO)
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
check("plugin: tên mơ hồ thì TỪ CHỐI kèm danh sách, không tự chọn (gắn nhầm nhóm là "
      "báo/im nhầm cuộc chat)",
      out.startswith("ERROR") and "g1" in out and "g2" in out)
check("plugin: luật KHÔNG được tạo khi tên mơ hồ", zr.list_rules(B2) == [])

# Chatbot đã bị bỏ: plugin phải TỪ CHỐI mode này, không tạo luật.
out = zp._handler({"op": "set", "thread": "g2", "mode": "chatbot"}, ctx)
check("plugin: 'chatbot' không còn hợp lệ, bị từ chối", out.startswith("ERROR") and "mode" in out)
check("plugin: không tạo luật khi mode không hợp lệ", zr.rule_for(zr.list_rules(B2), "g2") is None)

out = zp._handler({"op": "set", "thread": "g2", "mode": "bao-het"}, ctx)
r2 = zr.rule_for(zr.list_rules(B2), "g2")
check("plugin: chế độ báo hợp lệ thì bật ngay được (chỉ báo cho chủ, sai cũng chỉ phiền chủ)",
      r2 and r2["mode"] == "bao-het" and r2["enabled"] is True)

zp._handler({"op": "set", "thread": "g1", "mode": "nhac-quen", "escalate_after_min": 30}, ctx)
r1 = zr.rule_for(zr.list_rules(B2), "g1")
check("plugin: chế độ nhac-quen bật ngay được", r1 and r1["enabled"] is True)
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


# ---- 7. Javis phải BIẾT là có công cụ này ----
# Lỗi thật: chủ dặn về cách ứng xử một nhóm, Javis đáp "ghi nhớ rồi" và tạo một file
# preference trong Memory - tức là NGHĨ đây là sở thích chứ không phải hành động. Không
# luật nào được tạo nên chẳng có gì đổi. Công cụ nạp được nhưng system prompt không hề
# nhắc tới Zalo, nên Javis không biết mà với tới.
CLAUDE_MD = (Path(__file__).resolve().parents[1] / "CLAUDE.md").read_text(encoding="utf-8")
check("prompt: CLAUDE.md có dạy dùng javis_zalo_rule (trước đây không nhắc chữ Zalo nào)",
      "javis_zalo_rule" in CLAUDE_MD)
check("prompt: nói rõ đây là HÀNH ĐỘNG, không phải ghi nhớ sở thích",
      "không phải ghi nhớ" in CLAUDE_MD and "đừng ghi vào Memory" in CLAUDE_MD)
for cau in ("đừng báo nữa", "30 phút chưa ai trả lời"):
    check(f"prompt: có ví dụ câu thật của chủ - '{cau}'", cau in CLAUDE_MD)

desc = None
for t in zp.__dict__.get("_LAST_TOOLS", []) or []:
    pass
import types as _t2  # noqa: E402
_captured = {}
zp.register(_t2.SimpleNamespace(
    register_tool=lambda **kw: _captured.update(kw), vault_root=B2, data_dir=B2, slug="zalo-rule"))
desc = _captured.get("description", "")
check("tool: mô tả dặn thẳng là đừng chỉ ghi Memory", "đừng chỉ ghi" in desc)
check("tool: mô tả nói rõ Javis KHÔNG tự trả lời khách trên Zalo",
      "KHÔNG tự trả lời" in desc and "javis_zalo_send" in desc)
for cau in ("đừng báo telegram nữa", "im lặng thôi"):
    check(f"tool: mô tả có câu kích hoạt thật - '{cau}'", cau in desc)


print("\n" + ("TAT CA OK" if not _fails else f"{len(_fails)} FAIL: {_fails}"))
sys.exit(1 if _fails else 0)
