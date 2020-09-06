import json
import logging
import typing
from datetime import datetime

import discord

from cogbot.types import ServerId, ChannelId


log = logging.getLogger(__name__)


class CogBotServerState:
    def __init__(self, bot, server: discord.Server, log_channel: ChannelId = None):
        self.bot = bot
        self.server: discord.Server = server

        # resolve log channel
        self.log_channel: discord.Channel = None
        if log_channel:
            self.log_channel = self.bot.get_channel(log_channel)
            if not self.log_channel:
                log.warning(
                    f"[{self.server}] Failed to resolve log channel <{log_channel}>"
                )

    async def mod_log(
        self,
        member: discord.Member = None,
        content: str = None,
        message: discord.Message = None,
        icon: str = None,
        color: int = None,
        show_timestamp: bool = True,
        channel: discord.Channel = None,
    ):
        actual_channel = channel or self.log_channel
        if self.log_channel:
            icon = icon or ":arrow_right:"
            color = color or discord.Embed.Empty

            description_parts = []
            if member:
                description_parts.append(str(member.mention))
            if content:
                description_parts.append(content)
            description = " ".join(description_parts)

            if message:
                message_link = self.bot.make_message_link(message)
                description = " ".join((f"[{icon}]({message_link})", description))
            else:
                description = " ".join((icon, description))

            if show_timestamp:
                em = discord.Embed(
                    timestamp=datetime.utcnow(), description=description, color=color
                )
            else:
                em = discord.Embed(description=description, color=color)

            if member and message:
                em.set_footer(
                    text=f"{member} in #{message.channel}", icon_url=member.avatar_url
                )
            elif member:
                em.set_footer(text=f"{member}", icon_url=member.avatar_url)

            await self.bot.send_message(actual_channel, embed=em)
