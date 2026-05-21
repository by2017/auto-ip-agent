"""封面生成服务 — 从视频截取帧 + 文字叠加"""

import subprocess
import uuid
from pathlib import Path
from backend.config import COVERS_DIR, OUTPUT_DIR


async def generate_cover(video_path: str, title: str = "", style: dict = None) -> str:
    """从视频中截取关键帧作为封面，可选叠加标题文字"""
    cover_path = str(COVERS_DIR / f"cover_{uuid.uuid4().hex[:8]}.png")

    # 截取视频第2秒的帧作为封面
    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-ss", "2",
        "-vframes", "1",
        "-q:v", "2",
        cover_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"封面截取失败: {result.stderr[-300:]}")

    # 如果有标题，叠加文字
    if title:
        try:
            from PIL import Image, ImageDraw, ImageFont
            img = Image.open(cover_path)
            draw = ImageDraw.Draw(img)
            w, h = img.size

            ratio = (style or {}).get("ratio", "9:16")
            font_size = (style or {}).get("font_size", 32)
            font_color = (style or {}).get("font_color", "#FFFFFF")
            bg_opacity = (style or {}).get("bg_opacity", 0.4)

            # 尝试加载字体
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc", font_size)
            except Exception:
                try:
                    font = ImageFont.truetype("/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc", font_size)
                except Exception:
                    font = ImageFont.load_default()

            # 计算文字位置（底部居中）
            bbox = draw.textbbox((0, 0), title, font=font)
            tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]

            # 半透明背景条
            bar_h = th + 40
            bar_y = h - bar_h
            overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
            overlay_draw = ImageDraw.Draw(overlay)
            overlay_draw.rectangle(
                [0, bar_y, w, h],
                fill=(0, 0, 0, int(255 * bg_opacity)),
            )
            img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")

            # 绘制文字
            draw = ImageDraw.Draw(img)
            text_x = (w - tw) // 2
            text_y = bar_y + (bar_h - th) // 2
            draw.text((text_x, text_y), title, fill=font_color, font=font)

            img.save(cover_path, quality=95)
        except ImportError:
            pass  # Pillow 不可用则只返回截帧

    return cover_path
