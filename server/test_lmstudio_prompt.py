"""Kiểm tra prompt gọn cho chat qua LM Studio. Chạy: cd server && python test_lmstudio_prompt.py."""
import os
import sys
import tempfile
from pathlib import Path

os.environ["JAVIS_STATE_DIR"] = tempfile.mkdtemp(prefix="javis-local-prompt-")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import main  # noqa: E402

_fails = []


def check(name, cond):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        _fails.append(name)


root = Path(tempfile.mkdtemp(prefix="javis-local-brain-"))
memory = root / "Memory" / "MEMORY.md"
memory.parent.mkdir(parents=True)
memory.write_text("Thông tin bền vững.\n" + "x" * 5000, encoding="utf-8")
main._brain_memory_dir = lambda _brain: root / "Memory"

prompt = main.build_local_system_prompt("brain")
check("có vai trò Javis", "Bạn là Javis" in prompt)
check("nêu đúng giới hạn chat thuần", "chế độ chat thuần" in prompt)
check("giữ Memory", "Thông tin bền vững." in prompt)
check("Memory được giới hạn 4000 ký tự", len(prompt) < 5000)
check("không nhét hướng dẫn MCP", "LỚP AGENTIC" not in prompt and "MCP đa-model" not in prompt)

if _fails:
    print(f"\nFAIL - {len(_fails)} test: {_fails}")
    sys.exit(1)
print("\nOK - test_lmstudio_prompt: tất cả pass")
