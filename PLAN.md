# 短视频搬运工作流 — 实施计划

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** 构建一个 Web 端短视频搬运工具：输入视频链接 → ASR提取文案 → AI改写 → TTS配音 → 换脸 → 合成新视频 → 发布到抖音/视频号

**Architecture:** FastAPI 后端 + 静态前端，各处理环节解耦为独立 Service，通过 Celery/asyncio 管道串联

**Tech Stack:** Python 3.12, FastAPI, faster-whisper(ASR), OpenRouter/AI改写, edge-tts(配音), insightface(换脸), FFmpeg+moviepy(视频合成), yt-dlp(下载)

---

## 项目结构

```
video-repurpose/
├── backend/
│   ├── main.py                 # FastAPI 入口
│   ├── config.py               # 配置管理
│   ├── api/
│   │   ├── __init__.py
│   │   ├── video.py            # 视频下载/上传 API
│   │   ├── pipeline.py         # 处理流水线 API
│   │   └── publish.py          # 发布 API
│   ├── services/
│   │   ├── __init__.py
│   │   ├── downloader.py       # yt-dlp 视频下载
│   │   ├── asr.py              # Whisper 语音识别
│   │   ├── rewriter.py         # AI 文案改写
│   │   ├── tts.py              # TTS 配音
│   │   ├── face_swap.py        # 换脸
│   │   └── compositor.py       # 视频合成
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py          # Pydantic 数据模型
│   └── utils/
│       ├── __init__.py
│       └── file_utils.py       # 文件工具
├── frontend/
│   ├── index.html              # 主页面
│   ├── css/
│   │   └── style.css
│   └── js/
│       └── app.js              # 前端逻辑
├── data/
│   ├── uploads/                # 原始视频
│   ├── outputs/                # 输出视频
│   └── faces/                  # 换脸素材
├── requirements.txt
└── README.md
```

---

## Task 1: 项目初始化 + FastAPI 骨架

**Objective:** 搭建项目骨架，FastAPI 能跑起来

**Files:**
- Create: `backend/main.py`
- Create: `backend/config.py`
- Create: `backend/models/schemas.py`
- Create: `backend/api/__init__.py`
- Create: `requirements.txt`

**Step 1: 创建 requirements.txt**

```txt
fastapi==0.115.0
uvicorn[standard]==0.30.0
pydantic==2.9.0
python-multipart==0.0.9
httpx==0.27.0
yt-dlp>=2024.0.0
openai-whisper>=20231117
faster-whisper>=1.0.0
edge-tts>=6.1.0
moviepy>=1.0.3
insightface>=0.7.3
onnxruntime>=1.18.0
opencv-python-headless>=4.10.0
numpy>=1.26.0
Pillow>=10.0.0
aiofiles>=24.0.0
```

**Step 2: 创建 backend/config.py**

```python
import os
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
OUTPUT_DIR = DATA_DIR / "outputs"
FACES_DIR = DATA_DIR / "faces"

# 确保目录存在
for d in [UPLOAD_DIR, OUTPUT_DIR, FACES_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# AI 改写配置
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
REWRITE_MODEL = os.getenv("REWRITE_MODEL", "openai/gpt-4o-mini")

# TTS 配置
TTS_VOICE = os.getenv("TTS_VOICE", "zh-CN-YunxiNeural")  # 男声
TTS_VOICE_FEMALE = "zh-CN-XiaoxiaoNeural"  # 女声

# ASR 配置
ASR_MODEL_SIZE = os.getenv("ASR_MODEL_SIZE", "large-v3")
ASR_DEVICE = "cuda" if os.getenv("CUDA_VISIBLE_DEVICES") else "cpu"

# 服务配置
HOST = "0.0.0.0"
PORT = 8200
```

**Step 3: 创建 backend/models/schemas.py**

```python
from pydantic import BaseModel
from enum import Enum
from typing import Optional

class SourcePlatform(str, Enum):
    DOUYIN = "douyin"
    WECHAT_VIDEO = "wechat_video"

class TaskStatus(str, Enum):
    PENDING = "pending"
    DOWNLOADING = "downloading"
    TRANSCRIBING = "transcribing"
    REWRITING = "rewriting"
    GENERATING_TTS = "generating_tts"
    FACESWAPPING = "faceswapping"
    COMPOSITING = "compositing"
    DONE = "done"
    FAILED = "failed"

class VideoRequest(BaseModel):
    url: str
    platform: SourcePlatform = SourcePlatform.DOUYIN
    rewrite_style: str = "保持原意，换个角度重新表述"
    voice_gender: str = "male"  # male / female
    face_image: Optional[str] = None  # 换脸目标图片路径

class TaskProgress(BaseModel):
    task_id: str
    status: TaskStatus
    progress: int = 0  # 0-100
    message: str = ""
    original_text: str = ""
    rewritten_text: str = ""
    output_video: str = ""
```

**Step 4: 创建 backend/main.py**

```python
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

app = FastAPI(title="短视频搬运工作流", version="1.0.0")

# 挂载静态文件
FRONTEND_DIR = Path(__file__).parent.parent / "frontend"
app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")
app.mount("/data", StaticFiles(directory="data"), name="data")

@app.get("/")
async def index():
    return FileResponse(str(FRONTEND_DIR / "index.html"))

@app.get("/api/health")
async def health():
    return {"status": "ok"}

# 后续注册路由
# from api.video import router as video_router
# from api.pipeline import router as pipeline_router
# app.include_router(video_router, prefix="/api/video")
# app.include_router(pipeline_router, prefix="/api/pipeline")
```

**Step 5: 验证启动**

```bash
cd /home/admin/video-repurpose
pip3.12 install fastapi uvicorn aiofiles -i https://mirrors.aliyun.com/pypi/simple/
python3.12 -m uvicorn backend.main:app --host 0.0.0.0 --port 8200
# 访问 http://localhost:8200/api/health 应返回 {"status":"ok"}
```

---

## Task 2: 视频下载服务 (downloader.py)

**Objective:** 支持从抖音/视频号下载视频

**Files:**
- Create: `backend/services/__init__.py`
- Create: `backend/services/downloader.py`
- Create: `backend/api/video.py`
- Modify: `backend/main.py`

**核心逻辑:**

```python
# backend/services/downloader.py
import yt_dlp
import uuid
from pathlib import Path
from backend.config import UPLOAD_DIR

async def download_douyin(url: str) -> dict:
    """下载抖音视频，返回 {video_path, title, description}"""
    task_id = str(uuid.uuid4())[:8]
    output_path = UPLOAD_DIR / f"{task_id}.mp4"

    ydl_opts = {
        'outtmpl': str(output_path),
        'format': 'best',
        'quiet': True,
        'no_warnings': True,
        # 处理抖音重定向
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)',
        },
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return {
            "video_path": str(output_path),
            "title": info.get("title", ""),
            "description": info.get("description", ""),
            "duration": info.get("duration", 0),
        }

async def download_wechat_video(url: str) -> dict:
    """下载视频号 — 需要用浏览器抓取真实地址"""
    # 视频号没有直接URL，需要通过微信接口或Selenium获取
    # 暂用 httpx 模拟请求
    # TODO: 实现视频号下载（复杂，需要cookie/登录态）
    raise NotImplementedError("视频号下载需要额外配置微信登录态")
```

---

## Task 3: ASR 语音识别 (asr.py)

**Objective:** 用 faster-whisper 提取视频中的语音文字

**Files:**
- Create: `backend/services/asr.py`

**核心逻辑:**

```python
from faster_whisper import WhisperModel
from backend.config import ASR_MODEL_SIZE, ASR_DEVICE

model = None

def get_model():
    global model
    if model is None:
        model = WhisperModel(ASR_MODEL_SIZE, device=ASR_DEVICE, compute_type="float32")
    return model

async def transcribe(video_path: str) -> dict:
    """从视频提取音频并转文字"""
    m = get_model()
    segments, info = m.transcribe(video_path, language="zh", beam_size=5)
    
    full_text = ""
    segment_list = []
    for seg in segments:
        full_text += seg.text
        segment_list.append({
            "start": seg.start,
            "end": seg.end,
            "text": seg.text.strip(),
        })
    
    return {
        "language": info.language,
        "full_text": full_text.strip(),
        "segments": segment_list,
        "duration": info.duration,
    }
```

---

## Task 4: AI 文案改写 (rewriter.py)

**Objective:** 用 OpenRouter API 改写文案（换人物/换角度）

**Files:**
- Create: `backend/services/rewriter.py`

**核心逻辑:**

```python
import httpx
from backend.config import OPENROUTER_API_KEY, OPENROUTER_BASE_URL, REWRITE_MODEL

SYSTEM_PROMPT = """你是一个短视频文案改写专家。你的任务是：
1. 保持原视频的核心信息和情感
2. 更换人物名称、地点、具体细节
3. 换一个叙述角度重新表达
4. 保持口语化风格，适合短视频配音
5. 控制时长与原文基本一致（字数±10%）
6. 不要加任何前缀说明，直接输出改写后的文案"""

async def rewrite_text(original_text: str, style: str = "") -> str:
    """AI改写文案"""
    user_prompt = f"请改写以下短视频文案：\n\n{original_text}"
    if style:
        user_prompt += f"\n\n改写要求：{style}"

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            f"{OPENROUTER_BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": REWRITE_MODEL,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.8,
                "max_tokens": 2000,
            },
        )
        data = resp.json()
        return data["choices"][0]["message"]["content"].strip()
```

---

## Task 5: TTS 配音 (tts.py)

**Objective:** 用 edge-tts 生成中文配音

**Files:**
- Create: `backend/services/tts.py`

**核心逻辑:**

```python
import edge_tts
import uuid
from backend.config import OUTPUT_DIR, TTS_VOICE, TTS_VOICE_FEMALE

async def generate_tts(text: str, voice_gender: str = "male") -> str:
    """生成TTS配音音频"""
    voice = TTS_VOICE if voice_gender == "male" else TTS_VOICE_FEMALE
    output_path = OUTPUT_DIR / f"tts_{uuid.uuid4().hex[:8]}.mp3"
    
    communicate = edge_tts.Communicate(text, voice, rate="+0%")
    await communicate.save(str(output_path))
    
    return str(output_path)
```

---

## Task 6: 换脸服务 (face_swap.py)

**Objective:** 用 insightface 实现人脸替换

**Files:**
- Create: `backend/services/face_swap.py`

**核心逻辑:**

```python
import cv2
import numpy as np
from pathlib import Path

# insightface 换脸核心
# 需要先下载模型: ~/.insightface/models/buffalo_l/

async def extract_frames(video_path: str) -> tuple:
    """提取视频帧"""
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    frames = []
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frames.append(frame)
    cap.release()
    return frames, fps

async def face_swap_video(video_path: str, target_face_path: str) -> str:
    """对视频每一帧做换脸"""
    import insightface
    from insightface.app import FaceAnalysis
    
    app = FaceAnalysis(name='buffalo_l', providers=['CPUExecutionProvider'])
    app.prepare(ctx_id=0, det_size=(640, 640))
    
    # 加载目标人脸
    target_face_img = cv2.imread(target_face_path)
    target_faces = app.get(target_face_img)
    if not target_faces:
        raise ValueError("目标图片中未检测到人脸")
    target_face = target_faces[0]
    
    # 加载换脸模型
    swapper = insightface.model_zoo.get_model('inswapper_128.onnx')
    
    # 处理视频帧
    frames, fps = await extract_frames(video_path)
    swapped_frames = []
    
    for frame in frames:
        source_faces = app.get(frame)
        if source_faces:
            # 用最大的人脸做替换
            source_face = max(source_faces, key=lambda f: f.bbox[2]-f.bbox[0])
            frame = swapper.get(frame, source_face, target_face, paste_back=True)
        swapped_frames.append(frame)
    
    # 写回视频
    output_path = video_path.replace('.mp4', '_swapped.mp4')
    h, w = swapped_frames[0].shape[:2]
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    writer = cv2.VideoWriter(output_path, fourcc, fps, (w, h))
    for f in swapped_frames:
        writer.write(f)
    writer.release()
    
    return output_path
```

---

## Task 7: 视频合成 (compositor.py)

**Objective:** 把新配音 + 原画面（或换脸画面）合成最终视频

**Files:**
- Create: `backend/services/compositor.py`

**核心逻辑:**

```python
import subprocess
import uuid
from backend.config import OUTPUT_DIR

async def composite_video(
    video_path: str,
    audio_path: str,
    face_swapped: bool = False,
) -> str:
    """合成最终视频：替换音频轨道"""
    source = video_path.replace('.mp4', '_swapped.mp4') if face_swapped else video_path
    output_path = str(OUTPUT_DIR / f"final_{uuid.uuid4().hex[:8]}.mp4")
    
    # 用 ffmpeg 替换音频，保留原始视频
    cmd = [
        'ffmpeg', '-y',
        '-i', source,           # 视频源
        '-i', audio_path,       # 新音频
        '-map', '0:v',          # 取原视频轨
        '-map', '1:a',          # 取新音频轨
        '-c:v', 'copy',         # 视频直接复制
        '-c:a', 'aac',          # 音频编码AAC
        '-shortest',            # 以短的为准
        '-movflags', '+faststart',
        output_path,
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg合成失败: {result.stderr}")
    
    return output_path
```

---

## Task 8: 处理流水线 API (pipeline.py)

**Objective:** 串联所有服务，提供一键处理接口

**Files:**
- Create: `backend/api/pipeline.py`
- Modify: `backend/main.py` (注册路由)

**核心逻辑:**

```python
# backend/api/pipeline.py
from fastapi import APIRouter, BackgroundTasks
from backend.models.schemas import VideoRequest, TaskProgress, TaskStatus
from backend.services import downloader, asr, rewriter, tts, compositor
import asyncio

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
        if req.platform == "douyin":
            video_info = await downloader.download_douyin(req.url)
        else:
            video_info = await downloader.download_wechat_video(req.url)
        
        # 2. ASR
        progress.status = TaskStatus.TRANSCRIBING
        progress.message = "正在识别语音..."
        progress.progress = 30
        asr_result = await asr.transcribe(video_info["video_path"])
        progress.original_text = asr_result["full_text"]
        
        # 3. AI改写
        progress.status = TaskStatus.REWRITING
        progress.message = "正在改写文案..."
        progress.progress = 50
        rewritten = await rewriter.rewrite_text(asr_result["full_text"], req.rewrite_style)
        progress.rewritten_text = rewritten
        
        # 4. TTS配音
        progress.status = TaskStatus.GENERATING_TTS
        progress.message = "正在生成配音..."
        progress.progress = 65
        audio_path = await tts.generate_tts(rewritten, req.voice_gender)
        
        # 5. 换脸（可选）
        face_video = video_info["video_path"]
        if req.face_image:
            progress.status = TaskStatus.FACESWAPPING
            progress.message = "正在换脸..."
            progress.progress = 75
            from backend.services import face_swap
            face_video = await face_swap.face_swap_video(
                video_info["video_path"], req.face_image
            )
        
        # 6. 合成
        progress.status = TaskStatus.COMPOSITING
        progress.message = "正在合成视频..."
        progress.progress = 90
        final_path = await compositor.composite_video(
            face_video, audio_path, face_swapped=bool(req.face_image)
        )
        
        progress.status = TaskStatus.DONE
        progress.progress = 100
        progress.message = "处理完成！"
        progress.output_video = final_path
        
    except Exception as e:
        progress.status = TaskStatus.FAILED
        progress.message = f"处理失败: {str(e)}"

@router.post("/start")
async def start_pipeline(req: VideoRequest, bg: BackgroundTasks):
    import uuid
    task_id = str(uuid.uuid4())[:8]
    tasks[task_id] = TaskProgress(task_id=task_id, status=TaskStatus.PENDING)
    bg.add_task(run_pipeline, task_id, req)
    return {"task_id": task_id}

@router.get("/status/{task_id}")
async def get_status(task_id: str):
    if task_id not in tasks:
        return {"error": "任务不存在"}
    return tasks[task_id]
```

---

## Task 9: 前端 Web 界面

**Objective:** 简洁的单页操作界面

**Files:**
- Create: `frontend/index.html`
- Create: `frontend/css/style.css`
- Create: `frontend/js/app.js`

**前端功能:**
- 输入视频链接
- 选择平台（抖音/视频号）
- 选择配音性别
- 上传换脸图片（可选）
- 自定义改写风格
- 实时显示处理进度
- 展示原文 vs 改写文案对比
- 下载最终视频

---

## Task 10: 发布服务（可选扩展）

**Objective:** 自动发布到抖音/视频号

**注意:** 抖音和视频号没有公开的视频发布 API，需要：
- 方案A: Selenium/Playwright 浏览器自动化
- 方案B: 使用抖音开放平台（需要企业资质）
- 方案C: 先做"下载到本地"，用户手动上传

**建议:** 先实现方案C，后续根据需求扩展

---

## 实施顺序

1. ✅ Task 1: 项目初始化
2. ✅ Task 2: 视频下载
3. ✅ Task 3: ASR 识别
4. ✅ Task 4: AI 改写
5. ✅ Task 5: TTS 配音
6. ✅ Task 6: 换脸（可选）
7. ✅ Task 7: 视频合成
8. ✅ Task 8: 流水线 API
9. ✅ Task 9: 前端界面
10. ✅ Task 10: 发布（后续扩展）
