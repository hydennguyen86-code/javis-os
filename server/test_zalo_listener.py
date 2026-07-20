"""Test listener Zalo liên tục (sidecar webhook). Chạy tay / CI:

    cd server && python test_zalo_listener.py

KHÔNG mạng, KHÔNG spawn npx. Phủ phần thuần: chuẩn hoá event (nhiều cách đặt tên
trường vì payload zalo-agent-cli chưa chốt), bộ lọc (tắt/bật, tin của chính mình,
dm_only, từ khoá có dấu lẫn không dấu, thread theo dõi, giờ im lặng), khử trùng
msgId, và giới hạn tần suất.
"""
import os
import sys
import tempfile
from datetime import datetime, timedelta, timezone

os.environ.setdefault("JAVIS_STATE_DIR", tempfile.mkdtemp(prefix="javis-zalo-"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

_fails = []
def check(n, c):
    print(("ok  " if c else "FAIL ") + n)
    if not c: _fails.append(n)


import zalo_listener as zl  # noqa: E402

VN = timezone(timedelta(hours=7))
def at(h, m=0):
    return datetime(2026, 7, 20, h, m, tzinfo=VN)


# ---- 1. Chuẩn hoá event (payload CLI chưa chốt → phải nhận nhiều biến thể) ----
e = zl.normalize_event({"event": "message", "data": {
    "msgId": "m1", "threadId": "t1", "type": 0,
    "content": "Cho hỏi giá con ốc này", "uidFrom": "u9", "dName": "Khách A"}})
check("normalize: dạng data lồng + type 0 = chat riêng",
      e["msg_id"] == "m1" and e["thread_id"] == "t1" and e["thread_type"] == "user"
      and "giá" in e["text"] and e["sender"] == "Khách A")

e2 = zl.normalize_event({"type": "message", "message_id": "m2", "thread_id": "t2",
                         "threadType": "group", "text": "ship về Hà Nội nhé", "isSelf": True})
check("normalize: dạng phẳng + snake_case + threadType chữ",
      e2["msg_id"] == "m2" and e2["thread_type"] == "group" and e2["is_self"] is True)

e3 = zl.normalize_event({"event": "message", "data": {"msgId": "m3", "threadId": "t3",
                         "content": {"title": "còn hàng không shop"}}})
check("normalize: content dạng object thì lấy title/text",
      "còn hàng" in e3["text"] and e3["msg_id"] == "m3")

check("normalize: rác thì không nổ, trả dict rỗng an toàn",
      zl.normalize_event(None)["msg_id"] == "" and zl.normalize_event("xin chao")["text"] == "")


# ---- 2. Bộ lọc ----
CFG = {"enabled": True, "dm_only": True, "keywords": ["giá", "còn hàng", "đặt"],
       "threads": [], "quiet_hours": ""}
def ev(**kw):
    base = {"kind": "message", "msg_id": "x", "thread_id": "t1", "thread_type": "user",
            "text": "cho hỏi giá cái này", "sender": "Khách", "is_self": False}
    base.update(kw)
    return base

ok, why = zl.should_notify(ev(), CFG, now=at(10))
check("lọc: tin riêng khớp từ khoá thì báo", ok and why == "")

ok, why = zl.should_notify(ev(), {**CFG, "enabled": False}, now=at(10))
check("lọc: tắt thì không báo", not ok and why == "tắt")

ok, why = zl.should_notify(ev(is_self=True), CFG, now=at(10))
check("lọc: tin của chính mình thì bỏ", not ok and why == "tin của mình")

ok, why = zl.should_notify(ev(text="hôm nay trời đẹp"), CFG, now=at(10))
check("lọc: không khớp từ khoá thì bỏ", not ok and why == "không khớp từ khoá")

ok, why = zl.should_notify(ev(thread_type="group"), CFG, now=at(10))
check("lọc: dm_only thì bỏ tin nhóm", not ok and why == "nhóm")

ok, _ = zl.should_notify(ev(thread_type="group"), {**CFG, "dm_only": False}, now=at(10))
check("lọc: tắt dm_only thì nhận tin nhóm", ok)

ok, _ = zl.should_notify(ev(text="CHO HỎI GIA CAI NAY"), CFG, now=at(10))
check("lọc: khớp từ khoá bỏ dấu + không phân biệt hoa thường", ok)

ok, _ = zl.should_notify(ev(text="alo shop ơi"), {**CFG, "keywords": []}, now=at(10))
check("lọc: keywords rỗng = không lọc nội dung", ok)

ok, _ = zl.should_notify(ev(text="alo shop oi", thread_id="t9"),
                         {**CFG, "threads": ["t9"]}, now=at(10))
check("lọc: thread theo dõi thì báo bất kể từ khoá", ok)

ok, why = zl.should_notify(ev(kind="reaction"), CFG, now=at(10))
check("lọc: sự kiện không phải tin nhắn thì bỏ", not ok and why == "không phải tin nhắn")

ok, why = zl.should_notify(ev(text=""), CFG, now=at(10))
check("lọc: tin rỗng (ảnh/sticker) mà đang lọc từ khoá thì bỏ",
      not ok and why == "không khớp từ khoá")

QUIET = {**CFG, "quiet_hours": "23-07"}
ok, why = zl.should_notify(ev(), QUIET, now=at(2))
check("lọc: 2h sáng nằm trong giờ im lặng 23-07", not ok and why == "giờ im lặng")
ok, _ = zl.should_notify(ev(), QUIET, now=at(23, 30))
check("lọc: 23h30 cũng im lặng (khoảng vắt qua nửa đêm)", not ok)
ok, _ = zl.should_notify(ev(), QUIET, now=at(10))
check("lọc: 10h sáng thì báo bình thường", ok)
ok, _ = zl.should_notify(ev(), {**CFG, "quiet_hours": "rác"}, now=at(2))
check("lọc: quiet_hours sai định dạng thì bỏ qua luật, không nổ", ok)


# ---- 3. Khử trùng msgId ----
s = zl.SeenSet(cap=4)
check("dedup: lần đầu là mới", s.is_new("a"))
check("dedup: lần hai bị chặn", not s.is_new("a"))
for k in ("b", "c", "d", "e", "f"):
    s.is_new(k)
check("dedup: vượt trần thì cắt bớt, không phình vô hạn", len(s._seen) <= 4)
check("dedup: msgId rỗng thì luôn cho qua (không gộp nhầm tin khác nhau)",
      s.is_new("") and s.is_new(""))


# ---- 4. Giới hạn tần suất ----
r = zl.RateLimiter(limit=3, window_s=60)
check("rate: 3 tin đầu lọt", all(r.allow(now=1000 + i) for i in range(3)))
check("rate: tin thứ 4 trong cửa sổ bị chặn", not r.allow(now=1010))
check("rate: qua cửa sổ thì mở lại", r.allow(now=1100))


# ---- 5. Endpoint + chuỗi xử lý thật (lọc → khử trùng → rate → báo) ----
import asyncio  # noqa: E402
import json as _json  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

def json_dumps_safe(o):
    return _json.dumps(o, ensure_ascii=False)

_settings = {"zalo_listener": {**zl.DEFAULT_CFG, "enabled": True, "secret": "s3cret",
                               "keywords": ["giá"], "conn_id": "c1"}}
_sent = []

async def _fake_notify(owner, text):
    _sent.append((owner, text))
    return True, ""

app = FastAPI()
feat = zl.register(app, zl.ZaloListenerDeps(
    read_settings=lambda: _settings,
    write_settings=lambda s: _settings.update(s),
    get_connection=lambda cid: {"config": {"home_dir": "/khong-ton-tai"}} if cid == "c1" else None,
    notify=_fake_notify,
    port=lambda: 7777,
))
client = TestClient(app)

body = {"event": "message", "data": {"msgId": "w1", "threadId": "t1", "type": 0,
                                     "content": "shop ơi giá bao nhiêu"}}
r = client.post(zl.HOOK_PATH, json=body, headers={zl.SECRET_HEADER: "sai-secret"})
check("endpoint: sai secret thì 403", r.status_code == 403)

r = client.post(zl.HOOK_PATH, json=body, headers={zl.SECRET_HEADER: "s3cret"})
check("endpoint: đúng secret thì 200 và trả ngay", r.status_code == 200 and r.json() == {"ok": True})

r = client.post(zl.HOOK_PATH, content=b"khong-phai-json", headers={zl.SECRET_HEADER: "s3cret"})
check("endpoint: body rác vẫn 200 (không để CLI phải thử lại)", r.status_code == 200)

# `zalo-agent-cli --webhook` chỉ POST JSON trần, KHÔNG đặt được header tuỳ ý → nếu chỉ gác
# bằng header thì mọi tin bị 403 và tính năng chết câm. Secret PHẢI đi được qua query.
r = client.post(zl.HOOK_PATH + "?k=s3cret", json=body)
check("endpoint: secret qua query cũng lọt (đường sidecar thật sự dùng)", r.status_code == 200)
r = client.post(zl.HOOK_PATH + "?k=sai", json=body)
check("endpoint: secret query sai thì vẫn 403", r.status_code == 403)

_argv = zl._Runner(zl.ZaloListenerDeps(lambda: _settings, lambda s: None, lambda c: None,
                                       _fake_notify, lambda: 7777))._argv({"secret": "s3cret",
                                                                           "dm_only": True})
check("sidecar: URL webhook có mang secret (nếu quên thì listener chạy mà tin bị 403 hết)",
      _argv is None or any("k=s3cret" in a for a in _argv))
check("sidecar: dm_only bật thì truyền --filter dm",
      _argv is None or ("dm" in _argv and "--filter" in _argv))

cfg = zl.read_cfg(zl.ZaloListenerDeps(lambda: _settings, lambda s: None,
                                      lambda c: None, _fake_notify, lambda: 0))

# msgId RIÊNG cho phần này: "w1" ở trên đã đi qua endpoint nên đã nằm trong set khử trùng
# dùng chung - lấy lại sẽ bị chặn đúng như thiết kế và làm test hiểu nhầm là hỏng.
body_fresh = {"event": "message", "data": {"msgId": "w9", "threadId": "t1", "type": 0,
                                           "content": "shop ơi giá bao nhiêu"}}

async def _run():
    _sent.clear()
    await feat.handle_event(zl.normalize_event(body_fresh), cfg)
    await feat.handle_event(zl.normalize_event(body_fresh), cfg)     # trùng msgId
    await feat.handle_event(zl.normalize_event(
        {"event": "message", "data": {"msgId": "w2", "threadId": "t1",
                                      "content": "chào shop"}}), cfg)   # không khớp từ khoá
asyncio.run(_run())
check("chuỗi xử lý: khớp từ khoá thì báo đúng 1 lần (tin trùng và tin lạc bị loại)",
      len(_sent) == 1 and "giá bao nhiêu" in _sent[0][1])

r = client.post("/zalo-listener/status")
check("status: có endpoint trạng thái", client.get("/zalo-listener/status").status_code == 200)
st = client.get("/zalo-listener/status").json()
check("status: KHÔNG lộ secret ra frontend",
      "secret" not in st.get("cfg", {}) and "s3cret" not in json_dumps_safe(st))

r = client.post("/zalo-listener/start", json={"conn_id": "khong-co"})
check("start: connection không tồn tại thì báo lỗi rõ, không spawn",
      r.json().get("ok") is False and "Chưa chọn" in r.json().get("error", ""))

r = client.post("/zalo-listener/start", json={"conn_id": "c1"})
check("start: home_dir không tồn tại thì đòi quét QR lại",
      r.json().get("ok") is False and "QR" in r.json().get("error", ""))


print("\n" + ("TAT CA OK" if not _fails else f"{len(_fails)} FAIL: {_fails}"))
sys.exit(1 if _fails else 0)
