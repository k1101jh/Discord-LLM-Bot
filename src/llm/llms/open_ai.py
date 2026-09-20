"""
OpenAI 호환 API 기반 LLM 프로바이더 모듈

Ollama 또는 OpenAI 호환 REST API 서버를 호출하는 LLM 클래스입니다.
"""

import os
from typing import List, Dict, Any, Optional
import openai

from llm.base_llm import BaseLLM
from database.database import MessageData
from constants import PARAMS
from util.logger import wrap_log, logger


class OpenAI(BaseLLM):
    """OpenAI API 규격을 준수하는 LLM 구현 클래스"""

    def __init__(self) -> None:
        """OpenAI 클라이언트를 초기화합니다."""
        super().__init__()
        self.name: str = "AI"
        base_url: str = os.getenv("OPENAI_API_BASE", "http://localhost:11434/v1")
        api_key: str = os.getenv("OPENAI_API_KEY", "ollama")
        timeout: float = float(os.getenv("OPENAI_TIMEOUT", "30.0"))

        self.client: openai.OpenAI = openai.OpenAI(
            base_url=base_url,
            api_key=api_key,
            timeout=timeout,
        )
        logger.info(f"OpenAI 클라이언트 초기화 완료 (base_url='{base_url}')")

    def set_name(self, new_name: str) -> None:
        """챗봇의 이름을 변경합니다.

        Args:
            new_name (str): 새로 설정할 이름
        """
        if new_name in ("user", "system"):
            logger.warning("AI의 이름은 'user' 또는 'system'일 수 없습니다.")
            return
        self.name = new_name

    @wrap_log
    def get_available_models(self) -> List[str]:
        """Ollama/OpenAI API 서버에서 현재 사용 가능한 LLM 모델 목록을 동적으로 조회합니다.

        Returns:
            List[str]: 모델 ID 목록
        """
        try:
            models_page = self.client.models.list()
            model_list: List[str] = [model.id for model in models_page.data]
            return model_list
        except Exception as e:
            logger.error(f"모델 목록 조회 실패: {e}")
            default_model = PARAMS.get("model", "qwen2.5:7b")
            return [default_model]

    @wrap_log
    def create(self, prompt: str, chat_messages: List[MessageData], model_name: Optional[str] = None) -> str:
        """프롬프트와 메시지 이력을 바탕으로 텍스트 응답을 생성합니다.

        Args:
            prompt (str): 시스템 프롬프트 지침
            chat_messages (List[MessageData]): 이전 대화 메시지 이력 목록
            model_name (Optional[str]): 사용할 특정한 모델명 (None일 경우 기본 모델 사용)

        Returns:
            str: 생성을 완료한 답변 문자열
        """
        messages: List[Dict[str, str]] = [
            {"role": "system", "content": prompt},
        ]

        for message in chat_messages:
            role = "assistant" if message.author in ("assistant", self.name) else "user"
            messages.append({"role": role, "content": message.content})

        params = PARAMS.copy()
        if model_name:
            params["model"] = model_name

        response = self.client.chat.completions.create(
            messages=messages,
            **params,
        )
        msg_obj = response.choices[0].message
        content: str = (
            getattr(msg_obj, "content", None)
            or getattr(msg_obj, "reasoning_content", None)
            or getattr(msg_obj, "thinking", None)
            or ""
        )
        return content.strip()


