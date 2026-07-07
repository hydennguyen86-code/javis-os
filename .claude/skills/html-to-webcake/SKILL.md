---
name: HTML sang Webcake
description: Kích hoạt khi người dùng muốn CHUYỂN một file/đoạn HTML thành file Webcake (.pke) để upload lên Webcake chỉnh sửa (vd "chuyển file html này sang webcake", "đổi html thành pke", "tạo file webcake từ html", "làm landing này thành file sửa được trên webcake", "html to webcake", "convert html sang webcake"). Đọc HTML, tái dựng thành page_source đúng khuôn Webcake rồi xuất .pke.
group: Marketing
---

# HTML sang Webcake (.pke)

Biến một trang HTML thành **file `.pke`** mở và sửa được trong trình dựng trang Webcake.

## Hiểu đúng bản chất trước khi làm

- File `.pke` = `base64( MessagePack( envelope ) )`, trong đó `envelope.source` chính là **page_source** của editor Webcake (`settings, popup, page, options, cartConfigs`).
- Webcake là **canvas định vị TUYỆT ĐỐI theo pixel**, mỗi phần tử ghi `top/left/width/height` RIÊNG cho 2 khổ: mobile rộng 420, desktop rộng 960. Không phải HTML trôi theo dòng.
- Vì vậy skill này **TÁI DỰNG** nội dung HTML thành các section Webcake xếp dọc, sạch và sửa được - KHÔNG phải bản sao pixel y hệt trang HTML gốc. Luôn nói rõ điều này với người dùng.
- HTML do Webcake publish (bản đã xuất để chạy) không chứa source biên tập; skill vẫn đọc được nội dung của nó để dựng lại.

## Công cụ (đi kèm skill, không cần cài gói)

Ở thư mục `tools/` cạnh file SKILL.md này (đường dẫn hệ thống thường là
`D:\Project\Javis-OS\.claude\skills\html-to-webcake\tools\`):

- `webcake-build.js` - nhận một **spec JSON** (mô tả trang đơn giản) → sinh page_source → xuất `.pke`.
  `node tools/webcake-build.js spec.json out.pke`
- `webcake-pke.js` - codec 2 chiều nếu cần thao tác tay:
  `node tools/webcake-pke.js decode file.pke file.json` và `encode file.json file.pke`.

Ví dụ spec mẫu: `examples/demo-spec.json`.

## Quy trình khi kích hoạt

1. **Xác định HTML nguồn.** Người dùng đưa đường dẫn file `.html` (hoặc dán HTML). Đọc bằng Read.
2. **Bóc nội dung theo thứ tự trên xuống.** Chia trang thành các **section** hợp lý; trong mỗi section nhận diện:
   - tiêu đề → `heading`; đoạn văn → `text` (giữ in đậm/highlight bằng thẻ inline trong text, xuống dòng bằng `<br>`);
   - ảnh (`<img src>`, hoặc background-image) → `image` (lấy URL);
   - nút/CTA (`<a>`, `<button>`) → `button` (text + link);
   - form (`<form>`, các `<input>`) → `form` với danh sách `fields`.
   - Ghi nhận màu nền section, màu chữ, canh lề để đưa vào spec.
3. **Viết `spec.json`** theo schema bên dưới (ghi vào thư mục làm việc hoặc scratchpad).
4. **Chạy** `node <đường-dẫn-tools>/webcake-build.js spec.json out.pke` (đặt `out.pke` cạnh file HTML gốc hoặc trong vault để tiện đưa cho người dùng).
5. **Kiểm nhanh** (khuyến nghị): `node <tools>/webcake-pke.js decode out.pke check.json` để chắc file giải mã lại sạch.
6. **Đưa file cho người dùng**: nhúng link markdown để dashboard cho tải, vd `[out.pke](đường-dẫn-tương-đối)`. Báo cáo NGẮN bằng văn nói: đã chuyển bao nhiêu section, file đâu, và nhắc "upload lên Webcake để sửa".

## Schema của spec.json

```json
{
  "name": "Tên trang",
  "title": "Tiêu đề SEO",
  "description": "Mô tả SEO",
  "favicon": "https://...(tùy chọn)",
  "font": "Montserrat",
  "owner_id": "(tùy chọn, uuid tài khoản Webcake)",
  "sections": [
    {
      "background": "rgba(17,17,17,1)",
      "padTop": 48, "gap": 22, "padBottom": 40,
      "elements": [
        { "kind": "heading", "text": "TIÊU ĐỀ", "size": 32, "color": "rgba(255,255,255,1)", "align": "center", "bold": true, "tag": "h2" },
        { "kind": "text",    "html": "Dòng 1<br><span style=\"font-weight:bold;background-color:rgba(255,235,59,0.95);\">nhấn mạnh</span>", "size": 18, "color": "rgba(230,230,230,1)", "align": "center" },
        { "kind": "image",   "src": "https://...png", "ratio": 1.4, "width": 0.9 },
        { "kind": "button",  "text": "MUA NGAY", "href": "https://...", "width": 0.7, "bg": "linear-gradient(90deg, rgba(255,81,47,1) 0%, rgb(221,36,118) 100%)", "color": "#fff" },
        { "kind": "spacer",  "height": 40 },
        { "kind": "form", "redirect": "https://.../thank", "submit": 2, "width": 0.85, "submitText": "GỬI NGAY",
          "fields": [
            { "name": "full_name",    "placeholder": "Họ và tên",     "type": "text",  "required": true },
            { "name": "email",        "placeholder": "Email",         "type": "email", "required": true },
            { "name": "phone_number", "placeholder": "Số điện thoại", "type": "phone", "required": true }
          ]
        }
      ]
    }
  ]
}
```

Các loại `kind` LÁ: `heading`, `text`, `image`, `button`, `form`, `spacer`, `badge`, `card`, `window`.
Các loại `kind` BỐ CỤC (nhiều cột): `row`, `cardsRow`.
Trường dùng chung: `width` = tỉ lệ bề rộng (0..1). `button.href` (URL ngoài) thành link; `button.scrollTo` (id) thành cuộn tới. Bộ sinh tự tính top/left/width/height cho cả mobile lẫn desktop; desktop xếp cột cạnh nhau, mobile tự xếp dọc.

### Bố cục nhiều cột + thẻ card (DÙNG cái này để trang không bị 1 cột đơn điệu)

```json
{ "kind": "row", "gap": 44, "cols": [
    { "w": 0.55, "gap": 22, "items": [ { "kind":"heading", ... }, { "kind":"text", ... } ] },
    { "w": 0.45, "items": [ { "kind":"window", "title":"...", "lines":[{"who":"you","text":"..."},{"who":"bot","text":"..."}] } ] }
]}
```
- `card`  `{ "icon":"🧠", "title":"...", "text":"...", "bg":"rgba(16,18,43,1)", "borderColor":"...", "radius":16, "titleColor":"...", "titleSize":19, "align":"left" }` -> hộp nền bo góc (rectangle) + tiêu đề + mô tả.
- `cardsRow` `{ "gap":22, "cards":[ {icon,title,text}, {...}, {...} ] }` -> đường tắt: 1 hàng gồm các card đều nhau (dùng cho mọi khối "3 ý cạnh nhau").
- `badge` `{ "text":"...", "align":"left|center", "color":"...", "bg":"...", "borderColor":"..." }` -> viên thuốc bo tròn.
- `window` `{ "title":"...", "lines":[ {"who":"you|bot","text":"..."} ] }` -> khung cửa sổ chat.

Quy tắc bố cục: khối "kicker + tiêu đề + mô tả + 3 thẻ" -> dùng `text`(kicker) + `heading` + `text`(lead) + `cardsRow`. Khối "chữ một bên, hình/khung một bên" (hero, telegram) -> dùng `row` 2 cột. Nhờ vậy trang ra giống web thật, không bị dồn 1 cột.

### Nền động + màu (JS/CSS) - đưa vào chính file .pke

Webcake cho nhồi script/CSS ở Cài đặt > HTML/JavaScript. Map vào spec (bộ sinh tự ghi vào `settings`):
- `spec.extraScript` -> ô "Custom Javascript" (`extra_script`). Vd tạo `<canvas>` nền sao bay `position:fixed;z-index:-1`.
- `spec.extraCss` -> ô "Custom CSS" (`extra_css`). Vd `.grad{background:linear-gradient(...);-webkit-background-clip:text;color:transparent}` cho chữ gradient.
- `spec.beforeHead` -> "Before head" (`bhet`); `spec.beforeBody` -> "Before Body" (`bbet`).

Mẹo giữ hiệu ứng như HTML gốc:
- **Chữ gradient**: bọc phần nhấn trong tiêu đề bằng `<span class='grad'>...</span>` rồi định nghĩa `.grad` trong `extraCss` (class render được vì text-block giữ HTML inline). KHÔNG cần biết id phần tử.
- **Nền canvas hiện xuyên trang**: canvas `position:fixed;z-index:-1` + trong `extraCss` đặt `html,body{background:transparent !important}` + để nền các section HƠI trong suốt (alpha 0.85-0.92; hero để ~0.15 cho lộ rõ) thì sao bay ánh qua.
- Script CHỈ chạy khi Xem trước / Xuất bản, KHÔNG chạy trong editor -> phải dặn người dùng bấm Preview mới thấy.
- Hiệu ứng cuộn hiện dần thì mỗi phần tử đã tự có animation `fadeInUp` sẵn, không cần thêm.

## Nguyên tắc chuyển đổi (bám để ra trang đẹp, sửa được)

- **Chữ nhấn mạnh**: giữ bằng thẻ inline trong trường text - in đậm `<span style="font-weight:bold;">`, tô nền vàng `background-color: rgba(255,235,59,0.95);`. Xuống dòng `<br>`, KHÔNG dùng `<p>` lồng nhau.
- **Màu**: luôn dạng `rgba(r,g,b,a)`. Nút mặc định dùng nền gradient nếu HTML gốc là nút nổi bật.
- **Ảnh**: Webcake tải ảnh theo URL public. Nếu HTML dùng ảnh local hoặc base64 → CẢNH BÁO người dùng cần upload ảnh lên host (hoặc Pancake content) rồi thay `src` bằng URL, nếu không ảnh sẽ trống.
- **Cỡ chữ**: heading 26-36, text thân 16-20. Bộ sinh tự thu nhỏ ~82% cho mobile.
- **Số section vừa phải**: gộp nội dung liền mạch vào một section, đừng cắt vụn mỗi dòng một section.
- **KHÔNG dùng ký tự em dash** ở bất cứ đâu (text, spec, báo cáo) - dùng "-".

## Cách nâng cao (tự dựng page_source rồi encode)

Nếu cần kiểm soát sâu (group lồng nhau, popup, radio/checkbox sản phẩm), tự dựng nguyên object `source`
(`{settings, popup, page, options, cartConfigs}`) đúng schema node Webcake, ghi ra JSON rồi:
`node tools/webcake-pke.js encode source.json out.pke` (file chỉ chứa `source` sẽ được tự bọc envelope; thêm `--name` `--owner` nếu cần).

## Giới hạn cần nói thẳng với người dùng

Skill tái dựng bố cục sạch theo chiều dọc, không sao chép y hệt vị trí pixel của HTML gốc. Radio/checkbox
chọn sản phẩm (gắn `product_id`/`variation` của Pancake) không tự sinh được - để người dùng thêm trong Webcake
sau khi upload. Nên khuyến khích upload thử file `.pke` trước, lệch đâu chỉnh spec rồi build lại.
