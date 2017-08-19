import logging
import re

from discord.ext import commands
from discord.ext.commands import CommandError, Context

log = logging.getLogger(__name__)


class Vote:
    DEFAULT_REACTIONS = u'✔ ✖'
    ALIAS_MAP = {c: r for c, r in zip(
        'abcdefghijklmnopqrstuvwxyz',
        '🇦🇧🇨🇩🇪🇫🇬🇭🇮🇯🇰🇱🇲🇳🇴🇵🇶🇷🇸🇹🇺🇻🇼🇽🇾🇿')}
    SERVER_EMOJI_PATTERN = re.compile('<:(\w+):(\d+)>')

    def __init__(self, bot):
        self.bot = bot

    @commands.command(pass_context=True)
    async def vote(self, ctx: Context, *, reactions=DEFAULT_REACTIONS):
        reactions = reactions.split()

        failure = True

        for reaction in reactions:
            # aliases take precedence
            reaction = self.ALIAS_MAP.get(reaction.lower(), reaction)

            # handle server emojis exceptionally
            if reaction.startswith('<'):
                match = self.SERVER_EMOJI_PATTERN.match(reaction)
                if match:
                    emoji_name, emoji_id = match.groups()
                    reaction = '{}:{}'.format(emoji_name, emoji_id)
                else:
                    # skip invalid custom emoji
                    continue

            try:
                await self.bot.add_reaction(ctx.message, reaction)
                failure = False
            except Exception as ex:
                log.warning('Invalid reaction "{}" caused error: {}'.format(reaction, ex))

        if failure:
            raise CommandError('All instances failed')


def setup(bot):
    bot.add_cog(Vote(bot))
