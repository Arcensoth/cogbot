from cogbot import checks
from discord.ext import commands
from discord.ext.commands import Context, Bot


class Say:
    def __init__(self, bot):
        self.bot: Bot = bot

    @checks.is_manager()
    @commands.command(pass_context=True)
    async def say(self, ctx: Context, *, message: str):
        await self.bot.delete_message(ctx.message)
        await self.bot.say(message)


def setup(bot):
    bot.add_cog(Say(bot))
