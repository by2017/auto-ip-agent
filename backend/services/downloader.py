"""视频下载服务 — 支持抖音/视频号"""

import uuid
import re
import yt_dlp
from pathlib import Path
from backend.config import UPLOAD_DIR


async def download_douyin(url: str) -> dict:
    """下载抖音视频"""
    task_id = str(uuid.uuid4())[:8]
    output_path = UPLOAD_DIR / f"{task_id}.mp4"

    ydl_opts = {
        "outtmpl": str(output_path),
        "format": "best",
        "quiet": True,
        "no_warnings": True,
        "http_headers": {
            "User-Agent": (
                "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) "
                "AppleWebKit/605.1.15 (KHTML, like Gecko) "
                "Version/16.6 Mobile/15E148 Safari/604.1"
            ),
        },
        "socket_timeout": 30,
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
    """下载视频号视频 — 需要真实视频地址"""
    # 视频号链接通常是 https://channels.weixin.qq.com/...
    # 需要从页面中提取视频URL
    import httpx

    task_id = str(uuid.uuid4())[:8]
    output_path = UPLOAD_DIR / f"{task_id}.mp4"

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
        )
    }

    async with httpx.AsyncClient(follow_redirects=True, timeout=30) as client:
        resp = await client.get(url, headers=headers)
        html = resp.text

    # 尝试从页面提取视频URL
    video_url = None
    patterns = [
        r'"url"\s*:\s*"(https?://[^"]+\.mp4[^"]*)"',
        r'"videoUrl"\s*:\s*"(https?://[^"]+)"',
        r'src="(https?://[^"]+\.mp4[^"]*)"',
    ]
    for pat in patterns:
        m = re.search(pat, html)
        if m:
            video_url = m.group(1).replace("\\u002F", "/")
            break

    if not video_url:
        raise ValueError(
            "无法从视频号页面提取视频地址。"
            "视频号需要微信登录态，请直接上传视频文件。"
        )

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.get(video_url, headers=headers)
        output_path.write_bytes(resp.content)

    return {
        "video_path": str(output_path),
        "title": "",
        "description": "",
        "duration": 0,
    }


async def download_video(url: str, platform: str) -> dict:
    """统一下载入口"""
    if platform == "douyin":
        return await download_douyin(url)
    elif platform == "wechat_video":
        return await download_wechat_video(url)
    else:
        raise ValueError(f"不支持的平台: {platform}")
