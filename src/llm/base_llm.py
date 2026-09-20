"""
LLM 추상 베이스 클래스 모듈

다양한 LLM 프로바이더(OpenAI, Ollama 등)를 통일된 인터페이스로 다루기 위한 추상 클래스 정의입니다.
"""

from abc import ABC, abstractmethod
from typing import List
from database.database import MessageData


class BaseLLM(ABC):
    """LLM 프로바이더 추상 베이스 클래스"""

    @abstractmethod
    def create(self, prompt: str, chat_messages: List[MessageData]) -> str:
        """프롬프트와 메시지 이력을 기반으로 LLM 응답을 생성합니다.

        Args:
            prompt (str): 시스템 프롬프트 지침
            chat_messages (List[MessageData]): 이전 대화 메시지 이력 목록

        Returns:
            str: LLM이 생성한 응답 텍스트
        """
        raise NotImplementedError


