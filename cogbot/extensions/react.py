from discord.ext import commands
from discord.ext.commands import Context, Bot

from cogbot import checks


class React:
    def __init__(self, bot):
        self.bot: Bot = bot

    @checks.is_manager()
    @commands.command(pass_context=True)
    async def react(self, ctx: Context, message_id, *emojis):
        await self.bot.delete_message(ctx.message)
        message = await self.bot.get_message(ctx.message.channel, message_id)
        for emoji in emojis:
            await self.bot.add_reaction(message, emoji)


def setup(bot):
    bot.add_cog(React(bot))
