import pytest
import os
from dotenv import load_dotenv
from datetime import datetime
from datetime import timedelta

print(os.path.curdir)

from src.database.database import ChatDatabase
from src.database.database import ChatData
from src.database.database import MessageData

load_dotenv()

@pytest.fixture
def database():
    return ChatDatabase(uri=os.getenv("MONGO_URI"), db_name="discord_bot_test")

def test_get_chat(database):
    chat = ChatData(id=1, first_message_id=1, messages=[], created_at=datetime.now(), channel_id=1)
    
    chat_id = database.create_chat(chat)
    
    retrieved_chat = database.get_chat(chat_id)
    
    assert chat_id is not None
    assert retrieved_chat.first_message_id == chat.first_message_id
    assert retrieved_chat.messages == chat.messages
    
    database.delete_all_chats()
    
def test_get_last_channel_chat(database):
    chat1 = ChatData(
        id=1,
        first_message_id=1,
        messages=[],
        created_at=datetime.now(),
        channel_id=1,
    )
    
    chat2 = ChatData(
        id=2,
        first_message_id=2,
        messages=[],
        created_at=datetime.now() + timedelta(days=0, hours=0, minutes=30),
        channel_id=1,
    )
    
    chat_id1 = database.create_chat(chat1)
    chat_id2 = database.create_chat(chat2)
    
    retrieved_chat = database.get_last_channel_chat(1)
    
    assert retrieved_chat.id == chat2.id
    assert retrieved_chat.first_message_id == chat2.first_message_id
    assert retrieved_chat.messages == chat2.messages
    assert retrieved_chat.channel_id == chat2.channel_id
    
    database.delete_all_chats()
    
def test_add_message(database: ChatDatabase):
    chat = ChatData(id=1, first_message_id=1, messages=[], created_at=datetime.now(), channel_id=1)
    
    chat_id = database.create_chat(chat)
    
    message = MessageData(id=1, content="Hello, world!", author="user", timestamp=datetime.now(), chat_id=chat_id)
    
    database.add_message(chat_id, message)
    
    retrieved_chat = database.get_chat(chat_id)
    
    assert len(retrieved_chat.messages) == 1
    assert retrieved_chat.messages[0].id == message.id
    assert retrieved_chat.messages[0].content == message.content
    assert retrieved_chat.messages[0].author == message.author
    assert retrieved_chat.messages[0].chat_id == message.chat_id
    
    database.delete_all_chats() 