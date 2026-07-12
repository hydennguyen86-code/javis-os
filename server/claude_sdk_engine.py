"""
Engine Claude qua claude-agent-sdk CHÍNH CHỦ (Phase 1-2 của docs/dev/2026-07-ke-hoach-agent-sdk.md).

Đây là engine Claude DUY NHẤT từ v0.9.37 (nhánh ClaudeCLI Popen đã gỡ). Hợp đồng engine:
  - __init__(system_prompt, cwd, tag, allowed_tools, model) + các attr gán sau
    (session_id, mcp_config, mcp_strict, disallowed_tools, max_wall_s)
  - .query(prompt) -> async yield dict {type: text|tool_call|tool_result|final|error}
  - cancel_all(tag) interrupt theo họ tag (claude_cli.cancel_all gọi hộ)

Bật bằng env JAVIS_CLAUDE_ENGINE=sdk (mặc định cli - qua factory claude_cli.claude_engine).
Auth kế thừa đăng nhập Claude Code CLI (subscription) - không cần API key.

Nâng cấp so với CLI Popen: khi có allowed_tools (fork nền an toàn của loop/workflow),
quyền enforce PER-CALL bằng callback can_use_tool - tool ngoài whitelist bị TỪ CHỐI THẬT
từng lần gọi (kể cả Bash/Write builtin) + ghi audit, thay vì chỉ dựa --allowedTools tĩnh.
"""
import asyncio
import fnmatch
import json
import os
import sys
import threading
import time

try:
    import claude_agent_sdk as _sdk   # noqa: F401
    _SDK_OK = True
    # Tắt cảnh báo "can_use_tool bị allowed_tools che": đó CHÍNH là thiết kế của gate -
    # tool trong whitelist tự duyệt, mọi tool khác rơi vào _permission_gate → deny.
    import warnings as _warnings
    _warnings.filterwarnings("ignore", category=_sdk.CanUseToolShadowedWarning)
except Exception:
    _SDK_OK = False

from config import STATE_DIR

_AUDIT_PATH = STATE_DIR / "logs" / "sdk_tool_audit.jsonl"

# client đang chạy -> (tag, loop) để cancel_all interrupt theo họ tag như claude_cli
_ACTIVE = {}
_LOCK = threading.Lock()


def sdk_available() -> bool:
    return _SDK_OK


def cancel_all(tag=None) -> int:
    """Interrupt các phiên SDK đang chạy. tag=None → tất cả; khớp HỌ tag như claude_cli
    ('chat' ngắt cả 'chat:abc'). Trả số phiên đã ngắt."""
    with _LOCK:
        items = [(c, t, lp) for c, (t, lp) in _ACTIVE.items()
                 if tag is None or t == tag or str(t).startswith(str(tag) + ":")]
    for client, _t, loop in items:
        try:
            asyncio.run_coroutine_threadsafe(client.interrupt(), loop)
        except Exception:
            pass
    return len(items)


def _audit(tag, tool_name, allowed, reason=""):
    """Ghi 1 dòng audit quyết định quyền tool (JSONL). Lỗi ghi không được phá lượt chạy."""
    try:
        _AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(_AUDIT_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps({"ts": time.time(), "tag": tag, "tool": tool_name,
                                "allowed": allowed, "reason": reason}, ensure_ascii=False) + "\n")
    except Exception:
        pass
    print(f"[sdk-audit] {tag} {'ALLOW' if allowed else 'DENY '} {tool_name}"
          + (f" ({reason})" if reason else ""), file=sys.stderr)


def map_message(msg):
    """Map 1 message SDK → (list event dict 'hợp đồng ClaudeCLI', session_id|None).
    PURE - test offline được, không cần CLI/auth."""
    from claude_agent_sdk import (AssistantMessage, UserMessage, SystemMessage, ResultMessage,
                                  TextBlock, ToolUseBlock, ToolResultBlock)
    events = []
    if isinstance(msg, SystemMessage):
        return events, (msg.data or {}).get("session_id")
    if isinstance(msg, AssistantMessage):
        for b in msg.content:
            if isinstance(b, TextBlock):
                if (b.text or "").strip():
                    events.append({"type": "text", "content": b.text})
            elif isinstance(b, ToolUseBlock):
                events.append({"type": "tool_call", "name": b.name or "", "input": b.input or {}})
        return events, None
    if isinstance(msg, UserMessage):
        content = msg.content
        if isinstance(content, list):
            for b in content:
                if isinstance(b, ToolResultBlock):
                    c = b.content
                    if isinstance(c, list):
                        c = " ".join(x.get("text", "") for x in c if isinstance(x, dict))
                    events.append({"type": "tool_result", "content": str(c or "")[:500]})
        return events, None
    if isinstance(msg, ResultMessage):
        u = msg.usage or {}
        events.append({
            "type": "final",
            "content": msg.result or "",
            "session_id": msg.session_id,
            "cost_usd": msg.total_cost_usd,
            "duration_ms": msg.duration_ms,
            "tokens_in": ((u.get("input_tokens") or 0) + (u.get("cache_read_input_tokens") or 0)
                          + (u.get("cache_creation_input_tokens") or 0)),
            "tokens_out": u.get("output_tokens") or 0,
        })
        return events, msg.session_id
    return events, None


class ClaudeSDK:
    """Engine Claude qua Agent SDK - engine Claude duy nhất (tạo qua claude_cli.claude_engine)."""

    def __init__(self, system_prompt=None, cwd=None, tag="chat", allowed_tools=None, model=None):
        self.system_prompt = system_prompt
        self.cwd = cwd or os.getcwd()
        self.session_id = None
        self.tag = tag
        self.allowed_tools = allowed_tools
        self.model = model
        self.mcp_config = None
        self.mcp_strict = False
        self.disallowed_tools = None
        self.max_wall_s = None
        self.javis_mode = None    # _apply_mcp đặt (suggest|auto|full) - enforce min_mode plugin in-process

    def is_available(self) -> bool:
        if not _SDK_OK:
            return False
        from claude_cli import find_claude_cli
        return find_claude_cli() is not None

    def reset_session(self):
        self.session_id = None

    async def _permission_gate(self, tool_name, input_data, context):
        """can_use_tool: whitelist THẬT per-call khi chạy chế độ nền an toàn (allowed_tools).
        Hỗ trợ pattern fnmatch (vd 'mcp__javis__pos_*')."""
        from claude_agent_sdk import PermissionResultAllow, PermissionResultDeny
        allowed = self.allowed_tools or []
        ok = any(tool_name == p or fnmatch.fnmatch(tool_name, p) for p in allowed)
        _audit(self.tag, tool_name, ok, "" if ok else "ngoài whitelist chế độ nền an toàn")
        if ok:
            return PermissionResultAllow()
        return PermissionResultDeny(
            message=f"Tool '{tool_name}' bị chặn: phiên nền này chỉ được dùng {', '.join(allowed)}.")

    def _plugins_server(self):
        """Phase 3: dựng MCP server IN-PROCESS từ tool plugin (plugins_host) - engine SDK gọi
        thẳng handler Python, không qua hub HTTP. Trả McpSdkServerConfig hoặc None (không plugin).
        min_mode enforce sẵn trong route của plugin_tools(mode); hook pre/post bọc như hub."""
        import plugins_host
        from claude_agent_sdk import tool as sdk_tool, create_sdk_mcp_server
        mode = (self.javis_mode or "full").strip().lower()
        p_tools, p_route = plugins_host.plugin_tools(mode, None)   # None = plugin toàn cục, như hub phục vụ CLI
        if not p_tools:
            return None
        use_hooks = plugins_host.has_tool_hooks(None)
        sdk_tools = []
        for t in p_tools:
            fn = t["fn"]
            call = p_route[fn]["call"]
            if use_hooks:
                call = plugins_host.wrap_with_hooks(fn, call, mode, None)

            async def _handler(args, _call=call):
                res = await _call(args or {})
                return {"content": [{"type": "text", "text": str(res)}]}

            sdk_tools.append(sdk_tool(fn, t.get("description") or fn,
                                      t.get("schema") or {"type": "object", "properties": {}})(_handler))
        return create_sdk_mcp_server("javis-plugins", tools=sdk_tools)

    def _mcp_servers(self):
        """(mcp_servers cho options, strict) - đọc file config (đường _apply_mcp) thành dict,
        đấu thêm plugin in-process khi KHÔNG gated. Gated fork (allowed_tools) giữ nguyên
        cô lập như CLI: chỉ file config (thường là MCP rỗng), KHÔNG plugin in-process."""
        servers = None
        if self.mcp_config:
            try:
                with open(self.mcp_config, encoding="utf-8") as f:
                    servers = dict(json.load(f).get("mcpServers") or {})
            except Exception as e:
                print(f"[sdk engine] đọc mcp_config lỗi ({e}) - truyền path thô", file=sys.stderr)
                return str(self.mcp_config), self.mcp_strict
        if self.allowed_tools:
            return servers, self.mcp_strict
        try:
            plug = self._plugins_server()
        except Exception as e:
            print(f"[sdk engine] plugin in-process lỗi: {type(e).__name__}: {e}", file=sys.stderr)
            plug = None
        if plug is not None:
            servers = dict(servers or {})
            servers["javis-plugins"] = plug
            hub = servers.get("javis")
            if isinstance(hub, dict) and hub.get("headers") is not None:
                # Báo hub bỏ nhóm plugin - model không thấy 2 tool trùng chức năng
                hub = dict(hub); hub["headers"] = dict(hub["headers"])
                hub["headers"]["X-Javis-No-Plugins"] = "1"
                servers["javis"] = hub
        return servers, self.mcp_strict

    def _options(self):
        from claude_agent_sdk import ClaudeAgentOptions
        kw = {
            "cwd": self.cwd,
            "system_prompt": ({"type": "preset", "preset": "claude_code", "append": self.system_prompt}
                              if self.system_prompt else {"type": "preset", "preset": "claude_code"}),
        }
        if self.model:
            kw["model"] = self.model
        if self.session_id:
            kw["resume"] = self.session_id
        servers, strict = self._mcp_servers()
        if servers is not None:
            kw["mcp_servers"] = servers
            if strict:
                kw["strict_mcp_config"] = True
        if self.disallowed_tools:
            kw["disallowed_tools"] = list(self.disallowed_tools)
        if self.allowed_tools:
            # Chế độ nền an toàn: whitelist auto-allow, MỌI tool khác rơi vào _permission_gate → DENY.
            # KHÔNG nạp settings filesystem: allow-rule trong settings user có thể che gate.
            kw["allowed_tools"] = list(self.allowed_tools)
            kw["permission_mode"] = "default"
            kw["can_use_tool"] = self._permission_gate
        else:
            kw["permission_mode"] = "bypassPermissions"   # parity --dangerously-skip-permissions
            # Parity CLI: nạp settings máy (ambient MCP, CLAUDE.md, config user) như claude -p vẫn làm
            kw["setting_sources"] = ["user", "project", "local"]
        return ClaudeAgentOptions(**kw)

    async def query(self, prompt: str):
        if not self.is_available():
            yield {"type": "error", "content": "claude-agent-sdk chưa sẵn sàng (pip install claude-agent-sdk "
                                               "+ cài/đăng nhập Claude Code CLI)."}
            return
        from claude_agent_sdk import ClaudeSDKClient, ResultMessage
        IDLE = float(os.getenv("JAVIS_CLAUDE_IDLE_TIMEOUT", "180"))
        loop = asyncio.get_running_loop()
        client = ClaudeSDKClient(options=self._options())
        started = time.time()
        try:
            await client.connect()
            with _LOCK:
                _ACTIVE[client] = (self.tag, loop)
            await client.query(prompt)
            agen = client.receive_response().__aiter__()
            while True:
                # Watchdog parity với CLI: idle-timeout + trần wall-clock cho fork nền
                timeout = IDLE
                if self.max_wall_s:
                    timeout = min(timeout, max(1.0, self.max_wall_s - (time.time() - started)))
                try:
                    msg = await asyncio.wait_for(agen.__anext__(), timeout=timeout)
                except StopAsyncIteration:
                    break
                except asyncio.TimeoutError:
                    if self.max_wall_s and time.time() - started >= self.max_wall_s:
                        err = f"Fork vượt trần {int(self.max_wall_s)}s - đã dừng (cap wall-clock nền)."
                    else:
                        err = (f"Claude không phản hồi {int(IDLE)}s - đã dừng để tránh treo server. "
                               f"(tăng JAVIS_CLAUDE_IDLE_TIMEOUT nếu tác vụ thật sự dài)")
                    try:
                        await client.interrupt()
                    except Exception:
                        pass
                    yield {"type": "error", "content": err}
                    break
                events, sid = map_message(msg)
                if sid:
                    self.session_id = sid
                for ev in events:
                    yield ev
                if isinstance(msg, ResultMessage):
                    break
        except Exception as e:
            yield {"type": "error", "content": f"SDK engine: {type(e).__name__}: {e}"}
        finally:
            with _LOCK:
                _ACTIVE.pop(client, None)
            try:
                await client.disconnect()
            except Exception:
                pass
