"""Plugin bundled: tạo ảnh bằng gói ChatGPT (OAuth) cho MỌI engine.

Đây là câu trả lời cho "Hermes tạo ảnh bằng ChatGPT mà Javis chưa": đăng ký tool
javis_generate_image, gọi image_gen.generate_chatgpt (Codex Responses + tool image_generation).
Bất kỳ engine nào (Claude Code/Codex/API) khi user bảo "tạo ảnh ..." đều gọi được tool này.

- min_mode=safe: coi như thao tác GHI (tạo file + dùng quota) → chặn ở chế độ suggest.
- check_fn: chưa kết nối ChatGPT → tool báo rõ cách bật, không lỗi khó hiểu.
"""
from __future__ import annotations

import image_gen
import openai_oauth


def register(ctx):
    def _check():
        try:
            if not openai_oauth.status().get("connected"):
                return ("Chưa kết nối ChatGPT (OAuth). Vào trang Model đăng nhập ChatGPT rồi thử lại - "
                        "tạo ảnh dùng chính gói ChatGPT, không cần API key.")
        except Exception as e:
            return f"Không kiểm tra được kết nối ChatGPT: {e}"
        return None

    async def _gen(args, cctx):
        args = args or {}
        prompt = str(args.get("prompt") or "").strip()
        if not prompt:
            return "ERROR: thiếu 'prompt' (mô tả ảnh cần tạo)."
        aspect = str(args.get("aspect_ratio") or "square")
        quality = str(args.get("quality") or "medium")
        res = await image_gen.generate_chatgpt(prompt, aspect, quality, vault_root=cctx.vault_root)
        if not res.get("ok"):
            return "ERROR: " + str(res.get("error") or "tạo ảnh thất bại")
        rel = res["rel_path"]
        return (f"Đã tạo ảnh ({res['size']}, chất lượng {res['quality']}), lưu tại {rel}. "
                f"HÃY NHÚNG ngay vào câu trả lời cho người dùng bằng cú pháp markdown: "
                f"![{prompt[:40]}]({rel})")

    ctx.register_tool(
        name="javis_generate_image",
        description=("Tạo ẢNH từ mô tả bằng gói ChatGPT đang đăng nhập (không cần API key). Tham số: "
                     "prompt (mô tả ảnh, bắt buộc), aspect_ratio (square|landscape|portrait), "
                     "quality (low|medium|high). Sau khi gọi, NHÚNG ![](đường-dẫn) trả về vào câu trả lời."),
        handler=_gen, min_mode="safe", check_fn=_check,
        schema={"type": "object", "properties": {
            "prompt": {"type": "string", "description": "Mô tả ảnh cần tạo (càng rõ càng tốt)"},
            "aspect_ratio": {"type": "string", "enum": ["square", "landscape", "portrait"],
                             "description": "Tỉ lệ khung ảnh, mặc định square"},
            "quality": {"type": "string", "enum": ["low", "medium", "high"],
                        "description": "Chất lượng/độ chi tiết, mặc định medium"}},
            "required": ["prompt"]},
    )
