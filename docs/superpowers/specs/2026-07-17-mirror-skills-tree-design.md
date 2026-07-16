# B4: mirror_skills copy cả cây con + cổng chữ ký

Ngày: 2026-07-17
Trạng thái: đã duyệt thiết kế, chờ kế hoạch triển khai

Đây là spec riêng cho B4, phần đã bị HOÃN khỏi kế hoạch A+B ngày 2026-07-16
(xem `2026-07-16-skill-telemetry-authoring-design.md`, mục "HOÃN: B4").

## Phát hiện lật ngược quyết định hoãn

Lần trước em khuyên hoãn với lý do "làm đệ quy sẽ biến mỗi lượt chat thành một lần đi bộ +
băm toàn bộ cây skill". Lý do đó dựa trên **suy luận, không phải phép đo**. Đo thật:

| brain | file | `mirror_skills` HIỆN TẠI | cổng chữ ký stat-only |
|---|---|---|---|
| My Bullet Journal | 41 | **52,48 ms** | **5,79 ms** |
| Ngọc Thu Phạm | 30 | 44,23 ms | 6,02 ms |
| Brain Default | 9 | 11,62 ms | 1,64 ms |

Hai điều rơi ra:

**1. `mirror_skills` đang tốn ~52ms MỖI LƯỢT CHAT, ngay bây giờ, chưa cần đệ quy gì cả.**
Nó đọc và băm `SKILL.md` hai lần (nguồn + đích) cho mỗi skill, mỗi lần được gọi. Mà nó được
gọi từ `build_system_prompt` (`main.py:184`) - hàm ĐỒNG BỘ, chạy mỗi lượt chat dashboard, mỗi
tin Telegram, mỗi task Kanban, mỗi vòng loop, mỗi nhắc hẹn, mỗi lần spawn learn. Đây là một
lỗi hiệu năng CÓ SẴN mà không ai biết, và nó chặn event loop y hệt hai lỗi mà đợt A+B vừa vá
(`bump` phải qua `to_thread`, `BrainLock` phải hạ timeout xuống 1s).

**2. Cổng chữ ký chỉ dùng `stat`, không đọc byte nào, rẻ hơn 9 lần** - và phủ luôn thư mục con.

Nên bản đệ quy CÓ cổng chữ ký chạy ~6ms thay vì 52ms. Không phải "rủi ro cao đổi lấy lợi ích
bằng không". Nó **nhanh hơn hiện trạng 9 lần** và tiện thể mang `references/` theo.

Bài học ghi lại: sáu blocker lần trước đều CÓ THẬT, nhưng kết luận "hoãn" thì sai, vì nó dựa
trên một giả định về chi phí mà không ai đo. Đo trước, kết luận sau.

## Sáu blocker cũ, tình trạng bây giờ

1. **Chi phí mỗi lượt chat** - GIẢI bằng cổng chữ ký. 52ms -> ~6ms, tức là cải thiện chứ
   không phải hồi quy.
2. **Chặn event loop** - GIẢI. ~6ms là chấp nhận được, và lock lấy kiểu không-chờ nên không
   bao giờ xếp hàng.
3. **Bài toán lock** - GIẢI bằng lock RIÊNG cho mirror. Đã kiểm chứng bằng cách đọc code:
   `_LOCK` (`system_sync.py:280`) chỉ bị lấy ở ĐÚNG HAI chỗ - `sync_brain:289` và
   `ensure_synced:369` - và `mirror_skills` KHÔNG BAO GIỜ lấy nó. Một lock riêng chỉ được lấy
   bên trong `mirror_skills`, và không có lock nào khác bị lấy khi đang giữ nó => không có
   chu trình => không deadlock.
4. **Gọi kép lúc khởi động** - GIẢI miễn phí. Lần hai hoặc thấy chữ ký không đổi, hoặc không
   lấy được lock, đằng nào cũng thoát ngay.
5. **Không test nào** - dựng `test_system_sync.py` từ số 0. Nằm trong phạm vi.
6. **Không sửa được `html-to-webcake`** - ĐÚNG, và vẫn ngoài phạm vi (anh Quy chốt). Lỗ nằm
   ở `_system_items` (`system_sync.py:142-160`), phía TRÊN `mirror_skills`.

## Kiến trúc

### Cổng hai tầng trong `mirror_skills`

**Tầng 1 (đường nóng, ~6ms, 99% lượt chạm):** cộng chữ ký CHỈ bằng `stat` trên cây
`<root>/skills`. So với cache trong bộ nhớ theo root đã resolve. Không đổi -> trả về NGAY.

**Tầng 2 (hiếm):** chữ ký đổi -> copy đệ quy thật -> cập nhật cache.

### Thành phần

- `_mirror_signature(canonical: Path) -> str` - đi `os.scandir` đệ quy, gộp
  `(đường dẫn tương đối, st_mtime_ns, st_size)` của MỌI file thành một sha256. KHÔNG đọc nội
  dung file nào. Bỏ qua `.disabled`. `follow_symlinks=False` ở cả `is_dir` lẫn `stat`.
  Chuỗi rỗng nếu thư mục không tồn tại. OSError -> bỏ qua entry đó, không ném.
- `_MIRROR_SIG: dict[str, str]` - cache module-level, khoá = root đã resolve. Xoá theo tiến
  trình (khởi động lại là mất).
- `_MIRROR_LOCKS: dict[str, threading.Lock]` - lock theo root, lấy kiểu `acquire(blocking=False)`.
- `mirror_skills(root)` - điều phối: chữ ký -> kiểm cache -> lấy lock không-chờ -> copy đệ quy
  -> cập nhật cache -> nhả lock.

### Vì sao lock lấy kiểu không-chờ

Nếu luồng khác đang mirror đúng root đó, nó đang làm ĐÚNG việc mình định làm. Xếp hàng chờ
chỉ tổ chặn event loop mà không được gì. Trả về ngay là đúng.

Đây cũng là cách xử blocker 4: `ensure_synced` -> `sync_brain` -> `mirror_skills` (giữ
`_LOCK`), rồi `main.py:184` -> `mirror_skills` lần nữa. Lần hai thấy chữ ký vừa được cập nhật
nên thoát ở tầng 1, chưa cần tới lock.

### Copy đệ quy

```
rels = sorted(p.relative_to(d).as_posix() for p in d.rglob("*") if p.is_file())
for rel in rels:
    dst_f = dst_dir / rel
    dst_f.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(str(d / rel), str(dst_f))
```

**Bỏ hẳn việc băm nội dung trong mirror.** Cổng chữ ký đã làm đúng việc "nội dung có đổi
không", rẻ hơn nhiều. Giữ cả hai là thừa.

`skill_hash` KHÔNG đụng tới - `sync_brain:303`, `LEGACY_HASHES:388-405` và CLI `--hash`
phụ thuộc output chính xác của nó. Ta chỉ THÔI DÙNG nó trong `mirror_skills`.

### Bất biến phải giữ nguyên

- Add/update-only. KHÔNG xoá gì ở `mirror/<slug>` mà nguồn không có. Việc gỡ mirror khi
  tắt/xoá skill do endpoint lo (`main.py:2186` rmtree).
- Bỏ qua `.disabled` (mirror skill đã tắt = vô tình bật lại native).
- Cổng vào vẫn là `(p / "SKILL.md").is_file()`.
- try/except từng skill: 1 skill lỗi không chặn các skill còn lại.
- `mirror_skills` TUYỆT ĐỐI không lấy `_LOCK`.

## Bug có sẵn được vá miễn phí

Hôm nay cổng skip chỉ băm `SKILL.md` (`system_sync.py:251-256`) nhưng vòng copy lại copy MỌI
file top-level (`:258-260`). Nên file phụ ngang hàng đổi nội dung mà `SKILL.md` không đổi thì
bản mirror **không bao giờ nhận**. Chữ ký `stat` phủ mọi file nên lỗi này biến mất.

## Kiểm thử

Dựng `server/test_system_sync.py` từ số 0 - hôm nay KHÔNG một test nào trong repo chạm
`mirror_skills`, và file mà spec A+B giả định là có thì không tồn tại.

Quy ước nhà (bắt buộc): KHÔNG pytest. Script chạy thẳng, `check(name, cond)` + `_fails` +
`sys.exit(1)`. Mẫu: `server/test_loop_ambient.py:23-30` và `:117-120`. Env `JAVIS_STATE_DIR`
đặt TRƯỚC import. Tên file phải là `server/test_*.py` thì CI (`.github/workflows/ci.yml:29-39`)
mới glob thấy. Lệnh chạy: `cd server && ../.venv/Scripts/python.exe test_system_sync.py`.

Phủ:
- `references/` và `scripts/` tới được mirror (điều B4 sinh ra để làm).
- File phụ ngang hàng đổi -> mirror nhận (bug có sẵn ở trên).
- Bỏ qua `.disabled`.
- Add-only: file lạ trong mirror KHÔNG bị xoá.
- Không đổi gì -> **đếm được 0 lần copy**. Dùng spy trên `shutil.copy2`. TUYỆT ĐỐI không
  kiểm bằng `mtime`: `shutil.copy2` giữ nguyên mtime của NGUỒN nên đích luôn cùng mtime dù
  có copy lại hay không - test kiểu đó xanh cả khi code sai. Bài học đã trả giá ở đợt A+B.
- Không đổi gì -> **không đọc nội dung file nào**. Spy trên `Path.read_text`/`read_bytes`
  hoặc đếm qua `shutil.copy2`; chứng minh tầng 1 thật sự chặn ở `stat`.
- Hai luồng đồng thời trên cùng root -> một cái thoát ngay, không treo.
- File nhị phân đi qua nguyên vẹn (chữ ký dùng stat nên không đụng nội dung, nhưng cần chốt).

## Rủi ro

**Bước lùi tự-lành (thật, đã báo và anh Quy chấp nhận).** Cache nằm trong bộ nhớ và chữ ký
tính trên NGUỒN. Nếu bản mirror bị phá từ bên ngoài mà nguồn không đổi, `mirror_skills` sẽ
skip và mirror ở lại hỏng cho tới khi khởi động lại tiến trình. Code hôm nay so nguồn với
đích nên tự lành.

Giảm nhẹ: tắt skill thì `main.py:2186` rmtree mirror NHƯNG cũng dời nguồn sang `.disabled`
-> chữ ký đổi -> lần mirror kế tiếp phủ. Phá `.claude/skills` bằng tay không phải thao tác
bình thường. Khởi động lại tiến trình xoá cache -> tự lành.

**Chi phí lần đầu mỗi tiến trình:** cache rỗng -> lượt chat đầu tiên cho mỗi brain trả giá
một lần copy đầy đủ. Chấp nhận được, và vẫn rẻ hơn 52ms × mọi lượt như hiện nay.

**`rglob` trên cây có symlink có thể lặp.** Đã kiểm: đĩa hiện KHÔNG có symlink nào dưới bất
kỳ thư mục skill nào. Vẫn dùng `follow_symlinks=False` cho chắc.

## Ngoài phạm vi (cố ý)

- `_system_items` ship cây con cho skill HỆ THỐNG, tức là vá `html-to-webcake` đang hỏng ở
  mọi brain. Đòi đổi manifest từ per-item sang per-file - thứ quyết định app có tự đè skill
  user đã sửa hay không. Việc riêng, cần cân nhắc riêng.
- Gỡ `mirror_skills` khỏi `main.py:184` (đường nóng). Sau khi có cổng chữ ký thì ~6ms là
  chấp nhận được, và giữ nó ở đó bảo toàn tính chất "skill viết giữa phiên hiện ra ngay
  không cần khởi động lại" - đúng lý do dòng 184 tồn tại.
- Làm `build_system_prompt` thành async. Thay đổi lớn, chạm nhiều call site, không cần thiết
  một khi chi phí đã xuống ~6ms.
