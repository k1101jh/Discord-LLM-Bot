import os
import functools
import logging
import logging.handlers
import asyncio
from logging import Logger
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

logger = logging.getLogger('discord-llm-bot')

LOG_FILEPATH = "./logs/discord-llm-bot.log"


def setup_logging():
    # Create log formatter
    format = '%(asctime)s | %(name)s | %(levelname)s | %(module)s | %(message)s'
    formatter = logging.Formatter(format)
    
    # Basic logging configuration
    logging.basicConfig(level=logging.INFO, format=format)

    # This is to store logs into console
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # The following code is to create a directory if it doesn't exist and to store logs into a file
    os.makedirs(os.path.dirname(LOG_FILEPATH), exist_ok=True)

    # This logger stores logs into a file with a daily rotation
    file_debug_handler = logging.handlers.TimedRotatingFileHandler(LOG_FILEPATH, when='D', backupCount=10)
    file_debug_handler.setLevel(logging.DEBUG)
    file_debug_handler.setFormatter(formatter)
    logger.addHandler(file_debug_handler)
    
def wrap_log(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            logger.info(f"started '{func.__name__}', parameters: '{args}' and '{kwargs}'")
            return func(*args, **kwargs)
        except Exception as e:
            logger.exception(e)

    return wrapper


def wrap_log_async(func):
    @functools.wraps(func)
    async def wrapper(*args,**kwargs):
        try:
            logger.info(f"started '{func.__name__}', parameters: '{args}' and '{kwargs}'")
            return await func(*args, **kwargs)
        except Exception as e:
            logger.exception(e)

    return wrapper


setup_logging()