"""
디스코드 LLM 대화 처리 Cog 모듈

메시지 이벤트 수신, 대화 세션 관리, 슬래시 커맨드 핸들러를 담당합니다.
"""

import os
import time
from datetime import datetime
from typing import List, Optional, Any

import discord
from discord import ApplicationContext, Message, Interaction
from discord.commands import SlashCommandGroup, option
from discord.ext import commands, pages
from dotenv import load_dotenv

from constants import DEFAULT_BOT_INSTRUCTIONS, DEFAULT_BOT_NAME
from database.database import ChatData, ChatDatabase, MessageData
from llm.base_llm import BaseLLM
from llm.llm_loader import load_llm
from util.logger import logger, wrap_log_async


class SessionSelectView(discord.ui.View):
    """채팅 세션 전환 및 삭제를 위한 드롭다운 UI View 클래스"""

    def __init__(self, chats: List[ChatData], chat_database: ChatDatabase) -> None:
        super().__init__(timeout=180)
        self.chats: List[ChatData] = chats
        self.chat_database: ChatDatabase = chat_database

        # 1) 세션 전환 드롭다운
        switch_options = []
        for idx, chat in enumerate(chats[:10], start=1):
            created_str = chat.created_at.strftime("%m-%d %H:%M")
            prompt_preview = (chat.prompt[:25] + "..") if len(chat.prompt) > 25 else chat.prompt
            switch_options.append(
                discord.SelectOption(
                    label=f"{idx}번 세션 ({created_str})",
                    description=f"프롬프트: {prompt_preview}",
                    value=f"switch_{chat.id}",
                )
            )

        if switch_options:
            self.switch_select = discord.ui.Select(
                placeholder="🔄 전환할 세션을 선택하세요...",
                min_values=1,
                max_values=1,
                options=switch_options,
                custom_id="session_switch_select",
            )
            self.switch_select.callback = self.on_switch_select
            self.add_item(self.switch_select)

        # 2) 세션 삭제 드롭다운
        delete_options = []
        for idx, chat in enumerate(chats[:10], start=1):
            created_str = chat.created_at.strftime("%m-%d %H:%M")
            delete_options.append(
                discord.SelectOption(
                    label=f"{idx}번 세션 삭제 (ID: {chat.id})",
                    description=f"생성시각: {created_str}",
                    value=f"delete_{chat.id}",
                )
            )

        if delete_options:
            self.delete_select = discord.ui.Select(
                placeholder="🗑️ 삭제할 세션을 선택하세요...",
                min_values=1,
                max_values=1,
                options=delete_options,
                custom_id="session_delete_select",
            )
            self.delete_select.callback = self.on_delete_select
            self.add_item(self.delete_select)

    async def on_switch_select(self, interaction: Interaction) -> None:
        """세션 전환 드롭다운 처리"""
        val = self.switch_select.values[0]
        session_id = int(val.replace("switch_", ""))
        self.chat_database.chats.update_one({"id": session_id}, {"$set": {"created_at": datetime.now()}})
        await interaction.response.send_message(f"✅ 세션 `ID: {session_id}`로 대화 세션이 성공적으로 전환되었습니다!", ephemeral=False)

    async def on_delete_select(self, interaction: Interaction) -> None:
        """세션 삭제 드롭다운 처리"""
        val = self.delete_select.values[0]
        session_id = int(val.replace("delete_", ""))
        success = self.chat_database.delete_chat(session_id)
        if success:
            await interaction.response.send_message(f"🗑️ 세션 `ID: {session_id}`이(가) 성공적으로 삭제되었습니다.", ephemeral=False)
        else:
            await interaction.response.send_message(f"❌ 세션 `ID: {session_id}` 삭제 실패.", ephemeral=True)


class ModelSelectView(discord.ui.View):
    """LLM 모델 선택을 위한 드롭다운 UI View 클래스"""

    def __init__(self, models: List[str], current_model: str, chat_database: ChatDatabase, channel_id: int) -> None:
        super().__init__(timeout=180)
        self.chat_database: ChatDatabase = chat_database
        self.channel_id: int = channel_id

        options = []
        for m in models[:25]:  # Discord 최대 25개 개수 제한
            is_current = (m == current_model)
            options.append(
                discord.SelectOption(
                    label=m,
                    description="현재 선택된 모델" if is_current else f"LLM 모델 {m}",
                    value=m,
                    default=is_current,
                )
            )

        self.model_select = discord.ui.Select(
            placeholder="🤖 사용할 LLM 모델을 선택하세요...",
            min_values=1,
            max_values=1,
            options=options,
        )
        self.model_select.callback = self.on_model_select
        self.add_item(self.model_select)

    async def on_model_select(self, interaction: Interaction) -> None:
        selected_model = self.model_select.values[0]
        chat = self.chat_database.get_last_channel_chat(self.channel_id)
        if chat:
            self.chat_database.update_chat_model(chat.id, selected_model)
        else:
            new_chat = ChatData(
                id=int(time.time() * 1000),
                first_message_id=0,
                name=DEFAULT_BOT_NAME,
                prompt=DEFAULT_BOT_INSTRUCTIONS,
                chat_enabled=True,
                messages=[],
                created_at=datetime.now(),
                channel_id=self.channel_id,
                model=selected_model,
            )
            self.chat_database.create_chat(new_chat)

        await interaction.response.send_message(f"✅ 현재 채널의 대화 모델이 **`{selected_model}`**(으)로 설정되었습니다!", ephemeral=False)


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
            "mongodb://localhost:27017/discord_chat_bot",
        )
        database_name: str = os.getenv("DATABASE_NAME", "discord_chat_bot")
        self.chat_database: ChatDatabase = ChatDatabase(uri=database_uri, db_name=database_name)



    llm_cog: SlashCommandGroup = SlashCommandGroup("llm", "LLM 대화 관련 명령어 그룹입니다.")

    @commands.Cog.listener()
    @wrap_log_async
    async def on_message(self, message: Message) -> None:
        """수신된 디스코드 메시지를 감지하여 조건(멘션, 전용 채널, 스레드)에 맞춰 LLM 응답을 생성합니다.

        Args:
            message (Message): 디스코드 메시지 객체
        """
        # 봇 자신 또는 봇 타입 사용자의 메시지는 무시
        if message.author == self.bot.user or message.author.bot:
            return
        # 커맨드 관련 메시지는 무시
        if message.content.startswith("!") or message.content.startswith("/"):
            return

        # 반응 조건 검사: 1) 봇 멘션 2) 대화 스레드 내부 3) 채널 auto_respond 설정 ON
        is_mentioned: bool = self.bot.user in message.mentions
        is_thread: bool = isinstance(message.channel, discord.Thread)
        is_auto_channel: bool = self.chat_database.get_channel_auto_respond(message.channel.id)

        if not (is_mentioned or is_thread or is_auto_channel):
            return

        # 멘션 텍스트 정리 (예: <@!123456> 텍스트 제거)
        clean_content: str = message.content
        if is_mentioned and self.bot.user:
            clean_content = clean_content.replace(f"<@{self.bot.user.id}>", "")
            clean_content = clean_content.replace(f"<@!{self.bot.user.id}>", "").strip()

        if not clean_content:
            clean_content = "안녕하세요!"

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
            content=clean_content,
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
        async with message.channel.typing():
            try:
                response: str = self.llm.create(chat.prompt, chat.messages, model_name=chat.model)

                if not response or not response.strip():
                    logger.warning("LLM 응답이 빈 문자열로 반환되었습니다.")
                    response = "⚠️ LLM 답변 생성이 비어있거나 실패했습니다. 다시 질문해 주시거나 `/llm list_models`로 다른 모델을 선택해 보세요."
                    if chat.messages:
                        self.chat_database.delete_message(chat.id, chat.messages[-1].id)
                else:
                    # 정상 응답 시 DB 기록 추가
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

        # 답장(Reply) 전달 (빈 메시지 방지 및 2000자 길이지 제한 청크 분할)
        if len(response) > 1900:
            chunks = [response[i:i + 1900] for i in range(0, len(response), 1900)]
            for chunk in chunks:
                await message.reply(chunk, mention_author=False)
        else:
            await message.reply(response, mention_author=False)



    @llm_cog.command(name="prompt", description="현재 채팅 세션의 프롬프트를 출력합니다.")
    @wrap_log_async
    async def print_prompt(self, ctx: ApplicationContext) -> None:
        """현재 채널 채팅 세션의 시스템 프롬프트를 디스코드 채널에 출력합니다."""
        chat: Optional[ChatData] = self.chat_database.get_last_channel_chat(ctx.channel.id)
        if chat:
            await ctx.respond(f"현재 프롬프트:\n{chat.prompt}", ephemeral=False)
        else:
            await ctx.respond("채팅 내역이 없습니다.", ephemeral=False)

    @llm_cog.command(name="generate_prompt", description="자연어 요청을 바탕으로 AI 시스템 프롬프트를 자동 생성합니다.")
    @option("description", str, description="어떤 역할/성격의 프롬프트를 만들지 설명하세요 (예: 파이썬 튜터)")
    @option("apply", bool, description="생성된 프롬프트를 현재 채널에 즉시 적용할지 여부", default=False)
    @wrap_log_async
    async def generate_prompt(self, ctx: ApplicationContext, description: str, apply: bool = False) -> None:
        """사용자의 요구사항을 기반으로 맞춤형 LLM 프롬프트를 자동 작성합니다."""
        await ctx.defer()
        meta_instruction: str = (
            "당신은 AI 프롬프트 작성 전문가입니다. "
            "사용자의 요구에 따라 챗봇이 사용할 한국어 System Prompt를 150자 이내로 명확하고 간결하게 작성하세요. "
            "인사말이나 서론 없이, 오직 완성된 프롬프트 지침 텍스트만 출력하세요."
        )
        meta_messages = [
            MessageData(
                id=int(time.time() * 1000),
                content=f"다음 역할/성격에 맞는 챗봇 프롬프트를 간결하게 작성해 줘: {description}",
                author=ctx.author.display_name,
                timestamp=datetime.now(),
                chat_id=0,
            )
        ]

        try:
            generated_prompt: str = self.llm.create(meta_instruction, meta_messages)
            generated_prompt = generated_prompt.strip(' "`\'\n')


            # 빈 응답 검증 및 방어
            if not generated_prompt:
                await ctx.respond("❌ 프롬프트 생성에 실패하였습니다. (LLM에서 빈 응답이 반환되었습니다. 다시 시도해 주세요.)", ephemeral=True)
                return

            response_msg = f"✨ **생성된 시스템 프롬프트:**\n```\n{generated_prompt}\n```"

            if apply:
                chat: Optional[ChatData] = self.chat_database.get_last_channel_chat(ctx.channel.id)
                chat_enabled: bool = chat.chat_enabled if chat else True
                current_model: Optional[str] = chat.model if chat else None

                new_chat = ChatData(
                    id=int(time.time() * 1000),
                    first_message_id=0,
                    name=DEFAULT_BOT_NAME,
                    prompt=generated_prompt,
                    chat_enabled=chat_enabled,
                    messages=[],
                    created_at=datetime.now(),
                    channel_id=ctx.channel.id,
                    model=current_model,
                )
                self.chat_database.create_chat(new_chat)
                response_msg += "\n✅ 현재 채널의 새 세션 프롬프트로 성공적으로 적용되었습니다!"
            else:
                response_msg += "\n💡 *이 프롬프트를 적용하려면 `/llm set_prompt prompt:<내용>` 명령어를 사용하시거나 `/llm generate_prompt apply:True`로 다시 실행하세요.*"

            await ctx.respond(response_msg)
        except Exception as e:
            logger.error(f"프롬프트 생성 실패: {e}")
            await ctx.respond(f"프롬프트 생성 중 오류가 발생했습니다: {e}")



    @llm_cog.command(name="list_models", description="사용 가능한 LLM 모델 목록을 드롭다운 메뉴로 확인하고 선택합니다.")
    @wrap_log_async
    async def list_models(self, ctx: ApplicationContext) -> None:
        """Ollama API를 통해 사용 가능한 모델 목록 및 UI 드롭다운 메뉴를 출력합니다."""
        await ctx.defer()
        available_models: List[str] = self.llm.get_available_models()
        chat: Optional[ChatData] = self.chat_database.get_last_channel_chat(ctx.channel.id)
        current_model: str = (chat.model if chat and chat.model else os.getenv("OLLAMA_MODEL", "gemma4:12b"))

        embed = discord.Embed(
            title="🤖 사용 가능한 LLM 모델 목록",
            description=f"현재 채널에서 선택된 모델: **`{current_model}`**\n\n*아래 드롭다운 메뉴에서 변경할 모델을 바로 선택하세요.*",
            color=discord.Color.green(),
        )

        view = ModelSelectView(
            models=available_models,
            current_model=current_model,
            chat_database=self.chat_database,
            channel_id=ctx.channel.id,
        )
        await ctx.respond(embed=embed, view=view)

    @llm_cog.command(name="list_sessions", description="현재 채널의 대화 세션 목록을 조회하고 UI 드롭다운으로 전환/삭제합니다.")
    @wrap_log_async
    async def list_sessions(self, ctx: ApplicationContext) -> None:
        """현재 채널에 저장된 과거 대화 세션 목록 및 UI 드롭다운을 출력합니다."""
        chats: List[ChatData] = self.chat_database.get_channel_chats(ctx.channel.id, limit=10)
        if not chats:
            await ctx.respond("저장된 세션이 없습니다.", ephemeral=True)
            return

        embed = discord.Embed(
            title="📜 채널 대화 세션 목록",
            description="아래 목록의 번호를 확인하고, 하단 드롭다운 메뉴에서 **세션 전환** 또는 **세션 삭제**를 선택하세요.",
            color=discord.Color.blue(),
        )

        for idx, chat in enumerate(chats, start=1):
            created_str = chat.created_at.strftime("%Y-%m-%d %H:%M:%S")
            msg_count = len(chat.messages)
            prompt_preview = (chat.prompt[:30] + "...") if len(chat.prompt) > 30 else chat.prompt
            is_active = " 🟢 (현재 활성 세션)" if idx == 1 else ""

            embed.add_field(
                name=f"📌 {idx}번 세션 {is_active}",
                value=f"• **세션 ID**: `{chat.id}`\n• **생성 시각**: {created_str}\n• **메시지 수**: {msg_count}개\n• **프롬프트**: {prompt_preview}",
                inline=False,
            )

        view = SessionSelectView(chats=chats, chat_database=self.chat_database)
        await ctx.respond(embed=embed, view=view, ephemeral=False)


    @llm_cog.command(name="select_model", description="현재 채널 세션에서 사용할 LLM 모델을 선택합니다.")
    @option("model_name", str, description="설정할 LLM 모델명 (예: gemma4:12b, qwen2.5:7b)")
    @wrap_log_async
    async def select_model(self, ctx: ApplicationContext, model_name: str) -> None:
        """현재 채널의 대화 세션 모델을 변경합니다."""
        available_models: List[str] = self.llm.get_available_models()
        if available_models and model_name not in available_models:
            models_str = ", ".join([f"`{m}`" for m in available_models])
            await ctx.respond(
                f"⚠️ 입력하신 모델 `{model_name}`이(가) 사용 가능 모델 목록에 없습니다.\n"
                f"사용 가능 모델: {models_str}",
                ephemeral=True,
            )
            return

        chat: Optional[ChatData] = self.chat_database.get_last_channel_chat(ctx.channel.id)
        if chat:
            self.chat_database.update_chat_model(chat.id, model_name)
        else:
            new_chat = ChatData(
                id=int(time.time() * 1000),
                first_message_id=0,
                name=DEFAULT_BOT_NAME,
                prompt=DEFAULT_BOT_INSTRUCTIONS,
                chat_enabled=True,
                messages=[],
                created_at=datetime.now(),
                channel_id=ctx.channel.id,
                model=model_name,
            )
            self.chat_database.create_chat(new_chat)

        await ctx.respond(f"✅ 현재 채널의 대화 모델이 **`{model_name}`**(으)로 설정되었습니다!", ephemeral=False)

    @llm_cog.command(name="set_prompt", description="지정한 시스템 프롬프트로 새 대화 세션을 시작합니다.")
    @option("prompt", str, description="챗봇에 설정할 새 시스템 프롬프트")
    @wrap_log_async
    async def set_prompt(self, ctx: ApplicationContext, prompt: str) -> None:
        """지정한 시스템 프롬프트로 새로운 대화 세션을 시작합니다."""
        chat: Optional[ChatData] = self.chat_database.get_last_channel_chat(ctx.channel.id)
        chat_enabled: bool = chat.chat_enabled if chat else True
        current_model: Optional[str] = chat.model if chat else None

        new_chat: ChatData = ChatData(
            id=int(time.time() * 1000),
            first_message_id=0,
            name=DEFAULT_BOT_NAME,
            prompt=prompt,
            chat_enabled=chat_enabled,
            messages=[],
            created_at=datetime.now(),
            channel_id=ctx.channel.id,
            model=current_model,
        )
        self.chat_database.create_chat(new_chat)
        await ctx.respond(f"새 지정 프롬프트로 대화 세션을 시작하였습니다.\n**설정된 프롬프트:** {new_chat.prompt}", ephemeral=False)

    @llm_cog.command(name="new_chat", description="현재 채널의 대화 세션을 기본 프롬프트로 새로 생성/초기화합니다.")
    @wrap_log_async
    async def new_chat(self, ctx: ApplicationContext) -> None:
        """기존 내역을 보존하면서 기본 프롬프트(DEFAULT_BOT_INSTRUCTIONS)로 새 세션을 시작합니다."""
        chat: Optional[ChatData] = self.chat_database.get_last_channel_chat(ctx.channel.id)
        chat_enabled: bool = chat.chat_enabled if chat else True
        current_model: Optional[str] = chat.model if chat else None

        new_chat: ChatData = ChatData(
            id=int(time.time() * 1000),
            first_message_id=0,
            name=DEFAULT_BOT_NAME,
            prompt=DEFAULT_BOT_INSTRUCTIONS,  # 무조건 디폴트 프롬프트로 초기화!
            chat_enabled=chat_enabled,
            messages=[],
            created_at=datetime.now(),
            channel_id=ctx.channel.id,
            model=current_model,
        )
        self.chat_database.create_chat(new_chat)
        await ctx.respond("기본 프롬프트로 새로운 대화 세션을 생성하였습니다. (기존 대화 이력은 보존되어 있습니다.)", ephemeral=False)

    @llm_cog.command(name="delete_session", description="특정 대화 세션을 데이터베이스에서 삭제합니다.")
    @option("session_id", int, description="삭제할 대화 세션 ID")
    @wrap_log_async
    async def delete_session(self, ctx: ApplicationContext, session_id: int) -> None:
        """지정한 세션 ID의 대화 기록 및 세션을 DB에서 완전히 제거합니다."""
        target_chat: Optional[ChatData] = self.chat_database.get_chat(session_id)
        if not target_chat or target_chat.channel_id != ctx.channel.id:
            await ctx.respond("해당 채널의 올바른 세션 ID가 아닙니다.", ephemeral=True)
            return

        success: bool = self.chat_database.delete_chat(session_id)
        if success:
            await ctx.respond(f"🗑️ 세션 `ID: {session_id}`이(가) 성공적으로 삭제되었습니다.", ephemeral=False)
        else:
            await ctx.respond(f"❌ 세션 `ID: {session_id}` 삭제에 실패하였습니다.", ephemeral=True)



    @llm_cog.command(name="switch_session", description="이전 대화 세션으로 전환합니다.")
    @option("session_id", int, description="전환할 세션 ID")
    @wrap_log_async
    async def switch_session(self, ctx: ApplicationContext, session_id: int) -> None:
        """특정 세션 ID의 과거 세션으로 활성화 세션을 전환합니다."""
        target_chat: Optional[ChatData] = self.chat_database.get_chat(session_id)
        if not target_chat or target_chat.channel_id != ctx.channel.id:
            await ctx.respond("해당 채널의 올바른 세션 ID가 아닙니다.", ephemeral=True)
            return

        # 세션의 생성 시각을 현재로 업데이트하여 가장 최신 세션으로 재설정
        self.chat_database.chats.update_one({"id": session_id}, {"$set": {"created_at": datetime.now()}})
        await ctx.respond(f"세션 `ID: {session_id}`로 성공적으로 전환되었습니다!", ephemeral=False)


    @llm_cog.command(name="toggle_auto_respond", description="현재 채널의 멘션 없는 자동 대답 기능(Auto-Response)을 ON/OFF 합니다.")
    @wrap_log_async
    async def toggle_auto_respond(self, ctx: ApplicationContext) -> None:
        """현재 채널에서 멘션 없이 입력하는 일반 메시지에 자동 대답할지 여부를 설정합니다."""
        current_status: bool = self.chat_database.get_channel_auto_respond(ctx.channel.id)
        new_status: bool = not current_status
        self.chat_database.set_channel_auto_respond(ctx.channel.id, new_status)
        status_str: str = "활성화 (멘션 없이도 항상 대답)" if new_status else "비활성화 (멘션 시에만 대답)"
        await ctx.respond(f"현재 채널의 자동 대답 기능이 **{status_str}**되었습니다.", ephemeral=False)

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

    @llm_cog.command(name="reset_context", description="현재 채널의 대화 컨텍스트/히스토리를 초기화합니다.")
    @wrap_log_async
    async def reset_context(self, ctx: ApplicationContext) -> None:
        """현재 채널/스레드의 대화 히스토리를 리셋하여 새 세션을 시작합니다."""
        await self.new_chat(ctx)


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

