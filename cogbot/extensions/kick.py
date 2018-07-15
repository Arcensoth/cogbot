import logging
import re

from discord import Message, Server
from discord.ext import commands
from discord.ext.commands import Bot, Context

from cogbot import checks
from cogbot.cog_bot import CogBot

log = logging.getLogger(__name__)


class Kick:
    MENTION_PATTERN = re.compile('<@(\w+)>')
    ID_PATTERN = re.compile('\d+')

    def __init__(self, bot: CogBot, ext: str):
        self.bot = bot

    @checks.is_staff()
    @commands.has_permissions(kick_members=True)
    @commands.command(pass_context=True)
    async def kick(self, ctx: Context, user: str, *, reason: str):
        cmd: Message = ctx.message
        server: Server = cmd.server

        # 1. check for a mention
        mention_match = self.MENTION_PATTERN.match(user)
        if mention_match:
            (user_id,) = mention_match.groups()
            member = server.get_member(user_id)

        # 2. check for a raw user id
        elif self.ID_PATTERN.match(user):
            member = server.get_member(user)

        # 3. check for a user string (doesn't work with spaces, etc)
        elif '#' in user:
            member = server.get_member_named(user)

        # otherwise, error
        else:
            await self.bot.mod_log(
                ctx, f'Please provide a mention, an id, or a username + discriminator (without spaces)',
                destination=cmd.channel)
            await self.bot.add_reaction(cmd, '➖')
            return

        if not member:
            await self.bot.mod_log(
                ctx, f'Couldn\'t find anyone matching the input **{user}**', destination=cmd.channel)
            await self.bot.add_reaction(cmd, '❓')
            return

        direct_message = f'You got a warning kick from **{server.name}** for the following reason: {reason}'
        log.info(f'Kicking <{member.name}> with message: {direct_message}')

        try:
            await self.bot.send_message(member, direct_message)
        except:
            log.warning(f'Failed to warn <{member}> about being kicked')
            await self.bot.mod_log(
                ctx, f'Aw. Couldn\'t message **{member}** about being kicked. ¯\_(ツ)_/¯', destination=cmd.channel)

        try:
            await self.bot.kick(member)
        except:
            log.warning(f'Failed to kick <{member}> altogether')
            await self.bot.mod_log(ctx, f'Uh oh! Couldn\'t kick **{member}** at all!', destination=cmd.channel)
            await self.bot.add_reaction(cmd, '❗')
            return

        await self.bot.mod_log(ctx, f'Kicked **{member}** with a warning!', destination=cmd.channel)
        await self.bot.add_reaction(cmd, '👢')


def setup(bot):
    bot.add_cog(Kick(bot, __name__))
