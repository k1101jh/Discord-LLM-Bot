import pymongo
from datetime import datetime
from typing import List
from typing import Dict
from typing import Optional
from pydantic import BaseModel
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database as MongoDatabase

from util.logger import wrap_log, logger


class MessageData(BaseModel):
    id: int
    content: str
    author: str
    timestamp: datetime
    chat_id: int
    
    
class ChatData(BaseModel):
    id: int
    first_message_id: int
    messages: List[MessageData]
    created_at: datetime
    channel_id: int


class ChatDatabase:
    def __init__(self, uri: str, db_name: str):
        self.client: MongoClient = pymongo.MongoClient(uri)
        self.db: MongoDatabase = self.client[db_name]
        self.chats: Collection = self.db["chats"]
        
        print(self.db)
        for db in self.client.list_databases():
            print(db)
        
    @wrap_log
    def create_chat(self, chat: ChatData) -> Optional[int]:
        chat_dict = chat.model_dump()
        result = self.chats.insert_one(chat_dict)
        return chat.id if result and result.inserted_id else None
    
    @wrap_log
    def delete_chat(self, chat_id: int) -> bool:
        result = self.chats.delete_one({"id": chat_id})
        return result.deleted_count > 0
    
    @wrap_log
    def delete_all_chats(self) -> None:
        self.chats.delete_many({})
            
    @wrap_log
    def get_chat(self, chat_id: int) -> Optional[ChatData]:
        chat = self.chats.find_one({"id": chat_id})
        return ChatData(**chat) if chat else None
    
    @wrap_log
    def get_last_channel_chat(self, channel_id: int) -> Optional[ChatData]:
        chat = self.chats.find_one({"channel_id": channel_id}, sort=[("created_at", -1)])
        return ChatData(**chat) if chat else None
    
    @wrap_log
    def add_message(self, chat_id: int, message: MessageData) -> None:
        self.chats.update_one({"id": chat_id}, {"$push": {"messages": message.model_dump()}})
        
    @wrap_log
    def delete_message(self, chat_id: int, message_id: int) -> bool:
        result = self.chats.update_one({"id": chat_id}, {"$pull": {"messages": {"id": message_id}}})
        return result.modified_count > 0

    @wrap_log
    def delete_last_message(self, chat_id: int) -> bool:
        result = self.chats.update_one({"id": chat_id}, {"$pop": {"messages": -1}})
        return result.modified_count > 0

    @wrap_log
    def close(self):
        self.client.close()