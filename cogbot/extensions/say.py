from discord.ext import commands
from discord.ext.commands import Context

from cogbot import checks
from cogbot.cog_bot import CogBot


class Say:
    def __init__(self, bot):
        self.bot: CogBot = bot

    @checks.is_staff()
    @commands.command(pass_context=True, hidden=True)
    async def say(self, ctx: Context, channel_id, *, message: str):
        channel = self.bot.get_channel(channel_id)
        await self.bot.send_message(channel, message)
        await self.bot.react_success(ctx)


def setup(bot):
    bot.add_cog(Say(bot))
