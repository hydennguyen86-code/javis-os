"""Test hệ plugin (plugins_host). Chạy tay:

    cd server && JAVIS_STATE_DIR=<temp> .venv/Scripts/python test_plugins_host.py

Không cần pytest, không chạm mạng: chỉ dùng plugin bundled trong system/plugins/.
Tự cô lập STATE_DIR sang thư mục tạm để không đụng state thật.
"""
import asyncio
import json
import os
import sys
import tempfile

os.environ["JAVIS_STATE_DIR"] = tempfile.mkdtemp(prefix="javis-plugtest-")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import plugins_host  # noqa: E402


def _names(tools):
    return {t["fn"] for t in tools}


async def main():
    # 1) khám phá bundled + trạng thái mặc định
    desc = {d["slug"]: d for d in plugins_host.describe(None)}
    assert "datetime-vn" in desc and "tool-audit" in desc, sorted(desc)
    assert desc["datetime-vn"]["enabled"] and desc["datetime-vn"]["loaded"]
    assert desc["tool-audit"]["enabled"] is False

    # 2) tool datetime-vn xuất hiện + chạy đúng
    tools, route = plugins_host.plugin_tools("full", None)
    assert {"javis_now", "javis_date_add"} <= _names(tools)
    assert "javis_tool_stats" not in _names(tools)
    now = json.loads(await route["javis_now"]["call"]({}))
    assert now["tz"].startswith("Asia/Ho_Chi_Minh")
    add = json.loads(await route["javis_date_add"]["call"]({"days": 3, "from": "2026-07-09"}))
    assert add["date"] == "2026-07-12", add

    # 3) gate min_mode theo mode chạy
    assert plugins_host._min_mode_ok("readonly", "suggest")
    assert not plugins_host._min_mode_ok("safe", "suggest")
    assert plugins_host._min_mode_ok("safe", "auto")
    assert not plugins_host._min_mode_ok("full", "auto")
    assert plugins_host._min_mode_ok("full", "full")

    # 4) bật tool-audit → hook chạy, đếm đúng
    assert plugins_host.set_enabled("tool-audit", True, None)["ok"]
    assert plugins_host.has_tool_hooks(None)
    tools2, route2 = plugins_host.plugin_tools("full", None)
    assert "javis_tool_stats" in _names(tools2)
    wrapped = plugins_host.wrap_with_hooks("javis_now", route2["javis_now"]["call"], "full", None)
    await wrapped({})
    await wrapped({})
    stats = json.loads(await route2["javis_tool_stats"]["call"]({}))
    assert stats["total_calls"] >= 2, stats
    assert any(t["tool"] == "javis_now" for t in stats["top"]), stats

    # 5) reserved / collision: plugin không được đè tool lõi
    assert "javis_read_file" not in _names(tools2)  # không do plugin cung cấp
    # 6) tắt lại → biến mất
    plugins_host.set_enabled("tool-audit", False, None)
    assert "javis_tool_stats" not in _names(plugins_host.plugin_tools("full", None)[0])

    # 7) gate vault: dù enabled, thiếu env → không nạp
    vault = tempfile.mkdtemp(prefix="javis-vault-")
    pdir = os.path.join(vault, "plugins", "demo-x")
    os.makedirs(pdir)
    with open(os.path.join(pdir, "plugin.yaml"), "w", encoding="utf-8") as f:
        f.write("name: Demo\nslug: demo-x\nenabled: true\nmin_mode: readonly\n")
    with open(os.path.join(pdir, "plugin.py"), "w", encoding="utf-8") as f:
        f.write("def register(ctx):\n"
                "    ctx.register_tool('demo_ping','ping',lambda a,c:'pong',min_mode='readonly')\n")
    os.environ["JAVIS_ENABLE_VAULT_PLUGINS"] = ""      # gate OFF
    plugins_host.invalidate()
    assert "demo_ping" not in _names(plugins_host.plugin_tools("full", vault)[0]), "vault plugin ran without gate!"
    d = {x["slug"]: x for x in plugins_host.describe(vault)}
    assert d["demo-x"]["gated"] is True
    os.environ["JAVIS_ENABLE_VAULT_PLUGINS"] = "true"  # gate ON
    plugins_host.invalidate()
    assert "demo_ping" in _names(plugins_host.plugin_tools("full", vault)[0]), "vault plugin didn't run with gate"

    print("OK - test_plugins_host: tất cả assertion pass")


if __name__ == "__main__":
    asyncio.run(main())
