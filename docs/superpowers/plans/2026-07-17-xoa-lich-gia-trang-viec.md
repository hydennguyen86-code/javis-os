# Giai đoạn 1: Xoá Lịch giả, gộp về một trang "Việc" - Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Xoá registry Lịch (không executor nào đọc nó), bịt lỗ `bypassPermissions` của `/automations/sync`, và gộp loop + nhắc hẹn về một trang "Việc" duy nhất.

**Architecture:** Thuần xoá + đổi tên, không đổi hành vi thực thi. `automations.json` chưa từng được scheduler đọc (`main.py:3613-3656` không có nhánh nào), và 0 file `automations.json` tồn tại trên cả 4 brain, nên phía dữ liệu user không có gì để migrate. Endpoint `/automations` GET được thay bằng `/jobs` trả union loop + nhắc hẹn (đúng thứ nó vốn đã trả qua `builtin`), phần registry tay bị bỏ. Studio page Lịch bị xoá, rail `selfimprove` đổi nhãn thành "Việc" và render thêm nhắc hẹn - nếu không, xoá rail Lịch sẽ làm user **mất chỗ nhìn nhắc hẹn**, vì `pending_as_automations` hiện chỉ hiện ở đó.

**Tech Stack:** Python 3.12, FastAPI, vanilla JS (dashboard), test script thuần (không pytest).

Spec: `docs/superpowers/specs/2026-07-17-hop-nhat-viec-dinh-ky-design.md`

## Global Constraints

- **TUYỆT ĐỐI không dùng ký tự em dash (U+2014)** trong bất kỳ file nào: code, comment, test, doc, commit message. Dùng "-" hoặc viết lại câu. (CLAUDE.md, nguyên tắc 8.)
- Tiếng Việt là ngôn ngữ chính cho comment, docstring, tên hiển thị, thông báo lỗi.
- Test là **script thuần, không pytest**. Quy ước nhà: `server/test_*.py`, có `def check(name, cond)`, gom `_fails`, `sys.exit(1)` khi có lỗi. CI chạy `for f in test_*.py; do python "$f"; done` (`.github/workflows/ci.yml:35-37`), nên mọi file `server/test_*.py` tự động vào CI.
- Chạy test bằng venv: `.venv/Scripts/python.exe` (python hệ thống thiếu lib).
- Test phải tự cô lập: `os.environ.setdefault("JAVIS_STATE_DIR", tempfile.mkdtemp(prefix="..."))` **trước** khi import module Javis.
- **Helper của `dashboard/console.js`** (dùng cho Task 3): chỉ có `esc(s)` (`:116`) và `fbrain()` (`:363`), gọi HTTP bằng `fetch()` trần với `FormData` dựng tại chỗ. **KHÔNG** có `api()`, `fd()`, `brain()` - đó là helper của `studio.js`, không dùng được ở console.js.
- Không chạm `Javis/loops/*.md`, `loop-state.json`, hay `system_sync.LEGACY_HASHES` trong giai đoạn này. Loop giữ nguyên hành vi.
- Không sửa `self_improve.py:105-113` (`_isolate`). Nó là nhánh chết trong production (`main.py:3029` luôn inject `apply_mcp`) nhưng `test_loop_ambient.py` đang dựa vào nó.

## File Structure

| File | Trách nhiệm sau giai đoạn 1 |
|---|---|
| `server/main.py` | Bỏ 5 route `/automations*` + 3 helper registry + khối caps. Thêm `_jobs_payload` + route `/jobs`, `/jobs/toggle`, `/jobs/cancel`. |
| `server/test_jobs.py` | **Mới.** Phủ: route cũ chết, route mới sống, helper đã xoá, caps sạch, union loop + nhắc hẹn, đếm `running`. |
| `dashboard/studio.js` | Bỏ page `automations` (loader, form `editAutomation`, nút sync). |
| `dashboard/console.js` | Bỏ rail `automations`. Rail `selfimprove` đổi nhãn "Loop" → "Việc", render thêm khối nhắc hẹn, sửa copy trỏ tới tab Lịch. |
| `dashboard/index.html` | Bỏ `panel-automations`. Bỏ panel loop cũ đã chết (`:160-192`). |
| `dashboard/app.js` | Bỏ fetch `/loop/config` của panel chết (`:1497`). |

**Ghi chú decomposition:** khối registry + khối caps **phải cùng một task**. `_gather_capabilities` (`main.py:3352`) gọi `_read_automations`; xoá helper mà để lại lời gọi thì `rebuild_javis_index` ném `NameError` **mỗi tick scheduler** (`main.py:3650-3651`). Reviewer không thể duyệt cái này mà từ chối cái kia, nên chúng là một deliverable.

---

### Task 1: Xoá registry Lịch, thay bằng `/jobs`

**Files:**
- Modify: `server/main.py:3140-3262` (xoá `_automations_path`/`_read_automations`/`_write_automations`, 4 route `/automations*`; thêm `_jobs_payload` + 3 route mới)
- Modify: `server/main.py:3324, 3352-3354, 3411-3413` (xoá khối caps chết)
- Test: `server/test_jobs.py` (tạo mới)

**Interfaces:**
- Consumes: `_loops_as_routines(brain) -> list[dict]` (`main.py:3169`, giữ nguyên), `reminders_feature.pending_as_automations(brain) -> list[dict]` (`reminders.py:278`, giữ nguyên), `reminders_feature.cancel(brain, rid) -> bool` (`reminders.py:300`), `loop_feature.toggle(brain, slug) -> dict|None`.
- Produces: `_jobs_payload(brain: str) -> dict` trả `{"jobs": list[dict], "running": int, "total": int}`. Route `GET /jobs`, `POST /jobs/toggle`, `POST /jobs/cancel`. Task 3 (UI) tiêu thụ đúng ba route này. `_gather_capabilities(brain)` trả dict **không còn** key `"automations"`.

- [ ] **Step 1: Viết test thất bại**

Tạo `server/test_jobs.py`:

```python
"""Test trang Việc (/jobs) sau khi xoá registry Lịch giả. Chạy tay / CI:

    cd server && python test_jobs.py

Bối cảnh: automations.json CHƯA TỪNG có executor - _scheduler_loop (main.py:3613-3656) không
có nhánh nào đọc nó, và 0 file automations.json tồn tại trên cả 4 brain. Giai đoạn 1 xoá nó và
thay /automations GET bằng /jobs = union loop (việc bền) + nhắc hẹn (việc phù du).

Phủ:
- 5 route /automations* đã biến mất khỏi app.routes; /jobs + /jobs/toggle + /jobs/cancel có mặt.
- 3 helper registry đã xoá khỏi module (không còn đường ghi automations.json).
- caps: key 'automations' đã xoá, và _gather_capabilities/_render_javis_index còn chạy được
  (nếu xoá helper mà để lại lời gọi thì rebuild_javis_index NameError MỖI tick scheduler).
- _jobs_payload gộp đúng 2 nguồn và đếm running đúng.
"""
import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("JAVIS_STATE_DIR", tempfile.mkdtemp(prefix="javis-jobstest-"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import main  # noqa: E402

_fails = []


def check(name, cond):
    print(("ok  " if cond else "FAIL ") + name)
    if not cond:
        _fails.append(name)


src = (Path(__file__).parent / "main.py").read_text(encoding="utf-8")
paths = {getattr(r, "path", "") for r in main.app.routes}

# ---- 1. Route: cũ chết, mới sống ----
check("route: mọi /automations* đã xoá", not any(p.startswith("/automations") for p in paths))
check("route: GET /jobs có mặt", "/jobs" in paths)
check("route: POST /jobs/toggle có mặt", "/jobs/toggle" in paths)
check("route: POST /jobs/cancel có mặt", "/jobs/cancel" in paths)

# ---- 2. Helper registry đã xoá hẳn (không còn đường ghi automations.json) ----
check("helper: _read_automations đã xoá", not hasattr(main, "_read_automations"))
check("helper: _write_automations đã xoá", not hasattr(main, "_write_automations"))
check("helper: _automations_path đã xoá", not hasattr(main, "_automations_path"))
check("nguồn: không còn chuỗi 'automations.json'", "automations.json" not in src)

# ---- 3. caps sạch VÀ còn chạy được ----
# Đây là assert quan trọng nhất của task: xoá _read_automations mà để lại lời gọi ở
# _gather_capabilities:3352 → rebuild_javis_index (main.py:3650-3651) ném NameError mỗi tick.
caps = main._gather_capabilities("brain")
check("caps: không còn key 'automations'", "automations" not in caps)
check("caps: _gather_capabilities vẫn chạy (không NameError)", isinstance(caps, dict))
check("caps: _render_javis_index vẫn chạy", isinstance(main._render_javis_index(caps), str))
check("caps: index không còn mục 'Lịch (automations)'",
      "Lịch (automations)" not in main._render_javis_index(caps))

# ---- 4. _jobs_payload gộp 2 nguồn + đếm running ----
main._loops_as_routines = lambda brain: [
    {"id": "__loop__:a", "name": "Loop A", "status": "active"},
    {"id": "__loop__:b", "name": "Loop B", "status": "paused"},
]
main.reminders_feature.pending_as_automations = lambda brain: [
    {"id": "__reminder__:r1", "name": "Uống thuốc", "status": "active"},
]

p = main._jobs_payload("brain")
check("jobs: gộp loop + nhắc hẹn thành 1 danh sách", len(p["jobs"]) == 3)
check("jobs: total = 3", p["total"] == 3)
check("jobs: running đếm đúng status active (2)", p["running"] == 2)
check("jobs: loop đứng trước nhắc hẹn", p["jobs"][0]["id"] == "__loop__:a")

main._loops_as_routines = lambda brain: []
main.reminders_feature.pending_as_automations = lambda brain: []
p0 = main._jobs_payload("brain")
check("jobs: rỗng → total 0, running 0", p0["total"] == 0 and p0["running"] == 0)


if _fails:
    print(f"\nFAIL - test_jobs: {len(_fails)} lỗi: {_fails}")
    sys.exit(1)
print("\nOK - test_jobs: tất cả pass")
```

- [ ] **Step 2: Chạy test để xác nhận nó FAIL**

Run: `cd server && ../.venv/Scripts/python.exe test_jobs.py`

Expected: FAIL. Cụ thể: `route: mọi /automations* đã xoá` fail (4 route còn sống), `helper: _read_automations đã xoá` fail, `caps: không còn key 'automations'` fail, rồi đổ ở `main._jobs_payload` với `AttributeError: module 'main' has no attribute '_jobs_payload'`.

- [ ] **Step 3: Xoá 3 helper registry + 4 route cũ**

Trong `server/main.py`, xoá nguyên khối từ `def _automations_path(brain):` (`:3145`) tới hết `_write_automations` (`:3166`), và xoá 4 route: `automations_list` (`:3196-3202`), `automations_save` (`:3205-3221`), `automations_toggle` (`:3224-3249`), `automations_delete` (`:3251-3261`).

Giữ nguyên `_loops_as_routines` (`:3169-3193`).

Sửa comment đầu khối (`:3140-3144`) thành:

```python
# ============================================================
# Trang Việc: loop (việc bền, chạy engine theo chu kỳ) + nhắc hẹn (việc phù du, 1 lần).
# KHÔNG còn registry tay: automations.json cũ chưa từng có executor (_scheduler_loop không
# đọc nó) nên đã bị xoá cùng 5 route /automations*. Xem spec 2026-07-17-hop-nhat-viec-dinh-ky.
# ============================================================
```

- [ ] **Step 4: Thêm `_jobs_payload` + 3 route mới**

Thêm ngay sau `_loops_as_routines` trong `server/main.py`:

```python
def _jobs_payload(brain: str) -> dict:
    """Union hai kho: loop (Javis/loops/*.md) + nhắc hẹn (reminders store).
    Cố ý KHÔNG gộp kho: loop là tài liệu user sửa trong Obsidian, nhắc hẹn là thứ phù du."""
    jobs = _loops_as_routines(brain) + reminders_feature.pending_as_automations(brain)
    running = sum(1 for j in jobs if j.get("status") == "active")
    return {"jobs": jobs, "running": running, "total": len(jobs)}


@app.get("/jobs")
async def jobs_list(brain: str = Query("brain")):
    return _jobs_payload(brain)


@app.post("/jobs/toggle")
async def jobs_toggle(id: str = Form(...), brain: str = Form("brain")):
    """Gạt 1 việc. Nhắc hẹn chỉ có 1 nút gạt → coi như HUỶ (nhắc là 1-lần, không tạm dừng)."""
    if id.startswith("__reminder__:"):
        async with reminders_feature._io:
            hit = reminders_feature.cancel(brain, id.split(":", 1)[1])
        return {"ok": hit, "status": "paused", "error": ("" if hit else "not found")}
    if id == "__loop__" or id.startswith("__loop__:"):
        # "__loop__" trần (client cũ) = loop legacy vong-lap-goc.
        slug = id.split(":", 1)[1] if ":" in id else self_improve.LEGACY_SLUG
        lp = loop_feature.toggle(brain, slug)
        if not lp and ":" not in id:
            legacy_brain = _read_loop_config().get("brain") or "brain"
            lp = loop_feature.toggle(legacy_brain, slug)
        if not lp:
            return {"ok": False, "error": "not found"}
        return {"ok": True, "status": "active" if lp["enabled"] else "paused"}
    return {"ok": False, "error": "id không hợp lệ"}


@app.post("/jobs/cancel")
async def jobs_cancel(id: str = Form(...), brain: str = Form("brain")):
    """Huỷ 1 nhắc hẹn. Loop xoá bằng nút xoá của loop (/loops/delete), không xoá từ đây."""
    if id.startswith("__reminder__:"):
        async with reminders_feature._io:
            hit = reminders_feature.cancel(brain, id.split(":", 1)[1])
        return {"ok": hit, "error": ("" if hit else "not found")}
    if id == "__loop__" or id.startswith("__loop__:"):
        return {"ok": False, "error": "Xoá loop bằng nút xoá của loop, không xoá từ đây"}
    return {"ok": False, "error": "id không hợp lệ"}
```

- [ ] **Step 5: Xoá khối caps chết (bắt buộc cùng task, xem ghi chú decomposition)**

Ba sửa trong `server/main.py`:

1. Dòng `:3324`, bỏ key `"automations"`:

```python
    caps = {"agents": [], "skills": [], "workflows": [], "loops": [], "plugins": []}
```

2. Xoá 3 dòng `:3352-3354`:

```python
    for a in _read_automations(brain):
        caps["automations"].append({"id": a.get("id"), "name": a.get("name"), "type": a.get("type"),
            "schedule": a.get("schedule", ""), "status": a.get("status", "active")})
```

3. Xoá 4 dòng `:3411-3413`:

```python
    if caps["automations"]:
        L.append("\n## Lịch (automations)")
        for a in caps["automations"]:
            L.append(f"- **{a['name']}** - {a['type']} · {a['schedule']} · {a['status']}")
```

Ghi chú: khối này **không** rác vào system prompt. Nó đi vào `Javis/index.md` qua `rebuild_javis_index` (`main.py:3462`), và vì list luôn rỗng nên `if caps["automations"]:` luôn falsy → section chưa từng render. Đây là dọn code chết. `_javis_capability_summary` (`:3477`) không hề nhắc automations.

- [ ] **Step 6: Chạy test để xác nhận PASS**

Run: `cd server && ../.venv/Scripts/python.exe test_jobs.py`

Expected: PASS, in `OK - test_jobs: tất cả pass`.

- [ ] **Step 7: Xác nhận không còn ai gọi route cũ trong server/**

Run: `cd /d/Project/Javis-OS && grep -rn "/automations\|_read_automations" server/ --include=*.py`

Expected: **0 hit** (trừ `server/test_jobs.py` là chuỗi trong assert). Nếu còn hit code thật, xoá nốt trước khi commit.

- [ ] **Step 8: Commit**

```bash
git add server/main.py server/test_jobs.py
git commit -m "refactor(jobs): thay /automations bang /jobs, xoa registry Lich gia

automations.json chua tung co executor: _scheduler_loop (main.py:3613-3656)
khong co nhanh nao doc no, va 0 file automations.json ton tai tren ca 4 brain.
Tab Lich phan lon dang chieu chinh loop vao qua _loops_as_routines.

Xoa 3 helper registry + 4 route /automations* + khoi caps chet (caps phai xoa
CUNG dot: _gather_capabilities:3352 goi _read_automations, de lai la NameError
moi tick scheduler). Them /jobs = union loop (viec ben) + nhac hen (viec phu du),
/jobs/toggle, /jobs/cancel.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: Xoá `/automations/sync` (bịt lỗ `bypassPermissions`)

**Files:**
- Modify: `server/main.py:3264-3300` (xoá route `automations_sync`)
- Test: `server/test_jobs.py` (thêm khối)

**Interfaces:**
- Consumes: không.
- Produces: không. Đây là task xoá thuần.

**Vì sao tách task riêng:** một reviewer có thể muốn giữ tính năng đồng bộ routine claude.ai trong khi vẫn đồng ý xoá registry ở Task 1. Nếu muốn giữ, viết lại thành nút riêng ở trang Model **có `allowed_tools`**, đừng khôi phục nguyên trạng.

**Bối cảnh bảo mật:** `main.py:3269` gọi `claude_engine(system_prompt=None, cwd=CLAUDE_CWD, tag="routines")` không truyền `allowed_tools`. Theo `claude_sdk_engine.py:290-301`, nhánh `else` khi `allowed_tools` rỗng đặt `permission_mode="bypassPermissions"` **và** nạp `setting_sources=["user","project","local"]`. Bảo đảm "CHỈ LIỆT KÊ, KHÔNG tạo/sửa/xoá/chạy gì" (`main.py:3273`) chỉ là chữ trong prompt.

- [ ] **Step 1: Viết test thất bại**

Thêm vào `server/test_jobs.py`, ngay trước khối `if _fails:`:

```python
# ---- 5. /automations/sync đã xoá: không còn engine call bypassPermissions ----
# main.py:3269 cũ gọi claude_engine(..., tag="routines") KHÔNG truyền allowed_tools →
# claude_sdk_engine.py:290-301 đặt permission_mode="bypassPermissions" + nạp setting_sources.
# Đây là engine call ít rào nhất codebase; "CHỈ LIỆT KÊ" của nó chỉ là chữ trong prompt.
check("sync: route /automations/sync đã xoá", "/automations/sync" not in paths)
check("sync: không còn engine call tag='routines'", 'tag="routines"' not in src)
check("sync: không còn prompt RemoteTrigger list", "RemoteTrigger" not in src)
```

- [ ] **Step 2: Chạy test để xác nhận nó FAIL**

Run: `cd server && ../.venv/Scripts/python.exe test_jobs.py`

Expected: FAIL ở `sync: không còn engine call tag='routines'` và `sync: không còn prompt RemoteTrigger list`. (Assert route đã pass sẵn nhờ Task 1 xoá theo prefix; hai assert nguồn thì chưa.)

- [ ] **Step 3: Xoá route sync**

Trong `server/main.py`, xoá nguyên hàm `automations_sync` từ decorator `@app.post("/automations/sync")` (`:3264`) tới hết thân hàm (kết thúc ngay trước định nghĩa tiếp theo).

Kiểm tra `re` có còn dùng chỗ khác không trước khi động vào import:

Run: `cd /d/Project/Javis-OS && grep -c "re\." server/main.py`

Nếu kết quả > 0 thì **giữ** `import re`. Không xoá import đang có người dùng.

- [ ] **Step 4: Chạy test để xác nhận PASS**

Run: `cd server && ../.venv/Scripts/python.exe test_jobs.py`

Expected: PASS.

- [ ] **Step 5: Xác nhận app vẫn import được và đếm route đúng**

Run:

```bash
cd server && ../.venv/Scripts/python.exe -c "
import os, sys, tempfile
os.environ.setdefault('JAVIS_STATE_DIR', tempfile.mkdtemp())
sys.path.insert(0, '.')
import main
print('routes:', len({getattr(r,'path','') for r in main.app.routes}))
"
```

Expected: **157**.

Cẩn thận số học ở đây, dễ đếm nhầm: có **5 endpoint** `/automations*` nhưng chỉ **4 path duy nhất** (`/automations`, `/automations/delete`, `/automations/sync`, `/automations/toggle`) - vì GET và POST `/automations` dùng **chung một path**, và lệnh trên đếm path bằng `set`. Nên: 158 - 4 + 3 = **157**. Nếu ra số khác, có gì đó xoá thừa hoặc thiếu - dừng và rà lại.

- [ ] **Step 6: Commit**

```bash
git add server/main.py server/test_jobs.py
git commit -m "fix(security): xoa /automations/sync - engine call bypassPermissions khong rao

main.py:3269 goi claude_engine khong truyen allowed_tools -> theo
claude_sdk_engine.py:290-301 no chay permission_mode=bypassPermissions VA nap
setting_sources user/project/local. Bao dam 'CHI LIET KE' chi la chu trong prompt.

Route nay dong bo routine chay tren ha tang Anthropic, mot khai niem khac han
lich cuc bo, nen no khong thuoc cuoc hop nhat nay. Can lai thi viet lai thanh
nut rieng o trang Model, co allowed_tools tu te.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: Một trang "Việc" - xoá studio page Lịch, gộp nhắc hẹn vào rail selfimprove

**Files:**
- Modify: `dashboard/console.js:23, 46, 49, 64-65, 94, 97, 107` (rail + nhãn), `:683` (copy), `:708` (thêm host), `:809-826` (`loadLoops`: gọi render nhắc hẹn)
- Modify: `dashboard/studio.js:46, 55, 58, 306-380` (xoá loader + form + sync)
- Modify: `dashboard/index.html` (xoá `panel-automations`)

**Interfaces:**
- Consumes: `GET /jobs`, `POST /jobs/cancel` (Task 1).
- Produces: không có API mới. Rail `automations` biến mất; rail `selfimprove` **giữ nguyên id** (không đổi id để khỏi vỡ deep-link/localStorage) nhưng đổi nhãn thành "Việc".

**Vì sao không xoá trơn rail Lịch:** nhắc hẹn **chỉ** hiện ở tab Lịch, qua `pending_as_automations` (`reminders.py:278`). Xoá rail mà không gộp = user mất chỗ nhìn nhắc hẹn đang chờ. Đây là hồi quy dễ lọt nhất của cả plan.

**Nhắc lại ràng buộc helper:** console.js **chỉ** có `esc()` (`:116`) và `fbrain()` (`:363`). Dùng `fetch()` trần + `FormData` dựng tại chỗ. `api()`/`fd()`/`brain()` là của studio.js, gọi ở đây sẽ `ReferenceError`.

- [ ] **Step 1: Chụp trạng thái trước (để so sau)**

Run: `cd /d/Project/Javis-OS && grep -rc "automations" dashboard/console.js dashboard/studio.js dashboard/index.html`

Ghi lại ba con số. Cuối task cả ba phải về **0**.

- [ ] **Step 2: Xoá rail `automations` khỏi console.js**

Trong `dashboard/console.js`:

1. Xoá dòng `:49`: `{ id: "automations", icon: ICON.automations, label: "Lịch" },`
2. Xoá `ICON.automations` (`:23`).
3. Xoá entry `automations:` trong map mô tả (`:97`).
4. Bỏ `"automations"` khỏi `STUDIO_PAGES` (`:107`) - còn lại `["workflows", "agents", "skills"]`.
5. Sửa nhóm rail (`:64-65`):

```js
    { label: "Năng lực",    ids: ["agents", "skills", "workflows", "plugins"] },
    { label: "Việc",        ids: ["kanban", "selfimprove"] },
```

6. Sửa nhãn rail `selfimprove` (`:46`):

```js
    { id: "selfimprove", icon: ICON.selfimprove, label: "Việc" },
```

7. Sửa mô tả (`:94`):

```js
    selfimprove: { icon: "♻", label: "Việc", sub: "Việc định kỳ + nhắc hẹn đang chờ" },
```

- [ ] **Step 3: Sửa copy trỏ tới tab Lịch (dễ sót)**

`dashboard/console.js:683` hiện kết thúc bằng: `Loop bật sẽ hiện ở tab <b>Lịch</b>.` Tab đó sắp không tồn tại. Bỏ đúng câu cuối đó, giữ nguyên phần còn lại của đoạn văn.

Run kiểm chứng: `cd /d/Project/Javis-OS && grep -n "tab <b>Lịch</b>" dashboard/console.js`

Expected sau khi sửa: 0 hit.

- [ ] **Step 4: Thêm host cho khối nhắc hẹn**

`dashboard/console.js:708` hiện là `<div id="lpCards">Đang tải...</div>`. Thêm host ngay sau nó, trước `<div class="si-log">`:

```html
      <div id="lpCards">Đang tải...</div>
      <div id="lpReminders"></div>
```

- [ ] **Step 5: Viết `loadReminders` + gọi từ `loadLoops`**

Thêm hàm này vào `renderSelfImprove`, ngay trước `async function loadLoops()` (`:809`):

```js
    // Nhắc hẹn đang chờ: trước đây CHỈ hiện ở tab Lịch (đã xoá). Không gộp vào đây thì user
    // mất chỗ nhìn chúng. Loop = việc bền (.md, sửa trong Obsidian); nhắc = việc phù du.
    async function loadReminders() {
      if (myGen !== _renderGen) return;
      const box = el.querySelector("#lpReminders");
      if (!box) return;
      let d = { jobs: [] };
      try { d = await (await fetch(`/jobs?brain=${encodeURIComponent(fbrain())}`)).json(); } catch (e) {}
      if (myGen !== _renderGen) return;
      const rem = (d.jobs || []).filter(j => String(j.id || "").startsWith("__reminder__:"));
      if (!rem.length) { box.innerHTML = ""; return; }
      box.innerHTML = `<h3 style="font-size:15px;color:#cdd8ee;margin:18px 0 8px">Nhắc hẹn đang chờ</h3>`;
      rem.forEach(r => {
        const div = document.createElement("div");
        div.className = "si-card";
        div.innerHTML = `<b>${esc(r.name)}</b>
          <div class="dim" style="font-size:12px;color:#6b7894">${esc(r.schedule)} · ${esc(r.note || "")}</div>
          <button class="s-btn-ghost rmCancel" style="margin-top:8px">Huỷ</button>`;
        div.querySelector(".rmCancel").onclick = async () => {
          if (!confirm(`Huỷ "${r.name}"?`)) return;
          const f = new FormData();
          f.append("id", r.id);
          f.append("brain", fbrain());
          await fetch("/jobs/cancel", { method: "POST", body: f });
          loadReminders();
        };
        box.appendChild(div);
      });
    }
```

Rồi gọi nó ở cuối `loadLoops` (`:809-826`), ngay trước dòng `clearTimeout(pollTimer);`:

```js
      loadReminders();
```

- [ ] **Step 6: Xoá studio page `automations`**

Trong `dashboard/studio.js`:
- Bỏ `automations: loadAutomations` khỏi map (`:46`).
- Bỏ `"automations"` khỏi mảng `["workflows", "agents", "skills", "automations"]` (`:55`).
- Xoá nhánh `else if (tab === "automations") loadAutomations();` (`:58`).
- Xoá nguyên hàm `loadAutomations` (`:306` tới hết) và `editAutomation` (`:358` tới hết), gồm cả nút gọi `/automations/sync` (`:314`).

Trong `dashboard/index.html`: xoá `<div id="panel-automations">...</div>`.

- [ ] **Step 7: Xác nhận không còn tham chiếu**

Run: `cd /d/Project/Javis-OS && grep -rn "automations" dashboard/*.js dashboard/*.html`

Expected: **0 hit**. (So với ba con số ghi ở Step 1.)

- [ ] **Step 8: Kiểm tra bằng mắt trong app thật**

Chạy server, mở dashboard:
1. Rail trái **không còn** mục "Lịch".
2. Mục "Loop" giờ tên là "Việc", nằm trong nhóm "Việc" cùng Kanban.
3. Mở trang Việc: thấy danh sách loop; đoạn mô tả đầu trang **không** còn câu "Loop bật sẽ hiện ở tab Lịch".
4. Console trình duyệt **không** có lỗi 404 tới `/automations`, không có `ReferenceError`.
5. Tạo một nhắc hẹn qua chat ("30 phút nữa nhắc anh test"), tải lại trang Việc: thấy khối "Nhắc hẹn đang chờ" với đúng nhắc đó. Bấm Huỷ: nhắc biến mất và không quay lại sau khi tải lại.

- [ ] **Step 9: Commit**

```bash
git add dashboard/console.js dashboard/studio.js dashboard/index.html
git commit -m "feat(dashboard): mot trang Viec thay cho Loop + Lich

Xoa studio page Lich (form 4 field khong dan toi executor nao) va rail
automations. Rail selfimprove doi nhan thanh Viec, render them khoi nhac hen
dang cho, va bo cau copy tro toi tab Lich da xoa.

Bat buoc phai gop nhac hen: pending_as_automations (reminders.py:278) truoc
day CHI hien o tab Lich, xoa rail ma khong gop = user mat cho nhin chung.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: Dọn panel loop chết trong index.html

**Files:**
- Modify: `dashboard/index.html:160-192` (xoá panel `display:none`)
- Modify: `dashboard/app.js:1497` (xoá fetch `/loop/config` phục vụ panel đó)

**Interfaces:**
- Consumes: không.
- Produces: không. Task xoá thuần, tách riêng để reviewer từ chối được độc lập.

**Bối cảnh:** panel loop cũ ở `index.html:160-192` có `display:none` (không ai thấy) nhưng `app.js:1497` vẫn fetch `/loop/config` mỗi lần tải trang. Route `/loop/config` là shim legacy (`self_improve.py:988-1036`) và giai đoạn 2 sẽ đụng nó, nên dọn client trước cho gọn.

- [ ] **Step 1: Xác nhận panel thật sự chết**

Run: `cd /d/Project/Javis-OS && sed -n '160,192p' dashboard/index.html | grep -n "display:none"; grep -rn "loop/config" dashboard/*.js`

Expected: thấy `display:none` trong panel, và hit `loop/config` ở `app.js:1497`. Nếu **không** thấy `display:none`, DỪNG - panel đang sống, task này sai giả định, báo lại người review.

- [ ] **Step 2: Xoá panel + fetch**

Xoá khối `dashboard/index.html:160-192`. Xoá fetch `/loop/config` và code xử lý kết quả của nó ở `dashboard/app.js:1497`.

- [ ] **Step 3: Xác nhận route legacy vẫn còn (chưa xoá backend)**

Run:

```bash
cd server && ../.venv/Scripts/python.exe -c "
import os, sys, tempfile
os.environ.setdefault('JAVIS_STATE_DIR', tempfile.mkdtemp())
sys.path.insert(0, '.')
import main
paths = {getattr(r,'path','') for r in main.app.routes}
print('/loop/config con:', '/loop/config' in paths)
"
```

Expected: `True`. Giai đoạn 1 **không** xoá shim backend, chỉ bỏ client chết. Giai đoạn 2 quyết định số phận shim.

- [ ] **Step 4: Kiểm tra bằng mắt**

Tải lại dashboard. Tab Network không có request tới `/loop/config`, console không có lỗi JS, trang Việc vẫn hiện đúng.

- [ ] **Step 5: Commit**

```bash
git add dashboard/index.html dashboard/app.js
git commit -m "chore(dashboard): xoa panel loop chet + fetch /loop/config thua

Panel index.html:160-192 co display:none (khong ai thay) nhung app.js:1497 van
fetch /loop/config moi lan tai trang. Shim backend giu nguyen, giai doan 2
quyet dinh so phan no.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5: Chạy toàn bộ test + cập nhật tài liệu

**Files:**
- Modify: `CLAUDE.md` (bỏ nhắc tab Lịch ở mục điều phối)
- Modify: `.claude/skills/javis-builder/SKILL.md` (nếu có nhắc automations/Lịch)
- Modify: `CHANGELOG.md`, `VERSION`

**Interfaces:**
- Consumes: mọi task trước.
- Produces: không.

- [ ] **Step 1: Chạy toàn bộ test suite như CI**

Run: `cd server && for f in test_*.py; do echo "--- $f"; ../.venv/Scripts/python.exe "$f" || echo "FAIL: $f"; done`

Expected: mọi file in `OK - ...`. Không file nào FAIL. Đặc biệt chú ý `test_loop_ambient.py` (dựa vào `_isolate`) và `test_system_sync.py` (dựa vào `LEGACY_HASHES`) - giai đoạn 1 không được đụng hai thứ đó.

- [ ] **Step 2: Chạy compileall như CI**

Run: `cd /d/Project/Javis-OS && .venv/Scripts/python.exe -m compileall -q server system/plugins`

Expected: không output (thành công).

- [ ] **Step 3: Chạy test JS của CI**

Run: `cd /d/Project/Javis-OS && node dashboard/test_chat_ask.js`

Expected: pass. (CI chạy đúng lệnh này ở `.github/workflows/ci.yml:27`.)

- [ ] **Step 4: Sửa CLAUDE.md**

Run: `cd /d/Project/Javis-OS && grep -n "tab Lịch\|automations" CLAUDE.md`

Ở mục "Điều phối", bậc 6 hiện ghi: `**Tạo Lịch** - nhắc nhở / job có MỐC GIỜ cố định → qua automations (tab Lịch).` Sửa thành:

```markdown
6. **Tạo Nhắc hẹn** - nhắc nhở / job có MỐC GIỜ cố định → `POST /reminders` (xem ở trang Việc).
```

Giữ nguyên 8 bậc, không đánh số lại, để khỏi vỡ các chỗ khác tham chiếu tới thang này.

- [ ] **Step 5: Kiểm tra javis-builder skill**

Run: `cd /d/Project/Javis-OS && grep -rn "automations\|tab Lịch" .claude/skills/javis-builder/SKILL.md skills/javis-builder/SKILL.md 2>/dev/null`

Nếu có hit, sửa theo cùng cách Step 4. Nếu không có hit, bỏ qua step này.

- [ ] **Step 6: Bump VERSION + CHANGELOG**

Đọc `VERSION`, tăng patch. Thêm mục đầu `CHANGELOG.md`:

```markdown
## <phiên bản mới>

- Xoá tab Lịch: registry `automations.json` chưa từng có executor (scheduler không đọc nó), 0 file tồn tại trên mọi brain. Thay bằng một trang **Việc** duy nhất hiện loop + nhắc hẹn đang chờ.
- Bảo mật: xoá `/automations/sync`, route gọi engine không truyền `allowed_tools` nên chạy `bypassPermissions` + nạp `setting_sources`; bảo đảm "chỉ liệt kê" của nó chỉ là chữ trong prompt.
- Endpoint mới `/jobs`, `/jobs/toggle`, `/jobs/cancel` thay 5 route `/automations*`.
```

- [ ] **Step 7: Commit + push**

```bash
git add CLAUDE.md CHANGELOG.md VERSION .claude/skills/javis-builder/SKILL.md
git commit -m "docs: cap nhat tai lieu sau khi xoa tab Lich

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
git push origin main
```

---

## Còn lại cho giai đoạn 2 (plan riêng)

Không làm trong plan này, ghi ra để khỏi quên:

- `parse_schedule()` dùng chung: một field `schedule` → `{kind: once|interval|cron}` kiểu Hermes.
- `cron` trong `_eligible_overdue` (`self_improve.py:455-466`) + jitter theo `hash(slug)`.
- Hub `X-Javis-Connectors` + `connectors: [...]` trên frontmatter loop (rủi ro cao nhất: hub là lớp cứng, phải fail-closed).
- `allow_real_actions` thay dial 3 nấc, map vào `effective_perm` (`mcp_hub.py:314`) sẵn có.
- Tool `javis_schedule` route hai kho; `op: list`/`cancel` phải nhìn union cả hai.
- Số phận 5 route shim legacy `/loop/*` (`self_improve.py:988-1036`).

## Bug độc lập phát hiện khi soạn plan (tách issue riêng)

`main.py:3631` gọi `tasks_feature.tick(["brain"])` với brain **hardcode**, trong khi `tick(brains)` nhận list. Board Kanban ở brain khác `"brain"` không bao giờ được dispatch. Không thuộc plan này.
