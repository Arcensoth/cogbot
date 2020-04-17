import logging

import discord
from discord.ext import commands
from discord.ext.commands import CommandError, Context

log = logging.getLogger(__name__)


DEFAULT_EMOJI = ("👍", "👎")


class Vote:
    def __init__(self, bot):
        self.bot = bot

    @commands.command(pass_context=True)
    async def vote(self, ctx: Context):
        message: discord.Message = ctx.message
        emojis = self.bot.get_emojis(message) or DEFAULT_EMOJI
        for emoji in emojis[:10]:
            await self.bot.add_reaction(message, emoji)


def setup(bot):
    bot.add_cog(Vote(bot))
