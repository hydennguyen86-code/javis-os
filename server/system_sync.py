"""
system_sync.py - Tầng NĂNG LỰC HỆ THỐNG của Javis OS (tách khỏi dữ liệu người dùng trong brain).

Vấn đề giải quyết: trước đây các chức năng mặc định (skill javis-builder, ingest/query/lint,
loop tự-cải-tiến) được seed create-if-missing vào TỪNG brain → brain tạo ở bản cũ không bao
giờ nhận bản skill mới; brain ngoài (path:) không có gì; đổi brain là "mất" chức năng hệ thống.

Kiến trúc mới - 2 tầng rõ ràng:
  - TẦNG HỆ THỐNG (đi theo repo/image, update theo phiên bản app):
      <project>/.claude/skills/<slug>/SKILL.md   - skill hệ thống (nguồn chuẩn; chat cwd=/app
                                                    nên Claude Code nạp NATIVE, không phụ thuộc brain)
      <project>/system/loops/<slug>.md            - loop hệ thống (template, placeholder {today})
  - TẦNG BRAIN (dữ liệu người dùng, đổi theo brain): memory/, sources/, wiki/, agent/workflow/
      skill/loop do user tạo. KHÔNG bị update ghi đè.

Skill trong brain có CANONICAL phẳng <brain>/skills/<slug>/SKILL.md (cùng hướng agents/workflows/
memory). Tầng hệ thống được cài vào canonical đó qua sync có manifest, rồi MIRROR sang
<brain>/.claude/skills để Claude Code nạp NATIVE ở ngữ cảnh cwd=brain (workflow/loop/learn/lint) -
mirror chỉ là bản phái sinh (bonus), router chính của Javis không phụ thuộc nó. Brain cũ để skill
ở .claude/skills được migrate_brain() dời sang skills/ (idempotent, 1 chiều, không mất data):
  - Manifest <brain>/.javis/system-manifest.json ghi hash bản đã cài của từng file hệ thống.
  - Thiếu → cài (kể cả khi user lỡ xoá: file hệ thống tự hồi phục như file HĐH; muốn ngừng
    dùng thì TẮT skill - chuyển vào skills/.disabled - sync tôn trọng, không bật lại).
  - Có + CHƯA bị user sửa (hash khớp manifest, hoặc khớp bộ hash các bản đã ship LEGACY_HASHES)
    → ghi đè bằng bản mới của app (đây là cách "chức năng hệ thống update theo phiên bản").
  - Có + user ĐÃ SỬA → GIỮ NGUYÊN bản của user (user override; từ đó app không tự đụng nữa).
  - Loop: các trường trạng thái user chỉnh (enabled/mode/interval_min/goal/quiet_hours/
    max_runs_per_day/workspace/tools_profile) được BẢO TOÀN khi update thân prompt.

Hash CHUẨN HOÁ để so "cùng nội dung": CRLF→LF, ngày ISO → <DATE> (seed đóng dấu ngày lúc cài),
bỏ khoảng trắng cuối dòng; với loop bỏ luôn các frontmatter key volatile ở trên.

BẢO TRÌ: khi bản phát hành MỚI đổi nội dung 1 file hệ thống, thêm hash bản CŨ vào
LEGACY_HASHES (chạy `python server/system_sync.py --hash` TRƯỚC khi sửa để lấy hash hiện tại).
Manifest lo phần còn lại cho mọi brain đã sync ít nhất một lần.
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import sys
import threading
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

import yaml

PROJECT_ROOT = Path(__file__).parent.parent
SYSTEM_SKILLS_DIR = PROJECT_ROOT / ".claude" / "skills"
SYSTEM_LOOPS_DIR = PROJECT_ROOT / "system" / "loops"
MANIFEST_REL = Path(".javis") / "system-manifest.json"

# Frontmatter key của loop mà user/UI chỉnh trong vận hành bình thường → KHÔNG tính là "đã sửa"
# và được BẢO TOÀN khi update. (self_improve.save_loop rewrite các key này khi user bật/tắt.)
_LOOP_VOLATILE_KEYS = {"enabled", "mode", "interval_min", "goal", "quiet_hours",
                       "max_runs_per_day", "workspace", "tools_profile", "updated"}

_DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")


def _today() -> str:
    return datetime.now(timezone(timedelta(hours=7))).strftime("%Y-%m-%d")


def _app_version() -> str:
    try:
        return (PROJECT_ROOT / "VERSION").read_text(encoding="utf-8").strip()
    except Exception:
        return ""


# ────────────────────────── chuẩn hoá + hash ──────────────────────────

def _norm_text(text: str) -> str:
    t = (text or "").replace("\r\n", "\n").replace("﻿", "")
    t = _DATE_RE.sub("<DATE>", t)
    t = "\n".join(line.rstrip() for line in t.split("\n"))
    return t.strip() + "\n"


def _split_frontmatter(text: str):
    """Trả (meta dict, body). Không có frontmatter → ({}, text)."""
    if (text or "").startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            try:
                meta = yaml.safe_load(parts[1]) or {}
            except Exception:
                meta = {}
            return (meta if isinstance(meta, dict) else {}), parts[2]
    return {}, (text or "")


def skill_hash(text: str) -> str:
    """Hash chuẩn hoá của 1 file SKILL.md (toàn văn)."""
    return hashlib.sha256(_norm_text(text).encode("utf-8")).hexdigest()


def loop_hash(text: str) -> str:
    """Hash chuẩn hoá của 1 file loop: frontmatter BỎ key volatile + thân prompt."""
    meta, body = _split_frontmatter(text)
    stable = {str(k): meta[k] for k in sorted(meta, key=str) if str(k) not in _LOOP_VOLATILE_KEYS}
    payload = json.dumps(stable, ensure_ascii=False, sort_keys=True, default=str) + "\n---\n" + _norm_text(body)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


# ────────────────────────── bộ hash các bản ĐÃ SHIP (pre-manifest) ──────────────────────────
# Nhận diện file trong brain là bản seed cũ CHƯA bị user sửa → an toàn để update.
# Sinh bằng scripts trích meta_tools.py tại các commit v0.7.9 (fe33c2c), v0.8.1 (703fe54),
# v0.8.2 (0d3c953), v0.8.3 (f4fe71c). Điền ở cuối file (sau khi tính) - xem __main__.
LEGACY_HASHES: dict[str, set] = {}   # key "skills/<slug>" | "loops/<slug>" → set hash


# ────────────────────────── nguồn hệ thống ──────────────────────────

def system_skill_slugs() -> set:
    """Slug các skill HỆ THỐNG (từ <project>/.claude/skills). Cache theo process."""
    global _SKILL_SLUGS_CACHE
    if _SKILL_SLUGS_CACHE is None:
        s = set()
        try:
            if SYSTEM_SKILLS_DIR.is_dir():
                for p in SYSTEM_SKILLS_DIR.iterdir():
                    if p.is_dir() and not p.name.startswith(".") and (p / "SKILL.md").is_file():
                        s.add(p.name)
        except Exception:
            pass
        _SKILL_SLUGS_CACHE = s
    return _SKILL_SLUGS_CACHE


_SKILL_SLUGS_CACHE: Optional[set] = None


def is_system_skill(slug: str) -> bool:
    return slug in system_skill_slugs()


def _system_items():
    """Danh sách item hệ thống: (key, kind, slug, nội dung ĐÃ RENDER)."""
    items = []
    try:
        if SYSTEM_SKILLS_DIR.is_dir():
            for p in sorted(SYSTEM_SKILLS_DIR.iterdir()):
                f = p / "SKILL.md"
                if p.is_dir() and not p.name.startswith(".") and f.is_file():
                    items.append((f"skills/{p.name}", "skill", p.name, f.read_text(encoding="utf-8")))
    except Exception as e:
        print(f"[system sync] đọc skills hệ thống lỗi: {e}", file=sys.stderr)
    try:
        if SYSTEM_LOOPS_DIR.is_dir():
            for f in sorted(SYSTEM_LOOPS_DIR.glob("*.md")):
                content = f.read_text(encoding="utf-8").replace("{today}", _today())
                items.append((f"loops/{f.stem}", "loop", f.stem, content))
    except Exception as e:
        print(f"[system sync] đọc loops hệ thống lỗi: {e}", file=sys.stderr)
    return items


# ────────────────────────── manifest ──────────────────────────

def _manifest_path(root: Path) -> Path:
    return root / MANIFEST_REL


def _read_manifest(root: Path) -> dict:
    try:
        p = _manifest_path(root)
        if p.exists():
            data = json.loads(p.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                data.setdefault("files", {})
                return data
    except Exception:
        pass
    return {"files": {}}


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8", newline="\n")
    tmp.replace(path)


def _write_manifest(root: Path, data: dict) -> None:
    data["app_version"] = _app_version()
    data["synced_at"] = datetime.now(timezone(timedelta(hours=7))).isoformat(timespec="seconds")
    _atomic_write(_manifest_path(root), json.dumps(data, ensure_ascii=False, indent=2))


# ────────────────────────── sync ──────────────────────────

def _skill_paths(root: Path, slug: str):
    """(path đang BẬT, path đang TẮT) của 1 skill trong brain.
    CANONICAL = <root>/skills (phẳng, cùng hướng agents/workflows/memory). Skill hệ thống được
    cài vào đây; mirror_skills() copy sang <root>/.claude/skills cho Claude Code native."""
    base = root / "skills"
    return base / slug / "SKILL.md", base / ".disabled" / slug / "SKILL.md"


def migrate_brain(root) -> None:
    """Idempotent: dời skill legacy <root>/.claude/skills/** → CANONICAL <root>/skills/**.
    Dời CẢ cây bật lẫn cây .disabled (để skill người dùng đã TẮT không bị cài lại thành BẬT).
    CHỈ move khi đích CHƯA có (canonical thắng - không ghi đè). Nguồn+đích đều dưới <root> nên
    cùng ổ đĩa → shutil.move = rename nguyên tử (không lo copy dở dang). Per-slug try/except:
    1 skill lỗi không chặn các skill còn lại."""
    root = Path(root)
    legacy = root / ".claude" / "skills"
    canonical = root / "skills"
    if not legacy.is_dir():
        return
    pairs = [(legacy, canonical), (legacy / ".disabled", canonical / ".disabled")]
    for src_base, dst_base in pairs:
        try:
            if not src_base.is_dir():
                continue
            for d in sorted(p for p in src_base.iterdir()
                            if p.is_dir() and p.name != ".disabled" and (p / "SKILL.md").is_file()):
                dst = dst_base / d.name
                try:
                    if dst.exists():
                        continue   # canonical đã có bản này → giữ nguyên, KHÔNG ghi đè
                    dst_base.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(d), str(dst))
                except Exception as e:
                    print(f"[skill migrate] {d} → {dst}: {type(e).__name__}: {e}", file=sys.stderr)
        except Exception as e:
            print(f"[skill migrate] {src_base}: {type(e).__name__}: {e}", file=sys.stderr)


def mirror_skills(root) -> None:
    """Mirror MỘT CHIỀU <root>/skills → <root>/.claude/skills (CHỈ skill đang BẬT).
    Mục đích: các ngữ cảnh Claude Code chạy cwd=brain (workflow/loop/learn/lint) vẫn nạp skill
    NATIVE như bonus. Add/update-only (so hash, trùng thì bỏ qua = rẻ), BỎ QUA .disabled (mirror
    skill đã tắt = vô tình bật lại native). KHÔNG xoá entry lạ ở .claude (việc gỡ mirror khi
    tắt/xoá skill do endpoint xử lý). Đây là bản phái sinh - hỏng cũng không phá router chính."""
    root = Path(root)
    canonical = root / "skills"
    mirror = root / ".claude" / "skills"
    if not canonical.is_dir():
        return
    try:
        for d in sorted(p for p in canonical.iterdir()
                        if p.is_dir() and p.name != ".disabled" and (p / "SKILL.md").is_file()):
            try:
                dst_dir = mirror / d.name
                dst = dst_dir / "SKILL.md"
                src_text = (d / "SKILL.md").read_text(encoding="utf-8", errors="replace")
                if dst.is_file():
                    cur = dst.read_text(encoding="utf-8", errors="replace")
                    if skill_hash(cur) == skill_hash(src_text):
                        continue   # đã trùng nội dung → khỏi ghi lại
                dst_dir.mkdir(parents=True, exist_ok=True)
                for f in d.iterdir():   # SKILL.md + file phụ (asset) cùng thư mục skill
                    if f.is_file():
                        shutil.copy2(str(f), str(dst_dir / f.name))
            except Exception as e:
                print(f"[skill mirror] {d.name}: {type(e).__name__}: {e}", file=sys.stderr)
    except Exception as e:
        print(f"[skill mirror] {root}: {type(e).__name__}: {e}", file=sys.stderr)


def _merge_loop_update(new_content: str, cur_text: str) -> str:
    """Update loop nhưng BẢO TOÀN trường trạng thái user đã chỉnh (enabled/mode/interval...)."""
    new_meta, new_body = _split_frontmatter(new_content)
    cur_meta, _ = _split_frontmatter(cur_text)
    for k in _LOOP_VOLATILE_KEYS:
        if k in cur_meta and k != "updated":
            new_meta[k] = cur_meta[k]
    new_meta["updated"] = _today()
    fm = yaml.safe_dump(new_meta, allow_unicode=True, sort_keys=False,
                        default_flow_style=False, width=1000).strip()
    return f"---\n{fm}\n---\n{new_body.lstrip()}" if new_body.strip() else f"---\n{fm}\n---\n"


_LOCK = threading.Lock()
_SYNCED_ROOTS: set = set()


def sync_brain(brain_root) -> dict:
    """Đồng bộ năng lực hệ thống vào 1 brain. Idempotent, an toàn chạy nhiều lần.
    Trả {"ok", "installed": [...], "updated": [...], "kept_user": [...]}."""
    root = Path(brain_root)
    result = {"ok": True, "installed": [], "updated": [], "kept_user": []}
    with _LOCK:
        # (1) Migrate legacy .claude/skills → canonical skills/ TRƯỚC khi cài skill hệ thống,
        #     để skill hệ thống user đã TẮT (đã migrate cả cây .disabled) không bị cài lại BẬT.
        try:
            migrate_brain(root)
        except Exception as e:
            print(f"[system sync] migrate {root}: {type(e).__name__}: {e}", file=sys.stderr)
        # (2) Cài/cập nhật skill + loop hệ thống vào canonical (bỏ qua nếu app không ship item nào).
        items = _system_items()
        manifest = _read_manifest(root)
        files = manifest["files"]
        changed = False
        for key, kind, slug, content in items:
            try:
                hasher = skill_hash if kind == "skill" else loop_hash
                new_hash = hasher(content)
                if kind == "skill":
                    enabled_p, disabled_p = _skill_paths(root, slug)
                    dst = enabled_p if enabled_p.exists() else (disabled_p if disabled_p.exists() else enabled_p)
                else:
                    dst = root / "Javis" / "loops" / f"{slug}.md"

                entry = files.get(key) or {}
                if not dst.exists():
                    # Thiếu → cài mới (file hệ thống tự hồi phục; tắt bằng .disabled chứ không xoá)
                    _atomic_write(dst, content)
                    files[key] = {"hash": new_hash, "status": "managed"}
                    result["installed"].append(key)
                    changed = True
                    continue

                cur_text = dst.read_text(encoding="utf-8")
                cur_hash = hasher(cur_text)
                if cur_hash == new_hash:
                    # Đã đúng bản mới nhất → chỉ ghi nhận vào manifest (brain pre-manifest)
                    if entry.get("hash") != new_hash or entry.get("status") != "managed":
                        files[key] = {"hash": new_hash, "status": "managed"}
                        changed = True
                    continue

                prev_hash = entry.get("hash")
                shipped_old = cur_hash == prev_hash or cur_hash in LEGACY_HASHES.get(key, set())
                if shipped_old:
                    # Bản seed cũ CHƯA bị user sửa → update theo phiên bản app
                    if kind == "loop":
                        _atomic_write(dst, _merge_loop_update(content, cur_text))
                    else:
                        _atomic_write(dst, content)
                    files[key] = {"hash": new_hash, "status": "managed"}
                    result["updated"].append(key)
                    changed = True
                else:
                    # User đã sửa → tôn trọng bản của user, app không tự đụng nữa
                    if entry.get("status") != "user-modified":
                        files[key] = {"hash": prev_hash or cur_hash, "status": "user-modified"}
                        changed = True
                    result["kept_user"].append(key)
            except Exception as e:
                print(f"[system sync] {key} @ {root}: {type(e).__name__}: {e}", file=sys.stderr)
                result["ok"] = False
        if changed:
            try:
                _write_manifest(root, manifest)
            except Exception as e:
                print(f"[system sync] ghi manifest {root}: {e}", file=sys.stderr)
        # (3) Mirror canonical skills/ → .claude/skills để Claude native (cwd=brain) nạp được.
        try:
            mirror_skills(root)
        except Exception as e:
            print(f"[system sync] mirror {root}: {type(e).__name__}: {e}", file=sys.stderr)
    return result


def ensure_synced(brain_root) -> Optional[dict]:
    """Sync 1 lần cho mỗi brain root trong vòng đời process (gọi được ở hot path).
    Bao phủ brain ngoài chọn qua 'path:' ngay lượt dùng đầu tiên."""
    try:
        key = str(Path(brain_root).resolve())
    except Exception:
        key = str(brain_root)
    with _LOCK:
        if key in _SYNCED_ROOTS:
            return None
        _SYNCED_ROOTS.add(key)
    try:
        r = sync_brain(brain_root)
        if r.get("installed") or r.get("updated"):
            print(f"[system sync] {brain_root}: cài {len(r['installed'])}, cập nhật {len(r['updated'])}",
                  file=sys.stderr)
        return r
    except Exception as e:
        print(f"[system sync] {brain_root}: {type(e).__name__}: {e}", file=sys.stderr)
        return None


# ────────────────────────── LEGACY_HASHES (dữ liệu) ──────────────────────────
# Hash các bản seed đã ship TRƯỚC khi có manifest (v0.7.9 → v0.8.3; nội dung không đổi giữa
# các bản nên mỗi item 1 hash). Sinh từ git history meta_tools.py (fe33c2c/703fe54/0d3c953/f4fe71c).
LEGACY_HASHES.update({
    "loops/tu-cai-tien-javis": {
        "4028fbc34972449c072e750d7b2fe3c458b97ff7eee35d9d486af7efe98625bb",
    },
    "skills/ingest-source": {
        "313675bc61ad2aae69b282e9289a1a126ce89eb7688e1e2bfa3cfa409428878d",
    },
    "skills/javis-builder": {
        "24081f68ed0152b09fc482dc79680e68e249e8153bc1c442f4a01af15b7f012f",
        # bản v0.9.32 (trước khi thêm khung metaprompt v0.9.33)
        "6f040dde409adf27ee69fed22c2c0490a5717c53a640d02d02fd670ee1bbfd76",
    },
    # ingest-source bản trước contextual-retrieval (v0.9.33) = 313675bc... đã có ở trên
    "skills/lint-wiki": {
        "d12ab25e78405804c378af7ffb13c136d5fd6639cd5140b17231a533704b8bc8",
    },
    "skills/query-wiki": {
        "de1f90fb9094ea7ab66fef95b62f0c8627058599165bb0ba1ae99e40163eb261",
    },
})


if __name__ == "__main__" and "--hash" in sys.argv:
    # In hash chuẩn hoá của bộ file hệ thống HIỆN TẠI - chạy TRƯỚC khi sửa nội dung
    # để thêm vào LEGACY_HASHES của bản sau.
    for key, kind, slug, content in _system_items():
        h = (skill_hash if kind == "skill" else loop_hash)(content)
        print(f"{key}: {h}")
