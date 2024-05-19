import os
from dotenv import load_dotenv

from llm.base_llm import BaseLLM
from llm.llms.open_ai import OpenAI
# from llm.llms.text_generation_web_ui import TextGenerationWebUI

load_dotenv()

llm_dict = {
    "openai": OpenAI,
    # "text_generation_web_ui": TextGenerationWebUI,
}


def load_llm() -> BaseLLM:
    provider = os.getenv("LLM_PROVIDER")

    if provider not in llm_dict:
        raise ValueError(f"Unknown LLM provider: {provider}")

    return llm_dict[provider]()
