import logging

import discord
import requests
from discord.ext import commands
from discord.ext.commands import Context

from cogbot import checks
from cogbot.cog_bot import CogBot

log = logging.getLogger(__name__)


class Nick:
    def __init__(self, bot):
        self.bot: CogBot = bot

    def needs_correction(self, nick: str) -> bool:
        return nick and nick.startswith("!")

    async def on_member_update(self, before: discord.Member, after: discord.Member):
        if self.needs_correction(after.nick):
            log.info(f"Correcting member nickname: {after.nick}")
            await self.bot.change_nickname(after, f"\u17b5{after.nick}")


def setup(bot):
    bot.add_cog(Nick(bot))
