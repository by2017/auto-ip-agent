"""字幕生成服务 — 基于 ASR 分段生成 SRT"""

import subprocess
import uuid
from pathlib import Path
from backend.config import OUTPUT_DIR


def format_srt_time(seconds: float) -> str:
    """将秒数转为 SRT 时间格式 HH:MM:SS,mmm"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


async def generate_subtitles(video_path: str, style: dict = None) -> dict:
    """从视频生成字幕（复用 ASR）"""
    from backend.services.asr import transcribe

    asr_result = await transcribe(video_path)
    segments = asr_result.get("segments", [])
    duration = asr_result.get("duration", 0)

    # 构建字幕段
    subtitle_segments = []
    srt_lines = []
    for i, seg in enumerate(segments, 1):
        start = format_srt_time(seg["start"])
        end = format_srt_time(seg["end"])
        text = seg["text"].strip()

        subtitle_segments.append({
            "index": i,
            "start": start,
            "end": end,
            "start_seconds": seg["start"],
            "end_seconds": seg["end"],
            "text": text,
        })

        srt_lines.append(f"{i}")
        srt_lines.append(f"{start} --> {end}")
        srt_lines.append(text)
        srt_lines.append("")

    # 写入 SRT 文件
    srt_path = str(OUTPUT_DIR / f"subtitle_{uuid.uuid4().hex[:8]}.srt")
    Path(srt_path).write_text("\n".join(srt_lines), encoding="utf-8")

    return {
        "segments": subtitle_segments,
        "srt_path": srt_path,
        "full_text": asr_result.get("full_text", ""),
        "duration": duration,
    }


async def burn_subtitles_into_video(video_path: str, srt_path: str, style: dict = None) -> str:
    """将字幕烧录到视频中"""
    output_path = str(OUTPUT_DIR / f"subtitled_{uuid.uuid4().hex[:8]}.mp4")

    # 字幕样式
    font_name = (style or {}).get("font_name", "Source Han Sans SC")
    font_size = (style or {}).get("font_size", 10)
    font_color = (style or {}).get("font_color", "&H000000")
    margin_v = (style or {}).get("margin_v", 0.04)

    # 使用 FFmpeg subtitles filter
    # 转义路径中的特殊字符
    srt_escaped = srt_path.replace(":", "\\:").replace("'", "\\'")

    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-vf", f"subtitles={srt_escaped}:force_style='FontSize={font_size}'",
        "-c:a", "copy",
        "-movflags", "+faststart",
        output_path,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        # fallback: 不烧录，直接返回原视频
        return video_path

    return output_path
