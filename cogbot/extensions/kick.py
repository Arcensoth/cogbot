import logging
import re

from discord import Message, Server
from discord.ext import commands
from discord.ext.commands import Bot, Context

from cogbot import checks
from cogbot.cog_bot import CogBot

log = logging.getLogger(__name__)


class Kick:
    MENTION_PATTERN = re.compile("<@(\w+)>")
    ID_PATTERN = re.compile("\d+")

    def __init__(self, bot: CogBot, ext: str):
        self.bot = bot

    @checks.is_staff()
    @commands.has_permissions(kick_members=True)
    @commands.command(pass_context=True, hidden=True)
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
        elif "#" in user:
            member = server.get_member_named(user)

        # otherwise, error
        else:
            response = "Please provide a mention, an id, or a username + discriminator (without spaces)"
            await self.bot.send_message(cmd.channel, response)
            await self.bot.add_reaction(cmd, "➖")
            return

        if not member:
            response = f"Couldn't find anyone matching the input: {user}"
            await self.bot.send_message(cmd.channel, response)
            await self.bot.add_reaction(cmd, "❓")
            return

        elif member == self.bot.user:
            response = f"I don't think you want to do that."
            await self.bot.send_message(cmd.channel, response)
            await self.bot.add_reaction(cmd, "🤖")
            return

        direct_message = (
            f"You got a warning kick from **{server.name}** for:\n>>> {reason}"
        )
        log.info(f"Kicking <{member.name}> with message: {direct_message}")

        try:
            await self.bot.send_message(member, direct_message)
            await self.bot.mod_log(
                cmd.author,
                f"Messaged {member.mention} about being kicked for:\n>>> {reason}",
                context=ctx,
            )
        except:
            log.warning(f"Unable to warn <{member}> about being kicked")
            await self.bot.mod_log(
                cmd.author,
                f"Unable to message {member.mention} about being kicked. They may have DMs disabled.",
                context=ctx,
            )

        try:
            await self.bot.kick(member)
        except:
            log.warning(f"Failed to kick <{member}>")
            await self.bot.send_message(
                cmd.channel,
                f"Uh oh! Couldn't kick {member.mention}! You should look in to this.",
            )
            await self.bot.add_reaction(cmd, "❗")
            return

        response = f"Kicked {member.mention} with a warning!"
        await self.bot.mod_log(cmd.author, response, context=ctx)
        await self.bot.send_message(cmd.channel, response)
        await self.bot.add_reaction(cmd, "👢")


def setup(bot):
    bot.add_cog(Kick(bot, __name__))
