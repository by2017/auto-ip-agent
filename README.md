# 🎬 短视频搬运工作流 (Video Repurpose)

一键式短视频搬运工具：输入视频链接 → AI解析文案 → 智能改写 → TTS配音 → 换脸 → 合成新视频

## 功能特性

| 功能 | 说明 | 技术方案 |
|------|------|----------|
| 📥 视频下载 | 抖音/视频号链接解析下载 | yt-dlp |
| 🎤 语音识别 | 视频语音转文字 | faster-whisper (large-v3) |
| ✍️ AI改写 | 智能改写文案，换人物/角度 | OpenRouter API (GPT-4o-mini) |
| 🔊 TTS配音 | 中文男声/女声配音 | edge-tts (微软免费) |
| 👤 换脸 | 替换视频中的人脸 | insightface + inswapper |
| 🎬 视频合成 | 自动合成最终视频 | FFmpeg |
| 🌐 Web界面 | 暗色主题单页操作 | FastAPI + 原生HTML/CSS/JS |

## 快速开始

### 1. 环境要求

- Python 3.12+
- FFmpeg 4.x+
- Linux (推荐 Ubuntu 20.04+)

### 2. 安装依赖

```bash
cd /home/admin/video-repurpose
pip install -r requirements.txt
```

### 3. 配置环境变量

```bash
export OPENROUTER_API_KEY="sk-xxx"   # OpenRouter API Key（用于AI改写）
export ASR_MODEL_SIZE="large-v3"      # ASR模型大小: tiny/base/small/medium/large-v3
export ASR_DEVICE="cpu"               # 推理设备: cpu / cuda
export REWRITE_MODEL="openai/gpt-4o-mini"  # 改写用的模型
```

### 4. 启动服务

```bash
# 方式一：轻量启动（推荐）
cd /home/admin/video-repurpose
OPENROUTER_API_KEY=sk-xxx python3.12 run.py

# 方式二：模块化启动
OPENROUTER_API_KEY=sk-xxx python3.12 -m uvicorn backend.main:app --host 0.0.0.0 --port 8200
```

访问 `http://<服务器IP>:8200/`

### 5. 使用流程

1. 在浏览器打开 Web 界面
2. 粘贴抖音/视频号视频链接
3. 选择来源平台、配音性别
4. 自定义改写风格（可选）
5. 上传换脸目标图片（可选）
6. 点击"🚀 开始处理"
7. 实时查看进度：下载 → 识别 → 改写 → 配音 → 合成
8. 对比查看原文 vs 改写文案
9. 下载最终视频

## 项目结构

```
video-repurpose/
├── run.py                      # 轻量版启动入口（推荐）
├── PLAN.md                     # 详细实施计划
├── README.md                   # 本文件
├── requirements.txt            # Python 依赖
├── backend/
│   ├── main.py                 # 模块化 FastAPI 入口
│   ├── config.py               # 配置管理
│   ├── api/
│   │   └── pipeline.py         # 处理流水线 API
│   ├── services/
│   │   ├── downloader.py       # 视频下载（抖音/视频号）
│   │   ├── asr.py              # ASR 语音识别
│   │   ├── rewriter.py         # AI 文案改写
│   │   ├── tts.py              # TTS 配音
│   │   ├── face_swap.py        # 换脸服务
│   │   └── compositor.py       # 视频合成
│   └── models/
│       └── schemas.py          # Pydantic 数据模型
├── frontend/
│   ├── index.html              # 主页面
│   ├── css/style.css           # 样式
│   └── js/app.js               # 前端逻辑
└── data/
    ├── uploads/                # 原始视频
    ├── outputs/                # 输出视频 + 音频
    └── faces/                  # 换脸素材图片
```

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/` | Web 界面 |
| GET | `/api/health` | 健康检查 |
| POST | `/api/pipeline/start` | 启动处理流水线 |
| GET | `/api/pipeline/status/{task_id}` | 查询任务状态 |
| POST | `/api/pipeline/upload-face` | 上传换脸图片 |
| GET | `/api/pipeline/tasks` | 列出所有任务 |

### 启动流水线示例

```bash
curl -X POST http://localhost:8200/api/pipeline/start \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.douyin.com/video/xxx",
    "platform": "douyin",
    "rewrite_style": "保持原意，换个角度重新表述",
    "voice_gender": "male"
  }'
```

返回：`{"task_id": "a1b2c3d4"}`

### 查询状态示例

```bash
curl http://localhost:8200/api/pipeline/status/a1b2c3d4
```

返回：

```json
{
  "task_id": "a1b2c3d4",
  "status": "done",
  "progress": 100,
  "message": "✅ 处理完成！",
  "original_text": "原始语音文案...",
  "rewritten_text": "AI改写后的文案...",
  "output_video": "/path/to/final_a1b2c3d4.mp4"
}
```

## 配置说明

| 环境变量 | 默认值 | 说明 |
|----------|--------|------|
| `OPENROUTER_API_KEY` | (无) | OpenRouter API Key，用于 AI 文案改写 |
| `REWRITE_MODEL` | `openai/gpt-4o-mini` | 改写使用的模型 |
| `ASR_MODEL_SIZE` | `large-v3` | Whisper 模型大小 |
| `ASR_DEVICE` | `cpu` | 推理设备，有 GPU 设为 `cuda` |
| `TTS_VOICE_MALE` | `zh-CN-YunxiNeural` | 男声 TTS |
| `TTS_VOICE_FEMALE` | `zh-CN-XiaoxiaoNeural` | 女声 TTS |

### 可用的 edge-tts 中文声音

| 声音ID | 性别 | 风格 |
|--------|------|------|
| `zh-CN-YunxiNeural` | 男 | 年轻，适合讲故事 |
| `zh-CN-YunjianNeural` | 男 | 成熟，适合新闻 |
| `zh-CN-XiaoxiaoNeural` | 女 | 甜美，适合生活类 |
| `zh-CN-XiaoyiNeural` | 女 | 活泼，适合娱乐类 |

## 换脸说明

1. 准备一张包含清晰正面人脸的图片
2. 在 Web 界面上传该图片
3. 系统会自动检测人脸并替换视频中的所有人脸
4. 注意：换脸处理较慢（逐帧处理），建议短视频（<60s）

首次使用需要下载 insightface 模型（约 300MB）：

```bash
python3.12 -c "
from insightface.app import FaceAnalysis
app = FaceAnalysis(name='buffalo_l', providers=['CPUExecutionProvider'])
app.prepare(ctx_id=0, det_size=(640, 640))
print('模型下载完成')
"
```

## 常见问题

**Q: 抖音链接下载失败？**
A: 确保链接是完整的分享链接或网页链接。短链接会自动重定向。部分受限视频可能需要 cookie。

**Q: 视频号下载不了？**
A: 视频号需要微信登录态，目前建议直接上传视频文件（后续版本支持）。

**Q: ASR 识别不准？**
A: 使用 `large-v3` 模型效果最好但较慢。如果视频噪音大，可先用 FFmpeg 降噪：
```bash
ffmpeg -i input.mp4 -af "highpass=f=200,lowpass=f=3000" clean.mp4
```

**Q: 如何使用 GPU 加速？**
A: 设置 `ASR_DEVICE=cuda`，需要安装 CUDA 版本的 onnxruntime：
```bash
pip install onnxruntime-gpu
```

**Q: 换脸效果不好？**
A: 确保目标图片人脸清晰、正面、光线均匀。视频中人脸越大效果越好。

## License

MIT
