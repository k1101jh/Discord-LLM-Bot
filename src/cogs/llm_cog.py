import os
import time
import discord
from dotenv import load_dotenv
from datetime import datetime
from discord.commands import option
from discord.ext import commands, pages
from discord.commands import SlashCommandGroup
from discord.ext.pages import Paginator, Page
from discord import ApplicationContext
from llm.llm_loader import load_llm

from discord import Message
from database.database import ChatDatabase
from database.database import MessageData
from database.database import ChatData
from util.logger import wrap_log, wrap_log_async, logger


class LLMCog(commands.Cog):
    def __init__(self, bot):
        load_dotenv()
        self.bot = bot
        self.llm = load_llm()

        ### DB
        database_uri = os.getenv("MONGO_URI")
        database_name = os.getenv("DATABASE_NAME")

        self.chat_database = ChatDatabase(uri=database_uri, db_name=database_name)

        ### page
        self.pages = []

    llm_cog = SlashCommandGroup("llm", "Commands for llm.")

    @commands.Cog.listener()
    @wrap_log_async
    async def on_message(self, message: Message):
        # This function listens for incoming messages and generates a response using the LLM

        # Ignore messages from the bot itself
        if message.author == self.bot.user:
            return

        # Ignore command messages
        if message.content.startswith("!") or message.content.startswith("/"):
            return

        # Ignore messages that mention someone
        if message.mentions:
            return

        ctx = await self.bot.get_context(message)

        # Show typing indicator while generating response
        async with ctx.typing():
            # Get last chat or create a new one
            chat = self.chat_database.get_last_channel_chat(message.channel.id)
            new_chat = False
            if chat is None:
                new_chat = True
                chat = ChatData(
                    id=int(time.time() * 1000),
                    first_message_id=0,
                    messages=[],
                    created_at=datetime.now(),
                    channel_id=message.channel.id,
                )

            new_message = MessageData(
                id=int(time.time() * 1000),
                content=message.content,
                author=message.author.display_name,
                timestamp=message.created_at,
                chat_id=chat.id,
            )

            if not new_chat:
                # Add new message to existing chat
                self.chat_database.add_message(chat.id, new_message)
                chat.messages.append(new_message)
            else:
                # Create new chat and add first message
                chat.first_message_id = new_message.id
                chat.messages.append(new_message)
                self.chat_database.create_chat(chat)

            try:
                # Generate response from LLM
                response = self.llm.create(chat.messages)

                # Add LLM response to new chat
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
                logger.error(e)
                response = str(e)
                # delete last user message in self.chat
                self.chat_database.delete_message(chat.id, chat.messages[-1].id)

        await ctx.send(response)

    @llm_cog.command(name="prompt", description="현재 프롬프트 출력")
    @wrap_log_async
    async def print_prompt(self, ctx):
        await ctx.respond(f"현재 프롬프트:\n{self.llm.prompt}", ephemeral=False)

    @llm_cog.command(name="set_prompt", description="프롬프트 수정")
    @wrap_log_async
    async def set_prompt(self, ctx: ApplicationContext, prompt):
        self.llm.prompt = prompt
        await ctx.respond("프롬프트를 수정하였습니다.\n프롬프트: {self.llm.prompt", ephemeral=False)

    @llm_cog.command(name="delete_last_message", description="마지막 메시지 제거")
    @wrap_log_async
    async def delete_last_message(self, ctx: ApplicationContext):
        chat = self.chat_database.get_last_channel_chat(ctx.channel.id)
        if chat is not None and len(chat.messages) >= 2:
            self.chat_database.delete_last_message(chat.id)
            self.chat_database.delete_last_message(chat.id)
            await ctx.respond("마지막 메시지를 제거하였습니다.", ephemeral=False)
        else:
            await ctx.respond("제거할 메시지가 없습니다.", ephemeral=True)

    @llm_cog.command(name="new_chat", description="start new chat")
    @wrap_log_async
    async def new_chat(self, ctx: ApplicationContext):
        chat = self.chat_database.get_last_channel_chat(ctx.channel.id)
        if self.chat_database.delete_chat(chat.id):
            await ctx.respond("채팅 내역을 초기화했습니다.", ephemeral=False)
        else:
            await ctx.respond("채팅 내역이 없습니다.", ephemeral=True)

    @llm_cog.command(name="history", description="display chat history")
    @wrap_log_async
    async def history(self, ctx: ApplicationContext):
        chat = self.chat_database.get_last_channel_chat(ctx.channel.id)
        if chat == None:
            await ctx.respond("채팅 내역을 찾을 수 없습니다.", ephemeral=True)
        chat_pages = []
        embed_fields = []
        for message in chat.messages:
            content = message.content
            if len(content) > 256:
                content = content[:50] + "\n...\n" + content[-50:]

            embed_fields.append(
                discord.EmbedField(name=f"{message.author}:", value=f"{content}", inline=False)
            )
            if len(embed_fields) == 10:
                chat_pages.append(discord.Embed(title="History", fields=embed_fields))
                embed_fields = []

        if embed_fields:
            chat_pages.append(discord.Embed(title="History", fields=embed_fields))

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

    @llm_cog.command(name="test", description="Test command")
    # @wrap_log_async
    @option(
        "test",
        description="test",
        autocomplete=discord.utils.basic_autocomplete(["test"]),
    )
    async def test(self, ctx: ApplicationContext, test: str):
        await ctx.respond(f"test: {test}", ephemeral=False)
