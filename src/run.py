"""
Discord LLM Bot 메인 실행 엔트리포인트 모듈

디스코드 봇 인스턴스를 생성하고 이벤트/Cog 핸들러를 등록한 뒤 봇을 실행합니다.
"""

import os
from typing import Dict, Any
import discord
from discord.ext import commands
from dotenv import load_dotenv

from cogs.llm_cog import LLMCog
from help_command import MyHelp
from util.logger import logger

load_dotenv()


def main() -> None:
    """디스코드 봇을 초기화하고 실행하는 메인 함수입니다."""
    intents: discord.Intents = discord.Intents.default()
    intents.members = True
    intents.message_content = True

    bot: commands.Bot = commands.Bot(commands.when_mentioned_or("!"), intents=intents)

    help_attributes: Dict[str, Any] = {
        "name": "help",
        "aliases": ["helpme"],
        "cooldown": commands.CooldownMapping.from_cooldown(3, 5, commands.BucketType.user),
    }

    # Cog 및 도움말 커맨드 추가
    bot.add_cog(LLMCog(bot))
    bot.help_command = MyHelp(command_attrs=help_attributes)

    token: str = str(os.getenv("DISCORD_TOKEN", ""))
    if not token:
        logger.error("DISCORD_TOKEN 환경 변수가 설정되지 않았습니다.")
        raise ValueError("DISCORD_TOKEN이 .env 파일에 누락되어 있습니다.")

    logger.info("Discord LLM Bot 시작 중...")
    bot.run(token)


if __name__ == "__main__":
    main()

