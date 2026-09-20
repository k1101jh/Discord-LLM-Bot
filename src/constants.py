"""
Discord LLM Bot 전역 상수 모듈

이 모듈은 LLM 기본 파라미터 및 챗봇 기본 프롬프트 설정을 관리합니다.
"""

import os
from typing import Dict, Any
from omegaconf import OmegaConf


# config/prompts.yaml 로드 시도
config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "prompts.yaml")
loaded_config = None

if os.path.exists(config_path):
    try:
        loaded_config = OmegaConf.load(config_path)
    except Exception:
        loaded_config = None

bot_cfg = loaded_config.get("bot_settings", {}) if loaded_config else {}
llm_cfg = loaded_config.get("llm_parameters", {}) if loaded_config else {}

# 디폴트 챗봇 이름
DEFAULT_BOT_NAME: str = str(bot_cfg.get("name", "Assistant"))

# 디폴트 챗봇 지침 프롬프트 (YAML 파일에서 편리하게 수정 가능)
DEFAULT_BOT_INSTRUCTIONS: str = str(
    bot_cfg.get(
        "default_instructions",
        "친절한 챗봇으로서 상대방의 요청에 최대한 자세하고 친절하게 답하자. 모든 대답은 한국어(Korean)으로 대답해 줘.",
    )
).strip()

PARAMS: Dict[str, Any] = {
    "model": os.getenv("OLLAMA_MODEL", "gemma4:12b"),
    "max_tokens": int(llm_cfg.get("max_tokens", 500)),
    "temperature": float(llm_cfg.get("temperature", 0.7)),
    "top_p": float(llm_cfg.get("top_p", 0.9)),
    "stop": None,
    "stream": False,
}