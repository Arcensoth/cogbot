from discord.ext import commands
from discord.ext.commands import Context


class Ping:
    def __init__(self, bot):
        self.bot = bot

    @commands.command(pass_context=True)
    async def ping(self, ctx: Context):
        await self.bot.say(f'{ctx.message.author.mention} Pong!')
        await self.bot.add_reaction(ctx.message, u'🏓')


def setup(bot):
    bot.add_cog(Ping(bot))
