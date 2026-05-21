"""轻量启动 — 跳过 heavy deps (ASR/换脸)"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, BackgroundTasks, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pathlib import Path
from pydantic import BaseModel
from enum import Enum
from typing import Optional
import uuid
import asyncio

app = FastAPI(title="短视频搬运工作流", version="1.0.0")

FRONTEND_DIR = Path(__file__).parent / "frontend"
DATA_DIR = Path(__file__).parent / "data"
for d in [DATA_DIR / "uploads", DATA_DIR / "outputs", DATA_DIR / "faces"]:
    d.mkdir(parents=True, exist_ok=True)

app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")
app.mount("/data", StaticFiles(directory=str(DATA_DIR)), name="data")


# === Models ===
class SourcePlatform(str, Enum):
    DOUYIN = "douyin"
    WECHAT_VIDEO = "wechat_video"

class TaskStatus(str, Enum):
    PENDING = "pending"
    DOWNLOADING = "downloading"
    TRANSCRIBING = "transcribing"
    REWRITING = "rewriting"
    GENERATING_TTS = "generating_tts"
    COMPOSITING = "compositing"
    DONE = "done"
    FAILED = "failed"

class VideoRequest(BaseModel):
    url: str
    platform: SourcePlatform = SourcePlatform.DOUYIN
    rewrite_style: str = "保持原意，换个角度重新表述"
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

tasks: dict[str, TaskProgress] = {}


# === Pipeline ===
async def run_pipeline(task_id: str, req: VideoRequest):
    progress = tasks[task_id]
    try:
        # 1. Download
        progress.status = TaskStatus.DOWNLOADING
        progress.message = "正在下载视频..."
        progress.progress = 10
        import yt_dlp
        output_path = str(DATA_DIR / "uploads" / f"{task_id}.mp4")
        ydl_opts = {
            "outtmpl": output_path,
            "format": "best",
            "quiet": True,
            "no_warnings": True,
            "http_headers": {"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X)"},
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(req.url, download=True)

        # 2. ASR
        progress.status = TaskStatus.TRANSCRIBING
        progress.message = "正在识别语音..."
        progress.progress = 30
        try:
            from faster_whisper import WhisperModel
            model = WhisperModel("large-v3", device="cpu", compute_type="float32")
            segments, info_asr = model.transcribe(output_path, language="zh", beam_size=5, vad_filter=True)
            full_text = ""
            for seg in segments:
                full_text += seg.text.strip()
            progress.original_text = full_text or "(无语音或识别为空)"
        except Exception as e:
            progress.original_text = f"(ASR不可用: {e})"

        # 3. AI Rewrite
        progress.status = TaskStatus.REWRITING
        progress.message = "正在改写文案..."
        progress.progress = 50
        import httpx
        api_key = os.getenv("OPENROUTER_API_KEY", "")
        if api_key and progress.original_text and not progress.original_text.startswith("("):
            async with httpx.AsyncClient(timeout=120) as client:
                resp = await client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                    json={
                        "model": "openai/gpt-4o-mini",
                        "messages": [
                            {"role": "system", "content": "你是短视频文案改写专家。保持原意，换个角度重述，更换人物细节，口语化，字数±10%。直接输出改写文案，不要前缀。"},
                            {"role": "user", "content": f"改写：\n\n{progress.original_text}"},
                        ],
                        "temperature": 0.8,
                    },
                )
                data = resp.json()
                progress.rewritten_text = data["choices"][0]["message"]["content"].strip().strip('"').strip('"')
        else:
            progress.rewritten_text = "(无API key或原文为空，跳过改写)"

        # 4. TTS
        progress.status = TaskStatus.GENERATING_TTS
        progress.message = "正在生成配音..."
        progress.progress = 70
        import edge_tts
        voice = "zh-CN-YunxiNeural" if req.voice_gender == "male" else "zh-CN-XiaoxiaoNeural"
        tts_path = str(DATA_DIR / "outputs" / f"tts_{task_id}.mp3")
        await edge_tts.Communicate(progress.rewritten_text, voice).save(tts_path)

        # 5. Composite
        progress.status = TaskStatus.COMPOSITING
        progress.message = "正在合成视频..."
        progress.progress = 90
        import subprocess
        final_path = str(DATA_DIR / "outputs" / f"final_{task_id}.mp4")
        result = subprocess.run(
            ["ffmpeg", "-y", "-i", output_path, "-i", tts_path, "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-shortest", "-movflags", "+faststart", final_path],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg 失败: {result.stderr[-200:]}")

        progress.status = TaskStatus.DONE
        progress.progress = 100
        progress.message = "✅ 处理完成！"
        progress.output_video = final_path

    except Exception as e:
        progress.status = TaskStatus.FAILED
        progress.message = f"❌ 失败: {e}"
        import traceback
        traceback.print_exc()


# === Routes ===
@app.get("/")
async def index():
    return FileResponse(str(FRONTEND_DIR / "index.html"))

@app.get("/api/health")
async def health():
    return {"status": "ok"}

@app.post("/api/pipeline/start")
async def start_pipeline(req: VideoRequest, bg: BackgroundTasks):
    task_id = str(uuid.uuid4())[:8]
    tasks[task_id] = TaskProgress(task_id=task_id)
    bg.add_task(run_pipeline, task_id, req)
    return {"task_id": task_id}

@app.post("/api/pipeline/upload-face")
async def upload_face(file: UploadFile = File(...)):
    ext = file.filename.split(".")[-1] if "." in file.filename else "jpg"
    filename = f"face_{uuid.uuid4().hex[:8]}.{ext}"
    filepath = DATA_DIR / "faces" / filename
    filepath.write_bytes(await file.read())
    return {"path": str(filepath)}

@app.get("/api/pipeline/status/{task_id}")
async def get_status(task_id: str):
    if task_id not in tasks:
        return {"task_id": task_id, "status": "failed", "message": "任务不存在"}
    return tasks[task_id]


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8200)
