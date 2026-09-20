"""
ChatDatabase 단위 테스트 모듈

mongomock을 활용하여 실제 MongoDB 연결 없이 메모리 상에서 데이터베이스 동작을 검증합니다.
"""

from datetime import datetime, timedelta
from typing import Generator
import mongomock
import pytest
from unittest.mock import patch

from database.database import ChatData, ChatDatabase, MessageData


@pytest.fixture
def database() -> Generator[ChatDatabase, None, None]:
    """mongomock 클라이언트를 주입받는 테스트용 ChatDatabase 피스처"""
    with patch("pymongo.MongoClient", mongomock.MongoClient):
        db = ChatDatabase(uri="mongodb://localhost:27017", db_name="discord_bot_test")
        yield db
        db.delete_all_chats()


def test_get_chat(database: ChatDatabase) -> None:
    """단일 채팅 세션 생성 및 조회 검증 테스트"""
    chat = ChatData(
        id=1,
        first_message_id=1,
        name="Assistant",
        prompt="테스트 프롬프트",
        chat_enabled=True,
        messages=[],
        created_at=datetime.now(),
        channel_id=1,
    )

    chat_id = database.create_chat(chat)
    retrieved_chat = database.get_chat(chat_id)

    assert chat_id is not None
    assert retrieved_chat is not None
    assert retrieved_chat.first_message_id == chat.first_message_id
    assert retrieved_chat.messages == chat.messages


def test_get_last_channel_chat(database: ChatDatabase) -> None:
    """동일 채널 내 최신 채팅 세션 조회 검증 테스트"""
    chat1 = ChatData(
        id=1,
        first_message_id=1,
        name="Assistant",
        prompt="프롬프트1",
        chat_enabled=True,
        messages=[],
        created_at=datetime.now(),
        channel_id=1,
    )

    chat2 = ChatData(
        id=2,
        first_message_id=2,
        name="Assistant",
        prompt="프롬프트2",
        chat_enabled=True,
        messages=[],
        created_at=datetime.now() + timedelta(minutes=30),
        channel_id=1,
    )

    database.create_chat(chat1)
    database.create_chat(chat2)

    retrieved_chat = database.get_last_channel_chat(1)

    assert retrieved_chat is not None
    assert retrieved_chat.id == chat2.id
    assert retrieved_chat.first_message_id == chat2.first_message_id
    assert retrieved_chat.channel_id == chat2.channel_id


def test_add_message(database: ChatDatabase) -> None:
    """채팅 세션 메시지 추가 검증 테스트"""
    chat = ChatData(
        id=1,
        first_message_id=1,
        name="Assistant",
        prompt="프롬프트",
        chat_enabled=True,
        messages=[],
        created_at=datetime.now(),
        channel_id=1,
    )

    chat_id = database.create_chat(chat)
    message = MessageData(
        id=1,
        content="안녕하세요!",
        author="user",
        timestamp=datetime.now(),
        chat_id=chat_id,
    )

    database.add_message(chat_id, message)
    retrieved_chat = database.get_chat(chat_id)

    assert retrieved_chat is not None
    assert len(retrieved_chat.messages) == 1
    assert retrieved_chat.messages[0].id == message.id
    assert retrieved_chat.messages[0].content == message.content
    assert retrieved_chat.messages[0].author == message.author
    assert retrieved_chat.messages[0].chat_id == message.chat_id
 