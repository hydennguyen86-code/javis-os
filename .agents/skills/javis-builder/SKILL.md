---
name: Javis Builder
description: Kích hoạt khi người dùng muốn TẠO hoặc SỬA một năng lực của Javis - agent, skill, workflow, loop, hoặc plugin (vd "tạo agent chuyên X", "thêm kỹ năng Y", "dựng workflow nghiên cứu rồi viết", "tạo loop mỗi 2 tiếng làm Z", "viết tool/plugin tính ...", "làm cho Javis biết làm ..."). Đây là hướng dẫn cách ghi đúng file chuẩn của Javis.
group: AI
---

# Javis Builder - tạo agent / skill / workflow / loop

Khi người dùng muốn Javis có thêm một năng lực, bạn TỰ GHI FILE .md đúng chuẩn dưới đây vào
vault (brain đang chọn). Studio / trang tương ứng tự nhận file mới. Luôn báo cáo ngắn sau khi tạo.

## Quy trình (làm đúng thứ tự)

1. **Hiểu nhu cầu.** Nếu mô tả đủ rõ thì làm luôn; thiếu điểm cốt lõi (mục tiêu, đầu ra mong
   muốn) thì hỏi 1 câu ngắn rồi làm. Đừng hỏi lan man.
2. **Chọn đúng LOẠI năng lực:**
   - Việc trả lời/kiến thức cách-làm tái dùng nhiều lần -> **skill**.
   - Một "vai" chuyên môn có system prompt riêng -> **agent**.
   - Chuỗi nhiều bước, nhiều vai nối nhau -> **workflow** (tạo trước các agent còn thiếu).
   - Việc LẶP theo chu kỳ, tự chạy nền -> **loop**.
   - Cần một TOOL native mới (làm được bằng Python, tái dùng, mọi engine gọi được) mà chưa có MCP -> **plugin**. Chỉ là hướng dẫn cách làm bằng tool sẵn -> skill. Nguồn dữ liệu ngoài có sẵn MCP -> đấu MCP.
   - Việc làm 1 lần -> KHÔNG tạo gì, cứ làm luôn hoặc đề xuất task Kanban.
3. **Chống trùng.** TRƯỚC khi tạo, đọc folder tương ứng (agents/ workflows/ .Codex/skills/
   loops/). Nếu đã có cái gần giống -> cập nhật cái cũ, đừng đẻ bản sao.
4. **Ghi file** đúng frontmatter (mẫu bên dưới). slug = ASCII không dấu, gạch nối. Tên hiển thị
   tiếng Việt. TUYỆT ĐỐI không dùng ký tự em dash, dùng "-".
5. **Báo cáo ngắn** bằng văn nói: đã tạo loại gì, tên/đường dẫn file, dùng ở đâu.

## Mẫu file (ghi CHÍNH XÁC theo đây)

### Agent -> `Javis/agents/<slug>.md`
```
---
type: agent
name: <Tên tiếng Việt>
slug: <ascii>
role: <vai trò 1 câu>
skills: [slug-skill]      # [] nếu chưa gán; chỉ gán skill đã có trong .Codex/skills
model: ""                 # "" mặc định | sonnet|opus|haiku|fable (Codex) | gpt-5.5|gpt-5.4|gpt-5.3-codex (ChatGPT/Codex)
updated: <YYYY-MM-DD>
---
<system prompt: cách làm việc, nguyên tắc, định dạng đầu ra mong muốn>
```

**Viết system prompt cho agent theo khung metaprompt** (rút từ metaprompt của Anthropic - ĐỪNG viết 1-2 câu chung chung kiểu "bạn là chuyên gia X"):
1. Vai + mục tiêu: 1 câu nêu vai, 1 câu nêu kết quả tốt trông như thế nào.
2. Bối cảnh nghiệp vụ: 2-3 dòng về sản phẩm/khách/lĩnh vực, lấy từ Memory nếu liên quan.
3. Quy trình: các bước làm việc đánh số, đúng thứ tự agent nên làm thật.
4. Định dạng đầu ra: nêu CỤ THỂ (độ dài, cấu trúc, giọng, ngôn ngữ); đầu ra có khuôn cố định thì kèm 1 ví dụ mẫu ngắn.
5. Trường hợp khó: thiếu dữ liệu / yêu cầu mơ hồ / ngoài phạm vi thì agent làm gì (nêu giả định rồi làm tiếp, hỏi lại 1 câu, hay từ chối).
6. Điều cấm: chỉ cấm CỤ THỂ kèm lý do (vd không bịa số liệu, không em dash), đừng viết cả tràng "không được".
Prompt tốt thường 10-25 dòng. Viết xong tự đọc lại bằng mắt một agent mới: có đủ để làm việc mà không phải hỏi thêm không? Thân skill cũng áp khung này (bỏ mục 1, thay bằng mô tả trigger).

### Skill -> `.Codex/skills/<slug>/SKILL.md`
```
---
name: <Tên skill>
description: <mô tả NGẮN nêu rõ KHI NÀO kích hoạt - đây là trigger, viết kỹ>
group: <Marketing|Bán hàng|Nội dung|Vận hành|Tài chính|AI|Năng suất|Cá nhân>
---
<hướng dẫn chi tiết cho AI khi skill kích hoạt>
```

### Workflow -> `Javis/workflows/<slug>.md`
```
---
type: workflow
name: <Tên>
slug: <ascii>
status: off               # tạo mới để 'off' cho user xem trước rồi bật
description: <mô tả ngắn>
steps:
  - agent: <agent-slug>
    task: "<việc; {{input}}=đầu vào user, {{prev}}=kết quả bước trước>"
    verify_agent: <agent-slug>   # tùy chọn: agent soi lỗi
    max_retries: 1               # tùy chọn
updated: <YYYY-MM-DD>
---
<mô tả>
```
Nếu workflow tham chiếu agent chưa tồn tại -> TẠO agent đó trước.

### Loop -> `Javis/loops/<slug>.md`
```
---
type: loop
name: <Tên>
slug: <ascii>
enabled: false            # LUÔN tạo ở trạng thái TẮT
mode: suggest             # suggest=chỉ đọc/đề xuất | auto=tự ghi nháp an toàn | full=toàn quyền
interval_min: 120         # tối thiểu 5
updated: <YYYY-MM-DD>
---
<mô tả nhiệm vụ: mỗi vòng loop làm ĐÚNG việc này - đây chính là prompt của loop, viết tự-đủ>
```

### Plugin -> mặc định TOÀN CỤC `<JAVIS_STATE_DIR>/plugins/<slug>/` (chung mọi brain); riêng 1 brain thì `<vault>/plugins/<slug>/`. 2 file: plugin.yaml + plugin.py
`plugin.yaml`:
```
name: <Tên tiếng Việt>
slug: <ascii>
version: 1.0.0
description: <tool này làm gì, khi nào engine nên gọi>
author: <ai tạo>
enabled: false            # LUÔN tạo ở trạng thái TẮT
min_mode: readonly        # readonly=chỉ đọc/tính (mặc định) | safe=có ghi | full=hành động thật
tools: [<ten_tool>]
hooks: []                 # vd [post_tool_call] nếu dùng hook
```
`plugin.py`:
```python
def register(ctx):
    def handler(args, ctx):            # args=dict; trả str (hoặc dict). Lỗi -> "ERROR: ...". Có thể async.
        return "..."
    ctx.register_tool(
        name="ten_tool", description="mô tả cho engine + tham số",
        handler=handler, min_mode="readonly",
        schema={"type":"object","properties":{},"required":[]})
    # tuỳ chọn hook: ctx.register_hook("post_tool_call", lambda tool_name="", **_: None)
```
ctx có `ctx.vault_root`, `ctx.data_dir` (state riêng plugin, không đụng vault), `ctx.slug`.

## Rào an toàn (BẮT BUỘC)

- Loop tạo qua chat LUÔN `enabled: false` + `mode: suggest`. Chỉ nâng `mode: auto/full` hoặc bật
  ngay khi user yêu cầu RÕ RÀNG, và phải cảnh báo rủi ro (full = tự tạo đơn/tiêu tiền/đăng bài).
- KHÔNG tạo năng lực tự làm hành động tiền/đơn/quảng cáo/gửi tin/đăng bài mà không có người duyệt.
- KHÔNG bao giờ để một loop/automation tự tạo hoặc tự bật loop khác (chống phình vô hạn) - chỉ ĐỀ XUẤT.
- Skill do engine TỰ HỌC sinh ra -> tạo BẬT sẵn (đánh dấu `origin: javis-learned`), nhưng KHÔNG ghi
  đè skill đã có và KHÔNG hồi sinh skill user đã tắt; agent tự động -> để nháp chờ duyệt. Skill do
  user yêu cầu trực tiếp -> tạo bật luôn nhưng phải kiểm trùng + `description` trigger rõ (skill rác
  làm Javis chọn skill sai). Đừng tạo skill trùng chức năng skill đã có.
- Plugin user (toàn cục lẫn vault) chạy CODE PYTHON THẬT trong tiến trình server -> tạo `enabled: false`,
  `min_mode: readonly`, và NÓI RÕ với user: plugin chỉ chạy khi họ đặt env `JAVIS_ENABLE_USER_PLUGINS=true`
  rồi khởi động lại (rào chống chạy code lạ). KHÔNG viết plugin làm hành động tiền/đơn/gửi tin; việc đó để MCP + mức quyền lo.
- Sau khi tạo, KHÔNG tự chạy thứ có side-effect; để user xem trước.
