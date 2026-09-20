"""
LLM 프로바이더 로더 모듈

환경변수(LLM_PROVIDER) 설정에 따라 알맞은 LLM 객체를 동적으로 생성하여 로드합니다.
"""

import os
from typing import Dict, Type
from dotenv import load_dotenv

from llm.base_llm import BaseLLM
from llm.llms.open_ai import OpenAI
from util.logger import logger

load_dotenv()

LLM_MAP: Dict[str, Type[BaseLLM]] = {
    "openai": OpenAI,
}


def load_llm() -> BaseLLM:
    """설정된 LLM 프로바이더 인스턴스를 반환합니다.

    환경 변수 `LLM_PROVIDER` (기본값: 'openai')를 읽어 해당 프로바이더 클래스를 인스턴스화합니다.

    Returns:
        BaseLLM: 구현된 LLM 객체

    Raises:
        ValueError: 지원하지 않는 LLM_PROVIDER 지정 시 발생
    """
    provider: str = os.getenv("LLM_PROVIDER", "openai").lower()

    if provider not in LLM_MAP:
        logger.error(f"지원하지 않는 LLM provider입니다: '{provider}'")
        raise ValueError(f"Unknown LLM provider: {provider}")

    logger.info(f"LLM 프로바이더 로드 완료: '{provider}'")
    return LLM_MAP[provider]()

