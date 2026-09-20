"""
Discord LLM Bot 전역 상수 모듈

이 모듈은 LLM 기본 파라미터 및 챗봇 기본 프롬프트 설정을 관리합니다.
"""

from typing import Dict, Any

import os

PARAMS: Dict[str, Any] = {
    "model": os.getenv("OLLAMA_MODEL", "qwen2.5:7b"),
    "max_tokens": 500,
    "temperature": 0.7,
    "top_p": 0.9,
    "stop": None,
    "stream": False,
}


# 디폴트 챗봇 이름
DEFAULT_BOT_NAME: str = "Assistant"

# 디폴트 챗봇 지침 프롬프트
DEFAULT_BOT_INSTRUCTIONS: str = (
    "친절한 챗봇으로서 상대방의 요청에 최대한 자세하고 친절하게 답하자. "
    "모든 대답은 한국어(Korean)으로 대답해줘."
)