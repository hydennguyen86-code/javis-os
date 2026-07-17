"""Test: plugin phải thấy ĐÚNG brain, không âm thầm rơi về Brain Default. Chạy tay / CI:

    cd server && python test_plugin_vault.py

Bối cảnh bug: claude_sdk_engine._plugins_server gọi plugin_tools(mode, None) nên
PluginContext.vault_root (plugins_host.py:218) = None với MỌI plugin gọi từ Claude Code.
image-chatgpt truyền cctx.vault_root xuống image_gen._resolve_vault (image_gen.py:95-98),
hàm này thấy rỗng thì rơi về brains/Brain Default -> ảnh lưu SAI brain, im lặng.

Phủ:
- PluginContext giữ đúng vault_root được truyền.
- plugin_tools(mode, vault) dựng ctx có vault đó (không None).
- _resolve_vault: có vault hợp lệ thì KHÔNG rơi về Brain Default (khẳng định tiền đề của bug).
"""
import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("JAVIS_STATE_DIR", tempfile.mkdtemp(prefix="javis-pvault-"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import plugins_host  # noqa: E402
import image_gen     # noqa: E402

_fails = []


def check(name, cond):
    print(("ok  " if cond else "FAIL ") + name)
    if not cond:
        _fails.append(name)


_BRAIN = tempfile.mkdtemp(prefix="javis-brain-that-")

# ---- 1. Tiền đề của bug: _resolve_vault rơi về Brain Default khi vault rỗng ----
# Nếu assert này đỏ thì bug đã được sửa ở nơi khác và test cần viết lại.
fallback = str(image_gen._resolve_vault(None))
check("tiền đề: _resolve_vault(None) rơi về Brain Default",
      fallback.endswith("Brain Default"))
check("tiền đề: _resolve_vault(<vault thật>) tôn trọng vault",
      str(image_gen._resolve_vault(_BRAIN)) == _BRAIN)

# ---- 2. PluginContext giữ vault_root ----
# Chữ ký THẬT (plugins_host.py:214): __init__(self, slug, source, plugin_dir, vault_root)
ctx = plugins_host.PluginContext(slug="thu-nghiem", source="bundled",
                                 plugin_dir=Path(_BRAIN), vault_root=_BRAIN)
check("ctx: giữ đúng vault_root được truyền", ctx.vault_root == _BRAIN)
check("ctx: data_dir là property, không phải field gán tay", isinstance(ctx.data_dir, Path))

# ---- 3. _load_all dựng ctx THẤY vault (đây là chỗ bug sống) ----
# Assert vào ctx THẬT của plugin đã nạp, không assert kiểu trả về. LoadedPlugin giữ ctx
# (plugins_host.py:257 __slots__ có "ctx"), nên đọc thẳng được. Assert kiểu
# `isinstance(tools, list)` là TAUTOLOGY: luôn đúng kể cả khi ctx mù vault.
ent = plugins_host._load_all(_BRAIN)
loaded = ent["plugins"]
check("nạp: có ít nhất 1 plugin bundled để soi ctx", len(loaded) > 0)
check("ctx: MỌI plugin đã nạp thấy đúng brain (không None, không Brain Default)",
      all(lp.ctx.vault_root == _BRAIN for lp in loaded))

# Chứng minh bug: truyền None thì ctx mù -> đây chính là thứ đường SDK đang làm.
ent_none = plugins_host._load_all(None)
check("bug: _load_all(None) -> ctx.vault_root là None (tiền đề của lỗi lưu nhầm brain)",
      all(lp.ctx.vault_root is None for lp in ent_none["plugins"]))


# ---- 4. scope_vault=False: ctx VẪN thấy vault nhưng KHÔNG nạp plugin riêng-của-vault ----
import inspect  # noqa: E402
sig = inspect.signature(plugins_host.plugin_tools)
check("plugin_tools: có tham số scope_vault", "scope_vault" in sig.parameters)
check("plugin_tools: scope_vault mặc định True (giữ hành vi cũ cho hub)",
      sig.parameters["scope_vault"].default is True)

import claude_sdk_engine  # noqa: E402
# Class THẬT tên ClaudeSDK (claude_sdk_engine.py:124), KHÔNG phải ClaudeSDKEngine.
check("SDK: có helper _brain_root", hasattr(claude_sdk_engine.ClaudeSDK, "_brain_root"))

src_sdk = (Path(__file__).parent / "claude_sdk_engine.py").read_text(encoding="utf-8")
check("SDK: không còn truyền None mù vào plugin_tools",
      "plugin_tools(mode, None)" not in src_sdk)
check("SDK: truyền brain thật + scope_vault=False",
      "scope_vault=False" in src_sdk)


if _fails:
    print(f"\nFAIL - test_plugin_vault: {len(_fails)} lỗi: {_fails}")
    sys.exit(1)
print("\nOK - test_plugin_vault: tất cả pass")
