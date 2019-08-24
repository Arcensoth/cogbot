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
        content: str,
        member: discord.Member = None,
        message: discord.Message = None,
    ):
        if self.log_channel:
            if not member:
                member = message.author if message else None

            em = discord.Embed(
                timestamp=datetime.utcnow(),
                description=content,
                # title="View message" if message else None,
                # url=self.bot.make_message_link(message) if message else None,
            )

            if member:
                em.set_author(
                    name=f"{member.display_name} ({member.name}#{member.discriminator})",
                    icon_url=member.avatar_url,
                )

            if message:
                em.set_footer(text=f"#{message.channel}")

            await self.bot.send_message(
                self.log_channel,
                embed=em,
                content="> " + self.bot.make_message_link(message) if message else None,
            )
