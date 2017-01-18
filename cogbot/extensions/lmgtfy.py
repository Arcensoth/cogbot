import urllib.parse

from discord.ext import commands
from discord.ext.commands import Context


class LMGTFY:
    def __init__(self, bot):
        self.bot = bot

    @commands.command(pass_context=True)
    async def lmgtfy(self, ctx: Context, *query):
        querystring = urllib.parse.urlencode(dict(q=' '.join(query)))
        await self.bot.say(f'http://lmgtfy.com/?{querystring}')


def setup(bot):
    bot.add_cog(LMGTFY(bot))
