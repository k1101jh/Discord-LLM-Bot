import os
import openai

from typing import Union, Optional, List
from dataclasses import dataclass
from llm.base_llm import BaseLLM
from database.database import ChatDatabase
from database.database import ChatData
from database.database import MessageData
from params import params
from util.logger import wrap_log, logger
    

class OpenAI:
    def __init__(self):
        super().__init__()
        self.name = "AI"
        self.__prompt = "친절한 챗봇으로서 상대방의 요청에 최대한 자세하고 친절하게 답하자. 모든 대답은 한국어(Korean)으로 대답해줘."
        self.client = openai.OpenAI(base_url=os.getenv("OPENAI_API_BASE"), api_key=os.getenv("OPENAI_API_KEY"), timeout=10)
        
        print(os.getenv("OPENAI_API_BASE"))
        
    @property
    def prompt(self):
        return self.__prompt

    @prompt.setter
    def prompt(self, prompt):
        self.__prompt = prompt
        
    def set_name(self, new_name):
        """
        추후 wrapper로 감싸기
        - 에러를 디스코드 메시지로 출력하도록
        """
        try:
            assert new_name != "user" or new_name != "system"
            self.name = new_name
        except AssertionError:
            print(AssertionError("AI의 이름은 'user' 또는 'system'일 수 없습니다."))
            
    @wrap_log
    def create(self, chat_messages: List[MessageData]) -> str:
        messages = [
            {"role": "system", "content": f"{self.__prompt}"},
        ]
        
        messages += [{"role": "manager" if message.author == "assistant" else "user", "content": message.content} for message in chat_messages]            
        
        response = self.client.chat.completions.create(
            messages=messages,
            **params,
        )
        return response.choices[0].message.content.strip()