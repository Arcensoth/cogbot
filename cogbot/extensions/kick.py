import logging

from discord import Message, Server
from discord.ext import commands
from discord.ext.commands import Bot, Context

from cogbot import checks

log = logging.getLogger(__name__)


class Kick:
    def __init__(self, bot):
        self.bot: Bot = bot

    @checks.is_staff()
    @commands.command(pass_context=True)
    async def kick(self, ctx: Context, name: str, *, reason: str):
        cmd: Message = ctx.message
        server: Server = cmd.server

        if '#' not in name:
            await self.bot.send_message(
                cmd.channel, f'Please provide an exact username with discriminator, like so: `Username#1234`')
            await self.bot.add_reaction(cmd, '➖')
            return

        member = server.get_member_named(name)

        if not member:
            await self.bot.send_message(cmd.channel, f'Couldn\'t find anyone with the name **{name}**')
            await self.bot.add_reaction(cmd, '❓')
            return

        direct_message = f'You got a warning kick from **{server.name}** for the following reason: {reason}'
        log.info(f'Kicking <{member.name}> with message: {direct_message}')

        try:
            await self.bot.send_message(member, direct_message)
        except:
            log.warning(f'Failed to warn <{member.name}> about being kicked')
            await self.bot.send_message(
                cmd.channel, f'Aw. Couldn\'t message **{member.name}** about being kicked. ¯\_(ツ)_/¯')

        try:
            await self.bot.kick(member)
        except:
            log.warning(f'Failed to kick <{member.name}> altogether')
            await self.bot.send_message(cmd.channel, f'Uh oh! Couldn\'t kick **{member.name}** at all!')
            await self.bot.add_reaction(cmd, '❗')
            return

        await self.bot.add_reaction(cmd, '✔')


def setup(bot):
    bot.add_cog(Kick(bot))
