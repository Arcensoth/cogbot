from discord.ext import commands
from discord.ext.commands import Context

from cogbot import checks
from cogbot.cog_bot import CogBot


class React:
    def __init__(self, bot):
        self.bot: CogBot = bot

    @checks.is_staff()
    @commands.command(pass_context=True)
    async def react(self, ctx: Context, channel_id, message_id, *emojis):
        channel = self.bot.get_channel(channel_id)
        message = await self.bot.get_message(channel, message_id)
        for emoji in emojis:
            await self.bot.add_reaction(message, emoji)
        await self.bot.react_success(ctx)


def setup(bot):
    bot.add_cog(React(bot))
