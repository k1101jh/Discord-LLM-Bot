import os
import discord
import time
from datetime import datetime
from discord.ext import commands
from discord import Message
from discord.ext.pages import Paginator, Page
from dotenv import load_dotenv

from util.logger import wrap_log
from util.logger import logger
from llm.base_llm import BaseLLM
from llm.llm_loader import load_llm
from database.database import ChatDatabase
from database.database import ChatData, MessageData
from cogs.llm_cog import LLMCog
from help_command import MyHelp

load_dotenv()


intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(commands.when_mentioned_or("!"), intents=intents)

help_attributes = {
    "name": "help",
    "aliases": ["helpme"],
    "cooldown": commands.CooldownMapping.from_cooldown(3, 5, commands.BucketType.user),
}
bot.add_cog(LLMCog(bot))
bot.help_command = MyHelp(command_attrs=help_attributes)

### start bot
token = str(os.getenv("DISCORD_TOKEN"))
bot.run(token)
