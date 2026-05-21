"""AI 文案改写服务 — OpenRouter"""

import httpx
from backend.config import OPENROUTER_API_KEY, OPENROUTER_BASE_URL, REWRITE_MODEL

SYSTEM_PROMPT = """你是一个短视频文案改写专家。你的任务是：
1. 保持原视频的核心信息和情感
2. 更换人物名称、地点、具体细节
3. 换一个叙述角度重新表达
4. 保持口语化风格，适合短视频配音
5. 控制时长与原文基本一致（字数±10%）
6. 不要加任何前缀说明，直接输出改写后的文案
7. 不要用引号包裹，直接输出纯文本"""


async def rewrite_text(original_text: str, style: str = "") -> str:
    """AI改写文案"""
    user_prompt = f"请改写以下短视频文案：\n\n{original_text}"
    if style:
        user_prompt += f"\n\n改写要求：{style}"

    async with httpx.AsyncClient(timeout=120) as client:
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
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        return content.strip().strip('"').strip('"').strip('"')
