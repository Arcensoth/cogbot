import asyncio
import logging
import typing
from datetime import datetime, timedelta

import discord
from discord.iterators import LogsFromIterator

from cogbot.cog_bot import CogBot

log = logging.getLogger(__name__)


ServerId = str
ChannelId = str


class HelpChatServerState:
    def __init__(
        self,
        bot: CogBot,
        server: ServerId,
        channels: typing.List[ChannelId],
        message_with_channel: str,
        message_without_channel: str,
        seconds_until_stale: int = 3600,
        relocate_emoji: str = "🛴",
        resolve_emoji: str = "✅",
        free_prefix: str = "✅",
        busy_prefix: str = "💬",
        stale_prefix: str = "⏰",
        resolve_with_reaction: bool = False,
    ):
        self.bot: CogBot = bot
        self.server: discord.Server = self.bot.get_server(server)
        self.channels: typing.List[discord.Channel] = [
            self.bot.get_channel(channel_id) for channel_id in channels
        ]
        self.message_with_channel: str = message_with_channel
        self.message_without_channel: str = message_without_channel
        self.seconds_until_stale: int = seconds_until_stale
        self.relocate_emoji: typing.Union[str, discord.Emoji] = self.bot.get_emoji(
            self.server, relocate_emoji
        )
        self.resolve_emoji: typing.Union[str, discord.Emoji] = self.bot.get_emoji(
            self.server, resolve_emoji
        )
        self.free_prefix: str = free_prefix
        self.busy_prefix: str = busy_prefix
        self.stale_prefix: str = stale_prefix
        self.resolve_with_reaction: bool = resolve_with_reaction

    def is_channel(self, channel: discord.Channel, prefix: str) -> bool:
        return channel.name.startswith(prefix)

    def is_channel_free(self, channel: discord.Channel) -> bool:
        return self.is_channel(channel, self.free_prefix)

    def is_channel_busy(self, channel: discord.Channel) -> bool:
        return self.is_channel(channel, self.busy_prefix)

    def is_channel_stale(self, channel: discord.Channel) -> bool:
        return self.is_channel(channel, self.stale_prefix)

    def get_free_channel(self) -> discord.Channel:
        for channel in self.channels:
            if self.is_channel_free(channel):
                return channel

    def get_base_channel_name(self, channel: discord.Channel) -> str:
        if self.is_channel_free(channel):
            return channel.name[len(self.free_prefix) :]
        if self.is_channel_busy(channel):
            return channel.name[len(self.busy_prefix) :]
        if self.is_channel_stale(channel):
            return channel.name[len(self.stale_prefix) :]
        return channel.name

    async def redirect(self, message: discord.Message):
        free_channel = self.get_free_channel()
        if free_channel:
            response = self.message_with_channel.format(
                mention=message.author.mention,
                name=message.author.display_name,
                channel=free_channel.mention,
            )
        else:
            response = self.message_without_channel.format(
                mention=message.author.mention, name=message.author.display_name
            )
        await self.bot.send_message(message.channel, response)

    async def mark_channel(self, channel: discord.Channel, prefix: str):
        base_name = self.get_base_channel_name(channel)
        # NOTE get_base_channel_name() depends on how this is constructed
        new_name = prefix + base_name
        await self.bot.edit_channel(channel, name=new_name)

    async def mark_channel_free(self, channel: discord.Channel):
        if self.is_channel_busy(channel) or self.is_channel_stale(channel):
            await self.mark_channel(channel, self.free_prefix)

    async def mark_channel_busy(self, channel: discord.Channel):
        if self.is_channel_free(channel) or self.is_channel_stale(channel):
            await self.mark_channel(channel, self.busy_prefix)

    async def mark_channel_stale(self, channel: discord.Channel):
        if self.is_channel_free(channel) or self.is_channel_busy(channel):
            await self.mark_channel(channel, self.stale_prefix)

    async def on_reaction(self, reaction: discord.Reaction, reactor: discord.Member):
        message: discord.Message = reaction.message
        channel: discord.Channel = message.channel
        reactee: discord.Member = message.author
        # relocate: only on the first of a reaction on a human message
        if (
            reaction.emoji == self.relocate_emoji
            and reaction.count == 1
            and reactee != self.bot.user
        ):
            log.info(f"[{reactor.server}/{reactor}] {self.relocate_emoji}")
            await self.redirect(reaction.message)
            await self.bot.add_reaction(reaction.message, self.relocate_emoji)
        # resolve: only when enabled and for managed channels
        if (
            reaction.emoji == self.resolve_emoji
            and self.resolve_with_reaction
            and channel in self.channels
        ):
            log.info(f"[{reactor.server}/{reactor}] {self.resolve_emoji}")
            await self.mark_channel_free(channel)
            await self.bot.add_reaction(reaction.message, self.resolve_emoji)

    async def on_message(self, message: discord.Message):
        channel: discord.Channel = message.channel
        # only care about managed channels
        if channel in self.channels:
            # resolve: only when the message contains exactly the resolve emoji
            if message.content == str(self.resolve_emoji):
                log.info(f"[{message.server}/{message.author}] {self.resolve_emoji}")
                await self.mark_channel_free(channel)
            # otherwise mark it as busy
            else:
                await self.mark_channel_busy(channel)

    async def poll_channels(self):
        for channel in self.channels:
            if self.is_channel_busy(channel):
                now: datetime = datetime.utcnow()
                delta = timedelta(seconds=self.seconds_until_stale)
                # look at the timestamp of the latest message
                async for message in self.bot.logs_from(channel, limit=1):
                    then: datetime = message.timestamp + delta
                # check if it passes the configured threshold
                if now > then:
                    await self.mark_channel_stale(channel)


class HelpChat:
    def __init__(self, bot: CogBot, ext: str):
        self.bot: CogBot = bot
        self.server_state: typing.Dict[ServerId, HelpChatServerState] = {}
        self.options = self.bot.state.get_extension_state(ext)

    def get_state(self, server: discord.Server) -> HelpChatServerState:
        return self.server_state.get(server.id)

    async def poll(self):
        while not self.bot.is_closed:
            for state in self.server_state.values():
                await state.poll_channels()
            await asyncio.sleep(10)

    async def on_ready(self):
        for server_id, options in self.options.items():
            if self.bot.get_server(server_id):
                state = HelpChatServerState(self.bot, server_id, **options)
                self.server_state[server_id] = state
        await self.poll()

    async def on_reaction_add(
        self, reaction: discord.Reaction, reactor: discord.Member
    ):
        # make sure this isn't a DM
        if isinstance(reactor, discord.Member):
            state = self.get_state(reactor.server)
            # ignore bot's reactions
            if state and reactor != self.bot.user:
                await state.on_reaction(reaction, reactor)

    async def on_message(self, message: discord.Message):
        state = self.get_state(message.server)
        # ignore bot's messages
        if state and message.author != self.bot.user:
            await state.on_message(message)


def setup(bot):
    bot.add_cog(HelpChat(bot, __name__))
