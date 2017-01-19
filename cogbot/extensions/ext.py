from discord.ext import commands
from discord.ext.commands import Context


class Ext:
    def __init__(self, bot):
        self.bot = bot

    @commands.group(pass_context=True, name='ext')
    async def cmd_ext(self, ctx: Context):
        if ctx.invoked_subcommand is None:
            ext_str = ', '.join([f'`{ext}`' for ext in self.bot.extensions])
            reply = f'Loaded extensions: {ext_str}'
            await self.bot.send_message(ctx.message.channel, reply)


def setup(bot):
    bot.add_cog(Ext(bot))
