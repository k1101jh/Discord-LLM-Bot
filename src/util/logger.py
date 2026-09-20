"""
로깅 유틸리티 모듈

디스코드 봇의 콘솔 및 파일 로깅을 설정하고 데코레이터를 제공합니다.
"""

import os
import functools
import logging
import logging.handlers
from datetime import datetime
from logging import Logger
from typing import Callable, Any

logger: Logger = logging.getLogger("discord-llm-bot")

# 실행 시작 시간 기반 로그 파일명 생성 (예: ./logs/discord-llm-bot_20260920_125039.log)
start_time_str: str = datetime.now().strftime("%Y%m%d_%H%M%S")
LOG_FILEPATH: str = f"./logs/discord-llm-bot_{start_time_str}.log"



def setup_logging() -> None:
    """로깅 설정을 초기화합니다.

    콘솔 출력 스트림 핸들러와 일별 로테이션 파일 핸들러를 구성합니다.

    Returns:
        None
    """
    if logger.handlers:
        return

    log_format: str = "%(asctime)s | %(name)s | %(levelname)s | %(module)s | %(message)s"
    formatter: logging.Formatter = logging.Formatter(log_format)

    logger.setLevel(logging.INFO)

    # 콘솔 로그 핸들러
    console_handler: logging.StreamHandler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 파일 로그 핸들러 (일별 로테이션)
    os.makedirs(os.path.dirname(LOG_FILEPATH), exist_ok=True)
    file_debug_handler: logging.handlers.TimedRotatingFileHandler = logging.handlers.TimedRotatingFileHandler(
        LOG_FILEPATH, when="D", backupCount=10, encoding="utf-8"
    )
    file_debug_handler.setLevel(logging.DEBUG)
    file_debug_handler.setFormatter(formatter)
    logger.addHandler(file_debug_handler)


def wrap_log(func: Callable[..., Any]) -> Callable[..., Any]:
    """동기 함수의 실행 시작 및 예외를 로깅하는 데코레이터입니다.

    Args:
        func (Callable[..., Any]): 감쌀 대상 동기 함수

    Returns:
        Callable[..., Any]: 로깅 로직이 포함된 래퍼 함수
    """
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            logger.info(f"started '{func.__name__}', parameters: '{args}' and '{kwargs}'")
            return func(*args, **kwargs)
        except Exception as e:
            logger.exception(e)
            raise e

    return wrapper


def wrap_log_async(func: Callable[..., Any]) -> Callable[..., Any]:
    """비동기 함수의 실행 시작 및 예외를 로깅하는 데코레이터입니다.

    Args:
        func (Callable[..., Any]): 감쌀 대상 비동기 함수

    Returns:
        Callable[..., Any]: 로깅 로직이 포함된 비동기 래퍼 함수
    """
    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            logger.info(f"started '{func.__name__}', parameters: '{args}' and '{kwargs}'")
            return await func(*args, **kwargs)
        except Exception as e:
            logger.exception(e)
            raise e

    return wrapper


setup_logging()