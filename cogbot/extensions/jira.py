import re
import urllib.parse

from discord.ext import commands
from discord.ext.commands import Context

from cogbot.cog_bot import CogBot


class Jira:
    REPORT_PATTERN = re.compile('^(mc-)?(\d+)$', re.IGNORECASE)

    def __init__(self, bot: CogBot, ext: str):
        self.bot = bot

    @commands.command(pass_context=True)
    async def jira(self, ctx: Context, *, query: str):
        rmatch = self.REPORT_PATTERN.match(query)
        if rmatch:
            rgroups = rmatch.groups()
            report_no = rgroups[1]
            url = 'https://bugs.mojang.com/browse/MC-' + report_no
        else:
            search_url = urllib.parse.urlencode({'searchString': query})
            url = 'https://bugs.mojang.com/secure/QuickSearch.jspa?' + search_url
        await self.bot.say(url)
        await self.bot.react_success(ctx)


def setup(bot):
    bot.add_cog(Jira(bot, __name__))
