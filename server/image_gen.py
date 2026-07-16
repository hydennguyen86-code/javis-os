"""
image_gen.py - Tạo ảnh bằng GÓI ChatGPT (OAuth device-code) - KHÔNG cần OpenAI API key.

Cơ chế (port từ plugin image_gen/openai-codex của nousresearch/hermes-agent): gọi Codex Responses
API (https://chatgpt.com/backend-api/codex/responses - CÙNG endpoint Javis đã dùng cho chat ChatGPT)
với builtin tool 'image_generation' (model gpt-image-2) + tool_choice=required, stream SSE, lấy ảnh
base64 trong 'image_generation_call.result'. Token OAuth lấy từ openai_oauth.valid_creds() (tự refresh).

Vì sao Javis trước đây KHÔNG tạo ảnh trực tiếp: đường chat ChatGPT (engine.responses_with_mcp) chỉ
gửi function tool, chưa từng gửi builtin tool 'image_generation'. Module này bổ sung đúng chỗ đó.

Ảnh lưu vào <vault>/attachments/ để nhúng thẳng vào chat: ![](attachments/<tên>.png)
(dashboard phục vụ qua /files/raw). Các hàm build_payload / extract_image_b64 / resolve_size /
save_png_b64 là THUẦN → test được không cần mạng.
"""
from __future__ import annotations

import base64
import json
import os
import re
import time
import uuid
from pathlib import Path
from typing import Any, Optional

import httpx

import openai_oauth

CODEX_RESPONSES_URL = "https://chatgpt.com/backend-api/codex/responses"
# Model chat 'chủ' chỉ để gọi tool; ảnh do IMAGE_MODEL sinh. Override qua env nếu gói đổi tên model.
HOST_MODEL = os.getenv("JAVIS_IMAGE_HOST_MODEL", "gpt-5.5")
IMAGE_MODEL = os.getenv("JAVIS_IMAGE_MODEL", "gpt-image-2")
INSTRUCTIONS = ("You are an assistant that must fulfill image generation and image editing "
                "requests by using the image_generation tool when provided.")

_SIZES = {"landscape": "1536x1024", "square": "1024x1024", "portrait": "1024x1536"}
_QUALITIES = {"low", "medium", "high"}
_ATTACH_RE = r"^(\d+\s*[-_.]\s*)?attachments$"


# ---------------------------------------------------------------------------
# Helpers thuần (test được)
# ---------------------------------------------------------------------------
def resolve_size(aspect_ratio: Optional[str]) -> str:
    return _SIZES.get((aspect_ratio or "square").strip().lower(), _SIZES["square"])


def build_payload(prompt: str, size: str, quality: str) -> dict:
    """Body Responses cho 1 lời gọi image_generation (mirror hermes openai-codex)."""
    return {
        "model": HOST_MODEL,
        "store": False,
        "instructions": INSTRUCTIONS,
        "input": [{"type": "message", "role": "user",
                   "content": [{"type": "input_text", "text": prompt}]}],
        "tools": [{"type": "image_generation", "model": IMAGE_MODEL, "size": size,
                   "quality": quality, "output_format": "png", "background": "opaque",
                   "partial_images": 1}],
        "tool_choice": {"type": "allowed_tools", "mode": "required",
                        "tools": [{"type": "image_generation"}]},
        "stream": True,
    }


def extract_image_b64(value: Any) -> Optional[str]:
    """Bới đệ quy 1 payload sự kiện SSE, trả b64 ảnh MỚI nhất (image_generation_call.result
    hoặc partial_image_b64). Bới đệ quy để chịu được thay đổi hình dạng sự kiện của backend."""
    found: Optional[str] = None
    if isinstance(value, dict):
        if value.get("type") == "image_generation_call":
            r = value.get("result")
            if isinstance(r, str) and r:
                found = r
        p = value.get("partial_image_b64")
        if isinstance(p, str) and p:
            found = p
        for v in value.values():
            n = extract_image_b64(v)
            if n:
                found = n
    elif isinstance(value, list):
        for v in value:
            n = extract_image_b64(v)
            if n:
                found = n
    return found


def _default_vault() -> str:
    return str(Path(os.getenv("BRAINS_DIR", str(Path(__file__).parent.parent / "brains"))) / "Brain Default")


def _resolve_vault(vault_root: Optional[str]) -> Path:
    if vault_root and os.path.isdir(vault_root):
        return Path(vault_root)
    return Path(_default_vault())


def _attachments_dir(vault: Path) -> Path:
    """Thư mục attachments của vault (khớp 'attachments'/'Attachments'/'NN - attachments'), tạo nếu thiếu."""
    try:
        for name in os.listdir(vault):
            if os.path.isdir(vault / name) and re.match(_ATTACH_RE, name.strip(), re.IGNORECASE):
                return vault / name
    except Exception:
        pass
    d = vault / "attachments"
    d.mkdir(parents=True, exist_ok=True)
    return d


def save_png_b64(b64: str, vault_root: Optional[str], prefix: str = "javis-img") -> dict:
    """Giải mã b64 → lưu PNG vào <vault>/attachments. Trả {ok, rel_path, abs_path, file}."""
    try:
        raw = base64.b64decode(b64)
    except Exception as e:
        return {"ok": False, "error": f"Ảnh base64 hỏng: {e}"}
    if not raw:
        return {"ok": False, "error": "Ảnh rỗng."}
    vault = _resolve_vault(vault_root)
    adir = _attachments_dir(vault)
    fname = f"{prefix}-{time.strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}.png"
    fpath = adir / fname
    try:
        fpath.write_bytes(raw)
    except Exception as e:
        return {"ok": False, "error": f"Lưu ảnh lỗi: {e}"}
    rel = os.path.relpath(fpath, vault).replace(os.sep, "/")
    return {"ok": True, "rel_path": rel, "abs_path": str(fpath), "file": fname}


def _headers(token: str, account_id: str) -> dict:
    # KHỚP đúng bộ header engine.responses_with_mcp đã chạy được (qua Cloudflare backend Codex).
    return {
        "Authorization": f"Bearer {token}", "chatgpt-account-id": account_id or "",
        "OpenAI-Beta": "responses=experimental", "originator": "codex_cli_rs",
        "session_id": str(uuid.uuid4()), "Content-Type": "application/json",
        "Accept": "text/event-stream", "User-Agent": "javis-os/0.3 (codex)",
    }


# ---------------------------------------------------------------------------
# Gọi thật
# ---------------------------------------------------------------------------
async def generate_chatgpt(prompt: str, aspect_ratio: str = "square", quality: str = "medium",
                           vault_root: Optional[str] = None, timeout_s: float = 300.0) -> dict:
    """Tạo 1 ảnh bằng gói ChatGPT. Trả {ok, rel_path, abs_path, size, quality, aspect} hoặc {ok:False, error}."""
    prompt = (prompt or "").strip()
    if not prompt:
        return {"ok": False, "error": "Thiếu mô tả ảnh (prompt)."}
    aspect = (aspect_ratio or "square").strip().lower()
    if aspect not in _SIZES:
        aspect = "square"
    quality = (quality or "medium").strip().lower()
    if quality not in _QUALITIES:
        quality = "medium"

    creds = openai_oauth.valid_creds()
    if not creds or not creds.get("access_token"):
        return {"ok": False, "error": "Chưa kết nối ChatGPT (OAuth). Vào trang Model đăng nhập ChatGPT rồi thử lại."}

    size = resolve_size(aspect)
    payload = build_payload(prompt, size, quality)
    headers = _headers(creds["access_token"], creds.get("account_id") or "")

    b64: Optional[str] = None
    err: Optional[str] = None
    try:
        timeout = httpx.Timeout(timeout_s, connect=20)
        async with httpx.AsyncClient(timeout=timeout) as client:
            async with client.stream("POST", CODEX_RESPONSES_URL, headers=headers, json=payload) as r:
                if r.status_code != 200:
                    body = await r.aread()
                    return {"ok": False, "error": f"ChatGPT {r.status_code}: {body.decode('utf-8', 'replace')[:300]}"}
                async for line in r.aiter_lines():
                    line = (line or "").strip()
                    if not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if not data or data == "[DONE]":
                        continue
                    try:
                        obj = json.loads(data)
                    except json.JSONDecodeError:
                        continue
                    if obj.get("type") in ("response.failed", "error", "response.error"):
                        e = (obj.get("response") or {}).get("error") or obj.get("error") or {}
                        err = e.get("message") if isinstance(e, dict) else str(e)
                        continue
                    got = extract_image_b64(obj)
                    if got:
                        b64 = got
    except Exception as e:
        return {"ok": False, "error": f"Gọi ChatGPT lỗi: {type(e).__name__}: {e}"}

    if not b64:
        return {"ok": False, "error": err or "ChatGPT không trả ảnh (gói ChatGPT có thể chưa hỗ trợ tạo ảnh qua Codex)."}

    saved = save_png_b64(b64, vault_root, prefix="javis-img")
    if not saved.get("ok"):
        return saved
    return {"ok": True, "rel_path": saved["rel_path"], "abs_path": saved["abs_path"],
            "file": saved["file"], "size": size, "quality": quality, "aspect": aspect,
            "provider": "openai-codex", "prompt": prompt}
