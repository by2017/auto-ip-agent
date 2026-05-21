"""逐步骤 API — 每步独立执行"""

import uuid
import subprocess
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException

from backend.models.schemas import (
    StepExtractRequest, StepExtractResponse,
    StepRewriteRequest, StepRewriteResponse,
    StepTTSRequest, StepTTSResponse,
    StepVideoRequest, StepVideoResponse,
    StepSubtitleRequest, StepSubtitleResponse,
    StepCoverRequest, StepCoverResponse,
    StepExportRequest, StepExportResponse,
    VoiceOption,
)
from backend.services import downloader, asr, rewriter, tts, compositor, subtitle, cover
from backend.config import TTS_VOICES, OUTPUT_DIR, FACES_DIR

router = APIRouter()


# === 步骤1: 提取文案素材 ===
@router.post("/extract", response_model=StepExtractResponse)
async def step_extract(req: StepExtractRequest):
    """下载视频 + ASR 提取文案"""
    try:
        video_info = await downloader.download_video(req.url, req.platform.value)
        asr_result = await asr.transcribe(video_info["video_path"])
        return StepExtractResponse(
            success=True,
            video_path=video_info["video_path"],
            title=video_info.get("title", ""),
            description=video_info.get("description", ""),
            full_text=asr_result.get("full_text", ""),
            segments=asr_result.get("segments", []),
            duration=asr_result.get("duration", 0),
        )
    except Exception as e:
        return StepExtractResponse(success=False, error=str(e))


# === 步骤2: 文案智能改写 ===
@router.post("/rewrite", response_model=StepRewriteResponse)
async def step_rewrite(req: StepRewriteRequest):
    """AI 改写文案"""
    try:
        result = await rewriter.rewrite_text(req.text, req.style)
        return StepRewriteResponse(
            success=True,
            rewritten_text=result,
            original_text=req.text,
        )
    except Exception as e:
        return StepRewriteResponse(success=False, error=str(e))


# === 步骤3: 语音配音合成 ===
@router.post("/tts", response_model=StepTTSResponse)
async def step_tts(req: StepTTSRequest):
    """TTS 语音合成"""
    try:
        from backend.services.tts import generate_tts_with_duration
        result = await generate_tts_with_duration(req.text, req.voice, req.rate)
        return StepTTSResponse(
            success=True,
            audio_path=result["path"],
            duration=result["duration"],
        )
    except Exception as e:
        return StepTTSResponse(success=False, error=str(e))


# === 步骤4: 视频素材生成 ===
@router.post("/video", response_model=StepVideoResponse)
async def step_video(req: StepVideoRequest):
    """合成视频（替换音频 + 可选换脸）"""
    try:
        video_source = req.video_path
        if req.face_image:
            from backend.services import face_swap
            video_source = await face_swap.face_swap_video(req.video_path, req.face_image)

        output_path = await compositor.composite_video(video_source, req.audio_path)

        # 获取输出时长
        probe = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", output_path],
            capture_output=True, text=True,
        )
        duration = float(probe.stdout.strip()) if probe.stdout.strip() else 0

        return StepVideoResponse(success=True, output_path=output_path, duration=duration)
    except Exception as e:
        return StepVideoResponse(success=False, error=str(e))


# === 步骤5: 字幕识别 ===
@router.post("/subtitle", response_model=StepSubtitleResponse)
async def step_subtitle(req: StepSubtitleRequest):
    """生成字幕"""
    try:
        style = req.style.model_dump() if req.style else None
        result = await subtitle.generate_subtitles(req.video_path, style)
        segments = [
            {
                "index": s["index"],
                "start": s["start"],
                "end": s["end"],
                "start_seconds": s["start_seconds"],
                "end_seconds": s["end_seconds"],
                "text": s["text"],
            }
            for s in result["segments"]
        ]
        return StepSubtitleResponse(
            success=True,
            segments=segments,
            srt_path=result["srt_path"],
            full_text=result["full_text"],
            duration=result["duration"],
        )
    except Exception as e:
        return StepSubtitleResponse(success=False, error=str(e))


# === 步骤6: 封面设计 ===
@router.post("/cover", response_model=StepCoverResponse)
async def step_cover(req: StepCoverRequest):
    """生成封面"""
    try:
        style = req.style.model_dump() if req.style else None
        cover_path = await cover.generate_cover(req.video_path, req.title, style)
        return StepCoverResponse(success=True, cover_path=cover_path)
    except Exception as e:
        return StepCoverResponse(success=False, error=str(e))


# === 步骤7: 导出 ===
@router.post("/export", response_model=StepExportResponse)
async def step_export(req: StepExportRequest):
    """最终导出 — 可选烧录字幕"""
    try:
        video_source = req.video_path

        # 烧录字幕
        if req.burn_subtitles and req.subtitle_path:
            video_source = await subtitle.burn_subtitles_into_video(
                video_source, req.subtitle_path
            )

        return StepExportResponse(success=True, output_path=video_source)
    except Exception as e:
        return StepExportResponse(success=False, error=str(e))


# === 辅助接口 ===
@router.get("/voices")
async def list_voices():
    """列出可用 TTS 音色"""
    return {"voices": TTS_VOICES}


@router.post("/upload-face")
async def upload_face(file: UploadFile = File(...)):
    """上传换脸图片"""
    ext = file.filename.split(".")[-1] if "." in file.filename else "jpg"
    filename = f"face_{uuid.uuid4().hex[:8]}.{ext}"
    filepath = FACES_DIR / filename
    content = await file.read()
    filepath.write_bytes(content)
    return {"path": str(filepath), "filename": filename}


@router.post("/upload-video")
async def upload_video(file: UploadFile = File(...)):
    """上传本地视频文件"""
    ext = file.filename.split(".")[-1] if "." in file.filename else "mp4"
    filename = f"local_{uuid.uuid4().hex[:8]}.{ext}"
    filepath = Path(OUTPUT_DIR) / filename
    content = await file.read()
    filepath.write_bytes(content)
    return {"path": str(filepath), "filename": filename}
