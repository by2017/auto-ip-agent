import os
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
OUTPUT_DIR = DATA_DIR / "outputs"
FACES_DIR = DATA_DIR / "faces"
COVERS_DIR = DATA_DIR / "covers"

for d in [UPLOAD_DIR, OUTPUT_DIR, FACES_DIR, COVERS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# AI
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
REWRITE_MODEL = os.getenv("REWRITE_MODEL", "openai/gpt-4o-mini")

# TTS
TTS_VOICE_MALE = "zh-CN-YunxiNeural"
TTS_VOICE_FEMALE = "zh-CN-XiaoxiaoNeural"

# 可用音色列表
TTS_VOICES = [
    {"id": "zh-CN-YunxiNeural", "name": "云希", "gender": "male", "style": "自然亲切"},
    {"id": "zh-CN-YunjianNeural", "name": "云健", "gender": "male", "style": "沉稳正式"},
    {"id": "zh-CN-YunyangNeural", "name": "云扬", "gender": "male", "style": "新闻播报"},
    {"id": "zh-CN-XiaoxiaoNeural", "name": "晓晓", "gender": "female", "style": "温柔甜美"},
    {"id": "zh-CN-XiaoyiNeural", "name": "晓依", "gender": "female", "style": "活泼年轻"},
    {"id": "zh-CN-XiaochenNeural", "name": "晓辰", "gender": "female", "style": "成熟知性"},
    {"id": "zh-CN-XiaohanNeural", "name": "晓涵", "gender": "female", "style": "温暖亲切"},
    {"id": "zh-CN-XiaomengNeural", "name": "晓梦", "gender": "female", "style": "甜美可爱"},
    {"id": "zh-CN-XiaomoNeural", "name": "晓墨", "gender": "female", "style": "文艺优雅"},
    {"id": "zh-CN-XiaoxuanNeural", "name": "晓萱", "gender": "female", "style": "活力阳光"},
]

# ASR
ASR_MODEL_SIZE = os.getenv("ASR_MODEL_SIZE", "large-v3")
ASR_DEVICE = os.getenv("ASR_DEVICE", "cpu")

# Server
HOST = "0.0.0.0"
PORT = 8200
