"""TTS 配音服务 — edge-tts"""

import uuid
import subprocess
import edge_tts
from backend.config import OUTPUT_DIR, TTS_VOICE_MALE, TTS_VOICE_FEMALE


async def generate_tts(text: str, voice_gender: str = "male") -> str:
    """生成TTS配音音频（旧接口，兼容 pipeline）"""
    voice = TTS_VOICE_MALE if voice_gender == "male" else TTS_VOICE_FEMALE
    output_path = str(OUTPUT_DIR / f"tts_{uuid.uuid4().hex[:8]}.mp3")
    communicate = edge_tts.Communicate(text, voice, rate="+0%")
    await communicate.save(output_path)
    return output_path


async def generate_tts_with_duration(text: str, voice: str = "", rate: str = "+0%") -> dict:
    """生成TTS配音音频并返回时长"""
    if not voice:
        voice = TTS_VOICE_MALE
    output_path = str(OUTPUT_DIR / f"tts_{uuid.uuid4().hex[:8]}.mp3")

    communicate = edge_tts.Communicate(text, voice, rate=rate)
    await communicate.save(output_path)

    # 获取音频时长
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", output_path],
        capture_output=True, text=True,
    )
    duration = float(probe.stdout.strip()) if probe.stdout.strip() else 0

    return {"path": output_path, "duration": round(duration, 2)}
