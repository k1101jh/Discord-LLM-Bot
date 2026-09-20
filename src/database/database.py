"""
MongoDB 데이터베이스 관리 모듈

디스코드 챗봇의 채팅 세션 및 메시지 이력을 MongoDB에 저장하고 관리합니다.
"""

from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import pymongo
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database as MongoDatabase

from util.logger import wrap_log, logger


class MessageData(BaseModel):
    """단일 메시지 데이터 모델

    Attributes:
        id (int): 메시지 고유 ID (타임스탬프 기반)
        content (str): 메시지 본문 텍스트
        author (str): 작성자 이름 (사용자 닉네임 또는 'assistant')
        timestamp (datetime): 메시지 생성 시각
        chat_id (int): 속한 채팅 세션 ID
    """

    id: int
    content: str
    author: str
    timestamp: datetime
    chat_id: int


class ChatData(BaseModel):
    """채팅 세션 데이터 모델

    Attributes:
        id (int): 채팅 세션 고유 ID
        first_message_id (int): 첫 메시지 ID
        name (str): 챗봇 이름
        prompt (str): 해당 채팅 세션의 시스템 프롬프트
        chat_enabled (bool): 채팅 기능 활성화 여부
        messages (List[MessageData]): 메시지 목록
        created_at (datetime): 세션 생성 시각
        channel_id (int): 디스코드 채널 ID
        model (Optional[str]): 해당 세션에서 사용할 특정 LLM 모델명
    """

    id: int
    first_message_id: int
    name: str = "Assistant"
    prompt: str = ""
    chat_enabled: bool = True
    messages: List[MessageData] = []
    created_at: datetime
    channel_id: int
    model: Optional[str] = None





class ChannelSettingData(BaseModel):
    """디스코드 채널별 설정 데이터 모델

    Attributes:
        channel_id (int): 디스코드 채널 ID
        auto_respond (bool): 멘션 없이 항상 대답하기 옵션 활성화 여부
    """

    channel_id: int
    auto_respond: bool = False


class ChatDatabase:
    """MongoDB 기반 채팅 데이터베이스 핸들러

    Args:
        uri (str): MongoDB 접속 URI
        db_name (str): 사용할 데이터베이스 이름
    """

    def __init__(self, uri: str, db_name: str) -> None:
        """ChatDatabase 인스턴스를 초기화하고 MongoDB 연결을 설정합니다.

        Args:
            uri (str): MongoDB 연결 문자열
            db_name (str): 데이터베이스명
        """
        self.client: MongoClient = pymongo.MongoClient(uri)
        self.db: MongoDatabase = self.client[db_name]
        self.chats: Collection = self.db["chats"]
        self.settings: Collection = self.db["channel_settings"]
        logger.info(f"MongoDB 연결 완료: database='{db_name}'")

    @wrap_log
    def get_channel_auto_respond(self, channel_id: int) -> bool:
        """채널의 자동 응답 설정(Auto-Response) 여부를 조회합니다.

        Args:
            channel_id (int): 디스코드 채널 ID

        Returns:
            bool: 자동 응답 활성화 여부 (기본값: False)
        """
        setting = self.settings.find_one({"channel_id": channel_id})
        if setting:
            return setting.get("auto_respond", False)
        return False

    @wrap_log
    def set_channel_auto_respond(self, channel_id: int, auto_respond: bool) -> None:
        """채널의 자동 응답 설정을 변경하거나 새로 저장합니다.

        Args:
            channel_id (int): 디스코드 채널 ID
            auto_respond (bool): 설정할 자동 응답 값
        """
        self.settings.update_one(
            {"channel_id": channel_id},
            {"$set": {"channel_id": channel_id, "auto_respond": auto_respond}},
            upsert=True,
        )


    @wrap_log
    def create_chat(self, chat: ChatData) -> Optional[int]:
        """새로운 채팅 세션을 생성하여 MongoDB에 저장합니다.

        Args:
            chat (ChatData): 생성할 채팅 세션 데이터

        Returns:
            Optional[int]: 성공 시 채팅 세션 ID, 실패 시 None
        """
        chat_dict: Dict[str, Any] = chat.model_dump()
        result = self.chats.insert_one(chat_dict)
        return chat.id if result and result.inserted_id else None

    @wrap_log
    def delete_chat(self, chat_id: int) -> bool:
        """특정 채팅 세션을 삭제합니다.

        Args:
            chat_id (int): 삭제할 채팅 세션 ID

        Returns:
            bool: 삭제 성공 여부
        """
        result = self.chats.delete_one({"id": chat_id})
        return result.deleted_count > 0

    @wrap_log
    def delete_all_chats(self) -> None:
        """모든 채팅 세션을 삭제합니다."""
        self.chats.delete_many({})

    @wrap_log
    def get_chat(self, chat_id: int) -> Optional[ChatData]:
        """특정 ID의 채팅 세션을 조회합니다.

        Args:
            chat_id (int): 조회할 채팅 세션 ID

        Returns:
            Optional[ChatData]: 채팅 세션 데이터 또는 None
        """
        chat = self.chats.find_one({"id": chat_id})
        return ChatData(**chat) if chat else None

    @wrap_log
    def get_last_channel_chat(self, channel_id: int) -> Optional[ChatData]:
        """특정 디스코드 채널의 가장 최근 채팅 세션을 조회합니다.

        Args:
            channel_id (int): 디스코드 채널 ID

        Returns:
            Optional[ChatData]: 최신 채팅 세션 데이터 또는 None
        """
        chat = self.chats.find_one({"channel_id": channel_id}, sort=[("created_at", -1)])
        return ChatData(**chat) if chat else None

    @wrap_log
    def get_channel_chats(self, channel_id: int, limit: int = 10) -> List[ChatData]:
        """특정 디스코드 채널의 세션 목록을 최신순으로 조회합니다.

        Args:
            channel_id (int): 디스코드 채널 ID
            limit (int): 조회할 최대 세션 수 (기본값: 10)

        Returns:
            List[ChatData]: 세션 목록
        """
        cursor = self.chats.find({"channel_id": channel_id}).sort("created_at", -1).limit(limit)
        return [ChatData(**chat) for chat in cursor]


    @wrap_log
    def update_chat_model(self, chat_id: int, model_name: str) -> bool:
        """채팅 세션에서 사용할 LLM 모델명을 변경합니다.

        Args:
            chat_id (int): 채팅 세션 ID
            model_name (str): 적용할 LLM 모델명

        Returns:
            bool: 업데이트 성공 여부
        """
        result = self.chats.update_one({"id": chat_id}, {"$set": {"model": model_name}})
        return result.modified_count > 0

    @wrap_log
    def add_message(self, chat_id: int, message: MessageData) -> None:

        """채팅 세션에 새로운 메시지를 추가합니다.

        Args:
            chat_id (int): 채팅 세션 ID
            message (MessageData): 추가할 메시지 객체
        """
        self.chats.update_one({"id": chat_id}, {"$push": {"messages": message.model_dump()}})

    @wrap_log
    def delete_message(self, chat_id: int, message_id: int) -> bool:
        """채팅 세션 내 특정 메시지를 삭제합니다.

        Args:
            chat_id (int): 채팅 세션 ID
            message_id (int): 삭제할 메시지 ID

        Returns:
            bool: 삭제 성공 여부
        """
        result = self.chats.update_one({"id": chat_id}, {"$pull": {"messages": {"id": message_id}}})
        return result.modified_count > 0

    @wrap_log
    def delete_last_message(self, chat_id: int) -> bool:
        """채팅 세션의 마지막 메시지를 제거합니다.

        Args:
            chat_id (int): 채팅 세션 ID

        Returns:
            bool: 삭제 성공 여부
        """
        result = self.chats.update_one({"id": chat_id}, {"$pop": {"messages": 1}})
        return result.modified_count > 0

    @wrap_log
    def close(self) -> None:
        """MongoDB 클라이언트 연결을 닫습니다."""
        self.client.close()