"""
디스코드 봇 커스텀 도움말 커맨드 모듈

기본 도움말 출력 스타일을 커스텀 임베드(Embed) 형태로 재정의합니다.
"""

from typing import Dict, List, Optional, Any
import discord
from discord.ext import commands


class MyHelp(commands.HelpCommand):
    """커스텀 디스코드 도움말 핸들러 클래스"""

    def get_command_signature(self, command: commands.Command[Any, Any, Any]) -> str:
        """명령어 사용법 서명을 문자열로 생성합니다.

        Args:
            command (commands.Command): 도움말을 조회할 커맨드 객체

        Returns:
            str: 포맷팅된 명령어 사용 구문 (예: '!help [command]')
        """
        return f"{self.context.clean_prefix}{command.qualified_name} {command.signature}"

    async def send_bot_help(
        self, mapping: Dict[Optional[commands.Cog], List[commands.Command[Any, Any, Any]]]
    ) -> None:
        """전체 봇 도움말 목록을 카테고리(Cog)별로 임베드로 전송합니다.

        Args:
            mapping (Dict[Optional[commands.Cog], List[commands.Command]]): Cog와 명령어의 매핑 딕셔너리
        """
        embed: discord.Embed = discord.Embed(title="도움말", color=discord.Color.blurple())

        for cog, cmds in mapping.items():
            filtered: List[commands.Command[Any, Any, Any]] = await self.filter_commands(cmds, sort=True)
            command_signatures: List[str] = [self.get_command_signature(c) for c in filtered]

            if command_signatures:
                cog_name: str = getattr(cog, "qualified_name", "일반")
                embed.add_field(name=cog_name, value="\n".join(command_signatures), inline=False)

        channel = self.get_destination()
        await channel.send(embed=embed)

    async def send_command_help(self, command: commands.Command[Any, Any, Any]) -> None:
        """개별 명령어에 대한 상세 도움말을 전송합니다.

        Args:
            command (commands.Command): 상세 정보를 조회할 커맨드
        """
        embed: discord.Embed = discord.Embed(
            title=self.get_command_signature(command), color=discord.Color.random()
        )
        if command.help:
            embed.description = command.help
        if alias := command.aliases:
            embed.add_field(name="별칭 (Aliases)", value=", ".join(alias), inline=False)

        channel = self.get_destination()
        await channel.send(embed=embed)

    async def send_cog_help(self, cog: commands.Cog) -> None:
        """특정 카테고리(Cog)에 속한 명령어 목록 도움말을 전송합니다.

        Args:
            cog (commands.Cog): 조회할 Cog 카테고리
        """
        embed: discord.Embed = discord.Embed(
            title=cog.qualified_name or "일반",
            description=cog.description,
            color=discord.Color.blurple(),
        )

        if filtered_commands := await self.filter_commands(cog.get_commands()):
            for command in filtered_commands:
                embed.add_field(
                    name=self.get_command_signature(command),
                    value=command.help or "도움말 설명이 없습니다.",
                )

        await self.get_destination().send(embed=embed)

    async def send_group_help(self, group: commands.Group[Any, Any, Any]) -> None:
        """명령어 그룹에 대한 하위 명령어 목록 도움말을 전송합니다.

        Args:
            group (commands.Group): 조회할 그룹 커맨드
        """
        embed: discord.Embed = discord.Embed(
            title=self.get_command_signature(group),
            description=group.help,
            color=discord.Color.blurple(),
        )

        if filtered_commands := await self.filter_commands(group.commands):
            for command in filtered_commands:
                embed.add_field(
                    name=self.get_command_signature(command),
                    value=command.help or "도움말 설명이 없습니다.",
                )

        await self.get_destination().send(embed=embed)

    async def send_error_message(self, error: str) -> None:
        """도움말 요청 시 발생한 오류 메시지를 전송합니다.

        Args:
            error (str): 에러 설명 문자열
        """
        embed: discord.Embed = discord.Embed(title="오류", description=error, color=discord.Color.red())
        channel = self.get_destination()
        await channel.send(embed=embed)

