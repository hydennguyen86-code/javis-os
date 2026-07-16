# Đo skill + Chuẩn viết skill (A+B)

Ngày: 2026-07-16
Trạng thái: đã duyệt thiết kế, chờ kế hoạch triển khai

## Bối cảnh

So sánh Javis với `NousResearch/hermes-agent` cho thấy Javis tạo skill/agent/workflow
không kém, nhưng thiếu hoàn toàn **vòng đời sau khi tạo**: không đo, không gộp, không dọn.
Javis có hệ miễn dịch mạnh (fork học read-only, Python là người ghi duy nhất, provenance
tier, secret/injection scan, git undo) nhưng không có trao đổi chất. Hermes ngược lại.

Định hướng: ghép cơ chế trao đổi chất của Hermes vào bộ khung an toàn sẵn có của Javis,
không phải ngược lại.

Toàn bộ lộ trình gồm 4 hệ con. Spec này CHỈ phủ A và B.

- **A. Vòng đời skill** - telemetry, trạng thái, hiển thị.
- **B. Chuẩn viết skill** - hạn mức description, bộ chuẩn authoring, skill package.
- C. Curator gộp ô dù (vòng sau, phụ thuộc A và B).
- D. `/learn` từ nguồn (vòng sau, độc lập).

C phụ thuộc cả A lẫn B: không có telemetry thì curator gộp mù, không có chuẩn thì không
biết gộp về hình gì.

## Phát hiện dẫn đường: lỗi cắt cụt description

Đây là lỗi CÓ THẬT, đang chạy, đo được, không phải suy đoán từ Hermes.

Javis cắt description ở hai nơi, với hai hạn mức khác nhau:

- `server/mcp_hub.py:256` - `(s['description'] or '')[:60]`, `metas[:20]`
- `server/main.py:3471` - `(s.get("description") or "")[:100]`, `metas[:15]`

Người viết skill không có cách nào biết mình đang bị chấm theo thước nào.

Đo bằng chính `skill_router.list_enabled_meta` trên brain `Brain Default`, **6/6 skill
đang bật đều bị cắt**:

- `html-to-webcake` 376 ký tự, mất 316 (84%)
- `javis-builder` 333, mất 273 (82%)
- `ingest-source` 266, mất 206
- `query-wiki` 249, mất 189
- `lint-wiki` 213, mất 153
- `tao-anh-minh-hoa-2d` 139, mất 79

Nghiêm trọng hơn con số: 5/6 skill mở đầu bằng đúng cụm `"Kích hoạt khi người dùng muốn"`
dài 29 ký tự. Gần nửa ngân sách 60 ký tự bị đốt cho boilerplate giống hệt nhau, chỉ còn
khoảng 31 ký tự thật sự phân biệt được skill này với skill kia. Mọi ví dụ trigger (`vd "..."`),
đúng cái phần khiến routing hoạt động, đều bị vứt sạch.

Tệ nhất là **tài liệu đang chủ động dạy viết sai**. CLAUDE.md bảo description phải "viết rõ
trigger", `javis-builder` bảo "viết kỹ", trong khi runtime cắt cụt. Hermes cảnh báo đúng
hiện tượng này và gọi nó là lỗi không-cosmetic: mô tả quá hạn bị cắt im lặng và skill không
bao giờ route được.

Quan hệ với A: skill không route được thì `use_count` sẽ mãi bằng 0, và telemetry ở A sẽ
đọc nhầm thành "skill chết". **B là điều kiện để A có nghĩa.**

## Quyết định đã chốt

1. Phạm vi: A + B chung một spec. C và D để vòng sau.
2. Mức tự động: **đo và hiển thị, không tự động gì**. Mọi việc tắt/archive do người bấm.
3. Hạn mức description: **150 ký tự**, một hằng số duy nhất cho cả hai điểm cắt.

Về con số 150: Hermes dùng 60, quá chật cho tiếng Việt có dấu. 300 đã được cân nhắc và loại,
vì ở mốc 15 skill nó tốn khoảng 3.000 token mỗi lượt mỗi engine và tăng tuyến tính khi
learn.py tự sinh thêm skill, trong khi 4/6 description hiện tại sẽ lọt, tức là không sửa
được bệnh gốc. Bệnh gốc không phải cắt cụt (đó là triệu chứng) mà là description đang bị
viết như tài liệu trong khi nó là một dòng mục lục. 150 rộng gấp 2,5 lần Hermes để tiếng
Việt thở được và nhét vừa 1 ví dụ trigger, vẫn đủ chặt để ép viết sắc.

Bằng chứng không mất thông tin, viết lại `html-to-webcake` (gốc 376 ký tự):

> Chuyển HTML sang file Webcake .pke để upload/sửa trên Webcake.

62 ký tự, và phân biệt TỐT HƠN 60 ký tự đầu của bản gốc (bản gốc cụt giữa chừng ở
`"...CHUYỂN một file/đoạn HTML thàn"`, mất luôn từ khoá quyết định là "Webcake").
316 ký tự còn lại là ví dụ trigger, chỗ của chúng là thân SKILL.md mục "Khi nào dùng".

Kiến trúc: **index để tìm, thân file để làm.**

## A. Đo skill

### A1. Nơi lưu

File `<brain>/Javis/skill-usage.json`. Module mới `server/skill_usage.py`.

Đặt ở `Javis/` chứ không phải `skills/.usage.json` như Hermes, để bám quy ước Javis đã có.
`server/self_improve.py` ghi rõ: "STATE runtime tách riêng, server sở hữu:
`<vault>/Javis/loop-state.json`". Telemetry là state runtime, cùng loại với loop-state,
nên nằm cạnh nhau.

Không nhét vào frontmatter SKILL.md: brain là git repo (`git_brain`), mỗi lần dùng skill sẽ
đẻ một commit rác và tạo áp lực xung đột lên file do người viết. Đây cũng là lý do Hermes
chọn sidecar.

Khoá theo slug. Mỗi bản ghi: `use_count`, `last_used_at`, `first_used_at`, `created_at`,
`created_by`, `pinned`.

Ghi atomic qua `atomic_write_text` sẵn có. Mọi thao tác best-effort: sidecar thiếu hoặc
hỏng thì trả rỗng và đi tiếp. **Sidecar hỏng tuyệt đối không được làm gãy lời gọi skill.**

### A2. Điểm đếm

Handler `_skill` trong `server/mcp_hub.py:259` (tool `javis_use_skill`). Một chỗ duy nhất,
mọi engine đi qua (Claude Code, Codex, OpenRouter, OpenAI, Anthropic API). Bump khi nạp
skill thành công, không bump khi slug sai.

### A3. Điểm mù (ghi rõ, chấp nhận)

`system_sync.mirror_skills` mirror skill sang `<brain>/.claude/skills` để Claude Code nạp
NATIVE. Đường native KHÔNG đi qua hub nên không đếm được. Bỏ mirror là mất tính năng thật,
nên không bỏ.

Hệ quả bắt buộc, áp cho toàn bộ spec và mọi vòng sau:

> `use_count` là **tín hiệu dương một chiều**. Có đếm nghĩa là skill chắc chắn có dùng.
> `use=0` chỉ có nghĩa "không có bằng chứng", KHÔNG bao giờ được diễn giải là vô dụng,
> và KHÔNG bao giờ được dùng làm căn cứ tự tắt hay tự archive bất cứ thứ gì.

Hermes tự nó cũng ra đúng luật này vì lý do khác (bộ đếm còn mới): "use=0 is not evidence a
skill is valuable; it's absence of evidence either way. Corollary: use=0 is ALSO not a reason
to PRUNE." Với Javis luật đó còn bắt buộc hơn vì có điểm mù thật.

### A4. Không có máy trạng thái

Vì đã chốt "đo và hiển thị, không tự động", bỏ luôn máy trạng thái. Không lưu `state` trong
file, không job nền, không scheduler.

`stale` là **hàm thuần** tính lúc đọc từ `(created_at, last_used_at, pinned, now)`.

Điều kiện cụ thể: `pinned == False` VÀ `use_count == 0` VÀ `now - created_at > SKILL_STALE_AFTER_DAYS`.
Hằng số `SKILL_STALE_AFTER_DAYS = 30`, đặt cùng chỗ với `SKILL_DESC_MAX`.

Ngưỡng 30 ngày lấy theo luật của Hermes: skill mới tạo có thể đơn giản là chưa gặp trigger,
nên chưa đủ già thì không được gắn nhãn gì. Skill có `use_count > 0` không bao giờ stale,
bất kể lần dùng cuối cách đây bao lâu (vì điểm mù native khiến `last_used_at` không đáng
tin làm căn cứ phủ định).

Cả A thu lại còn: một sidecar, một chỗ bump, một hàm tính. Phần lifecycle phức tạp của
Hermes (active/stale/archived, transition walk, `.archive/`) để dành cho C, khi đã có dữ
liệu telemetry thật để kiểm nghiệm.

### A5. Hiển thị

`GET /skills` trả thêm trường usage. Trang Skill hiện số lần dùng, lần dùng cuối, và nhãn
"chưa thấy dùng" cho skill đủ già mà chưa có tín hiệu dương.

Nhãn này BẮT BUỘC kèm chú thích rằng đường native không đếm được nên chỉ để tham khảo.
Không được trình bày như một phán quyết.

## B. Chuẩn viết skill

### B1. Một thước đo

Thêm vào `server/skill_router.py`:

- `SKILL_DESC_MAX = 150`
- `SKILL_LIST_MAX = 20` (gom hai cap 15 và 20 hiện nay về một; lấy 20 vì description đã
  giảm từ 300 xuống 150 nên ngân sách dôi ra, và 20 phủ hết số skill thực tế hiện nay)
- `SKILL_STALE_AFTER_DAYS = 30` (dùng cho A4)

Cả `main.py:3471` lẫn `mcp_hub.py:256` import từ đây. Hết cảnh hai thước.

Ghi nhận (KHÔNG sửa trong spec này): hai nơi này cùng render danh sách skill, nên chi phí
context bị trả gấp đôi mỗi lượt. Cả hai đều có lý do tồn tại (`_skill_router_block` phục vụ
engine không có tool, mô tả tool phục vụ engine có tool). Tối ưu chỗ này là việc riêng,
đừng gộp vào đây.

`skill_router` là nơi đặt đúng vì nó đã tự nhận là "nguồn chân lý DUY NHẤT cho việc khám phá
skill, dùng chung bởi main.py và mcp_hub.py để hai nơi KHÔNG bao giờ lệch nhau". Hằng số
hạn mức thuộc về chính trách nhiệm đó.

### B2. Ép lúc ghi

`POST /skills` từ chối description quá `SKILL_DESC_MAX` và từ chối cụm mở đầu boilerplate.

learn.py kiểm tra tương tự trong `_promote_sync`. Vi phạm thì đưa vào `rep["blocked"]` đúng
như secret-scan và injection-scan đang làm, KHÔNG ghi bừa rồi để runtime cắt.

Boilerplate bị cấm: các biến thể mở đầu kiểu `Kích hoạt khi (người dùng) muốn`,
`Dùng khi cần`, `Sử dụng skill này khi`. Chúng đốt tới 29 ký tự mà không phân biệt gì,
vì mọi skill đều mở đầu như vậy.

### B3. Bộ chuẩn dùng chung

Một hằng số text (theo mẫu `_AUTHORING_STANDARDS` của `hermes/agent/learn_prompt.py`),
nhúng vào cả prompt learn (`learn.py:_build_prompt`) lẫn `javis-builder/SKILL.md`.

Nội dung:

- Hạn mức 150 **kèm lý do**: router cắt đúng ở 150, viết dài hơn là mất im lặng và skill
  không route được. Viết xong TỰ ĐẾM. (Hermes nhấn mạnh đây là luật bị vi phạm nhiều nhất
  và không phải chuyện thẩm mỹ.)
- Cấm boilerplate mở đầu. Nêu năng lực, không nêu ngữ cảnh kích hoạt.
- Ví dụ trigger đầy đủ nằm ở mục "Khi nào dùng" trong thân file, không nhét vào description.
- Thứ tự mục cố định: Khi nào dùng / Chuẩn bị / Cách chạy / Quy trình / Bẫy / Kiểm chứng.
- Cấm bịa flag, path, API chưa thấy trong nguồn.
- Trần độ dài thân file: khoảng 100 dòng cho skill đơn giản, 200 cho skill phức tạp.
  Dài hơn thì đẩy xuống `references/`.
- Cấm skill kiểu router chỉ trỏ sang skill khác.
- Nội dung lớn đẩy xuống `scripts/` và `references/`, tham chiếu bằng đường dẫn tương đối.
- Giữ luật hiện có của Javis: `group` bắt buộc, slug ASCII không dấu, cấm em dash.

### B4. Skill thành package

Cho phép `references/`, `scripts/`, `templates/` trong thư mục skill.

**Ràng buộc bắt buộc đi kèm:** `system_sync.mirror_skills` hiện chỉ copy MỖI `SKILL.md`
(xem `system_sync.py:235-257`, vòng lặp chỉ đọc `d / "SKILL.md"`). Nếu chuẩn cho phép
`references/` mà mirror không copy, skill native sẽ trỏ vào file không tồn tại.

Phải sửa `mirror_skills` copy cả thư mục, giữ nguyên tối ưu so hash để không ghi lại khi
trùng. **Đây là chỗ rủi ro cao nhất của cả spec**, cần test riêng.

### B5. Viết lại 6 description

Không mất thông tin: ví dụ trigger chuyển xuống mục "Khi nào dùng" trong thân file, nơi
không bị cắt và chỉ được đọc khi skill đã nạp.

5 skill hệ thống sửa ở NGUỒN `<project>/.claude/skills/`
(`html-to-webcake`, `ingest-source`, `javis-builder`, `lint-wiki`, `query-wiki`),
KHÔNG sửa bản mirror trong brain.

1 skill của brain (`tao-anh-minh-hoa-2d`) sửa tại brain.

Sửa luôn hai chỗ tài liệu đang dạy sai: CLAUDE.md (mục description "viết rõ trigger") và
`javis-builder` (mục description "viết kỹ").

### B6. Lỗi lệch phát hiện trong lúc đọc

`javis-builder/SKILL.md:54` đang dạy ghi skill vào `.claude/skills/<slug>/SKILL.md`, trong
khi CLAUDE.md và `skill_router` nói canonical là `skills/<slug>/SKILL.md` còn `.claude/skills`
chỉ là bản mirror phái sinh. Skill builder đang dạy ghi vào chỗ mirror. Sửa trong phạm vi B.

## Kiểm thử

`test_skill_usage.py`: bump tăng đúng, ghi atomic, file thiếu, file hỏng (JSON rác), gọi
song song, sidecar hỏng không làm gãy lời gọi skill.

`test_skill_router.py`: khẳng định `main.py` và `mcp_hub.py` cùng dùng `SKILL_DESC_MAX`,
không còn hằng số rời (60 hay 100) nằm rải rác.

`test_system_sync.py`: `mirror_skills` copy đủ `references/`, `scripts/`, `templates/`;
vẫn bỏ qua `.disabled`; vẫn không ghi lại khi hash trùng.

**Test CI quan trọng nhất:** quét mọi skill hệ thống trong `<project>/.claude/skills/`,
FAIL nếu có description vượt `SKILL_DESC_MAX` hoặc dính boilerplate. Đây là thứ khiến con
bug hôm nay không bao giờ quay lại, và là lý do chính khiến B đáng làm chứ không chỉ là
dọn dẹp một lần.

Chạy test phải dùng `.venv` (python hệ thống thiếu lib).

## Rủi ro

Đổi nội dung system prompt sẽ phá prompt cache một lần ở lượt đầu sau deploy. Chấp nhận được.

Viết lại description là đổi hành vi routing thật. Kỳ vọng tốt lên nhưng vẫn là thay đổi
hành vi cần theo dõi.

`mirror_skills` copy thư mục là chỗ dễ sinh lỗi nhất. Rủi ro cụ thể: xoá nhầm file trong
`.claude/skills`, hoặc copy đè lên thứ người dùng sửa tay. Giữ nguyên tinh thần hiện tại
(add/update-only, không xoá entry lạ).

`Javis/skill-usage.json` là state runtime, không phải tri thức, nên PHẢI được gitignore ở
brain. Đây không phải chuyện cân nhắc: `.gitignore` của brain đã nêu nguyên tắc dứt khoát
là "Git chỉ version TRI THỨC ĐÃ CHƯNG CẤT (facts/wiki/skills/MEMORY.md)" và đã loại sẵn
learn-log, loop-log, conversations, lock. Telemetry rơi đúng vào nhóm bị loại.

Template `.gitignore` của brain nằm ở `server/git_brain.py:63-66`, kèm một danh sách path
song song ở `git_brain.py:268`. Phải thêm `Javis/skill-usage.json` vào CẢ HAI chỗ, và kiểm
tra brain đã tồn tại có được cập nhật `.gitignore` hay không (nếu template chỉ ghi lúc
`ensure_git_repo` khởi tạo thì brain cũ sẽ không nhận, cần xử lý idempotent).

## Ngoài phạm vi (cố ý)

Curator gộp ô dù (C). `/learn` từ nguồn (D). Auto-archive và `.archive/`. `related_skills`
thành graph. Máy trạng thái lifecycle đầy đủ. Skill templating kiểu `${HERMES_SKILL_DIR}`
và shell nội tuyến.

## Tham chiếu

Repo Hermes đọc tại commit `53adb3f`. Các file đáng đọc lại khi làm C:
`agent/learn_prompt.py` (bộ chuẩn authoring), `tools/skill_usage.py` (sidecar telemetry,
lifecycle), `agent/curator.py` (prompt gộp ô dù, các luật cứng), `agent/background_review.py`
(fork review sau lượt), `agent/learning_graph.py` (đồ thị hiển thị).
