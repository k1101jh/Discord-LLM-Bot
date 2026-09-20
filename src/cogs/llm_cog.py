"""
디스코드 LLM 대화 처리 Cog 모듈

메시지 이벤트 수신, 대화 세션 관리, 슬래시 커맨드 핸들러를 담당합니다.
"""

import os
import time
from datetime import datetime
from typing import List, Optional

import discord
from discord import ApplicationContext, Message
from discord.commands import SlashCommandGroup, option
from discord.ext import commands, pages
from dotenv import load_dotenv

from constants import DEFAULT_BOT_INSTRUCTIONS, DEFAULT_BOT_NAME
from database.database import ChatData, ChatDatabase, MessageData
from llm.base_llm import BaseLLM
from llm.llm_loader import load_llm
from util.logger import logger, wrap_log_async


class LLMCog(commands.Cog):
    """LLM 대화 기능 및 대화 세션 관리를 담당하는 Cog 클래스

    Args:
        bot (commands.Bot): 디스코드 봇 객체
    """

    def __init__(self, bot: commands.Bot) -> None:
        """LLMCog를 초기화하고 LLM과 데이터베이스 연결을 준비합니다.

        Args:
            bot (commands.Bot): 디스코드 봇 인스턴스
        """
        load_dotenv()
        self.bot: commands.Bot = bot
        self.llm: BaseLLM = load_llm()

        # MongoDB 설정
        database_uri: str = os.getenv(
            "MONGO_URI",
            "mongodb://root:examplepassword@localhost:27017/discord_chat_bot?authSource=admin",
        )
        database_name: str = os.getenv("DATABASE_NAME", "discord_chat_bot")
        self.chat_database: ChatDatabase = ChatDatabase(uri=database_uri, db_name=database_name)


    llm_cog: SlashCommandGroup = SlashCommandGroup("llm", "LLM 대화 관련 명령어 그룹입니다.")

    @commands.Cog.listener()
    @wrap_log_async
    async def on_message(self, message: Message) -> None:
        """수신된 디스코드 메시지를 감지하여 LLM 응답을 생성합니다.

        Args:
            message (Message): 디스코드 메시지 객체
        """
        # 봇 자신 또는 커맨드/멘션 메시지는 무시
        if message.author == self.bot.user:
            return
        if message.content.startswith("!") or message.content.startswith("/"):
            return
        if message.mentions:
            return

        ctx: commands.Context[Any] = await self.bot.get_context(message)

        # 채널의 최신 채팅 세션 조회 또는 생성
        chat: Optional[ChatData] = self.chat_database.get_last_channel_chat(message.channel.id)
        new_chat: bool = False

        if chat is None:
            new_chat = True
            chat = ChatData(
                id=int(time.time() * 1000),
                first_message_id=0,
                name=DEFAULT_BOT_NAME,
                prompt=DEFAULT_BOT_INSTRUCTIONS,
                chat_enabled=True,
                messages=[],
                created_at=datetime.now(),
                channel_id=message.channel.id,
            )

        if not chat.chat_enabled:
            return

        new_message: MessageData = MessageData(
            id=int(time.time() * 1000),
            content=message.content,
            author=message.author.display_name,
            timestamp=message.created_at,
            chat_id=chat.id,
        )

        if not new_chat:
            self.chat_database.add_message(chat.id, new_message)
            chat.messages.append(new_message)
        else:
            chat.first_message_id = new_message.id
            chat.messages.append(new_message)
            self.chat_database.create_chat(chat)

        # LLM 입력 중 표시 및 응답 생성
        async with ctx.typing():
            try:
                response: str = self.llm.create(chat.prompt, chat.messages)

                # LLM 답변 DB 추가
                self.chat_database.add_message(
                    chat_id=chat.id,
                    message=MessageData(
                        id=int(time.time() * 1000),
                        content=response,
                        author="assistant",
                        timestamp=datetime.now(),
                        chat_id=chat.id,
                    ),
                )
            except Exception as e:
                logger.error(f"LLM 응답 생성 중 오류 발생: {e}")
                response = f"오류가 발생했습니다: {e}"
                # 오류 발생 시 마지막 사용자 메시지 롤백
                if chat.messages:
                    self.chat_database.delete_message(chat.id, chat.messages[-1].id)

        await ctx.send(response)

    @llm_cog.command(name="prompt", description="현재 채팅 세션의 프롬프트를 출력합니다.")
    @wrap_log_async
    async def print_prompt(self, ctx: ApplicationContext) -> None:
        """현재 채널 채팅 세션의 시스템 프롬프트를 디스코드 채널에 출력합니다."""
        chat: Optional[ChatData] = self.chat_database.get_last_channel_chat(ctx.channel.id)
        if chat:
            await ctx.respond(f"현재 프롬프트:\n{chat.prompt}", ephemeral=False)
        else:
            await ctx.respond("채팅 내역이 없습니다.", ephemeral=False)

    @llm_cog.command(name="set_prompt", description="시스템 프롬프트를 수정하고 새 세션을 시작합니다.")
    @wrap_log_async
    async def set_prompt(self, ctx: ApplicationContext, prompt: str) -> None:
        """현재 채널의 시스템 프롬프트를 수정합니다.

        Args:
            ctx (ApplicationContext): 슬래시 커맨드 컨텍스트
            prompt (str): 변경할 새 시스템 프롬프트
        """
        chat: Optional[ChatData] = self.chat_database.get_last_channel_chat(ctx.channel.id)
        chat_enabled: bool = True

        if chat:
            chat_enabled = chat.chat_enabled
            self.chat_database.delete_chat(chat.id)

        new_chat: ChatData = ChatData(
            id=int(time.time() * 1000),
            first_message_id=0,
            name="AI",
            prompt=prompt,
            chat_enabled=chat_enabled,
            messages=[],
            created_at=datetime.now(),
            channel_id=ctx.channel.id,
        )
        self.chat_database.create_chat(new_chat)
        await ctx.respond(f"프롬프트를 수정하였습니다.\n프롬프트: {new_chat.prompt}", ephemeral=False)

    @llm_cog.command(name="toggle_chat", description="채팅 응답 기능을 켜거나 끕니다.")
    @wrap_log_async
    async def toggle_chat(self, ctx: ApplicationContext) -> None:
        """채팅 자동 응답 기능을 ON/OFF 토글합니다."""
        chat: Optional[ChatData] = self.chat_database.get_last_channel_chat(ctx.channel.id)
        if chat:
            chat.chat_enabled = not chat.chat_enabled
            status_str: str = "활성화" if chat.chat_enabled else "비활성화"
            await ctx.respond(f"채팅 기능을 {status_str}했습니다.", ephemeral=False)
        else:
            await ctx.respond("채팅 내역이 없습니다.", ephemeral=False)

    @llm_cog.command(name="regenerate", description="마지막 LLM 응답을 다시 생성합니다.")
    @wrap_log_async
    async def regenerate(self, ctx: ApplicationContext) -> None:
        """마지막 답변을 제거하고 LLM으로 답변을 재생성합니다."""
        chat: Optional[ChatData] = self.chat_database.get_last_channel_chat(ctx.channel.id)
        if chat is not None and len(chat.messages) >= 2:
            self.chat_database.delete_last_message(chat.id)
            try:
                # 마지막 답변 제거 후 남은 사용자 메시지로 재생성
                response: str = self.llm.create(chat.prompt, chat.messages[:-1])
                self.chat_database.add_message(
                    chat_id=chat.id,
                    message=MessageData(
                        id=int(time.time() * 1000),
                        content=response,
                        author="assistant",
                        timestamp=datetime.now(),
                        chat_id=chat.id,
                    ),
                )
            except Exception as e:
                logger.error(f"답변 재 생성 실패: {e}")
                response = f"재생성 중 오류가 발생했습니다: {e}"

            await ctx.respond(response)
        else:
            await ctx.respond("재생성할 대화 내역이 부족합니다.", ephemeral=True)

    @llm_cog.command(name="delete_last_message", description="마지막 사용자 및 AI 메시지를 제거합니다.")
    @wrap_log_async
    async def delete_last_message(self, ctx: ApplicationContext) -> None:
        """최근 메시지 쌍(사용자 질문 + AI 답변)을 채팅 내역에서 제거합니다."""
        chat: Optional[ChatData] = self.chat_database.get_last_channel_chat(ctx.channel.id)
        if chat is not None and len(chat.messages) >= 2:
            self.chat_database.delete_last_message(chat.id)
            self.chat_database.delete_last_message(chat.id)
            await ctx.respond("마지막 메시지 쌍을 제거하였습니다.", ephemeral=False)
        else:
            await ctx.respond("제거할 메시지가 없습니다.", ephemeral=True)

    @llm_cog.command(name="new_chat", description="현재 채널의 채팅 대화 내역을 초기화합니다.")
    @wrap_log_async
    async def new_chat(self, ctx: ApplicationContext) -> None:
        """새로운 대화 세션을 시작하여 대화 내역을 초기화합니다."""
        chat: Optional[ChatData] = self.chat_database.get_last_channel_chat(ctx.channel.id)
        if chat:
            new_chat: ChatData = ChatData(
                id=int(time.time() * 1000),
                first_message_id=0,
                name=chat.name,
                prompt=chat.prompt,
                chat_enabled=chat.chat_enabled,
                messages=[],
                created_at=datetime.now(),
                channel_id=ctx.channel.id,
            )
            self.chat_database.delete_chat(chat.id)
            self.chat_database.create_chat(new_chat)
            await ctx.respond("채팅 내역을 초기화했습니다.", ephemeral=False)
        else:
            await ctx.respond("채팅 내역이 없습니다.", ephemeral=True)

    @llm_cog.command(name="history", description="현재 채널의 대화 이력을 조회합니다.")
    @wrap_log_async
    async def history(self, ctx: ApplicationContext) -> None:
        """채팅 세션 메시지 히스토리를 페이지 형태(Paginator)로 보여줍니다."""
        chat: Optional[ChatData] = self.chat_database.get_last_channel_chat(ctx.channel.id)
        if chat is None or not chat.messages:
            await ctx.respond("채팅 내역이 없습니다.", ephemeral=True)
            return

        chat_pages: List[discord.Embed] = []
        embed_fields: List[discord.EmbedField] = []

        for message in chat.messages:
            content: str = message.content
            if len(content) > 256:
                content = content[:50] + "\n...\n" + content[-50:]

            embed_fields.append(
                discord.EmbedField(name=f"{message.author}:", value=content, inline=False)
            )
            if len(embed_fields) == 10:
                chat_pages.append(discord.Embed(title="대화 이력", fields=embed_fields))
                embed_fields = []

        if embed_fields:
            chat_pages.append(discord.Embed(title="대화 이력", fields=embed_fields))

        if chat_pages:
            page_buttons = [
                pages.PaginatorButton("first", emoji="⏪", style=discord.ButtonStyle.green),
                pages.PaginatorButton("prev", emoji="⬅", style=discord.ButtonStyle.green),
                pages.PaginatorButton("page_indicator", style=discord.ButtonStyle.gray, disabled=True),
                pages.PaginatorButton("next", emoji="➡", style=discord.ButtonStyle.green),
                pages.PaginatorButton("last", emoji="⏩", style=discord.ButtonStyle.green),
            ]

            paginator = pages.Paginator(
                pages=chat_pages,
                show_disabled=True,
                show_indicator=True,
                use_default_buttons=False,
                custom_buttons=page_buttons,
                loop_pages=False,
            )
            paginator.current_page = len(chat_pages) - 1
            await paginator.respond(ctx.interaction, ephemeral=True)
        else:
            await ctx.respond("채팅 내역이 없습니다.", ephemeral=True)

