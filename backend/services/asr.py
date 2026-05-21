"""ASR 语音识别服务 — faster-whisper"""

from backend.config import ASR_MODEL_SIZE, ASR_DEVICE

_model = None


def _get_model():
    global _model
    if _model is None:
        from faster_whisper import WhisperModel
        _model = WhisperModel(
            ASR_MODEL_SIZE,
            device=ASR_DEVICE,
            compute_type="float32" if ASR_DEVICE == "cpu" else "float16",
        )
    return _model


async def transcribe(video_path: str) -> dict:
    """从视频提取音频并转文字"""
    model = _get_model()
    segments, info = model.transcribe(
        video_path,
        language="zh",
        beam_size=5,
        vad_filter=True,
        vad_parameters=dict(min_silence_duration_ms=500),
    )

    full_text = ""
    segment_list = []
    for seg in segments:
        text = seg.text.strip()
        full_text += text
        segment_list.append({
            "start": round(seg.start, 2),
            "end": round(seg.end, 2),
            "text": text,
        })

    return {
        "language": info.language,
        "full_text": full_text.strip(),
        "segments": segment_list,
        "duration": round(info.duration, 2),
    }
