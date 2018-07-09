import logging

from discord.ext import commands
from discord.ext.commands import Context

from cogbot import checks

log = logging.getLogger(__name__)


class Kick:
    def __init__(self, bot):
        self.bot = bot

    @checks.is_staff()
    @commands.command(pass_context=True)
    async def kick(self, ctx: Context, user: str, reason: str):
        pass


def setup(bot):
    bot.add_cog(Kick(bot))
