import sys

import discord
from discord.ext import commands
from discord.ext.commands import Context

import cogbot
from cogbot import checks
from cogbot.cog_bot import CogBot


class Status:
    def __init__(self, bot: CogBot, ext: str):
        self.bot = bot

    @checks.is_manager()
    @commands.command(pass_context=True, name='status')
    async def cmd_status(self, ctx: Context):
        pyv = sys.version_info

        rows = (
            ('python version', f'{pyv[0]}.{pyv[1]}.{pyv[2]}'),
            ('discord.py version', discord.__version__),
            ('cogbot version', cogbot.__version__),
        )

        pad = 1 + max(len(row[0]) for row in rows)

        innards = (''.join((f'{row[0]}:'.ljust(pad), '  ', row[1])) for row in rows)

        await self.bot.say('\n'.join(('```', '\n'.join(innards), '```')))


def setup(bot):
    bot.add_cog(Status(bot, __name__))
