import logging

from discord.ext import commands
from discord.ext.commands import Context

from cogbot.cog_bot import CogBot

log = logging.getLogger(__name__)


class Ext:
    def __init__(self, bot: CogBot, ext: str):
        self.bot = bot

    @commands.group(pass_context=True, name='ext')
    async def cmd_ext(self, ctx: Context):
        if ctx.invoked_subcommand is None:
            ext_str = ', '.join([f'`{ext}`' for ext in self.bot.extensions])
            reply = f'Loaded extensions: {ext_str}'
            await self.bot.send_message(ctx.message.channel, reply)

    @cmd_ext.command(pass_context=True, name='load')
    async def cmd_ext_load(self, ctx: Context, *extensions):
        for ext in extensions:
            self.bot.load_extension(ext)
        await self.bot.react_success(ctx)

    @cmd_ext.command(pass_context=True, name='unload')
    async def cmd_ext_unload(self, ctx: Context, *extensions):
        for ext in extensions:
            self.bot.unload_extension(ext)
        await self.bot.react_success(ctx)


def setup(bot):
    bot.add_cog(Ext(bot, __name__))
