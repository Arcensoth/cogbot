import logging
import re
import typing
from datetime import datetime, timedelta

import discord
from discord.ext import commands
from discord.ext.commands import CommandError, Context

from cogbot import checks
from cogbot.cog_bot import ChannelId, CogBot, ServerId, MessageReport

log = logging.getLogger(__name__)


class MemberReport:
    def __init__(
        self,
        member: discord.Member,
        recency: timedelta,
        help_messages: int = 0,
        other_messages: int = 0,
    ):
        self.member: discord.Member = member
        self.recency: timedelta = recency
        self.help_messages: int = help_messages
        self.other_messages: int = other_messages


class NominateServerState:
    def __init__(
        self,
        bot: CogBot,
        server: discord.Server,
        help_channels: typing.List[ChannelId],
        other_channels: typing.List[ChannelId],
    ):
        self.bot: CogBot = bot
        self.server: discord.Server = server

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

    async def send_embed(self, ctx: Context, report: MemberReport):
        member = report.member
        help_messages = report.help_messages
        other_messages = report.other_messages
        total_messages = help_messages + other_messages

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
            value=f"{total_messages} in {report.recency.days} days",
        )

        # and the help ratio, if any
        if total_messages > 0:
            help_ratio = round(100 * help_messages / total_messages)
            em.add_field(
                name="Ratio of messages in help-chats",
                value=f"{help_ratio}% of {total_messages}",
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

    async def nominate(self, ctx: Context, days: int):
        # let the nominator know we're working on it
        await self.bot.add_reaction(ctx.message, "🤖")

        # calculate the date to start counting from
        recency = timedelta(days=days)
        now = datetime.utcnow()
        then = now - recency

        # get the nominees from mentions
        message: discord.Message = ctx.message
        members = message.mentions

        # map members to their number of messages in each channel type
        member_buckets = {member: MemberReport(member, recency) for member in members}

        # update on progress
        await self.bot.add_reaction(ctx.message, "🕛")

        # get a message report for help channels
        help_channels_report: MessageReport = await self.bot.make_message_report(
            self.help_channels, members, since=then
        )
        for messages_per_member in help_channels_report.messages_per_member.values():
            for member, count in messages_per_member.items():
                member_report: MemberReport = member_buckets[member]
                member_report.help_messages += count

        # update on progress
        await self.bot.add_reaction(ctx.message, "🕐")

        # and another report for other channels
        other_channels_report: MessageReport = await self.bot.make_message_report(
            self.other_channels, members, since=then
        )
        for messages_per_member in other_channels_report.messages_per_member.values():
            for member, count in messages_per_member.items():
                member_report: MemberReport = member_buckets[member]
                member_report.other_messages += count

        # update on progress
        await self.bot.add_reaction(ctx.message, "🕑")

        # and then spit out a separate embed for each nominee
        for member in members:
            await self.send_embed(ctx, member_buckets[member])

        # update on progress
        await self.bot.add_reaction(ctx.message, "☑️")


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
    async def nominate(self, ctx: Context, days: int, *, members):
        # make sure this isn't a DM
        if ctx.message.server:
            state = self.get_state(ctx.message.server)
            # ignore bot's messages
            if state and ctx.message.author != self.bot.user:
                # NOTE don't need to pass members because mentions are available in the context
                await state.nominate(ctx, days)


def setup(bot):
    bot.add_cog(Nominate(bot, __name__))
