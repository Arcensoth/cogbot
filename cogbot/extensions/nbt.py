import logging

from discord.ext import commands
from discord.ext.commands import Context
from nbtlib import parse_nbt

log = logging.getLogger(__name__)


class NBT:
    def __init__(self, bot):
        self.bot = bot

    async def nbt(self, ctx: Context, nbtstring: str):
        try:
            parse_nbt(nbtstring)
            await self.bot.add_reaction(ctx.message, u'✅')
        except ValueError as e:
            await self.bot.add_reaction(ctx.message, u'😬')
            await self.bot.send_message(ctx.message.channel, f'{ctx.message.author.mention} {str(e)}!')
        except:
            log.exception('An unexpected error occurred while parsing NBT: {}'.format(nbtstring))
            await self.bot.add_reaction(ctx.message, u'💩')

    @commands.command(pass_context=True, name='nbt')
    async def cmd_nbt(self, ctx: Context, *, nbtstring):
        await self.nbt(ctx, nbtstring)


def setup(bot):
    bot.add_cog(NBT(bot))
