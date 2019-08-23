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
        self, member: discord.Member, content: str, channel: discord.Channel = None
    ):
        if self.log_channel:
            now = datetime.utcnow()
            quote_name = f"{member.display_name} ({member.name}#{member.discriminator})"
            em = discord.Embed(description=content, timestamp=now)
            em.set_author(name=quote_name, icon_url=member.avatar_url)
            em.set_footer(text=f"#{channel}" if channel else None)
            await self.bot.send_message(self.log_channel, embed=em)
