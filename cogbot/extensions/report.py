import logging

from discord import User, Message, Channel
from discord.ext import commands
from discord.ext.commands import Context

from cogbot import checks
from cogbot.cog_bot import CogBot

log = logging.getLogger(__name__)


class Report:
    def __init__(self, bot: CogBot, ext: str):
        self.bot = bot
        self.options = bot.state.get_extension_state(ext)

    async def add_report(self, channel: Channel, user: User, reason: str):
        """ Add a report for the given user in the given server with the given reason. """
        await self.bot.send_message(channel, f'Successfully disambiguated user: {user}')  # TEMP

    async def get_reports(self, channel: Channel, user: User):
        """ Query reports for the given user in the given server. """
        await self.bot.send_message(channel, f'Successfully disambiguated user: {user}')  # TEMP

    @checks.is_moderator()
    @commands.command(pass_context=True, name='report')
    async def cmd_report(self, ctx: Context, user: str, *, reason: str = None):
        message: Message = ctx.message
        channel: Channel = message.channel
        user: User = await self.bot.disambiguate_user(ctx, user)
        if reason:
            await self.add_report(channel, user, reason)
            await self.bot.react_success(ctx)
        else:
            await self.get_reports(channel, user)


def setup(bot):
    bot.add_cog(Report(bot, __name__))
