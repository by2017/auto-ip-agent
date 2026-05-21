# 📖 短视频搬运工作流 — 操作手册

## 目录

1. [首次部署](#1-首次部署)
2. [日常使用](#2-日常使用)
3. [高级配置](#3-高级配置)
4. [故障排除](#4-故障排除)
5. [维护与更新](#5-维护与更新)

---

## 1. 首次部署

### 1.1 服务器环境检查

```bash
# 确认 Python 版本
python3.12 --version   # 需要 3.12+

# 确认 FFmpeg
ffmpeg -version        # 需要 4.x+

# 确认 yt-dlp
yt-dlp --version       # 需要 2024.0+
```

### 1.2 安装项目依赖

```bash
cd /home/admin/video-repurpose

# 核心依赖（必装）
pip install fastapi uvicorn python-multipart httpx aiofiles edge-tts yt-dlp numpy Pillow opencv-python-headless

# ASR 语音识别（可选但推荐）
pip install faster-whisper

# 换脸功能（可选，较大）
pip install insightface onnxruntime moviepy
```

> ⚠️ 国内服务器建议使用镜像：
> `pip install xxx -i https://mirrors.aliyun.com/pypi/simple/`

### 1.3 配置 API Key

```bash
# OpenRouter API Key（用于 AI 文案改写）
echo 'export OPENROUTER_API_KEY="sk-你的key"' >> ~/.bashrc
source ~/.bashrc
```

### 1.4 首次启动

```bash
cd /home/admin/video-repurpose
python3.12 run.py
```

看到以下输出表示启动成功：
```
INFO:     Started server process [xxx]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8200
```

### 1.5 设为后台服务（可选）

创建 systemd 服务：

```bash
sudo tee /etc/systemd/system/video-repurpose.service << 'EOF'
[Unit]
Description=短视频搬运工作流
After=network.target

[Service]
Type=simple
User=admin
WorkingDirectory=/home/admin/video-repurpose
Environment=OPENROUTER_API_KEY=sk-你的key
ExecStart=/home/admin/.agent-reach-venv/bin/python3.12 run.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable video-repurpose
sudo systemctl start video-repurpose
```

---

## 2. 日常使用

### 2.1 处理抖音视频

1. 打开浏览器访问 `http://<服务器IP>:8200/`
2. 在「视频链接」框粘贴抖音视频链接
3. 来源平台选择「抖音」
4. 选择配音性别（男声/女声）
5. 修改改写风格（可选）
6. 点击「🚀 开始处理」

### 2.2 添加换脸

1. 点击「📸 点击上传换脸目标图片」
2. 选择一张包含清晰正面人脸的图片
3. 图片上传成功后会显示预览
4. 点击「🚀 开始处理」

> 💡 换脸会大幅增加处理时间，建议视频时长 < 60 秒

### 2.3 查看结果

处理完成后页面会显示：
- **📝 原始文案**：从视频中识别出的原始语音文字
- **✍️ 改写文案**：AI 改写后的新文案
- **⬇️ 下载视频**：点击下载合成后的新视频

### 2.4 处理流程说明

| 阶段 | 耗时（1分钟视频） | 说明 |
|------|-------------------|------|
| 📥 下载视频 | 5-30s | 取决于视频大小和网速 |
| 🎤 语音识别 | 30-120s | CPU 较慢，GPU 很快 |
| ✍️ AI改写 | 5-15s | 调用 OpenRouter API |
| 🔊 TTS配音 | 3-10s | edge-tts 在线合成 |
| 👤 换脸 | 5-30min | 逐帧处理，非常慢 |
| 🎬 合成视频 | 5-30s | FFmpeg 替换音轨 |

---

## 3. 高级配置

### 3.1 修改 ASR 模型

```bash
# 小模型（快但不准）
export ASR_MODEL_SIZE="tiny"

# 中等模型（平衡）
export ASR_MODEL_SIZE="medium"

# 大模型（准但慢）
export ASR_MODEL_SIZE="large-v3"
```

### 3.2 使用 GPU 加速

```bash
# 安装 CUDA 版本的 onnxruntime
pip install onnxruntime-gpu

# 设置设备
export ASR_DEVICE="cuda"
```

### 3.3 切换 AI 模型

```bash
# 使用 GPT-4o（更贵但更好）
export REWRITE_MODEL="openai/gpt-4o"

# 使用 Claude
export REWRITE_MODEL="anthropic/claude-haiku-latest"

# 使用免费模型
export REWRITE_MODEL="baidu/cobuddy:free"
```

### 3.4 自定义 TTS 声音

修改 `run.py` 中的 voice 变量，或设置环境变量：

```bash
# 查看所有可用中文声音
python3.12 -c "
import asyncio, edge_tts
async def main():
    voices = await edge_tts.list_voices()
    for v in voices:
        if v['Locale'].startswith('zh-'):
            print(f\"{v['ShortName']:30s} {v['Gender']:8s} {v.get('FriendlyName', '')}\")
asyncio.run(main())
"
```

### 3.5 同时处理多个视频

直接开多个浏览器标签页，每个标签页提交一个任务。后端是异步的，支持并发。

---

## 4. 故障排除

### 4.1 服务启动失败

```bash
# 检查端口是否被占用
lsof -i :8200

# 查看错误日志
python3.12 run.py 2>&1 | tee /tmp/video-repurpose.log
```

### 4.2 视频下载失败

| 错误 | 原因 | 解决方案 |
|------|------|----------|
| `Unable to download` | 链接无效或已删除 | 检查链接是否可访问 |
| `HTTP Error 403` | 需要登录 | 配置 yt-dlp cookie |
| `No video formats` | 视频号链接 | 视频号暂不支持直接下载 |

### 4.3 ASR 识别失败

```bash
# 测试 faster-whisper 是否正常
python3.12 -c "
from faster_whisper import WhisperModel
model = WhisperModel('tiny', device='cpu', compute_type='float32')
segments, info = model.transcribe('/home/admin/video-repurpose/data/uploads/xxx.mp4')
for s in segments:
    print(s.text)
"
```

### 4.4 AI 改写失败

```bash
# 测试 API Key 是否有效
curl -s https://openrouter.ai/api/v1/models \
  -H "Authorization: Bearer $OPENROUTER_API_KEY" | head -c 100
```

### 4.5 TTS 配音失败

```bash
# 测试 edge-tts
python3.12 -c "
import asyncio, edge_tts
async def test():
    c = edge_tts.Communicate('你好世界', 'zh-CN-YunxiNeural')
    await c.save('/tmp/test.mp3')
    print('OK')
asyncio.run(test())
"
```

### 4.6 换脸报错

```bash
# 检查模型是否下载
ls ~/.insightface/models/buffalo_l/

# 手动下载模型
python3.12 -c "
from insightface.app import FaceAnalysis
app = FaceAnalysis(name='buffalo_l', providers=['CPUExecutionProvider'])
app.prepare(ctx_id=0, det_size=(640, 640))
print('OK')
"
```

---

## 5. 维护与更新

### 5.1 清理临时文件

```bash
# 清理超过 7 天的视频文件
find /home/admin/video-repurpose/data/ -name "*.mp4" -mtime +7 -delete
find /home/admin/video-repurpose/data/ -name "*.mp3" -mtime +7 -delete
find /home/admin/video-repurpose/data/ -name "*.wav" -mtime +7 -delete
```

### 5.2 更新 yt-dlp

```bash
# yt-dlp 经常需要更新以支持最新平台
pip install -U yt-dlp
```

### 5.3 备份配置

```bash
# 需要备份的文件
cp /home/admin/video-repurpose/run.py /home/admin/video-repurpose/run.py.bak
cp /home/admin/video-repurpose/backend/config.py /tmp/config.py.bak
```

### 5.4 查看运行日志

```bash
# systemd 方式
journalctl -u video-repurpose -f

# 直接运行方式
# 日志输出在终端
```

---

## 附录：完整处理流程图

```
用户输入视频URL
      │
      ▼
┌─────────────┐
│  yt-dlp下载  │  ← 抖音/视频号
└──────┬──────┘
       ▼
┌─────────────┐
│  FFmpeg提取  │  ← 提取音频
│    音频      │
└──────┬──────┘
       ▼
┌─────────────┐
│  Whisper ASR │  ← 语音转文字
│   语音识别    │
└──────┬──────┘
       ▼
┌─────────────┐
│  OpenRouter  │  ← AI改写文案
│   AI改写     │
└──────┬──────┘
       ▼
┌─────────────┐
│  edge-tts    │  ← 文字转语音
│   TTS配音    │
└──────┬──────┘
       ▼
┌─────────────┐     ┌──────────┐
│  可选：换脸  │ ←── │ 人脸图片  │
│  insightface │     └──────────┘
└──────┬──────┘
       ▼
┌─────────────┐
│  FFmpeg合成  │  ← 替换音轨
│   最终视频    │
└──────┬──────┘
       ▼
   下载/发布
```
