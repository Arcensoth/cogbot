import logging

from discord.ext import commands
from discord.ext.commands import Context

from cogbot import checks
from cogbot.cog_bot import CogBot

log = logging.getLogger(__name__)


class Ext:
    def __init__(self, bot: CogBot, ext: str):
        self.bot = bot

    @checks.is_manager()
    @commands.group(pass_context=True, name='ext', hidden=True)
    async def cmd_ext(self, ctx: Context):
        if ctx.invoked_subcommand is None:
            reply = '\n'.join(['Loaded extensions:'] + [f'    - {ext}' for ext in self.bot.extensions])
            await self.bot.send_message(ctx.message.channel, reply)

    @cmd_ext.command(pass_context=True, name='load')
    async def cmd_ext_load(self, ctx: Context, *extensions):
        self.bot.load_extensions(*extensions)
        await self.bot.react_success(ctx)

    @cmd_ext.command(pass_context=True, name='unload')
    async def cmd_ext_unload(self, ctx: Context, *extensions):
        self.bot.unload_extensions(*extensions)
        await self.bot.react_success(ctx)

    @cmd_ext.command(pass_context=True, name='reload')
    async def cmd_ext_reload(self, ctx: Context, *extensions):
        # Unload in order, then load in reverse order.
        self.bot.unload_extensions(*extensions)
        self.bot.load_extensions(*tuple(reversed(extensions)))
        await self.bot.react_success(ctx)


def setup(bot):
    bot.add_cog(Ext(bot, __name__))
