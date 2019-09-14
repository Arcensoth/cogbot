import asyncio
import logging
import typing
from datetime import datetime, timedelta

import discord
from discord.iterators import LogsFromIterator

from cogbot.cog_bot import CogBot, ServerId, ChannelId


log = logging.getLogger(__name__)


CLOCKS = ("🕛", "🕐", "🕑", "🕒", "🕓", "🕔", "🕕", "🕖", "🕗", "🕘", "🕙", "🕚", "⏰")


class HelpChatServerState:
    def __init__(
        self,
        bot: CogBot,
        server: discord.Server,
        channels: typing.List[ChannelId],
        message_with_channel: str,
        message_without_channel: str,
        seconds_until_stale: int = 3600,
        relocate_emoji: str = "🛴",
        resolve_emoji: str = "✅",
        free_prefix: str = "✅",
        busy_prefix: str = "💬",
        stale_prefixes: typing.Iterable[str] = ["⏰"],
        resolve_with_reaction: bool = False,
        destroy_audit_log: bool = False,
    ):
        self.bot: CogBot = bot
        self.server: discord.Server = server
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
        self.stale_prefixes: typing.Tuple[str] = CLOCKS if destroy_audit_log else tuple(
            stale_prefixes
        )
        self.resolve_with_reaction: bool = resolve_with_reaction

    def is_channel(self, channel: discord.Channel, prefix: str) -> bool:
        return channel.name.startswith(prefix)

    def is_channel_free(self, channel: discord.Channel) -> bool:
        return self.is_channel(channel, self.free_prefix)

    def is_channel_busy(self, channel: discord.Channel) -> bool:
        return self.is_channel(channel, self.busy_prefix)

    def is_channel_stale(self, channel: discord.Channel, index: int = None) -> bool:
        return self.is_channel(
            channel,
            self.stale_prefixes if index == None else self.get_stale_prefix(index),
        )

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
            return channel.name[len(self.stale_prefixes[0]) :]
        return channel.name

    def get_stale_prefix(self, index: int) -> str:
        return self.stale_prefixes[min(index, len(self.stale_prefixes) - 1)]

    async def redirect(self, message: discord.Message, reactor: discord.Member):
        author: discord.Member = message.author
        from_channel: discord.Channel = message.channel
        to_channel = self.get_free_channel()
        if to_channel:
            await self.bot.mod_log(
                reactor,
                f"relocated {author.mention} from {from_channel.mention} to {to_channel.mention}",
                message=message,
                icon=":arrow_right:",
            )
            response = self.message_with_channel.format(
                author=author,
                reactor=reactor,
                from_channel=from_channel,
                to_channel=to_channel,
            )
        else:
            await self.bot.mod_log(
                reactor,
                f"relocated {author.mention} from {from_channel.mention}",
                message=message,
                icon=":arrow_right:",
            )
            response = self.message_without_channel.format(
                author=author, reactor=reactor, from_channel=from_channel
            )
        await self.bot.send_message(message.channel, response)

    async def mark_channel(self, channel: discord.Channel, prefix: str) -> bool:
        base_name = self.get_base_channel_name(channel)
        # NOTE get_base_channel_name() depends on how this is constructed
        new_name = prefix + base_name
        if new_name != channel.name:
            await self.bot.edit_channel(channel, name=new_name)
            return True

    async def mark_channel_free(self, channel: discord.Channel) -> bool:
        if self.is_channel_busy(channel) or self.is_channel_stale(channel):
            return await self.mark_channel(channel, self.free_prefix)

    async def mark_channel_busy(self, channel: discord.Channel) -> bool:
        if self.is_channel_free(channel) or self.is_channel_stale(channel):
            return await self.mark_channel(channel, self.busy_prefix)

    async def mark_channel_stale(self, channel: discord.Channel, index: int) -> bool:
        if not self.is_channel_stale(channel, index) and (
            self.is_channel_free(channel)
            or self.is_channel_busy(channel)
            or self.is_channel_stale(channel)
        ):
            return await self.mark_channel(channel, self.get_stale_prefix(index))

    async def on_reaction(self, reaction: discord.Reaction, reactor: discord.Member):
        message: discord.Message = reaction.message
        channel: discord.Channel = message.channel
        author: discord.Member = message.author
        # relocate: only on the first of a reaction on a fresh human message
        if (
            reaction.emoji == self.relocate_emoji
            and reaction.count == 1
            and author != self.bot.user
        ):
            await self.redirect(message, reactor)
            await self.bot.add_reaction(message, self.relocate_emoji)
        # resolve: only when enabled and for the last message of a managed channel
        if (
            reaction.emoji == self.resolve_emoji
            and self.resolve_with_reaction
            and channel in self.channels
            and await self.bot.is_latest_message(message)
        ):
            if await self.mark_channel_free(channel):
                await self.bot.add_reaction(message, self.resolve_emoji)
                await self.bot.mod_log(
                    reactor,
                    f"resolved {channel.mention}",
                    message=message,
                    icon=":white_check_mark:",
                )

    async def on_message(self, message: discord.Message):
        channel: discord.Channel = message.channel
        # only care about managed channels
        if channel in self.channels:
            # resolve: only when the message contains exactly the resolve emoji
            if message.content == str(self.resolve_emoji):
                if await self.mark_channel_free(channel):
                    await self.bot.mod_log(
                        message.author,
                        f"resolved {channel.mention}",
                        message=message,
                        icon=":white_check_mark:",
                    )
            # otherwise mark it as busy
            else:
                await self.mark_channel_busy(channel)

    async def poll_channels(self):
        for channel in self.channels:
            if self.is_channel_busy(channel) or self.is_channel_stale(channel):
                latest_message = await self.bot.get_latest_message(channel)
                now: datetime = datetime.utcnow()
                then: datetime = latest_message.timestamp
                delta = now - then
                amount = delta.seconds // self.seconds_until_stale
                if amount > 0:
                    await self.mark_channel_stale(channel, amount - 1)


class HelpChat:
    def __init__(self, bot: CogBot, ext: str):
        self.bot: CogBot = bot
        self.server_state: typing.Dict[ServerId, HelpChatServerState] = {}
        self.options = self.bot.state.get_extension_state(ext)
        self.polling_task = None

    def get_state(self, server: discord.Server) -> HelpChatServerState:
        return self.server_state.get(server.id)

    async def poll(self):
        while not self.bot.is_closed:
            for state in self.server_state.values():
                await state.poll_channels()
            await asyncio.sleep(10)

    async def on_ready(self):
        # construct server state objects for easier context management
        for server_key, server_options in self.options.get("servers", {}).items():
            server = self.bot.get_server_from_key(server_key)
            if server:
                state = HelpChatServerState(self.bot, server, **server_options)
                self.server_state[server.id] = state

        # create a proper background task to poll managed channels
        self.polling_task = self.bot.loop.create_task(self.poll())

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
        # make sure this isn't a DM
        if message.server:
            state = self.get_state(message.server)
            # ignore bot's messages
            if state and message.author != self.bot.user:
                await state.on_message(message)


def setup(bot):
    bot.add_cog(HelpChat(bot, __name__))
