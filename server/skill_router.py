"""
skill_router.py - Nguồn chân lý DUY NHẤT cho việc khám phá skill, dùng chung bởi main.py và
mcp_hub.py để hai nơi KHÔNG bao giờ lệch nhau (tránh cảnh "API thấy skill mới, CLI thấy skill cũ").

Bố trí thư mục skill trong 1 brain:
  - CANONICAL (nơi ghi chuẩn) = <brain>/skills/<slug>/SKILL.md   (phẳng, cùng hướng agents/workflows/memory)
  - FALLBACK đọc (tương thích ngược, KHÔNG ghi vào đây):
        <brain>/.claude/skills/<slug>   - legacy + là bản MIRROR cho Claude Code native (cwd=brain)
        <brain>/.agents/<slug>          - vị trí rất cũ
  - Skill TẮT: <base>/.disabled/<slug>

Nguyên tắc độc lập engine: đây là router do Javis SỞ HỮU. Mọi engine (Claude/Codex/OpenRouter/
OpenAI/Anthropic API) dùng skill qua router này (list bơm vào system prompt + tool javis_use_skill),
KHÔNG phụ thuộc cơ chế native của Claude. `.claude/skills` chỉ là bản mirror phái sinh (bonus).

Mọi hàm ở đây CHỈ ĐỌC, an toàn OSError. Việc GHI/DI CHUYỂN (migration legacy → canonical, mirror
canonical → .claude) nằm ở system_sync.py.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

import yaml

# slug 1 đoạn an toàn (không '/', không '..') → chống path traversal khi join base/slug
_SLUG_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")

# Thứ tự ưu tiên đọc: canonical trước, rồi các fallback (canonical "thắng" khi trùng slug).
_READ_BASES = ("skills", ".claude/skills", ".agents")


def skills_base(root, canonical: bool = True) -> Path:
    """Thư mục skill trong brain. canonical=True → <root>/skills (nơi ghi chuẩn);
    canonical=False → <root>/.claude/skills (bản mirror cho Claude native + legacy)."""
    root = Path(root)
    return root / "skills" if canonical else root / ".claude" / "skills"


def mirror_base(root) -> Path:
    """Nơi đặt bản mirror để Claude Code nạp native ở ngữ cảnh cwd=brain."""
    return Path(root) / ".claude" / "skills"


def valid_slug(slug: str) -> bool:
    slug = str(slug or "").strip()
    return bool(slug) and ".." not in slug and bool(_SLUG_RE.match(slug))


def resolve_skill_file(root, slug: str) -> Optional[Path]:
    """Path SKILL.md của 1 skill ĐANG BẬT, tìm theo thứ tự canonical → .claude → .agents.
    None nếu slug không hợp lệ hoặc không tồn tại. slug đã validate (1 đoạn, không '..') nên
    join base/slug không thoát ra ngoài base."""
    if not valid_slug(slug):
        return None
    slug = str(slug).strip()
    root = Path(root)
    for base in _READ_BASES:
        f = root / base / slug / "SKILL.md"
        try:
            if f.is_file():
                return f
        except OSError:
            continue
    return None


def split_frontmatter(text: str):
    """(meta dict, body). Không có frontmatter → ({}, text). Tha lỗi YAML."""
    if (text or "").startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            try:
                meta = yaml.safe_load(parts[1]) or {}
            except Exception:
                meta = {}
            return (meta if isinstance(meta, dict) else {}), parts[2]
    return {}, (text or "")


def _meta_of(smd: Path) -> dict:
    """Bóc {name, description, group} từ 1 file SKILL.md (description rỗng → lấy dòng đầu body)."""
    try:
        text = smd.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return {"name": smd.parent.name, "description": "", "group": "Chung"}
    meta, body = split_frontmatter(text)
    body = (body or "").strip()
    desc = meta.get("description", "") or (body.split("\n")[0][:140] if body else "")
    return {"name": meta.get("name") or smd.parent.name,
            "description": desc,
            "group": meta.get("group") or "Chung"}


def _iter_skill_dirs(base: Path):
    """Yield các thư mục skill (có SKILL.md) trong base, bỏ .disabled."""
    try:
        for d in sorted(base.iterdir()):
            if d.is_dir() and d.name != ".disabled" and (d / "SKILL.md").is_file():
                yield d
    except OSError:
        return


def list_skills(root) -> list:
    """Mọi skill trong brain (bật + tắt), de-dup theo slug (canonical thắng - kể cả trạng thái
    bật/tắt). Mỗi item: {slug, name, description, group, enabled, source, path}."""
    root = Path(root)
    out, seen = [], set()

    def add(d: Path, source: str, enabled: bool):
        slug = d.name
        if slug in seen:
            return
        seen.add(slug)
        m = _meta_of(d / "SKILL.md")
        out.append({"slug": slug, "name": m["name"], "description": m["description"],
                    "group": m["group"], "enabled": enabled, "source": source,
                    "path": str(d / "SKILL.md")})

    def scan_base(base_rel: str):
        base = root / base_rel
        for d in _iter_skill_dirs(base):        # BẬT
            add(d, base_rel, True)
        dis = base / ".disabled"                # TẮT
        try:
            if dis.is_dir():
                for d in sorted(p for p in dis.iterdir()
                                if p.is_dir() and (p / "SKILL.md").is_file()):
                    add(d, base_rel, False)
        except OSError:
            pass

    scan_base("skills")           # canonical: quyết định trạng thái, thắng mọi fallback
    scan_base(".claude/skills")   # legacy / mirror
    for d in _iter_skill_dirs(root / ".agents"):   # rất cũ (chỉ bật)
        add(d, ".agents", True)
    return out


def list_enabled_meta(root) -> list:
    """Chỉ các skill đang BẬT (dùng để bơm router vào system prompt + mô tả tool javis_use_skill)."""
    return [s for s in list_skills(root) if s.get("enabled")]


def enabled_slugs(root) -> list:
    return [s["slug"] for s in list_enabled_meta(root)]
