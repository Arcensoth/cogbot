import logging
import re
import typing
from datetime import datetime, timedelta

import discord
from discord.ext import commands
from discord.ext.commands import CommandError, Context

from cogbot import checks
from cogbot.cog_bot import ChannelId, CogBot, ServerId

log = logging.getLogger(__name__)


class NominateServerState:
    def __init__(
        self,
        bot: CogBot,
        server: discord.Server,
        recency_in_days: int,
        help_channels: typing.List[ChannelId],
        other_channels: typing.List[ChannelId],
    ):
        self.bot: CogBot = bot
        self.server: discord.Server = server

        self.recency_in_days: int = recency_in_days

        self.help_channels: typing.List[discord.Channel] = [
            self.bot.get_channel(channel_id) for channel_id in help_channels
        ]

        help_channels_str = ", ".join(str(channel) for channel in self.help_channels)
        log.info(f"Resolved help channels: {help_channels_str}")

        self.other_channels: typing.List[discord.Channel] = [
            self.bot.get_channel(channel_id) for channel_id in other_channels
        ]

        other_channels_str = ", ".join(str(channel) for channel in self.other_channels)
        log.info(f"Resolved other channels: {other_channels_str}")

    async def count_recent_messages(
        self, channel: discord.Channel, member: discord.Member, since: datetime
    ) -> int:
        # this is horribly inefficient but apparently there's no better way
        # https://discordpy.readthedocs.io/en/v0.16.12/api.html#discord.Client.logs_from
        # https://github.com/discordapp/discord-api-docs/issues/663
        logs = self.bot.logs_from(channel, limit=999999999, after=since)
        messages = [message async for message in logs if message.author == member]
        return len(messages)

    async def nominate(self, ctx: Context, user_id):
        # let the nominator know we're working on it
        await self.bot.add_reaction(ctx.message, "🤖")

        # get the user as a member of this server
        member: discord.Member = self.server.get_member(user_id)

        # short-circuit if we can't find the user in this server
        if not member:
            await self.bot.react_question(ctx)
            return

        # grab recent messages
        now = datetime.utcnow()
        then = now - timedelta(days=self.recency_in_days)

        # sum up help messages first
        recent_help_messages = 0
        for channel in self.help_channels:
            recent_help_messages += await self.count_recent_messages(
                channel, member, since=then
            )

        # then sum up total messages
        total_recent_messages = recent_help_messages
        for channel in self.other_channels:
            total_recent_messages += await self.count_recent_messages(
                channel, member, since=then
            )

        # create an embed with clickable mention
        em = discord.Embed(
            description=f"Nominations for: {member.mention}",
            color=0x00ACED,
            timestamp=member.joined_at,
        )
        em.set_footer(text="Joined the server", icon_url=member.avatar_url)
        em.set_thumbnail(url=member.avatar_url)

        # add the total number of recent messages
        em.add_field(
            name="Number of recent messages",
            value=f"{total_recent_messages} in {self.recency_in_days} days",
        )

        # and the help ratio, if any
        if total_recent_messages > 0:
            help_ratio = round(100 * recent_help_messages / total_recent_messages)
            em.add_field(
                name="Ratio of messages in help-chats",
                value=f"{help_ratio}% of {total_recent_messages}",
            )
        else:
            em.add_field(name="Ratio of messages in help-chats", value=r"¯\_(ツ)_/¯")

        # send the message with embed
        nom_message = await self.bot.send_message(ctx.message.channel, embed=em)

        # edit-mention and add a username to the message content, just in case
        # people's clients bug out with the embeds
        content = f"{member.mention} ({member.name}#{member.discriminator})"
        await self.bot.edit_message(nom_message, content)

        # add some default reactions
        await self.bot.add_reaction(nom_message, "👍")
        await self.bot.add_reaction(nom_message, "👎")

        # delete the user command
        await self.bot.delete_message(ctx.message)


class Nominate:
    def __init__(self, bot: CogBot, ext: str):
        self.bot: CogBot = bot
        self.server_state: typing.Dict[ServerId, NominateServerState] = {}
        self.options = self.bot.state.get_extension_state(ext)

    def get_state(self, server: discord.Server) -> NominateServerState:
        return self.server_state.get(server.id)

    async def on_ready(self):
        # construct server state objects for easier context management
        for server_key, server_options in self.options.get("servers", {}).items():
            server = self.bot.get_server_from_key(server_key)
            if server:
                state = NominateServerState(self.bot, server, **server_options)
                self.server_state[server.id] = state

    @checks.is_staff()
    @commands.command(pass_context=True, hidden=True, aliases=["nom"])
    async def nominate(self, ctx: Context, user_id):
        # make sure this isn't a DM
        if ctx.message.server:
            state = self.get_state(ctx.message.server)
            # ignore bot's messages
            if state and ctx.message.author != self.bot.user:
                await state.nominate(ctx, user_id)


def setup(bot):
    bot.add_cog(Nominate(bot, __name__))
