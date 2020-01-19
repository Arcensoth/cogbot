import logging

from discord.ext import commands
from discord.ext.commands import Context

from cogbot import checks
from cogbot.cog_bot import CogBot

log = logging.getLogger(__name__)


class Say:
    def __init__(self, bot):
        self.bot: CogBot = bot

    @checks.is_manager()
    @commands.command(
        pass_context=True,
        name="reboot",
        aliases=["haveutriedturningitoffandbackonagain"],
        hidden=True,
    )
    async def cmd_reboot(self, ctx: Context):
        log.warning('Bot is being forcefully rebooted...')
        await self.bot.add_reaction(ctx.message, "🤖")
        # the bot should auto-recover, reloading all state and extensions
        await self.bot.logout()
        log.warning('Bot should attempt auto-recovery...')


def setup(bot):
    bot.add_cog(Say(bot))
