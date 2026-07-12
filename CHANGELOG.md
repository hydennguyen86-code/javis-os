# Nhật ký cập nhật

Lịch sử phiên bản Javis OS. Bản mới nhất ở trên cùng. Xem ngay trong app tại mục **Cập nhật** trên thanh bên trái.

Định dạng: mỗi phiên bản là một khối `## [x.y.z] - ngày`, bên dưới nhóm thay đổi theo `### Thêm mới / Sửa lỗi / Cải thiện / Bảo mật`.

## [0.9.40] - 2026-07-12
### Thêm mới
- **Kết nối Meta Ads bằng cách CHẠY ĐƯỢC ngay: tự tạo Facebook App, gọi thẳng Marketing API (như Composio)**: vì MCP chính chủ của Meta đang beta khóa allowlist (không tự nối được), Javis thêm connector mới "Meta Ads (tự tạo app - Graph API)" đi đường vòng đã được chứng minh - bạn tạo một Facebook App của riêng mình (~10 phút, có hướng dẫn từng bước trong app và trong tài liệu), dán App ID + App Secret, Javis đọc thẳng số liệu quảng cáo của bạn qua Graph API. Có sẵn công cụ: liệt kê tài khoản quảng cáo, hiệu suất (chi tiêu/hiển thị/click/CTR/CPC/reach/chuyển đổi) theo kỳ, danh sách chiến dịch, và một công cụ đọc Graph API tùy ý. TẤT CẢ CHỈ ĐỌC - không tạo/sửa chiến dịch, không tiêu tiền. Token Facebook (~60 ngày) được Javis tự gia hạn; hết hạn thì bấm Kết nối lại. Đây đúng là mô hình các nền tảng như Composio dùng cho Meta Ads. Kèm hướng dẫn tạo app đầy đủ trong [MCP & số liệu](docs/09-mcp-va-so-lieu.md) và test tự động (`test_meta_graph.py`).

## [0.9.39] - 2026-07-12
### Sửa lỗi
- **Kết nối Meta Ads báo lỗi trung thực, hết ngõ cụt "cần client_id thủ công"**: sau khi điều tra sâu (probe thật endpoint của Meta + đối chiếu tài liệu chính chủ và báo cáo cộng đồng), xác định `mcp.facebook.com/ads` là MCP chính chủ của Meta đang ở beta GIỚI HẠN: máy chủ chỉ chấp nhận vài ứng dụng được Meta cấp phép sẵn (trợ lý của ChatGPT, Claude, Perplexity) và đã TẮT tự đăng ký ứng dụng (DCR) - nên Javis, và cả các công cụ khác, chưa nối tự phục vụ được. Đây là giới hạn phía Meta, không phải lỗi máy người dùng. Thông báo lỗi cũ ("Server không hỗ trợ tự đăng ký client (DCR) - cần client_id thủ công") gây hiểu nhầm rằng chỉ cần dán client_id là xong, giờ đổi thành giải thích rõ + hiện nguyên văn thông báo của Meta. Mô tả và hướng dẫn của connector Meta Ads cũng viết lại đúng thực tế (bỏ câu "đăng nhập 1 chạm, không cần tạo app").

## [0.9.38] - 2026-07-12
### Thêm mới
- **Trang Tệp tin duyệt được ra ngoài brain (tới cả ổ đĩa)**: trước đây File Manager khoá cứng trong thư mục brain, bấm "Lên" tới gốc brain là hết - không đọc/sửa được dữ liệu nằm ngoài vault. Nay khi chạy trên máy cá nhân (localhost), trần duyệt mở tới ổ đĩa chứa brain: mặc định mở vẫn vào đúng thư mục brain như cũ, nhưng bấm "Lên" đi ra được tới tận gốc ổ đĩa để đọc/sửa/tải mọi file. Thêm nút "⌂ Brain" để nhảy nhanh về thư mục brain, và nút "Lên" tự ẩn khi đã ở gốc. An toàn giữ nguyên khi chạy public (VPS/có đăng nhập): vẫn khoá trong brain để không hở cả ổ đĩa ra web. Tinh chỉnh bằng biến `JAVIS_FILES_ROOT` (xem [Cấu hình env](docs/16-cau-hinh-env.md)): ép khoá brain, mở cả ổ đĩa, hay chỉ một thư mục cụ thể. Không xoá được thư mục brain hay gốc ổ đĩa.

## [0.9.37] - 2026-07-12
### Cải thiện
- **Gỡ hẳn nhánh engine Claude kiểu cũ (Popen) - khép hồ sơ kế hoạch Agent SDK**: engine Claude giờ chạy duy nhất qua Agent SDK chính chủ. Xoá ~220 dòng code tự chế spawn/parse tiến trình trong claude_cli.py (nơi từng phát sinh các lỗi kiểu WinError 206); Codex CLI và phần auth/ngắt tiến trình dùng chung giữ nguyên. Biến `JAVIS_CLAUDE_ENGINE` không còn tác dụng (đặt `cli`/`sdk-loops` sẽ bị bỏ qua kèm một dòng log). Máy chưa cài claude-agent-sdk sẽ được engine báo rõ cách cài thay vì lỗi khó hiểu. Toàn bộ 6 bộ test + kiểm tra sống qua factory đều pass; nhật ký hoàn công ở docs/dev/2026-07-ke-hoach-agent-sdk.md.

## [0.9.36] - 2026-07-12
### Thêm mới
- **Engine Claude chạy Agent SDK chính chủ theo MẶC ĐỊNH (hoàn tất cả 4 phase kế hoạch)**: sau spike và smoke đạt toàn bộ, engine Claude giờ mặc định chạy qua claude-agent-sdk. Người dùng không phải làm gì - vẫn đăng nhập Claude Code như cũ, chat/loop/workflow/Telegram chạy y hệt nhưng nền tảng do Anthropic bảo trì, fork nền được chặn quyền theo từng lần gọi tool kèm audit. Trục trặc thì đặt biến môi trường `JAVIS_CLAUDE_ENGINE=cli` là quay về cách cũ ngay (giữ tối thiểu một bản phát hành); có thêm mức trung gian `sdk-loops` (chỉ tác vụ nền dùng SDK). Đã kiểm chứng bằng phiên chạy thật cô lập đủ 3 luồng: chat 2 lượt có nhớ phiên, workflow chạy trọn chuỗi bước, loop chế độ đề xuất bị lệnh "tạo file bằng được" vẫn không tạo được file; log server sạch không lỗi không fallback.
- **Plugin chạy thẳng trong tiến trình server (in-process) trên engine SDK**: tool plugin (tạo ảnh ChatGPT, ngày giờ VN, plugin user tự viết) không còn đi vòng qua hub HTTP - engine gọi thẳng handler Python, nhanh hơn và dùng được plugin cả khi CHƯA đấu kết nối MCP nào. Hub tự bỏ nhóm plugin khi engine đã có bản in-process (không còn nguy cơ model thấy 2 tool trùng chức năng); các engine khác (Codex, API) vẫn dùng plugin qua hub như cũ. Mức quyền min_mode của plugin vẫn được tôn trọng đúng theo chế độ suggest/auto/full.

## [0.9.35] - 2026-07-12
### Thêm mới
- **Engine Claude chạy được qua Agent SDK chính chủ (thử nghiệm, Phase 0-2 của kế hoạch)**: spike đạt cả 7 hạng mục (auth subscription không cần API key, stream, resume, interrupt, MCP config, prompt 43k ký tự không WinError 206, và tới token đầu còn NHANH HƠN cách cũ 3.6s vs 4.0s). Thêm engine `claude_sdk_engine.py` cùng hợp đồng với engine CLI cũ; bật thử bằng biến môi trường `JAVIS_CLAUDE_ENGINE=sdk` rồi khởi động lại - mặc định vẫn là `cli` như cũ, SDK lỗi thì tự rơi về CLI. Nút Dừng ngắt được cả hai loại engine.
- **Quyền per-call cho fork nền (nâng cấp an toàn lớn nhất của đợt này)**: khi chạy engine SDK, các fork nền an toàn (loop suggest/auto, task, reminder, learn) chặn tool NGOÀI whitelist theo TỪNG LẦN GỌI kể cả Bash/Write builtin - kèm audit JSONL ở `logs/sdk_tool_audit.jsonl` trong thư mục state. Smoke test thật: fork chỉ-đọc bị lệnh "tạo file bằng mọi cách" vẫn không tạo được file. Trước đây chỉ giới hạn được bằng danh sách tĩnh lúc spawn, không có audit tool builtin.
### Sửa lỗi
- **Ghim starlette tránh gãy server khi cài dependency mới**: package `mcp` (dependency của claude-agent-sdk) kéo starlette 1.x xung đột fastapi 0.115; requirements.txt ghim `starlette<0.39` + `sse-starlette<3` (pip check sạch).

## [0.9.34] - 2026-07-12
### Thêm mới
- **Chat engine API hết "mất trí nhớ" trong phiên dài (nén hội thoại)**: trước đây phiên chat dài trên engine API (OpenRouter/OpenAI/Anthropic API/Gemini) chỉ giữ 12 message gần nhất, phần cũ bị cắt bỏ - hỏi lại chuyện đầu phiên là Javis quên sạch. Nay phần lịch sử cũ rơi khỏi cửa sổ được TÓM TẮT tự động (chạy nền sau mỗi lượt, gộp dồn với tóm tắt trước) và bơm lại vào đầu phiên - Javis vẫn nhớ mạch cũ (quyết định, con số, việc dang dở) mà payload không phình. Tóm tắt lưu bền trong SQLite theo phiên, DB cũ tự migrate. Port ý tưởng session_memory_compaction của cookbook Anthropic. Kèm test `test_compaction.py` chạy trong CI.
### Cải thiện
- **Workflow tự cải thiện đúng kiểu evaluator-optimizer**: bước có `verify_agent` khi bị chấm CHƯA ĐẠT giờ được xem lại KẾT QUẢ LẦN TRƯỚC kèm phản hồi để sửa tiếp (giữ phần tốt, sửa chỗ bị chê) thay vì làm lại mù từ đầu - đỡ lặp đúng lỗi cũ, hội tụ nhanh hơn. Mẫu workflow trong tài liệu hệ thống bổ sung 2 khoá tuỳ chọn `verify_agent`/`max_retries` để Javis tạo workflow qua chat biết dùng vòng kiểm chứng.
- **Kế hoạch chuyển engine Claude sang Agent SDK chính chủ**: viết bản kế hoạch chi tiết ở `docs/dev/2026-07-ke-hoach-agent-sdk.md` - vì sao (lớp Popen tự chế là ổ bug WinError 206, quyền tool tĩnh), kiến trúc adapter giữ nguyên giao diện ClaudeCLI, map 3 mức quyền suggest/auto/full vào callback `can_use_tool` từng tool call, lộ trình 4 phase + spike go/no-go, rủi ro và tiêu chí thành công. Chưa code - chờ duyệt.

## [0.9.33] - 2026-07-12
### Thêm mới
- **Prompt caching cho engine API**: học từ cookbook chính chủ của Anthropic. Nhánh Anthropic API có tool MCP (nhánh chạy nhiều request nhất - mỗi vòng gọi tool là một request chở lại nguyên system prompt ~26k ký tự + schema tool + hội thoại) giờ được cache system + tools + hội thoại, các vòng sau chỉ trả ~10% giá input cho phần đã cache. Cách đánh dấu mới không mutate hội thoại gốc nên không còn nguy cơ tích luỹ marker vượt trần 4 breakpoint của API (lý do trước đây nhánh này phải tắt cache). Model Claude chạy qua OpenRouter cũng được cache system prompt. Kèm test mới `test_engine_cache.py` chạy trong CI.
- **Second Brain: trang wiki tự đủ ngữ cảnh (contextual retrieval)**: skill `ingest-source` giờ yêu cầu mỗi trang wiki mở đầu bằng 1-2 câu định vị (khái niệm gì, thuộc nguồn/chủ đề nào, dùng khi nào) và khai `aliases` (tên gọi khác, thuật ngữ tiếng Anh) trong frontmatter - để sau này hỏi bằng từ khác thì tìm kiếm vẫn trúng trang, và đọc trang lẻ tách khỏi source vẫn hiểu. Ý tưởng lấy từ công thức contextual retrieval của Anthropic, áp cho search dạng file không cần vector DB.
- **javis-builder viết system prompt theo khung metaprompt**: khi tạo agent qua chat, Javis giờ dựng system prompt theo khung 6 phần rút từ metaprompt của Anthropic (vai + mục tiêu, bối cảnh nghiệp vụ, quy trình đánh số, định dạng đầu ra kèm ví dụ, cách xử lý trường hợp khó, điều cấm cụ thể) thay vì 1-2 câu chung chung - agent tạo ra làm việc được ngay, đỡ phải sửa đi sửa lại. Hai skill hệ thống tự cập nhật vào mọi brain chưa chỉnh tay (brain đã chỉnh giữ nguyên bản riêng).

## [0.9.32] - 2026-07-12
### Sửa lỗi
- **Kết nối Meta Ads hết báo "Server này không khai OAuth chuẩn MCP"**: Meta khai issuer OAuth có path (`mcp.facebook.com/ads`) và đặt metadata theo đúng chuẩn RFC 8414 dạng chèn giữa (`/.well-known/oauth-authorization-server/ads`), trong khi Javis chỉ tìm dạng nối đuôi và gốc domain nên không thấy. Nay bước discovery thử đủ cả hai dạng (chèn giữa trước, nối đuôi fallback) cho issuer lẫn URL MCP có path - bấm Kết nối là ra trang đăng nhập Facebook như thiết kế. Các connector OAuth khác không đổi hành vi.

## [0.9.31] - 2026-07-11
### Sửa lỗi
- **Dán bài dài vào chat không còn nổ "Subprocess error: WinError 206"**: trước đây tin nhắn (cộng system prompt) được truyền cho engine CLI qua command line, mà Windows giới hạn command line tối đa 32767 ký tự - dán một bài báo dài hay đoạn văn bản lớn là vượt trần và lỗi "FileNotFoundError: The filename or extension is too long" ngay trước khi engine kịp chạy. Nay prompt được bơm qua stdin (không đi qua command line) nên dán bao nhiêu cũng chạy; áp dụng cho cả engine Claude Code lẫn Codex. Đã test thật với prompt hơn 40 nghìn ký tự.

## [0.9.30] - 2026-07-11
### Thêm mới
- **Key ElevenLabs trong Cài đặt dùng chung cho chỉnh sửa video**: Javis giờ biết dựng và cắt sửa video qua hai bộ công cụ ngoài (HyperFrames tạo video mới từ HTML, video-use cắt từ thừa / chèn phụ đề / chỉnh màu footage quay thật - cài dạng skill cho engine CLI). Phần phiên âm của video-use cần key ElevenLabs: chỉ cần nhập key một chỗ ở **Cài đặt > Giọng đọc (ElevenLabs)** như lâu nay, server tự bơm biến môi trường `ELEVENLABS_API_KEY` cho engine và tool con lúc khởi động và ngay khi lưu Cài đặt (không cần restart, không phải sửa file .env). Key vẫn được mã hóa at rest như các secret khác.
### Sửa lỗi
- **Tiến trình Python con hết crash Unicode trên Windows**: server tự đặt `PYTHONUTF8=1` cho tiến trình con (tôn trọng giá trị user đã đặt sẵn), tránh lỗi UnicodeEncodeError khi tool như video-use in ký tự đặc biệt ra console cp1252.
- **Giá trị che "••••" không còn đè được key ElevenLabs thật**: client lạ lấy cài đặt từ GET /settings (key hiển thị dạng che) rồi POST nguyên object về sẽ không làm mất key đã lưu nữa.

## [0.9.29] - 2026-07-10
### Thêm mới
- **Nút tắt/bật giọng đọc ngay trên khung chat**: thêm một nút loa cạnh nút mic và đính kèm ở thanh nhập chat (hiện ở cả màn 3D lẫn tab Trò chuyện). Bấm để tắt/bật việc Javis đọc câu trả lời bằng giọng mà không phải lên góc trên hay vào Cài đặt. Khi tắt, nút chuyển màu đỏ kèm gạch chéo cho dễ thấy; trạng thái đồng bộ hai chiều với nút loa ở header và công tắc "Đọc trả lời bằng giọng" trong Cài đặt nhanh, và nhớ qua các lần tải lại.

## [0.9.28] - 2026-07-09
### Thêm mới
- **Telegram hiện trạng thái trung gian khi chờ**: trước đây nhắn cho Javis qua Telegram rồi phải chờ im lặng tới khi có câu trả lời, dễ tưởng bị treo. Nay bot gửi một tin trạng thái ("🤔 Javis đang xử lý…") rồi tự cập nhật theo tiến trình thật của lượt (đang gọi công cụ nào, đã nhận dữ liệu, đang soạn câu trả lời); soạn xong thì xoá tin trạng thái và gửi câu trả lời. Có tiết chế nhịp cập nhật (~2.5s) để không spam / dính giới hạn của Telegram. Áp dụng cho cả engine Claude Code lẫn engine API.

## [0.9.27] - 2026-07-09
### Thêm mới
- **Click node trên graph 3D mở popup đọc/sửa note**: trước đây bấm một node trên biểu đồ là gửi thẳng một câu hỏi vào khung chat (gây nhầm lẫn). Nay bấm node mở một cửa sổ hiện nội dung note để đọc và sửa trực tiếp rồi Lưu (đọc/ghi qua đúng API Tệp tin), kèm nút mở tab mới; nhấn Esc hoặc ✕ để đóng.
### Cải thiện
- **Esc không còn dừng câu trả lời / ngắt Javis đang nói**: trước đây nhấn Esc vừa tạm dừng giọng đọc vừa ngắt luôn lượt đang chạy, rất dễ lỡ tay mất câu trả lời. Nay Esc chỉ thoát chế độ rảnh tay, tắt mic và đóng popup. Muốn dừng thì dùng nút Dừng (ô đỏ) hoặc nút bật/tắt tiếng.

## [0.9.26] - 2026-07-09
### Thêm mới
- **Nhiều hội thoại chạy song song (như Claude)**: bấm "Hội thoại mới" giờ KHÔNG còn làm dừng hội thoại đang trả lời. Mỗi lượt chat chạy nền độc lập, nên bạn có thể mở một hội thoại mới và hỏi việc khác NGAY trong khi hội thoại cũ vẫn đang generate - cả hai chạy cùng lúc. Danh sách Lịch sử hiện dấu ⏳ ở hội thoại đang trả lời; bấm vào một hội thoại đang chạy nền để xem tiếp phần đang soạn trực tiếp, và mọi lượt tự lưu vào phiên của nó dù bạn đang xem chỗ khác. Nút Dừng chỉ ngắt đúng hội thoại đang xem, các hội thoại nền khác không bị ảnh hưởng.
### Cải thiện
- **Lõi chat xử lý mỗi lượt như một tác vụ nền**: server không còn khoá kiểu một-kết-nối-một-lượt-một-lúc; mỗi lượt có engine riêng và mọi gói gửi kèm session_id để giao diện định tuyến đúng phiên (có khoá ghi để nhiều lượt không xen kẽ làm hỏng gói). Toàn bộ luồng stream, phiên, MCP/skill và giọng nói giữ nguyên. Ngoài ra nếu chưa cài Claude Code CLI mà dùng engine API/OpenRouter thì không còn bị chặn kết nối như trước (báo lỗi theo từng lượt nếu thực sự cần CLI).

## [0.9.25] - 2026-07-09
### Thêm mới
- **Tab "Trò chuyện" - màn chat riêng, rộng rãi**: thêm tab mới trên thanh bên trái (ngay dưới "Javis") mở khung chat toàn màn hình kiểu Claude, tiện hơn hẳn khung chat chật ở cạnh màn hình 3D. Cột trái là lịch sử hội thoại (nút tạo mới, ô tìm trong mọi hội thoại, nhóm theo Hôm nay / 7 ngày qua / Cũ hơn, đổi tên và xoá, phiên đang mở được tô sáng); giữa là khung chat lớn dễ đọc kèm tiêu đề và badge engine thật (vd "CLI · opus"); ngay trên ô nhập là thanh chọn model + effort, dưới cùng là ô gõ kèm nút mic và đính kèm file. Tab này KHÔNG viết lại bộ máy chat mà dùng lại chính khung chat của màn 3D (mượn rồi trả về khi rời tab) nên cùng một cuộc trò chuyện hiện ở cả hai nơi, giữ nguyên WebSocket, stream, phiên, giọng nói và đính kèm; rời tab thì màn 3D vẫn chat bình thường. Vào tab chat, đồ hoạ 3D tự tắt cho nhẹ máy. Màn hẹp (điện thoại) thì cột lịch sử thu thành ngăn kéo, bấm nút 🕘 để mở.
### Sửa lỗi
- **Chống mất nội dung khi đổi trang nhanh**: mỗi lần chuyển trang quản lý, khung nội dung (`#cviewBody`) được thay bằng một vùng mới, nên nếu một trang tải chậm (Tổng quan, Models, Kết nối...) trả kết quả về TRỄ sau khi bạn đã sang trang khác thì cú ghi đó rơi vào vùng cũ đã bỏ, không đè lên trang đang xem. Trước đây chuyển thật nhanh từ một trang tải-chậm sang tab Trò chuyện có thể xoá mất khung chat vừa mở; nay đã an toàn, đồng thời hết luôn hiện tượng thoáng thấy nội dung trang cũ khi đổi trang.

## [0.9.20] - 2026-07-09
### Thêm mới
- **Loop và Việc tự báo kết quả về Telegram người yêu cầu**: giờ là hành vi mặc định của Javis - mỗi vòng loop chạy nền chạy xong, và mỗi việc (Kanban task) hoàn tất, đều tự nhắn kết quả về Telegram của đúng người đã yêu cầu (kèm tóm tắt, dòng kiểm chứng, và cảnh báo nếu loop tự tạm dừng). Loop hoặc việc tạo trên bản web (không rõ chủ) thì báo về ID Telegram đầu tiên trong whitelist. Loop lưu thêm `owner_chat` (chat_id người tạo) trong frontmatter; việc lưu `chat_id` tương ứng - Javis tự gắn khi bạn tạo qua chat. Vòng bị bỏ qua vì chưa có số liệu thì không nhắn để khỏi làm phiền; muốn một loop ngừng báo mỗi vòng thì đặt `notify: false` trong frontmatter loop đó.

- **Khung chat render chân thật như Claude, xem được Artifact**: câu trả lời của AI giờ hiện đầy đủ như trên khung chat Claude. Khi trả về một trang HTML tự chứa, ảnh SVG, sơ đồ mermaid hoặc một file code dài, Javis hiện một thẻ artifact gọn trong luồng chat; bấm vào mở một panel bên phải có tab Xem trước / Mã nguồn cùng nút Copy và Tải về. HTML chạy trong iframe sandbox cô lập (không đụng được trang cha), SVG render không cho script, mermaid vẽ thành sơ đồ (offline thì tự hạ xuống hiện mã nguồn kèm ghi chú). Nhấn Esc để đóng panel, không thu nhỏ luôn khung chat đang phóng to.
### Cải thiện
- **Markdown và code block đầy đủ hơn**: thêm heading nhiều cấp, danh sách đánh số + lồng nhau + checkbox, blockquote, đường kẻ ngang, in nghiêng, gạch ngang; code block có nhãn ngôn ngữ và tô màu cú pháp, giữ nút Copy. Lúc đang stream, đoạn code chưa đóng vẫn hiện gọn dạng khối code đang gõ thay vì chữ thô. Bộ render tách sang file riêng `dashboard/chat-render.js`, giữ nguyên số liệu panel trái, ảnh vault và link như cũ.

## [0.9.18] - 2026-07-07
### Cải thiện
- **Menu đổi model + effort có luôn trong khung chat phóng to**: trước đây thanh chọn model chỉ hiện ở khung chat thường; khi bấm phóng to hội thoại (nút ⛶ / Thu nhỏ bằng Esc) thì thanh này bị bỏ lại nên không thấy. Nay khi vào chế độ toàn màn hình, thanh chọn model được đưa theo vào ngay trên ô nhập, mở menu chọn nhà cung cấp/model và đổi effort bình thường; thu nhỏ lại thì trả về đúng chỗ cũ.

## [0.9.17] - 2026-07-07
### Thêm mới
- **Đổi model + effort ngay trên khung chat**: thêm một thanh nhỏ ngay phía trên ô chat của dashboard, hiện nhà cung cấp, model và mức "Suy nghĩ" (effort) đang chạy. Bấm vào mở một menu gộp: danh sách model gom theo 6 nhà cung cấp (Claude Code, ChatGPT, OpenRouter, Anthropic API, OpenAI API, Google Gemini), có ô tìm model và hàng chọn effort (Tắt/Thấp/Vừa/Cao) ở dưới. Nhà cung cấp đã nối thì bung ra chọn model (danh sách nạp động theo tài khoản), nhà cung cấp chưa nối hiện khoá kèm lối tắt sang trang Models để thêm key. Chọn model hay effort là lưu ngay vào cấu hình và có hiệu lực ở lượt chat kế, badge engine tự cập nhật. Toàn bộ tái dùng các endpoint sẵn có nên không đổi luồng chat/engine.

## [0.9.16] - 2026-07-07
### Thêm mới
- **Tự khởi động cùng máy (Windows)**: thêm mục "Khởi động cùng máy" ở trang Tổng quan để bật/tắt việc Javis tự chạy khi mở máy. Bật lên là Javis chạy nền ẩn ngay sau khi bạn đăng nhập Windows (không cửa sổ đen, mở `localhost:7777` để dùng), và tự tắt bản cũ trước khi chạy nên không mở trùng. Cơ chế dùng khóa registry theo tài khoản (`HKCU...\Run`, không cần quyền admin) trỏ tới `start-javis.vbs` sẵn có; kèm 2 endpoint `/autostart` để xem trạng thái và bật/tắt, có cờ nhận biết khi bạn dời thư mục cài đặt. Mục này tự ẩn trên bản Docker/Linux.
- **Nhắc hẹn từ chat**: nói kiểu "30 phút nữa nhắc anh...", "8h30 sáng mai nhắc...", "mỗi sáng 7h nhắc uống thuốc" là Javis tự đặt lịch, tới giờ tự thức dậy bắn nhắc qua Telegram cho đúng người đang nói. Hẹn được theo số phút, theo giờ trong ngày, theo ngày cụ thể, hoặc lịch định kỳ bằng biểu thức cron; server tự tính giờ Việt Nam nên chỉ cần nói bằng lời. Ba chế độ: chỉ nhắc lại (notify), tự làm việc rồi gửi kết quả về (task), hoặc chạy một script giám sát KHÔNG cần AI cho rẻ (script, chỉ chạy file bạn đã bỏ sẵn trong `Javis/scripts`). Nhắc hẹn hiện luôn ở trang Việc/Lịch, gạt công tắc để huỷ.
- **Thêm nhà cung cấp Google Gemini**: cắm API key Gemini là dùng được các model 2.5 Flash/Pro và 2.0 Flash để chat, kể cả chế độ agent dùng MCP của Javis y như OpenAI. Đi qua endpoint tương thích OpenAI nên tận dụng lại đúng luồng stream + tool-calling; danh sách model nạp động theo tài khoản, và bật "Suy nghĩ" áp cho model 2.5 trở lên.
- **Skill HTML → Webcake (.pke)**: chuyển một file hoặc đoạn HTML thành file Webcake mở sửa được trên trình dựng landing - đọc HTML, tái dựng thành `page_source` đúng khuôn Webcake rồi xuất `.pke` để tải lên chỉnh tiếp.

## [0.9.15] - 2026-07-06
### Sửa lỗi
- **Favicon giờ khớp logo app**: icon trên tab trình duyệt trước đây vẫn là ảnh mặc định cũ dù link đã trỏ đúng. Nguyên nhân: đường `/favicon.ico` (trình duyệt LUÔN tự gọi) trả về 404 nên trình duyệt giữ icon cache cũ. Đã thêm route trả thẳng logo hiện tại (mặc định `logo.png`, tự đổi theo ảnh bạn tải lên). Trình duyệt cache favicon rất lì nên cần đóng mở lại tab để thấy icon mới.
- **Dải trống bên trên khung chat**: lưới `.hud` khai báo thiếu một hàng nên thanh đính kèm (lúc trống) chiếm mất hàng 70px, để lại một dải trống chạy hết bề ngang ngay trên ô nhập. Đã thêm hàng `auto` cho thanh đính kèm để nó co về 0 khi trống; phần thân giờ giãn hết xuống sát ô chat.
- **Nút "Lịch sử" đè lên nút header**: nút "Lịch sử" để nổi cố định ở góc phải, che mất các nút Cài đặt / Đọc / Reset hội thoại phía dưới. Đã đưa nút vào nằm chung hàng với dãy nút header nên không còn chồng lên nhau.

## [0.9.14] - 2026-07-06
### Thêm mới
- **Panel "Mức dùng" - đo token đa nhà cung cấp**: sidebar giờ hiện lượng token Javis **tự đo** qua từng nhà cung cấp/model trong ngày (vào ↑ / ra ↓ + ước tính chi phí ở nơi provider trả về, vd Claude Code), cộng tổng. Đồng nhất cho mọi engine (Claude Code, ChatGPT/Codex, OpenRouter, OpenAI API, Anthropic API) vì Javis đọc usage trong mọi phản hồi. Kèm **số dư THẬT của OpenRouter** nếu đã cắm key (provider duy nhất lộ số dư qua API). Đây là lượng Javis dùng, KHÔNG phải hạn mức gói thuê bao - đa số nhà cung cấp không cho lấy hạn mức tài khoản qua API nên xem trong app của họ.

## [0.9.13] - 2026-07-06
### Thêm mới
- **Chia sẻ agent / skill / workflow qua file**: mỗi agent, skill, workflow giờ có nút **⤓ Xuất** để tải về một gói `.zip`, và mỗi trang (Agents / Skills / Workflows) có nút **⤒ Nhập** để tải gói lên - trao đổi năng lực với người khác dễ dàng. Gói workflow tự **kèm các agent nó dùng + skill của agent** (skill của bạn, KHÔNG kèm skill hệ thống) để bên nhận chạy được ngay; gói agent kèm skill của nó. Nhập chấp nhận `.zip`, file `.md` lẻ (agent/workflow), và **cả gói skill `.skill` của Claude** (Javis tự nhận diện `SKILL.md` trong gói và đưa vào đúng thư mục skill). Có rào an toàn (chống zip-slip, giới hạn dung lượng) và trùng tên thì bỏ qua trừ khi bạn chọn ghi đè.

## [0.9.12] - 2026-07-06
### Bảo mật
- **Vá 2 lỗ hổng DoS trong thư viện nền** (CVE-2024-47874 Starlette, CVE-2024-53981 python-multipart): nâng fastapi lên 0.115.6 (kéo Starlette lên 0.41.3) và python-multipart lên 0.0.18. Trước đây kẻ tấn công CHƯA đăng nhập có thể gửi multipart form dị dạng vào endpoint công khai (đăng nhập / thiết lập) để làm quá tải server VPS.
- **Chặn XSS trong dashboard**: các hàm escape giờ escape cả dấu nháy (`"` và `'`), tránh nội dung do AI/MCP sinh ra (tên file, nội dung task...) thoát khỏi thuộc tính HTML và chạy JavaScript same-origin điều khiển Javis. Ngoài ra link ngoài (kết quả tìm kiếm, URL xác thực) chỉ được render khi là http/https, chặn scheme `javascript:`.

## [0.9.11] - 2026-07-06
### Thêm mới
- **X (Twitter) vào kho Kết nối** (MCP chính chủ của X, remote): tìm và đọc bài đăng, xem hồ sơ và số liệu công khai. Dán Bearer Token App-only từ X Developer Portal; mặc định Chỉ đọc (token app-only không đăng bài/nhắn tin được nên an toàn). Đăng bài theo tài khoản người dùng cần OAuth - sẽ bổ sung khi bạn cần.
### Cải thiện
- **Logo thương hiệu cho connector**: X, Higgsfield, TikTok Ads, Google Ads và Gmail giờ hiện logo thật thay cho biểu tượng emoji.

## [0.9.10] - 2026-07-06
### Thêm mới
- **Higgsfield vào kho Kết nối** (MCP chính chủ, remote): tạo và chỉnh ảnh/video bằng AI - sinh ảnh, sinh video, nâng nét (upscale), mở rộng khung hình, xoá nền, cắt nhân vật, điều khiển chuyển động. Đăng nhập Higgsfield 1 chạm: Javis tự đăng ký ứng dụng theo chuẩn OAuth của MCP (tự dò metadata + DCR + PKCE, không cần tạo app hay dán key), dùng được trên mọi engine. Mặc định mức Ghi nháp để Javis tạo được nội dung ngay và chặn thao tác xoá/thanh toán; mỗi lần tạo tiêu credit Higgsfield trả trước của bạn.

## [0.9.9] - 2026-07-06
### Thêm mới
- **Xem ảnh và mở file ngay trong chat + trang Tệp tin**: Javis nhúng được ảnh vào câu trả lời (hiện luôn trong khung chat, bấm là mở full ở tab mới) và đính link mở/tải file như PDF, DOCX, XLSX. Trang Tệp tin xem trước được ảnh và PDF ngay trong app; file khác có nút "Mở" ra tab mới bằng đường dẫn tĩnh. Thêm endpoint `/files/raw` phục vụ file inline (khác `/files/download` luôn ép tải).
### Sửa lỗi
- **Ảnh/file trong chat bấm vào không xem được; trang Tệp tin không xem được ảnh và không mở được PDF/DOCX** (chỉ tải về): do khung chat chưa render ảnh/link markdown và chưa có URL phục vụ file inline. Nay hiển thị ảnh, mở PDF trong app, và mọi file đều có đường dẫn tĩnh để mở/tải.

## [0.9.8] - 2026-07-06
### Thêm mới
- **Skill chạy trên MỌI engine, hết phụ thuộc cấu trúc của Claude**: trước đây skill chỉ hoạt động ngon trên Claude Code (đọc native từ `.claude/skills`), còn ChatGPT/Codex thì gọi không ra. Nay Javis có một **skill router riêng** dùng chung cho mọi engine: danh sách skill (tên + mô tả) được bơm thẳng vào system prompt, kèm tool `javis_use_skill` để nạp nội dung skill và làm theo. Claude Code, ChatGPT/Codex, OpenRouter, OpenAI API và Anthropic API giờ đều dùng được skill như nhau.
- **Nơi lưu skill chuyển sang `skills/` (phẳng, do Javis sở hữu)**: đồng bộ với `agents/`, `workflows/`, `memory/`. Brain cũ để skill ở `.claude/skills` được **tự dời sang `skills/`** một lần (an toàn, không mất dữ liệu, giữ nguyên skill đang tắt). Javis vẫn tự **mirror** sang `.claude/skills` để Claude Code nạp native như một điểm cộng - nhưng router chính không còn phụ thuộc thư mục đó nữa.
### Cải thiện
- **Skill do Javis tự học giờ BẬT sẵn** (thay vì để nháp tắt chờ duyệt), đánh dấu `origin: javis-learned` để nhận diện; vẫn tuyệt đối KHÔNG ghi đè skill bạn đã có và KHÔNG hồi sinh skill bạn cố ý tắt.
### Sửa lỗi
- **ChatGPT/Codex không tìm thấy skill**: nhánh chat qua Codex trước đây không được nạp system prompt của Javis và chạy sai thư mục làm việc nên không thấy skill nào. Nay Codex chạy đúng thư mục brain và nhận đủ router skill, gọi được skill người dùng đã tạo.
- **Sửa skill đang tắt bị rỗng nội dung**: nút Sửa trước đây chỉ đọc skill ở vị trí bật nên skill đang tắt mở ra form trống. Nay đọc được cả skill trong `.disabled`; và Lưu khi sửa giữ nguyên trạng thái bật/tắt (không tự bật skill đang tắt, không để lại bản nháp mồ côi).

## [0.9.7] - 2026-07-05
### Cải thiện
- **Giọng nói mượt hơn, hết chèn giọng lạ, biết dừng khi bạn nói**: (1) audio đầu tiên phát NHANH hơn - tách câu đầu ra đoạn nhỏ để tổng hợp + tải tức thì, bớt cảnh khựng vài giây sau khi chữ đã hiện; (2) khi một đoạn đọc lỗi mạng, Javis thử lại đúng giọng Việt và TUYỆT ĐỐI không rơi về giọng mặc định trình duyệt (thường là tiếng Anh) - hết cảnh "giọng Anh lạ chèn giữa chừng"; (3) ngắt lời (barge-in) khi rảnh tay: đang đọc mà nghe bạn nói đủ rõ thì tự dừng và mở nghe ngay, kèm bật khử vọng/khử ồn mic để đỡ nghe lại chính giọng mình.
### Sửa lỗi
- Một đoạn đọc lỗi trước đây bị xử lý 2 lần (Chrome bắn cả sự kiện error lẫn play() reject cho cùng audio) gây 2 luồng đọc chồng nhau và audio không dừng được; nay mỗi đoạn lỗi chỉ xử lý đúng một lần.

## [0.9.6] - 2026-07-04
### Cải thiện
- **Trang Cài đặt gọn và hợp lý hơn**: gộp "Nhà cung cấp giọng đọc" vào chung nhóm Giọng nói (trước đây nằm tách tận cuối trang, sau avatar và tên miền); bỏ nút "Nghe thử" bị trùng (giữ 1 nút duy nhất); ẩn danh sách giọng Edge (HoaiMy/NamMinh) khi chọn provider OpenAI/ElevenLabs vì lúc đó chọn giọng ngay trong khối provider; sửa tiêu đề gây hiểu nhầm (bỏ "Giao diện" vì không có mục đó); nút nghe thử chuyển sang viền để nút Lưu nổi đúng vai trò chính.
- **Thông báo cập nhật bản Docker rõ ràng hơn**: bản Docker không bật Watchtower giờ hướng dẫn thẳng cách **Redeploy** để lấy image mới nhất (Hostinger bấm nút Redeploy trong Docker Manager; VPS chạy `docker compose up -d --pull always`), thay vì bảo "tự thêm service watchtower". Panel Phiên bản hiện luôn hướng dẫn này khi có bản mới mà không tự cập nhật tại chỗ được, không còn để bấm nút "Cập nhật ngay" rồi mới báo lỗi.
### Sửa lỗi
- Nút "Cập nhật ngay" trước đây coi là tự cập nhật được chỉ vì biến `WATCHTOWER_TOKEN` có sẵn trong compose (dù Watchtower chưa chạy), bấm vào trigger âm thầm thất bại rồi báo "phiên bản chưa đổi". Nay **dò Watchtower thật** (kiểm tra cổng, không gửi HTTP để khỏi kích hoạt update nhầm) mới quyết định, tránh báo nhầm.

## [0.9.5] - 2026-07-04
### Thêm mới
- **Lark** vào kho Kết nối (MCP chính chủ của Lark/LarkSuite, chạy local qua `@larksuiteoapi/lark-mcp`): nhắn tin, tài liệu (Docs), bảng dữ liệu (Base/Bitable), wiki, danh bạ. Tạo một Lark app rồi dán App ID + App Secret; Javis chỉ làm được đúng quyền bạn cấp cho app. Cần Node.js 18+. Mặc định Chỉ đọc; gửi tin nhắn và cấp quyền file là hành động nguy hiểm (phải Toàn quyền). Phân loại quyền theo 19 tool thật đã kiểm chứng.
- **Logo Zalo và Google Sheets**: hai connector này giờ hiện logo thật thay cho emoji.

## [0.9.4] - 2026-07-04
### Thêm mới
- **Slack** vào kho Kết nối (MCP chính chủ của Slack, remote): tìm/đọc/gửi tin, xem kênh và thành viên, quản lý canvas. Đăng nhập bằng OAuth qua một Slack app của chính bạn (Slack không cho tự đăng ký client, cần tạo app trong workspace + admin duyệt). Mặc định Chỉ đọc; gửi tin phải nâng Toàn quyền.
- **Systeme.io** vào kho Kết nối (MCP chính chủ, remote): quản lý liên hệ, tag, trường tuỳ biến, newsletter, phễu. Chỉ cần dán MCP key (tạo trong Cài đặt hồ sơ, hạn tối đa 90 ngày). Mặc định Chỉ đọc.
- **Logo thương hiệu cho connector**: các thẻ trong kho Kết nối giờ hiện logo thật (Pancake POS, Botcake, Webcake, Meta Ads, Google Calendar, Gmail, Slack, Systeme.io) thay cho biểu tượng emoji; connector chưa có logo vẫn dùng emoji như cũ.
### Cải thiện
- Nhánh OAuth explicit của hub nhận thêm 2 tinh chỉnh theo hãng: tên tham số scope và dấu ngăn (Slack dùng `user_scope` + dấu phẩy cho token người dùng, Google giữ `scope` + dấu cách) - để hỗ trợ đúng các nhà cung cấp OAuth không theo chuẩn chung.

## [0.9.3] - 2026-07-04
### Thêm mới
- **Kho Kết nối có Google Calendar và Gmail** (MCP chính chủ của Google, remote - chạy được cả trên VPS): Calendar xem lịch, tìm chỗ trống, tạo/sửa/xoá sự kiện; Gmail đọc/tìm thư, soạn NHÁP, gắn nhãn. Gmail bản chính chủ KHÔNG có tool gửi thẳng nên Javis luôn dừng ở bản nháp để bạn tự bấm gửi. Đăng nhập Google ngay trong dashboard; cần tạo OAuth client 1 lần (~10 phút, hướng dẫn từng bước trong cửa sổ kết nối, dùng chung 1 client cho cả hai). Mặc định Chỉ đọc; nâng lên Ghi nháp để tạo sự kiện/soạn nháp, Toàn quyền mới xoá được sự kiện.
### Cải thiện
- Hub OAuth giờ nhận **client tự khai (BYO client_id/secret)** cho nhà cung cấp không hỗ trợ tự đăng ký client như Google (trước đây chỉ chạy với server có DCR). Tự xin `access_type=offline` để giữ kết nối lâu dài (tự làm mới token), gửi kèm client secret khi đổi/làm mới token, và tự đặt tên tài khoản bằng email Google sau khi đăng nhập.

## [0.9.2] - 2026-07-04
### Thêm mới
- **Kho Kết nối có nhóm Quảng cáo - đủ 3 nền tảng lớn**: **Meta Ads** (Facebook & Instagram) qua MCP chính chủ của Meta - bấm Kết nối là đăng nhập Facebook, không cần tạo app hay dán key; **Google Ads** qua MCP chính chủ của Google (chỉ đọc, truy vấn GAQL: chi phí, chuyển đổi, từ khoá); **TikTok Ads** qua server cộng đồng trên Marketing API chính thức (chỉ đọc - TikTok chưa mở MCP chính chủ, khi mở sẽ thay trong kho). Cả 3 mặc định Chỉ đọc; Meta bật Toàn quyền mới tạo/sửa được chiến dịch (cảnh báo tiền thật, chiến dịch tạo mới luôn ở trạng thái tạm dừng chờ bạn tự bật).
### Cải thiện
- Kết nối OAuth (vd Meta Ads) sau khi đăng nhập giờ **tự đặt tên tài khoản** (lấy đúng tên tài khoản ads) như flow dán key, và ghi ngay profile MCP cho Codex - trước đây tên để mặc định và Codex phải đợi lần đổi cấu hình sau.

## [0.9.1] - 2026-07-04
### Sửa lỗi
- `start-javis.bat` chạy server ẩn hoàn toàn - hết cửa sổ CMD đen nằm lì.

## [0.9.0] - 2026-07-04
### Thêm mới
- **Trang "Kết nối" thay trang MCP**: kho connector cài sẵn (Pancake POS, Zalo cá nhân, Webcake Landing, Botcake) - bấm Kết nối, dán key (hoặc quét QR với Zalo) là xong, không còn tự gõ URL/transport/header. Javis tự kiểm tra key và tự đặt tên tài khoản (lấy đúng tên cửa hàng từ POS). Form kỹ thuật cũ vẫn còn ở card "Tự thêm (nâng cao)".
- **Đa tài khoản chính thức**: một dịch vụ nối NHIỀU tài khoản (nhiều shop POS, nhiều số Zalo) - mỗi tài khoản một chip có tên + quyền + dấu mặc định, thêm/tắt/xoá từng cái. Zalo mỗi tài khoản chạy cô lập (home riêng) nên nhiều số chạy song song không giẫm nhau.
- **MCP HUB**: mọi bộ não (Claude Code, ChatGPT/Codex, OpenRouter, OpenAI API, Anthropic API) đấu qua MỘT điểm - Codex và engine API giờ dùng được cả MCP local dạng stdio (Zalo, Webcake) chứ không chỉ http như trước.
- **Anthropic API có vòng gọi tool** - hết cảnh "chat thuần không MCP". Engine API còn được thêm tool đọc/ghi file trong vault, `javis_use_skill` (kích hoạt skill của brain) và `javis_connections` - engine nào cũng là agent thực thụ.
- **Phân quyền 3 mức mỗi kết nối** (Chỉ đọc / Ghi nháp / Toàn quyền) chặn CỨNG tại hub theo từng lời gọi, hiểu cả tool đa hành động kiểu Pancake (`action=list` cho qua, `action=create` chặn). Loop nền mode suggest/auto bị hub chặn hành động ghi/tiền-đơn bất kể prompt nói gì. Bật Toàn quyền phải tick xác nhận rủi ro; Zalo có cảnh báo riêng về nguy cơ bị khoá tài khoản (API không chính thức).
- **Nhật ký gọi tool (audit)** xem theo từng kết nối, nút Test lại, rate limit chống spam cho Zalo.
- **Đăng nhập Zalo bằng quét QR ngay trong dashboard**: Javis tự chạy zalo-agent-cli, hiện mã QR trong modal, quét xong tự tạo kết nối (cần Node.js 20+).
- **OAuth chuẩn MCP** (PKCE + tự đăng ký client): server nào theo chuẩn thì bấm Kết nối là xong ngay trên VPS, Javis tự giữ và tự refresh token - bỏ cảnh mở terminal gõ /mcp.
- Cầu nối **Botcake** tự viết qua Public API v1 (13 tool: khách hàng, tag, flow, gửi flow, keyword...) - không cần cài gì thêm.
- **3 card Google cho kinh doanh**: Google Sheets (đổ báo cáo doanh thu/tồn kho ra bảng tính - dán service account JSON là chạy, không cần đăng nhập), Google Search Console (số liệu SEO: khách tìm gì ra website), Google Workspace (Gmail + Lịch + Drive + Docs trong 1 kết nối, OAuth tự tạo có hướng dẫn từng bước; mặc định Ghi nháp - soạn nháp được nhưng KHÔNG tự gửi mail/xoá, bật Toàn quyền phải xác nhận). Kho hỗ trợ field dạng file (dán JSON, Javis tự lo phần còn lại) và tự kèm sẵn uv/uvx để chạy connector Python.
### Cải thiện
- MCP client có **session pool sống lâu** (giữ kết nối giữa các tin nhắn) + hỗ trợ stdio/internal: hết cảnh "mỗi tin nhắn kết nối MCP lại nên hơi chậm". Hub tự làm nóng lúc khởi động.
- Registry MCP chuyển sang STATE_DIR (Docker ghi được) và **tự migrate** từ bản cũ: server cũ thành connection, backup nguyên bản ở `mcp_servers.v1.bak.json`, không mất dữ liệu.
### Bảo mật
- API key/token của kết nối **mã hoá at rest** (Fernet, key riêng theo máy). Nhật ký audit chỉ ghi TÊN tham số, không ghi giá trị. Endpoint hub xác thực bằng token nội bộ riêng, không dùng session dashboard.

## [0.8.13] - 2026-07-03
### Cải thiện
- Bảng chọn model trong Telegram làm lại theo UX gateway Hermes: chọn provider ĐÃ KẾT NỐI (Claude Code, **ChatGPT**, OpenRouter, Claude API, OpenAI API - trước đây thiếu hẳn ChatGPT) có dấu ✓ + số model, rồi lưới model 2 cột **phân trang ◀ 1/N ▶**. Danh sách model lấy LIVE từ provider (OpenRouter đủ vài trăm model thay vì vài cái trong catalog; ChatGPT hiện model Codex), có mẹo gõ `/model <id>` chọn nhanh.
- Gõ tay `/model gpt-5.5` hoặc `/model gpt-5.3-codex` giờ tự hiểu là ChatGPT (Codex) nếu đã kết nối OAuth, không còn bị nhét nhầm sang Claude.

## [0.8.12] - 2026-07-03
### Thêm mới
- Telegram có lệnh **`/brain`** - xem và đổi brain (vault) cho RIÊNG phiên của mình: gõ `/brain` mở bảng nút bấm chọn (brain đang dùng có dấu ✓), hoặc gõ thẳng tên `/brain <tên>` (khớp một phần cũng được). Đổi xong hội thoại tự reset để nạp đúng bộ nhớ/skill của brain mới; người khác dùng chung bot và dashboard KHÔNG bị ảnh hưởng. `/reset` giữ nguyên brain đã chọn.
- File gửi lên Telegram giờ rơi vào `inbox/telegram` của brain PHIÊN người gửi (trước đây luôn vào brain mặc định).
- `/status` hiển thị brain phiên đang dùng.

## [0.8.11] - 2026-07-03
### Thêm mới
- Telegram **đa phiên theo tài khoản**: mỗi chat ID giờ có ngữ cảnh hội thoại RIÊNG, không còn lẫn lộn khi nhiều người dùng chung 1 bot. Trước đây tất cả người dùng dùng chung một session (người sau nối tiếp mạch của người trước, và chỉ 1 người được trả lời tại một thời điểm). Nay mỗi tài khoản có session Claude riêng (giữ `--resume` độc lập), lịch sử OpenRouter riêng, câu `/retry` riêng.
- Các tài khoản **chạy song song**: A đang được trả lời thì B hỏi vẫn được xử lý ngay, không phải xếp hàng chờ. Trong CÙNG một tài khoản vẫn tuần tự 1 lượt/lúc (gửi câu mới khi đang bận sẽ báo "đang xử lý câu trước").
- `/reset` và `/stop` chỉ tác động **phiên của chính người gõ**: reset xoá đúng ngữ cảnh của họ, stop chỉ giết đúng tiến trình Claude của họ (không đụng người khác đang chat). `/status` hiển thị mã phiên.
- File Javis tạo ra gửi về **đúng người đang hỏi**: endpoint `POST /telegram/send-file` nhận thêm `chat_id`, và gateway nhắc engine luôn gắn chat_id của người hỏi vào lệnh gửi (thiếu thì rơi về chủ bot như cũ). Whitelist vẫn chặn ID lạ.
### Sửa lỗi
- Dashboard web: nút **Stop không còn giết nhầm lượt của người khác** đang chat song song. Mỗi kết nối WebSocket giờ có tag phiên riêng (server phát qua message hello, frontend gửi kèm khi POST `/stop`) - web vốn đã đa phiên (mỗi tab/kết nối một session, lưu SQLite resume được), đây là lỗ hổng chéo duy nhất còn lại.
- Khung chat **phóng to (chat workspace) trước đây KHÔNG hiện trạng thái** "đang suy nghĩ / đang gọi tool": thanh trạng thái cũ nằm ngoài `#chatArea` nên bị bỏ lại khi phóng to. Đã thay bằng chip hoạt động ngay trong khung chat.
### Cải thiện
- **Chip hoạt động trong khung chat** (cả thường lẫn phóng to): bong bóng 3 chấm nhún + dòng trạng thái sống ("Javis đang suy nghĩ...", "⚙ Đang gọi: pos_statistics", "✍ Đang soạn câu trả lời...") + đồng hồ đếm giây khi đợi lâu (hiện từ giây thứ 3). Chip hiện NGAY khi bấm gửi, luôn nằm dưới cùng kể cả dưới bubble đang stream, tự biến mất khi xong lượt.

## [0.8.10] - 2026-07-03
### Thêm mới
- Telegram hỗ trợ **NHIỀU chat ID** dùng chung 1 bot: ô "Chat ID được phép dùng" giờ nhận nhiều ID cách nhau dấu phẩy (vd `123456789, 987654321`) - thêm người thân/nhân viên nhắn với Javis mà không phải dựng bot riêng. Whitelist chặn đúng theo danh sách; ID nhóm (số âm) cũng dùng được.
- Nút **Gửi test** gửi tin thử tới TẤT CẢ ID và báo rõ ID nào lỗi (thường do người đó chưa bấm Start bot); thông báo nền (loop tự tạm dừng...) cũng gửi tới tất cả ID; dòng trạng thái hiện số ID được phép, cảnh báo rõ khi đang để trống (mọi người nhắn được). File tự gửi về Telegram không kèm chat cụ thể sẽ về ID ĐẦU TIÊN (chủ bot).
- Tương thích ngược hoàn toàn: cấu hình 1 ID cũ giữ nguyên, không phải làm lại gì.

## [0.8.9] - 2026-07-03
### Thêm mới
- **Trang chủ giới thiệu** (`website/index.html`): landing page 1 file HTML/CSS/JS thuần, phong cách dark nebula đồng bộ dashboard - hero gõ chữ tự động, nền đồ thị hạt sao canvas, bảng so sánh chatbot vs Javis, bento 8 tính năng, mockup Telegram có bong bóng chạy, timeline 3 bước deploy, section giới thiệu tác giả Nguyễn Minh Quý, FAQ accordion, nút copy lệnh. Mọi link tài liệu trỏ về GitHub; KHÔNG hiển thị số phiên bản trên trang. Dùng ảnh thật: screenshot đồ thị tri thức trong ô tính năng lớn (kiêm og:image khi share) + chân dung tác giả (fallback chữ MQ nếu ảnh lỗi).

## [0.8.8] - 2026-07-03
### Sửa lỗi
- Đổi tên file mẫu `.env.example` → `env.example` (bỏ dấu chấm đầu): Docker Manager của Hostinger tự quét file `.env*` trong repo khi deploy từ URL và nhập nguyên nội dung (kể cả dòng chú thích `#`) vào ô Environment, gây một loạt biến đỏ "Invalid variable name" mỗi lần deploy. Ô Environment trên Hostinger giờ chỉ cần đúng 1 biến `DOMAIN_NAME`. Ai đã dính: xoá các dòng có dấu `#` trong ô Environment một lần là sạch vĩnh viễn. Chạy local không đổi gì ngoài lệnh copy: `cp env.example .env`.

## [0.8.7] - 2026-07-03
### Thêm mới
- **Telegram thành kênh làm việc đầy đủ** (port ý tưởng gateway của hermes-agent):
  - Javis giờ **biết mình đang trả lời qua kênh nào**: gateway chèn block "Kênh hội thoại hiện tại" (Telegram DM/nhóm với ai, chat_id, các nền tảng đang kết nối) vào system prompt mỗi lượt - hỏi "em đang chat với anh qua đâu" là khai đúng, không đoán.
  - **Tự gửi file về Telegram**: file Javis tạo trong lượt (tool Write) hoặc file có đường dẫn tuyệt đối nhắc trong câu trả lời được tự động đính kèm gửi ngay sau câu trả lời (tối đa 10 file/lượt, mỗi file dưới 50MB; ảnh gửi dạng photo có preview, còn lại gửi dạng document).
  - Endpoint nội bộ `POST /telegram/send-file` (CHỈ nhận từ localhost - bên ngoài qua proxy vẫn bị chặn đăng nhập): agent chủ động gửi file bất kỳ có sẵn trên máy giữa lượt bằng curl.
  - **Nhận file/ảnh từ Telegram**: gửi file/ảnh (kèm caption) cho bot là Javis tự tải về `inbox/telegram/` trong brain rồi đọc như file đính kèm trong chat (trần tải 20MB của bot API). Voice/video chưa hỗ trợ - Javis sẽ nói rõ.
  - Tin nhắn trả lời render **MarkdownV2** (đậm/nghiêng/code/link hiện đẹp), tự fallback plain text nếu Telegram từ chối parse - không mất tin.
### Cải thiện
- Dashboard web cũng có block kênh riêng: Javis phân biệt đang nói chuyện qua web hay Telegram, và biết cách đẩy file sang Telegram khi user yêu cầu (nếu bot đang chạy).

## [0.8.6] - 2026-07-02
### Thêm mới
- **Chat workspace**: phóng to chat (nút ⛶ hoặc 🕘 Lịch sử) giờ mở thành không gian làm việc gần full màn hình kiểu Claude/Cowork - cột trái là **sidebar Lịch sử hội thoại** (＋ Hội thoại mới, tìm toàn văn, danh sách nhóm Hôm nay/Hôm qua/7 ngày/Cũ hơn, badge engine + số tin, đổi tên/xoá khi rê chuột, phiên đang mở tô sáng, bấm phát mở lại ngay), cột phải là nội dung chat căn giữa rộng tối đa ~980px. Sidebar ẩn/hiện được (nhớ trạng thái); màn hẹp tự chuyển thành ngăn kéo nổi, Esc đóng ngăn kéo trước rồi mới thu nhỏ chat. Panel Lịch sử trượt bên phải cũ được gỡ, nút 🕘 góc phải mở thẳng workspace.
- Tiện ích đọc/soạn trong chat: nút **⧉ Copy** cho từng khối code + copy cả tin nhắn Javis (hiện khi rê chuột); tin nhắn dài của bạn tự thu gọn sau 10 dòng kèm "Xem thêm"; đang cuộn đọc phía trên thì tin mới KHÔNG kéo giật xuống - hiện nút **↓ Tin mới** ở đáy khung; chip file đính kèm hiển thị ngay trong workspace khi phóng to.
### Sửa lỗi
- Tin nhắn nhiều dòng của bạn (Shift+Enter) trước đây hiển thị dính thành một dòng - giờ giữ nguyên xuống dòng.
- Copy hoạt động cả khi trình duyệt chặn Clipboard API (tự fallback), vd truy cập qua HTTP LAN.

## [0.8.5] - 2026-07-02
### Thay đổi
- Sao lưu GitHub nâng cấp thành **đồng bộ 2 CHIỀU**: mỗi lượt vừa đẩy thay đổi của máy lên repo, vừa kéo thay đổi từ máy khác về và tự hoà nhập. Dùng được nhiều máy chung 1 repo (máy nhà + VPS làm việc xen kẽ, các máy tự khớp nhau) - hết cảnh 2 máy force-push đè mất backup của nhau.
- Xung đột cùng 1 file sửa ở 2 nơi: bản có lần sửa MỚI HƠN thắng, bản thua giữ nguyên thành file `.conflict-<local|remote>-<thời điểm>` ngay cạnh (không âm thầm mất chữ nào); một bên sửa một bên xoá thì bản sửa thắng. Đẩy lên bằng push thường (bỏ force-push); máy khác chen ngang thì tự kéo về hoà tiếp rồi đẩy lại.
- Khôi phục máy mới không cần git tay: dán repo + token rồi bấm Đồng bộ ngay là brain về đủ. Thư mục brains trống được coi là chế độ KHÔI PHỤC - chỉ nhận về, không bao giờ đẩy "trạng thái trống" lên đè backup. File thiếu cục bộ (wipe/volume mới) tự được vá lại từ bản đồng bộ.
### Sửa lỗi
- Đồng bộ truyền byte nguyên văn giữa các máy (tắt autocrlf của git trên mirror) - hết cảnh cùng 1 file lệch CRLF/LF giữa Windows và VPS Linux mãi không khớp.
### Cải thiện
- Trang Tự học: mục đổi tên "⇅ Đồng bộ brain với GitHub (2 chiều)", nút "Đồng bộ ngay" báo kết quả chi tiết (nhận về bao nhiêu file, có đẩy lên không, danh sách file xung đột); trạng thái lần cuối lưu kèm báo cáo. Không đẩy được về máy (file bị khoá) thì HOÃN push để giữ an toàn dữ liệu, lần sau tự thử lại.

## [0.8.4] - 2026-07-02
### Thay đổi
- Tách 2 tầng rõ ràng: **tầng hệ thống** (chức năng mặc định của Javis OS - skill javis-builder / ingest-source / query-wiki / lint-wiki + loop tự-cải-tiến) giờ đi theo mã nguồn app tại `.claude/skills/` và `system/loops/`, cập nhật cùng phiên bản khi update app; **tầng brain** chỉ còn dữ liệu của bạn (ký ức, sources, wiki, agent/skill/workflow/loop tự tạo). Đổi brain không còn mất chức năng mặc định.
- Đồng bộ có manifest (`.javis/system-manifest.json` trong mỗi brain): app lên bản mới thì bản skill/loop hệ thống trong brain được cập nhật theo, NHƯNG file bạn đã sửa thì giữ nguyên bản của bạn (user override); loop giữ nguyên trạng thái bật/tắt, chế độ, chu kỳ bạn đã chỉnh. Lỡ xoá file hệ thống thì tự cài lại (muốn ngừng dùng hãy TẮT skill - trạng thái tắt được tôn trọng qua mọi lần update).
- Lúc khởi động đồng bộ cho MỌI brain trong thư mục brains (trước đây chỉ Brain Default được seed lúc boot, brain tạo ở bản cũ không bao giờ nhận skill mới); brain ngoài chọn qua `path:` được đồng bộ ngay lượt dùng đầu. Nút "Tạo cấu trúc" (vault init) giờ seed đầy đủ như brain mới tạo.
- Skill hệ thống được nạp NATIVE cho chat ở mọi brain (nguồn chuẩn nằm trong thư mục app - engine Claude Code đọc trực tiếp), không còn phụ thuộc bản sao trong brain.
### Cải thiện
- Trang Skills: skill hệ thống có nhãn "hệ thống", không xoá được (chỉ tắt/bật hoặc sửa - sửa thì thành bản riêng của bạn và ngừng tự cập nhật).

## [0.8.3] - 2026-07-02
### Thêm mới
- Javis Index (`Javis/index.md`): chỉ mục tầng vận hành - liệt kê MỌI agent/skill/workflow/loop/lịch trong brain, tự sinh từ file (không sửa tay), kèm dòng tổng quan + cờ sức khoẻ (workflow trỏ agent không tồn tại, agent mồ côi, skill tắt, loop tự tạm dừng). Song song wiki/index.md để bất kỳ AI/engine đọc 1 chỗ là hiểu Javis có năng lực gì.
- Bản gọn (live) được chèn vào system prompt mọi engine (Claude/Codex/OpenRouter) → giải bài toán "đổi model là mất nhận biết skill", và giúp không tạo trùng năng lực. Endpoint GET /javis/index. Tự dựng lại khi khởi động + theo nhịp nền (chỉ ghi khi đổi, không churn git).

## [0.8.2] - 2026-07-02
### Cải thiện
- Engine Tự học siết 3 kỷ luật chống bịa (đồng bộ schema vault): citation cứng cho mọi câu wiki cụ thể, gắn nhãn mục-tiêu-vs-thực-tế (không biến câu tầm nhìn thành claim chắc nịch), giữ mâu thuẫn không ghi đè. Wiki tự sinh giờ ít mà chất, đáng tin để tích luỹ.
### Thêm mới
- 3 skill vận hành Second Brain (seed vào mỗi brain, create-if-missing): **ingest-source** (tiêu hoá source, kèm 3-pass cho source dài), **query-wiki** (trả lời có trích dẫn + lưu lại kết quả giá trị), **lint-wiki** (health-check 8 loại lỗi, chỉ trả checklist). Biến 3 phép toán INGEST/QUERY/LINT từ prose thành công cụ tự kích hoạt, nhất quán đa engine.

## [0.8.1] - 2026-07-02
### Thêm mới
- Brain mặc định giờ là bộ "compounding wiki" phổ quát (không còn tối giản): mỗi brain tự seed schema doc (CLAUDE.md + AGENTS.md để Claude Code lẫn Codex tự nạp) + file điều hướng wiki (index.md, log.md, _open-questions.md) + _session-handoff.md (chuyển giữa các model không mất mạch). Encode pattern tích luỹ tri thức + 3 kỷ luật chống bịa (citation bắt buộc, mục tiêu vs thực tế, mâu thuẫn giữ rõ) + 3 phép toán INGEST/QUERY/LINT.
- Trung lập ngành: KHÔNG seed folder marketing/Bullet Journal; taxonomy mọc dần theo source thật, gói theo-ngành để dành làm opt-in. Tất cả create-if-missing (không đè file bạn đã sửa).

## [0.8.0] - 2026-07-02
### Thay đổi
- Sao lưu GitHub giờ đồng bộ **TOÀN BỘ thư mục brains** (mọi brain) trong MỘT lần thay vì từng brain (sửa lỗi các brain đè nhau khi tự động backup vào cùng repo). Mỗi brain là một thư mục con trong repo; xoá brain khỏi máy thì backup sau cũng bỏ. Khuyến nghị để mọi brain trong thư mục brains (tạo brain mới bằng nút ➕ là tự vào đó) để chuyển máy dễ.
- Cơ chế mới dùng bản sao sạch (mirror): bỏ hội thoại gốc/log/khoá + git thô của từng brain (tránh lỗi nested-repo), token không lọt .git/config.
### Thêm mới
- Đổi avatar/logo mặc định của Javis.

## [0.7.9] - 2026-07-02
### Thêm mới
- Bộ "meta-capabilities" khởi đầu, tự seed vào mỗi brain: skill **javis-builder** (dạy Javis tự tạo agent/skill/workflow/loop đúng chuẩn, có chống trùng + rào an toàn) và loop **tự-cải-tiến-javis** (mặc định TẮT, chế độ đề xuất - mỗi vòng rà hệ thống, đề xuất 1 cải tiến nhỏ an toàn, ghi báo cáo vào 05 - Projects). Tạo dạng create-if-missing, không đè file bạn đã sửa.
- Quy tắc "Làm rõ trước khi trả lời" trong system prompt: câu hỏi phức tạp/mơ hồ thì Javis tự diễn đạt lại cách hiểu + nêu giả định rồi mới làm, chỉ hỏi lại khi thực sự tắc.

## [0.7.8] - 2026-07-02
### Thêm mới
- Agent chọn được model của ChatGPT/Codex (GPT-5.x) bên cạnh Claude (Sonnet/Opus/Haiku/Fable). Agent model Codex chạy qua Codex CLI - vẫn đọc/ghi file vault + dùng MCP. Dropdown model trong Studio chia 2 nhóm Claude / ChatGPT.
- An toàn: workflow chạy nền tự động (dispatcher, file-only) luôn dùng Claude Code để giữ giới hạn công cụ, kể cả khi agent chọn Codex; model Codex chỉ áp khi chạy workflow trực tiếp ở Studio.
### Thay đổi
- Tài liệu mô tả lại: Javis xây trên CLI dạng agent của nhà cung cấp (Claude Code + Codex) và tận dụng gói subscription, không còn xoay quanh chỉ Claude. Cập nhật README, docs 07/10, nhãn Docker và system prompt.

## [0.7.7] - 2026-07-02
### Sửa lỗi
- Agent: phần chọn Model (Sonnet/Opus/Haiku) trước đây lưu vào file nhưng KHÔNG được áp khi chạy - workflow luôn dùng model mặc định. Nay model của từng agent (kể cả agent kiểm chứng) được áp THẬT vào CLI lúc chạy. Thêm lựa chọn "Fable" + "Mặc định (theo CLI)" trong dropdown; agent để trống model = dùng model mặc định.

## [0.7.6] - 2026-07-02
### Sửa lỗi
- ChatGPT/Codex trên VPS báo "gpt-5-mini không hỗ trợ khi dùng Codex với tài khoản ChatGPT": model API thường (gpt-5-mini, gpt-4o, o3...) không chạy được qua Codex. Nay tự đổi (coerce) sang model Codex hợp lệ trong catalog (mặc định gpt-5.5) ở cả chat lẫn Telegram, tự chữa lại cấu hình đã lưu, và báo cho người dùng. Bộ chọn model của ChatGPT-OAuth cũng chỉ còn liệt kê đúng model Codex (bỏ nguồn trả model ChatGPT chung).
### Thêm mới
- Guide khi deploy: thêm OCI image labels (documentation/source/url) + nhãn compose để Docker Manager (Hostinger) hiện link Documentation/Quick start cho project. Thêm QUICKSTART.md (deploy 3 cách + sự cố hay gặp) ở gốc repo; mọi link tài liệu trỏ về docs trên GitHub.

## [0.7.5] - 2026-07-02
### Thêm mới
- Sao lưu brain lên GitHub: mục mới trong trang Tự học, có hướng dẫn 3 bước ngay trên màn hình (tạo repo private → tạo token fine-grained → dán vào). Nút Kiểm tra kết nối + Sao lưu ngay + công tắc tự sao lưu định kỳ. Tài liệu chi tiết: docs/18-sao-luu-github.md.
- Backup đẩy toàn bộ brain lên repo GitHub riêng (force-push, local là bản gốc); khôi phục bằng git clone khi mất máy/VPS.
### An toàn
- Token GitHub lưu nội bộ settings.json (gitignored), KHÔNG đẩy lên repo và tự che trong mọi thông báo lỗi; push dùng URL tạm nên token không nằm trong .git/config. File nhạy cảm (log thô, hội thoại gốc, khoá lock) được .gitignore loại khỏi bản đẩy. Cảnh báo rõ trên UI: chỉ dùng repo Private.

## [0.7.4] - 2026-07-02
### Thay đổi
- Tự học: mặc định BẬT sẵn + chế độ Tự ghi + bật cả 4 khả năng (Ký ức, Wiki, Kỹ năng, Việc) cho cài mới. Học chạy ngay từ đầu, không phải vào bật thủ công.
- Bỏ yêu cầu git: chế độ Tự ghi giờ hoạt động KỂ CẢ khi máy chưa có git (trước đây tự hạ về Chạy thử). Có git thì vẫn tự commit để hoàn tác 1 chạm; không có git thì vẫn ghi bình thường, chỉ thiếu undo/backup.
- Tự học giờ tự đăng ký brain đang trò chuyện: chat trên vault nào là học vault đó, không cần vào trang Tự học bấm lưu để thêm vault vào danh sách.
### An toàn
- Các rào an toàn của engine học GIỮ NGUYÊN: fork chỉ-đọc cô lập (0 MCP), quét lộ khoá + câu tiêm, chặn ghi ngoài phạm vi, ký ức chỉ thêm không đè.

## [0.7.3] - 2026-07-02
### Thêm mới
- Loop có thêm chế độ "Toàn quyền" (mode full): loop tự thao tác THẬT ra ngoài qua MCP không cần hỏi (tạo/sửa đơn, chạy quảng cáo tiêu tiền, gửi tin, đăng bài). Dành cho ai muốn loop tự làm hết. Kèm cảnh báo rủi ro đỏ trong form + hộp xác nhận khi lưu và khi bật; tab Lịch đánh dấu "⚠ TOÀN QUYỀN".
- 3 mức quyền rõ ràng: Đề xuất (chỉ đọc) · Tự làm an toàn (ghi nháp + đọc MCP, KHÔNG tiền/đơn) · Toàn quyền (làm mọi thứ). Mặc định vẫn là mức an toàn; chế độ toàn quyền phải tự bật.
### An toàn
- Loop toàn quyền vẫn tôn trọng cài đặt "chặn tool" (deny_tools) của từng MCP server; bước tự kiểm chứng chuyển sang soi "đúng phạm vi nhiệm vụ" thay vì cấm hành động. Javis khi chat KHÔNG bao giờ tự đặt loop sang toàn quyền - chỉ khi người dùng yêu cầu rõ.

## [0.7.2] - 2026-07-02
### Thay đổi
- Form tạo Loop gọn còn Tên + Mô tả (+ chế độ + chu kỳ): bỏ bộ chọn "Loại nhiệm vụ" 4 nút. Mỗi loop giờ chỉ cần mô tả việc cần làm mỗi vòng. Tinh chỉnh nâng cao (giờ im lặng, trần vòng/ngày, profile code) sửa trực tiếp trong file Javis/loops/<tên>.md.
- Loop giờ ĐỌC được dữ liệu thật qua MCP (POS, quảng cáo, lịch...) để làm việc - trước đây loop bị cô lập 0-MCP. An toàn giữ 3 lớp: tôn trọng deny_tools từng server, chỉ dẫn cứng cấm tạo đơn/tiêu tiền/quảng cáo/đăng bài/gửi tin (chỉ được đọc + ghi nháp), và kiểm chứng độc lập sẽ fail nếu phát hiện hành động ghi ra ngoài. Loop chạy nền vẫn KHÔNG có Bash/Web (trừ profile code cho loop sửa mã, vốn 0-MCP).

## [0.7.1] - 2026-07-02
### Cải thiện
- Trang loop: đổi tên mục sidebar "Tự cải thiện" thành "Loop" cho gọn, đúng bản chất.
- Bỏ nút "LINT Wiki" khỏi trang Loop (engine Tự học đã lo bảo trì Wiki qua curator/LINT chỉ-đề-xuất), tránh trùng chức năng.

## [0.7.0] - 2026-07-02
### Thêm mới
- MULTI-LOOP: "Vòng lặp tự cải thiện" nâng thành hệ NHIỀU loop. Mỗi loop = 1 file `Javis/loops/<slug>.md` trong vault (sửa được bằng Obsidian/chat/Studio), có bật/tắt, chu kỳ riêng, giờ im lặng (quiet_hours), trần vòng/ngày, workspace + tools_profile (vault-safe mặc định / code cho loop sửa mã). Thực thi TUẦN TỰ (1 vòng/lúc), state runtime tách riêng ở `Javis/loop-state.json`.
- Tự bảo vệ: loop lỗi/kiểm chứng ✗ 3 lần liên tiếp thì TỰ TẠM DỪNG (ghi lý do + log, báo Telegram nếu có bot); bật lại hoặc Chạy ngay để tiếp tục.
- API mới `/loops` (list/tạo/sửa/toggle/xoá/run-now/log lọc theo loop). `/loop/*` cũ giữ nguyên, trỏ về loop legacy `vong-lap-goc`.
- Trang "Tự cải thiện" thành DANH SÁCH loop: trạng thái, lần chạy cuối + kết quả kiểm chứng, next run, nút bật/tắt - chạy ngay - sửa - xoá, form tạo loop đầy đủ, nhật ký lọc theo loop.
- Tab Lịch hiện MỌI loop như routine builtin (id `__loop__:<slug>`): bật/tắt ngay tại đó; xoá thì phải sang trang Tự cải thiện.
- Javis chat = ĐIỀU PHỐI VIÊN: system prompt thêm quy trình chọn công cụ nhỏ nhất đủ hoàn thành (trả lời → task Kanban → skill → agent → workflow → lịch → loop), kiểm tra trùng trước khi tạo, loop tạo qua chat mặc định suggest + tắt.
### Cải thiện
- Migrate 1 lần: `loop_config.json` cũ tự sinh `Javis/loops/vong-lap-goc.md` (giữ nguyên toàn bộ custom_goal), json cũ giữ làm backup.

## [0.6.6] - 2026-07-02
### Thêm mới
- Nối engine tự học vào Kanban: capability "Việc (Kanban)" - sau mỗi hội thoại, engine học đề xuất việc nền vào backlog (dedup theo tên, chờ duyệt).
### Sửa lỗi
- Dashboard chết toàn bộ (Enter không gửi, stats trống, không graph) do app.js bám nút học cũ đã gỡ - đã guard + nghỉ hưu auto-learn client cũ.

## [0.6.5] - 2026-07-02
### Sửa lỗi
- docker-compose.hostinger.yml "không cài được": bỏ ${DOMAIN_NAME:?...} (bắt buộc biến, thiếu là deploy fail). Nay LUÔN deploy được: chưa đặt DOMAIN_NAME thì chạy tạm ở :7777, đặt DOMAIN_NAME thì có HTTPS. Publish lại cổng 7777 làm đường vào dự phòng.

## [0.6.4] - 2026-07-02
### Sửa lỗi
- docker-compose.yml: Watchtower chuyển sang profile "update" (mặc định TẮT) nên deploy base compose KHÔNG còn "Partially running" (Watchtower cần Docker socket, Hostinger hay chặn). Bật auto-update khi cần: docker compose --profile update up -d.
### Cải thiện
- README: sửa mục cài Hostinger dùng docker-compose.hostinger.yml + đặt DOMAIN_NAME cho tên miền/HTTPS; bỏ thông tin sai "Hostinger tự cấp URL hstgr.cloud".

## [0.6.3] - 2026-07-02
### Sửa lỗi
- docker-compose.hostinger.yml: đổi ports "7777:7777" (cố định) thành "7777" (ngẫu nhiên, giống Hermes) để nút Open trỏ thẳng domain HTTPS của Traefik thay vì http://<ip>:7777. Truy cập qua https://<DOMAIN_NAME>.

## [0.6.2] - 2026-07-02
### Sửa lỗi
- docker-compose.hostinger.yml: đã kiểm chứng Hostinger KHÔNG cấp biến TRAEFIK_HOST cho compose dán tay (link ra "javis-os." cụt). Nay Host BẮT BUỘC DOMAIN_NAME (dùng ${DOMAIN_NAME:?...}): thiếu thì deploy báo lỗi rõ ràng thay vì ra link hỏng. Tài liệu chỉ rõ đặt DOMAIN_NAME=javis.<hostname-vps>.hstgr.cloud ở ô Environment.

## [0.6.1] - 2026-07-01
### Sửa lỗi
- docker-compose.hostinger.yml: Host mặc định dùng ${COMPOSE_PROJECT_NAME}.${TRAEFIK_HOST} (đúng mẫu Hermes) thay cho giá trị localhost -> deploy trên Hostinger là TỰ có link <tên-project>.<hostname-vps>.hstgr.cloud + HTTPS, không cần đặt biến gì. Muốn tên miền riêng thì đặt DOMAIN_NAME (ghi đè). Ai deploy trên VPS của họ cũng ra link đúng.

## [0.6.0] - 2026-07-01
### Thay đổi
- Đồng bộ NỐT toàn bộ tên hạ tầng nội bộ sang javis: biến môi trường JAVIS_*, volume javis-data/javis-brains, service/container/user javis (/home/javis), profile codex javis, marker JAVIS_METRICS, và các file javis.service / start-javis.vbs / stop-javis.bat. Toàn dự án dùng một tên duy nhất.
- LƯU Ý khi redeploy: volume đã đổi tên nên bản mới bắt đầu TRỐNG (cần tạo lại admin + nạp lại brain), hoặc tự chép dữ liệu từ volume cũ sang javis-data/javis-brains. Nếu trước đó đặt biến admin trên Hostinger, đổi tiền tố sang JAVIS_ADMIN_USER / JAVIS_ADMIN_PASSWORD.

## [0.5.1] - 2026-07-01
### Thay đổi
- Đổi tên repo/image GitHub sang javis-os (image ghcr.io/blogminhquy/javis-os, GITHUB_REPO, link cài đặt trong README/DEPLOY).

## [0.5.0] - 2026-07-01
### Thay đổi
- Đổi thương hiệu hiển thị sang Javis (giao diện, tài liệu, README, system prompt).
### Thêm mới
- docker-compose.hostinger.yml dùng ${COMPOSE_PROJECT_NAME} cho tên router/service Traefik: chạy được nhiều bản Javis trên cùng 1 VPS mà không đụng nhau (giống đuôi ngẫu nhiên -efxd của Hermes).

## [0.4.7] - 2026-07-01
### Sửa lỗi
- docker-compose.hostinger.yml gắn nhãn Traefik đúng mẫu app Hermes: BỎ phần networks/external traefik-proxy (chính chỗ làm deploy báo "network not found"). Traefik của Hostinger tự thấy container qua nhãn.
### Thêm mới
- Có link mặc định chạy HTTPS mà không cần mua tên miền: đặt DOMAIN_NAME=javis.<hostname-vps>.hstgr.cloud (Hostinger có wildcard DNS + tự cấp SSL).

## [0.4.6] - 2026-07-01
### Sửa lỗi
- docker-compose.hostinger.yml không deploy được trên Hostinger: bỏ yêu cầu mạng ngoài `traefik-proxy` (gây lỗi "network not found"). Bản mới chỉ 1 container, publish cổng 7777, deploy là chạy; gắn tên miền + HTTPS là bước tùy chọn (Hostinger UI hoặc nhãn Traefik thủ công, hướng dẫn trong file).

## [0.4.5] - 2026-07-01
### Sửa lỗi
- docker-compose.hostinger.yml bỏ Watchtower (cần Docker socket, hay gây "Partially running" trên Hostinger Docker Manager). Bản Hostinger giờ chỉ 1 container javis + nhãn Traefik, cập nhật bằng Redeploy.

## [0.4.4] - 2026-07-01
### Thêm mới
- File docker-compose.hostinger.yml: chạy Javis trên Hostinger với tên miền riêng + HTTPS qua Traefik có sẵn của Hostinger, bỏ cổng :7777.
### Sửa lỗi
- Tài liệu Hostinger nói đúng thực tế: compose gốc chỉ vào bằng IP:7777; muốn tên miền và SSL phải dùng bản có nhãn Traefik (docker-compose.hostinger.yml).

## [0.4.3] - 2026-07-01
### Thêm mới
- Khu Tên miền & SSL trong Cài đặt làm mới: huy hiệu trạng thái DNS và SSL, nút Bật SSL chủ động xin chứng chỉ rồi kiểm tra kết quả.
### Sửa lỗi
- Số phiên bản ở góc thanh bên nay đọc đúng bản đang chạy (trước bị cố định 0.4.0).
### Cải thiện
- Trạng thái tên miền rõ ràng: DNS đã trỏ đúng chưa, SSL bật chưa, kèm lệnh bật Caddy cho bản Docker khi cần.

## [0.4.2] - 2026-07-01
### Thêm mới
- Trang **Cập nhật** (mục Logs cũ trên thanh bên): nhật ký phiên bản và các thay đổi mới, đọc thẳng trong app.
- Tự đối chiếu bản đang cài với bản mới nhất trên GitHub, đánh dấu phiên bản "đang dùng" và bản "có thể cập nhật".

## [0.4.1] - 2026-07-01
### Sửa lỗi
- Upload file trên Docker/VPS báo "lỗi máy chủ (500)": thư mục stage tạm đổi sang STATE_DIR ghi được (`/data/state`) thay vì code tree `/app` chỉ đọc.
- Endpoint upload bọc chống lỗi: sự cố môi trường trả thông báo rõ ràng kèm log thay vì lỗi 500 khó đoán.
### Thêm mới
- Bộ tài liệu hướng dẫn sử dụng chi tiết trong `docs/` (17 trang) và mục lục nối vào README.
### Cải thiện
- Bỏ toàn bộ ký tự gạch ngang dài khỏi giao diện và tài liệu cho giọng nói đọc mượt hơn.

## [0.4.0] - 2026-06-30
### Thêm mới
- Trang **Cài đặt** riêng: chọn giọng đọc theo nhà cung cấp (Edge TTS, OpenAI, ElevenLabs), tinh chỉnh giao diện, avatar, tên miền.
- Nút **Cập nhật ngay** trong Tổng quan: cập nhật phiên bản mới ngay trên giao diện, không cần terminal.
- Đổi logo/avatar và trỏ tên miền riêng chạy HTTPS ngay trong app.
### Cải thiện
- Gộp cài đặt vào thanh bên, thu gọn điều hướng.

## [0.3.0] - 2026-06-29
### Thêm mới
- Chạy ChatGPT qua Codex CLI trên VPS: đăng nhập bằng gói subscription, dùng được cả MCP của Javis.
- Đăng nhập Claude bằng OAuth device-code ngay trong giao diện (không cần terminal).
- Kiến trúc đa Second Brain: quản lý nhiều brain trong thư mục `brains/`, tạo và xoá brain trong app.
### Sửa lỗi
- Trạng thái bot Telegram hiển thị đúng thực tế (đang chạy, lỗi 409, chưa bật).

## [0.2.0] - 2026-06-28
### Thêm mới
- Bộ cài đặt lần đầu (wizard) chọn 1 trong 3 nhà cung cấp: Claude Code, ChatGPT, OpenRouter.
- Triển khai 1-click qua Hostinger Docker Manager (kéo image GHCR).
- Tự bật HTTPS bằng Caddy, logo và favicon thương hiệu.
### Bảo mật
- Bắt buộc đăng nhập khi chạy public, MÃ THIẾT LẬP chống chiếm tài khoản admin.

## [0.1.0] - 2026-06-26
### Thêm mới
- Bản đầu tiên: trợ lý AI cá nhân chạy bằng Claude Code, giọng nói, đồ thị tri thức 3D, Second Brain.
- README chi tiết: giới thiệu, cài đặt mọi cách, hướng dẫn dùng, bảo mật, khắc phục sự cố.
