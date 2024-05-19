import discord
from discord.ext import commands


class MyHelp(commands.HelpCommand):
    def get_command_signature(self, command):
        return "%s%s %s" % (self.context.clean_prefix, command.qualified_name, command.signature)
            
    async def send_bot_help(self, mapping):
        embed = discord.Embed(title="Help", color=discord.Color.blurple())

        for cog, commands in mapping.items():
            filtered = await self.filter_commands(commands, sort=True)
            command_signatures = [self.get_command_signature(c) for c in filtered]

            if command_signatures:
                cog_name = getattr(cog, "qualified_name", "No Category")
                embed.add_field(name=cog_name, value="\n".join(command_signatures), inline=False)

        channel = self.get_destination()
        await channel.send(embed=embed)

    async def send_command_help(self, command):
        embed = discord.Embed(title=self.get_command_signature(command), color=discord.Color.random())
        if command.help:
            embed.description = command.help
        if alias := command.aliases:
            embed.add_field(name="Aliases", value=", ".join(alias), inline=False)

        channel = self.get_destination()
        await channel.send(embed=embed)

    def get_command_signature(self, command):
        return "%s%s %s" % (self.context.clean_prefix, command.qualified_name, command.signature)

    async def send_cog_help(self, cog):
        embed = discord.Embed(
            title=cog.qualified_name or "No Category",
            description=cog.description,
            color=discord.Color.blurple(),
        )

        if filtered_commands := await self.filter_commands(cog.get_commands()):
            for command in filtered_commands:
                embed.add_field(
                    name=self.get_command_signature(command),
                    value=command.help or "No Help Message Found... ",
                )

        await self.get_destination().send(embed=embed)

    async def send_group_help(self, group):
        embed = discord.Embed(
            title=self.get_command_signature(group), description=group.help, color=discord.Color.blurple()
        )

        if filtered_commands := await self.filter_commands(group.commands):
            for command in filtered_commands:
                embed.add_field(
                    name=self.get_command_signature(command),
                    value=command.help or "No Help Message Found... ",
                )

        await self.get_destination().send(embed=embed)

    async def send_error_message(self, error):
        embed = discord.Embed(title="Error", description=error, color=discord.Color.red())
        channel = self.get_destination()

        await channel.send(embed=embed)
