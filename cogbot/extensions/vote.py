import logging
import re

from discord.ext import commands
from discord.ext.commands import CommandError, Context

log = logging.getLogger(__name__)


class Vote:
    def __init__(self, bot):
        self.bot = bot

    @commands.command(pass_context=True)
    async def vote(self, ctx: Context):
        await self.bot.add_reaction(ctx.message, u'👍')
        await self.bot.add_reaction(ctx.message, u'👎')


def setup(bot):
    bot.add_cog(Vote(bot))
