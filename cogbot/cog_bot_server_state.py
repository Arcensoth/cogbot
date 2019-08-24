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
        member: discord.Member,
        content: str,
        message: discord.Message = None,
        icon: str = None,
        color: int = None,
    ):
        if self.log_channel:
            icon = icon or ":arrow_right:"
            color = color or discord.Embed.Empty

            timestamp = datetime.utcnow()
            description = f"{member.mention} {content}"

            if message:
                message_link = self.bot.make_message_link(message)
                description = " ".join((f"[{icon}]({message_link})", description))
            else:
                description = " ".join((icon, description))

            em = discord.Embed(
                timestamp=timestamp, description=description, color=color
            )

            if message:
                em.set_footer(
                    text=f"{member} in #{message.channel}", icon_url=member.avatar_url
                )
            else:
                em.set_footer(text=f"{member}", icon_url=member.avatar_url)

            await self.bot.send_message(self.log_channel, embed=em)
