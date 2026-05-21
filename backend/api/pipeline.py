"""处理流水线 API"""

import uuid
import asyncio
import traceback
from fastapi import APIRouter, BackgroundTasks, UploadFile, File, Form
from typing import Optional

from backend.models.schemas import VideoRequest, TaskProgress, TaskStatus, SourcePlatform
from backend.services import downloader, asr, rewriter, tts, compositor
from backend.config import FACES_DIR

router = APIRouter()
tasks: dict[str, TaskProgress] = {}


async def run_pipeline(task_id: str, req: VideoRequest):
    """完整处理流水线"""
    progress = tasks[task_id]

    try:
        # 1. 下载
        progress.status = TaskStatus.DOWNLOADING
        progress.message = "正在下载视频..."
        progress.progress = 10
        video_info = await downloader.download_video(req.url, req.platform.value)
        progress.original_title = video_info.get("title", "")

        # 2. ASR 识别
        progress.status = TaskStatus.TRANSCRIBING
        progress.message = "正在识别语音..."
        progress.progress = 25
        asr_result = await asr.transcribe(video_info["video_path"])
        progress.original_text = asr_result["full_text"]

        if not progress.original_text.strip():
            progress.original_text = "(视频无语音或识别结果为空)"

        # 3. AI 改写
        progress.status = TaskStatus.REWRITING
        progress.message = "正在改写文案..."
        progress.progress = 45
        rewritten = await rewriter.rewrite_text(
            progress.original_text, req.rewrite_style
        )
        progress.rewritten_text = rewritten

        # 4. TTS 配音
        progress.status = TaskStatus.GENERATING_TTS
        progress.message = "正在生成配音..."
        progress.progress = 60
        audio_path = await tts.generate_tts(rewritten, req.voice_gender)

        # 5. 换脸（可选）
        face_video = video_info["video_path"]
        if req.face_image:
            progress.status = TaskStatus.FACESWAPPING
            progress.message = "正在换脸处理..."
            progress.progress = 75
            from backend.services import face_swap
            face_video = await face_swap.face_swap_video(
                video_info["video_path"], req.face_image
            )

        # 6. 合成
        progress.status = TaskStatus.COMPOSITING
        progress.message = "正在合成最终视频..."
        progress.progress = 90
        final_path = await compositor.composite_video(
            face_video, audio_path, face_swapped=bool(req.face_image)
        )

        progress.status = TaskStatus.DONE
        progress.progress = 100
        progress.message = "✅ 处理完成！"
        progress.output_video = final_path

    except Exception as e:
        progress.status = TaskStatus.FAILED
        progress.message = f"❌ 处理失败: {str(e)}"
        traceback.print_exc()


@router.post("/start", response_model=dict)
async def start_pipeline(req: VideoRequest, bg: BackgroundTasks):
    """启动处理流水线"""
    task_id = str(uuid.uuid4())[:8]
    tasks[task_id] = TaskProgress(task_id=task_id)
    bg.add_task(run_pipeline, task_id, req)
    return {"task_id": task_id, "message": "任务已创建"}


@router.post("/upload-face")
async def upload_face(file: UploadFile = File(...)):
    """上传换脸目标图片"""
    ext = file.filename.split(".")[-1] if "." in file.filename else "jpg"
    filename = f"face_{uuid.uuid4().hex[:8]}.{ext}"
    filepath = FACES_DIR / filename
    content = await file.read()
    filepath.write_bytes(content)
    return {"path": str(filepath), "filename": filename}


@router.get("/status/{task_id}", response_model=TaskProgress)
async def get_status(task_id: str):
    """查询任务状态"""
    if task_id not in tasks:
        return TaskProgress(
            task_id=task_id,
            status=TaskStatus.FAILED,
            message="任务不存在",
        )
    return tasks[task_id]


@router.get("/tasks")
async def list_tasks():
    """列出所有任务"""
    return {"tasks": [t.model_dump() for t in tasks.values()]}
