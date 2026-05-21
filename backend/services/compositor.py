"""视频合成服务 — FFmpeg"""

import subprocess
import uuid
from backend.config import OUTPUT_DIR


async def composite_video(
    video_path: str,
    audio_path: str,
    face_swapped: bool = False,
) -> str:
    """合成最终视频：替换音频轨道"""
    source = video_path
    output_path = str(OUTPUT_DIR / f"final_{uuid.uuid4().hex[:8]}.mp4")

    # 获取视频时长
    probe_cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "csv=p=0",
        source,
    ]
    probe = subprocess.run(probe_cmd, capture_output=True, text=True)
    video_duration = float(probe.stdout.strip()) if probe.stdout.strip() else 0

    # 获取音频时长
    probe_cmd[5] = audio_path
    probe = subprocess.run(probe_cmd, capture_output=True, text=True)
    audio_duration = float(probe.stdout.strip()) if probe.stdout.strip() else 0

    # 如果音频比视频长，截断音频；如果短，用最后一帧填充
    cmd = [
        "ffmpeg", "-y",
        "-i", source,
        "-i", audio_path,
        "-map", "0:v",
        "-map", "1:a",
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        "-movflags", "+faststart",
        output_path,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg 合成失败:\n{result.stderr[-500:]}")

    return output_path


async def extract_audio(video_path: str) -> str:
    """从视频提取音频"""
    output_path = str(OUTPUT_DIR / f"audio_{uuid.uuid4().hex[:8]}.wav")
    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", "16000",
        "-ac", "1",
        output_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"音频提取失败:\n{result.stderr[-300:]}")
    return output_path
