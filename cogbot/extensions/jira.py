import re
import urllib.parse

from discord.ext import commands
from discord.ext.commands import Context

from cogbot.cog_bot import CogBot


class JiraConfig:
    def __init__(self, **options):
        self.base_url = options['base_url']


class Jira:
    REPORT_PATTERN = re.compile('^(mc-)?(\d+)$', re.IGNORECASE)

    def __init__(self, bot: CogBot, ext: str):
        self.bot = bot
        self.config = JiraConfig(**bot.state.get_extension_state(ext))

    @commands.command(pass_context=True)
    async def jira(self, ctx: Context, *, query: str):
        rmatch = self.REPORT_PATTERN.match(query)
        if rmatch:
            rgroups = rmatch.groups()
            report_no = rgroups[1]
            url = ''.join((self.config.base_url, '/browse/MC-', report_no))
        else:
            search_url = urllib.parse.urlencode({'searchString': query})
            url = ''.join((self.config.base_url, '/secure/QuickSearch.jspa?', search_url))
        await self.bot.say(url)


def setup(bot):
    bot.add_cog(Jira(bot, __name__))
