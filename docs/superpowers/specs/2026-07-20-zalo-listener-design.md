# Zalo listener liên tục (sidecar webhook)

Ngày: 2026-07-20
Trạng thái: đã chốt thiết kế, đang thực thi

## Vấn đề

Javis đã nối được Zalo qua connector `zalo` (`zalo-agent-cli`, đăng nhập QR, xem
`server/zalo_login.py`). Nhưng connector đó là **pull-only**: phải gọi tool
`zalo_get_messages` mới biết có tin. Không có đường nào để Javis biết ngay khi
khách nhắn tới.

Hai thứ chặn việc nghe liên tục:

1. `mcp_client.py:30` đặt `_IDLE_TTL = 600`. Quá 10 phút không gọi tool là pool
   đóng session, subprocess bị kill, websocket đứt và ring buffer 500 tin của
   `zalo-agent-cli mcp start` mất sạch.
2. Javis chưa có cổng nào để connector đẩy sự kiện ngược vào.

Nên nghe liên tục **không** làm được bằng cách gọi MCP. Phải có một tiến trình
sống độc lập với pool.

## Quyết định

| Điểm | Chốt |
|---|---|
| Đường đi | Sidecar `zalo-agent listen --webhook`, tài khoản Zalo phụ |
| Hành vi | Chỉ báo Telegram, có lọc. KHÔNG tự trả lời khách |
| Nơi chạy | VPS Hostinger (bật 24/7, IP tĩnh) |
| Quản tiến trình | Javis tự quản, theo khuôn `zalo_login.py` |

Các lựa chọn đã cân nhắc và loại: chạy container riêng trong docker-compose
(phải sửa compose, chia volume home để đăng nhập, mất nút bật tắt trong UI);
dùng `--save` ghi jsonl rồi đọc file (quay về polling, mất realtime); đi OA
chính thức (không rủi ro khoá nhưng cần OA đã xác thực và nhiều khả năng gói
trả phí, lại chỉ bắt hội thoại OA chứ không đụng chat cá nhân).

## Kiến trúc

```
npx zalo-agent-cli listen  --(HOME = home cô lập của connection)
        |
        |  POST http://127.0.0.1:<port>/hook/zalo   (mỗi sự kiện 1 JSON)
        v
Javis  /hook/zalo  ->  trả 200 ngay  ->  hàng đợi
                                            |
                                     lọc + khử trùng lặp
                                            |
                                     _notify_owner -> Telegram
```

Không gọi model ở bất kỳ khâu nào, nên listener chạy cả ngày không tốn token.

## Thành phần

### 1. `server/zalo_listener.py`

Module độc lập, **không import main** (tiêm helper qua dataclass deps, đúng
kiểu `reminders.py`). Gồm:

- Quản vòng đời tiến trình: `start()`, `stop()`, `status()`. Spawn npx với
  `HOME`/`USERPROFILE` trỏ vào `config.home_dir` của connection Zalo đã chọn.
- Đọc stdout để biết trạng thái: đang nối, đứt, trùng phiên, lỗi đăng nhập.
- Tự dựng lại có backoff (5s rồi 30s, trần 5 phút). Trùng phiên hoặc lỗi xác
  thực lặp lại thì dừng hẳn và báo lên UI thay vì quay vòng vô ích.
- Hàm thuần `should_notify(event, cfg, now)` và `seen_once(msg_id)` tách riêng
  để test được không cần tiến trình thật.

### 2. Endpoint `POST /hook/zalo`

Trong router của module, đăng ký vào app ở main.py. Thêm đường dẫn vào
`_AUTH_LOCAL_EXACT` (main.py:82) để miễn cookie đăng nhập khi gọi từ loopback;
request từ ngoài vẫn bị `_auth_guard` chặn.

Bắt buộc **trả 200 ngay** rồi xử lý bất đồng bộ, vì `zalo-agent-cli` chỉ chờ 5
giây rồi bỏ qua âm thầm.

### 3. Bộ lọc

Đọc cấu hình từ `settings.json` khoá `zalo_listener`:

```json
{
  "enabled": false,
  "conn_id": "<id connection zalo>",
  "keywords": ["giá", "còn hàng", "đặt", "ship"],
  "threads": [],
  "dm_only": true,
  "quiet_hours": "23-07",
  "secret": "<sinh tự động>",
  "owner_chat": ""
}
```

Mặc định **chặt**: chỉ tin nhắn riêng có chứa từ khoá, không báo nhóm. Nới ra
sau khi dùng vài ngày thấy sót, an toàn hơn là mặc định báo hết rồi phải tắt bớt.

`threads` rỗng nghĩa là không lọc theo cuộc chat. Bỏ qua tin của chính mình
(`--no-self`). Trong giờ im lặng thì nuốt thông báo, không dồn lại bắn một loạt.

### 4. Chống trùng lặp

Giữ set `msgId` đã xử lý gần đây (trần 2000, hết thì cắt nửa cũ). CLI gửi lại
sau khi nối lại là chuyện bình thường, không được bắn Telegram hai lần.

### 5. UI trang Kết nối

Chọn connection Zalo nào làm listener, ô nhập từ khoá, nút bật/tắt, và hiện
trạng thái thật: đang nghe, mất kết nối đang thử lại, hay trùng phiên.

## An toàn

- Endpoint chỉ nhận từ `127.0.0.1`/`::1`, kèm shared secret phòng tiến trình khác
  trên cùng VPS gọi bừa.

  Secret đi trong **query** (`/hook/zalo?k=...`), không phải header. Lý do: cờ
  `--webhook <url>` của `zalo-agent-cli` chỉ POST JSON trần, không có cách đặt
  header tuỳ ý, nên gác bằng header là chặn sạch tin và tính năng chết câm.
  Đánh đổi chấp nhận được vì kênh này chỉ sống trên loopback: rào CHÍNH là
  `_AUTH_LOCAL_EXACT` cộng loopback, secret chỉ là tầng hai. Endpoint vẫn nhận
  cả header cho ai tự dựng nguồn đẩy khác.
- Javis vẫn **không tự gửi tin Zalo**. Loop nền vẫn bị cấm gửi như hiện tại.
- Giới hạn tần suất thông báo để một nhóm đông không làm nổ Telegram.
- `home_dir` chứa `zalo-session.json`, tương đương quyền đăng nhập đầy đủ. Đã
  kiểm tra: `.gitignore:33` che `server/connector-home/` và `STATE_DIR` mặc định
  trỏ vào `server/`, nên không lọt lên git.
- Rủi ro nền: chạy 24/7 trên tài khoản cá nhân là vi phạm điều khoản Zalo, có
  thể bị khoá số. Dùng SIM phụ, không dùng số chính của cửa hàng.

## Điều chưa kiểm chứng

**Zalo chỉ cho một socket mỗi tài khoản.** Connector `zalo` (`mcp start`) cũng
giữ socket, sidecar `listen` cũng cần socket. Cùng một tài khoản thì có thể đá
nhau, `zalo-agent-cli` thấy trùng phiên là tự thoát. Chưa kiểm chứng được hai
tiến trình cùng home có sống chung nổi không.

Cách xử lý: **không đoán, làm cho va chạm hiện ra rõ**. Bắt chuỗi trùng phiên
trong stdout, đẩy lên UI thành trạng thái đọc được, tự dừng thay vì quay vòng.
Anh dùng ngày đầu là biết ngay có va hay không.

Nếu va chạm là thật và xảy ra thường xuyên, bước tiếp theo là tạm dừng listener
khi cần gửi tin rồi bật lại. Chưa làm bây giờ vì chưa có bằng chứng là cần, mà
nó kéo theo lỗ hổng mất tin trong lúc dừng.

## Test

- Unit test cho `should_notify` và `seen_once`: hàm thuần, phủ từ khoá, dm_only,
  giờ im lặng, tin của chính mình, trùng msgId.
- Test endpoint bằng POST giả, kiểm tra trả 200 nhanh và sai secret thì bị chặn.
- Phần socket thật phải thử tay vì phụ thuộc tài khoản Zalo sống. Không giả vờ
  test được.

## Ngoài phạm vi

Tự trả lời khách, soạn nháp trả lời bằng model, đường OA chính thức, và đồng bộ
tin Zalo vào Second Brain. Để lần sau nếu cần.
