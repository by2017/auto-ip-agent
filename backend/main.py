"""短视频搬运工作流 — FastAPI 入口"""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

app = FastAPI(title="短视频搬运工作流", version="2.0.0")

# 挂载静态文件
FRONTEND_DIR = Path(__file__).parent.parent / "frontend"
DATA_DIR = Path(__file__).parent.parent / "data"

app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")
app.mount("/data", StaticFiles(directory=str(DATA_DIR)), name="data")

# 注册路由
from backend.api.pipeline import router as pipeline_router
from backend.api.steps import router as steps_router
app.include_router(pipeline_router, prefix="/api/pipeline")
app.include_router(steps_router, prefix="/api/steps")


@app.get("/")
async def index():
    return FileResponse(str(FRONTEND_DIR / "index.html"))


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "短视频搬运工作流", "version": "2.0.0"}
