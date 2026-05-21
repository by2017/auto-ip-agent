from pydantic import BaseModel
from enum import Enum
from typing import Optional
from datetime import datetime


class SourcePlatform(str, Enum):
    DOUYIN = "douyin"
    WECHAT_VIDEO = "wechat_video"
    LOCAL = "local"


class TaskStatus(str, Enum):
    PENDING = "pending"
    DOWNLOADING = "downloading"
    TRANSCRIBING = "transcribing"
    REWRITING = "rewriting"
    GENERATING_TTS = "generating_tts"
    FACESWAPPING = "faceswapping"
    COMPOSITING = "compositing"
    GENERATING_SUBTITLE = "generating_subtitle"
    GENERATING_COVER = "generating_cover"
    EXPORTING = "exporting"
    DONE = "done"
    FAILED = "failed"


class VideoRequest(BaseModel):
    url: str
    platform: SourcePlatform = SourcePlatform.DOUYIN
    rewrite_style: str = "保持原意，换个角度重新表述，更换人物和细节"
    voice_gender: str = "male"
    face_image: Optional[str] = None


class TaskProgress(BaseModel):
    task_id: str
    status: TaskStatus = TaskStatus.PENDING
    progress: int = 0
    message: str = ""
    original_text: str = ""
    rewritten_text: str = ""
    output_video: str = ""
    original_title: str = ""
    audio_path: str = ""
    subtitle_path: str = ""
    cover_path: str = ""


# === 逐步骤 API 模型 ===

class StepExtractRequest(BaseModel):
    url: str
    platform: SourcePlatform = SourcePlatform.DOUYIN

class StepExtractResponse(BaseModel):
    success: bool
    video_path: str = ""
    title: str = ""
    description: str = ""
    full_text: str = ""
    segments: list = []
    duration: float = 0
    error: str = ""


class StepRewriteRequest(BaseModel):
    text: str
    style: str = "保持原意，换个角度重新表述"
    model: str = ""

class StepRewriteResponse(BaseModel):
    success: bool
    rewritten_text: str = ""
    original_text: str = ""
    error: str = ""


class StepTTSRequest(BaseModel):
    text: str
    voice: str = "zh-CN-YunxiNeural"
    rate: str = "+0%"

class StepTTSResponse(BaseModel):
    success: bool
    audio_path: str = ""
    duration: float = 0
    error: str = ""


class StepVideoRequest(BaseModel):
    video_path: str
    audio_path: str
    face_image: Optional[str] = None

class StepVideoResponse(BaseModel):
    success: bool
    output_path: str = ""
    duration: float = 0
    error: str = ""


class SubtitleStyle(BaseModel):
    font_name: str = "Source Han Sans SC"
    font_size: int = 10
    font_color: str = "#000000"
    bg_color: str = "#FFFFFF"
    position: str = "bottom"  # bottom / top / center
    margin_v: float = 0.04

class StepSubtitleRequest(BaseModel):
    video_path: str
    style: Optional[SubtitleStyle] = None

class SubtitleSegment(BaseModel):
    index: int
    start: str
    end: str
    start_seconds: float
    end_seconds: float
    text: str

class StepSubtitleResponse(BaseModel):
    success: bool
    segments: list[SubtitleSegment] = []
    srt_path: str = ""
    full_text: str = ""
    duration: float = 0
    error: str = ""


class CoverStyle(BaseModel):
    ratio: str = "9:16"  # 9:16 / 16:9 / 1:1
    title: str = ""
    font_size: int = 32
    font_color: str = "#FFFFFF"
    bg_opacity: float = 0.4

class StepCoverRequest(BaseModel):
    video_path: str
    title: str = ""
    style: Optional[CoverStyle] = None

class StepCoverResponse(BaseModel):
    success: bool
    cover_path: str = ""
    error: str = ""


class StepExportRequest(BaseModel):
    video_path: str
    audio_path: str
    subtitle_path: Optional[str] = None
    cover_path: Optional[str] = None
    burn_subtitles: bool = False

class StepExportResponse(BaseModel):
    success: bool
    output_path: str = ""
    error: str = ""


class VoiceOption(BaseModel):
    id: str
    name: str
    gender: str
    style: str
