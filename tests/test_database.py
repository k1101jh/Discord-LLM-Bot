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


def test_channel_auto_respond(database: ChatDatabase) -> None:
    """채널별 자동 응답 설정 조회 및 변경 테스트"""
    channel_id: int = 12345

    # 기본값은 False
    assert database.get_channel_auto_respond(channel_id) is False

    # True로 설정
    database.set_channel_auto_respond(channel_id, True)
    assert database.get_channel_auto_respond(channel_id) is True

    # 다시 False로 설정
    database.set_channel_auto_respond(channel_id, False)
    assert database.get_channel_auto_respond(channel_id) is False


def test_get_channel_chats(database: ChatDatabase) -> None:
    """특정 채널의 세션 목록 조회 검증 테스트"""
    chat1 = ChatData(
        id=101,
        first_message_id=1,
        name="Assistant",
        prompt="프롬프트1",
        chat_enabled=True,
        messages=[],
        created_at=datetime.now(),
        channel_id=99,
    )
    chat2 = ChatData(
        id=102,
        first_message_id=2,
        name="Assistant",
        prompt="프롬프트2",
        chat_enabled=True,
        messages=[],
        created_at=datetime.now() + timedelta(minutes=10),
        channel_id=99,
    )

    database.create_chat(chat1)
    database.create_chat(chat2)

    sessions = database.get_channel_chats(99)
    assert len(sessions) == 2
    assert sessions[0].id == 102  # 최신순 정렬 확인
    assert sessions[1].id == 101


def test_update_chat_model(database: ChatDatabase) -> None:
    """채팅 세션 모델 변경 검증 테스트"""
    chat = ChatData(
        id=201,
        first_message_id=1,
        name="Assistant",
        prompt="프롬프트",
        chat_enabled=True,
        messages=[],
        created_at=datetime.now(),
        channel_id=1,
        model="gemma4:12b",
    )
    database.create_chat(chat)
    assert database.get_chat(201).model == "gemma4:12b"

    database.update_chat_model(201, "qwen2.5:7b")
    updated_chat = database.get_chat(201)
    assert updated_chat is not None
    assert updated_chat.model == "qwen2.5:7b"



 