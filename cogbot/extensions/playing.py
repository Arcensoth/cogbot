from discord import Game
from discord.ext import commands
from discord.ext.commands import Context

from cogbot import checks
from cogbot.cog_bot import CogBot


class Playing:
    def __init__(self, bot):
        self.bot: CogBot = bot

    @checks.is_manager()
    @commands.command(pass_context=True)
    async def playing(self, ctx: Context, *, game: str):
        await self.bot.change_presence(game=Game(name=game))
        await self.bot.react_success(ctx)


def setup(bot):
    bot.add_cog(Playing(bot))
