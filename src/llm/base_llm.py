from database.database import ChatData, MessageData
from abc import *

class BaseLLM(metaclass=ABCMeta):
    @abstractmethod
    def create(self, message: MessageData) -> str:
        raise NotImplementedError

