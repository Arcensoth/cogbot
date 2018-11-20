import requests
from discord.ext import commands
from discord.ext.commands import Context

from cogbot import checks
from cogbot.cog_bot import CogBot


class Avatar:
    def __init__(self, bot):
        self.bot: CogBot = bot

    @checks.is_manager()
    @commands.command(pass_context=True, hidden=True)
    async def avatar(self, ctx: Context, *, url: str):
        image_response = requests.get(url)
        image_data = image_response.content
        await self.bot.edit_profile(avatar=image_data)
        await self.bot.react_success(ctx)


def setup(bot):
    bot.add_cog(Avatar(bot))
