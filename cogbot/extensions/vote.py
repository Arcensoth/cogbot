import logging

from discord.ext import commands
from discord.ext.commands import CommandError, Context

log = logging.getLogger(__name__)


class Vote:
    DEFAULT_REACTIONS = u'✔ ✖'
    ALIAS_MAP = {c: r for c, r in zip('abcdefghijklmnopqrstuvwxyz', '🇦🇧🇨🇩🇪🇫🇬🇭🇮🇯🇰🇱🇲🇳🇴🇵🇶🇷🇸🇹🇺🇻🇼🇽🇾🇿')}

    def __init__(self, bot):
        self.bot = bot

    @commands.command(pass_context=True)
    async def vote(self, ctx: Context, *, reactions=DEFAULT_REACTIONS):
        reactions = reactions.split()
        failure = True
        for reaction in reactions:
            reaction = self.ALIAS_MAP.get(reaction, reaction)
            try:
                await self.bot.add_reaction(ctx.message, reaction)
                failure = False
            except Exception as ex:
                log.warning('Invalid reaction "{}" caused error: {}'.format(reaction, ex))
        if failure:
            raise CommandError('All instances failed')


def setup(bot):
    bot.add_cog(Vote(bot))
