import logging
import typing
from datetime import datetime, timedelta

import discord

from cogbot.cog_bot import ChannelId, CogBot
from cogbot.extensions.helpchat.channel_state import ChannelState

RELOCATE_EMOJI = "🛴"
FREE_EMOJI = "✅"
BUSY_EMOJI = "💬"
STALE_EMOJI = "⏰"
HOISTED_EMOJI = "👋"
DUCKED_EMOJI = "🦆"


class HelpChatServerState:
    def __init__(
        self,
        ext: str,
        bot: CogBot,
        server: discord.Server,
        channels: typing.Dict[str, ChannelId],
        message_with_channel: str,
        message_without_channel: str,
        seconds_until_stale: int = 3600,
        seconds_to_poll: int = 600,
        free_category: str = None,
        busy_category: str = None,
        stale_category: str = None,
        hoisted_category: str = None,
        min_hoisted_channels: int = 0,
        max_hoisted_channels: int = 0,
        relocate_emoji: str = RELOCATE_EMOJI,
        resolve_emoji: str = FREE_EMOJI,
        free_emoji: str = FREE_EMOJI,
        busy_emoji: str = BUSY_EMOJI,
        stale_emoji: str = STALE_EMOJI,
        hoisted_emoji: str = HOISTED_EMOJI,
        resolve_with_reaction: bool = False,
        auto_poll: bool = True,
    ):
        self.log: logging.Logger = logging.getLogger(f"{ext}:{server.name}")

        self.bot: CogBot = bot
        self.server: discord.Server = server

        self.channel_map: typing.Dict[discord.Channel, str] = {
            self.bot.get_channel(channel_id): name
            for name, channel_id in channels.items()
        }

        self.channels: typing.List[discord.Channel] = list(self.channel_map.keys())

        self.log.info(f"Resolved {len(self.channels)} help channels")

        self.message_with_channel: str = message_with_channel
        self.message_without_channel: str = message_without_channel
        self.seconds_until_stale: int = seconds_until_stale
        self.seconds_to_poll: int = seconds_to_poll
        self.min_hoisted_channels: int = min_hoisted_channels
        self.max_hoisted_channels: int = max(min_hoisted_channels, max_hoisted_channels)
        self.relocate_emoji: typing.Union[str, discord.Emoji] = self.bot.get_emoji(
            self.server, relocate_emoji
        )
        self.resolve_emoji: typing.Union[str, discord.Emoji] = self.bot.get_emoji(
            self.server, resolve_emoji
        )

        self.free_category: discord.Channel = self.bot.get_channel(
            free_category
        ) if free_category else None

        self.busy_category: discord.Channel = self.bot.get_channel(
            busy_category
        ) if busy_category else None

        self.stale_category: discord.Channel = self.bot.get_channel(
            stale_category
        ) if stale_category else None

        self.hoisted_category: discord.Channel = self.bot.get_channel(
            hoisted_category
        ) if hoisted_category else None

        self.log.info(f"Free category: {self.free_category}")
        self.log.info(f"Busy category: {self.busy_category}")
        self.log.info(f"Stale category: {self.stale_category}")
        self.log.info(f"Hoisted category: {self.hoisted_category}")

        self.free_emoji: str = free_emoji
        self.busy_emoji: str = busy_emoji
        self.stale_emoji: str = stale_emoji
        self.hoisted_emoji: str = hoisted_emoji

        self.resolve_with_reaction: bool = resolve_with_reaction

        self.free_state: str = ChannelState(free_emoji, "{emoji}free-chat-{name}")
        self.busy_state: str = ChannelState(busy_emoji, "{emoji}busy-chat-{name}")
        self.stale_state: str = ChannelState(stale_emoji, "{emoji}stale-chat-{name}")
        self.hoisted_state: str = ChannelState(hoisted_emoji, "{emoji}ask-here")
        self.ducked_state: str = ChannelState(DUCKED_EMOJI, "{emoji}duck-chat-{name}")

        self.auto_poll: bool = auto_poll

        if not self.auto_poll:
            self.log.warning("Auto-polling is DISABLED")

        self.last_polled = datetime.utcnow()
        self.delta_until_stale = timedelta(seconds=self.seconds_until_stale)
        self.delta_to_poll = timedelta(seconds=self.seconds_to_poll)

    def is_channel(self, channel: discord.Channel, channel_state: ChannelState) -> bool:
        return channel_state.matches(channel)

    def is_channel_free(self, channel: discord.Channel) -> bool:
        return self.is_channel(channel, self.free_state)

    def is_channel_busy(self, channel: discord.Channel) -> bool:
        return self.is_channel(channel, self.busy_state) or self.is_channel_ducked(
            channel
        )

    def is_channel_stale(self, channel: discord.Channel) -> bool:
        return self.is_channel(channel, self.stale_state)

    def is_channel_hoisted(self, channel: discord.Channel) -> bool:
        return self.is_channel(channel, self.hoisted_state)

    def is_channel_ducked(self, channel: discord.Channel) -> bool:
        return self.is_channel(channel, self.ducked_state)

    def get_channels(self, state: ChannelState) -> typing.Iterable[discord.Channel]:
        for channel in self.channels:
            if self.is_channel(channel, state):
                yield channel

    def get_free_channels(self) -> discord.Channel:
        return self.get_channels(self.free_state)

    def get_busy_channels(self) -> discord.Channel:
        return self.get_channels(self.busy_state)

    def get_stale_channels(self) -> discord.Channel:
        return self.get_channels(self.stale_state)

    def get_hoisted_channels(self) -> discord.Channel:
        return self.get_channels(self.hoisted_state)

    def get_channel(self, state: ChannelState) -> discord.Channel:
        return next(self.get_channels(state), None)

    def get_free_channel(self) -> discord.Channel:
        return self.get_channel(self.free_state)

    def get_busy_channel(self) -> discord.Channel:
        return self.get_channel(self.busy_state)

    def get_stale_channel(self) -> discord.Channel:
        return self.get_channel(self.stale_state)

    def get_hoisted_channel(self) -> discord.Channel:
        return self.get_channel(self.hoisted_state)

    def get_base_name(self, channel: discord.Channel) -> str:
        return self.channel_map.get(channel)

    async def set_channel(
        self,
        channel: discord.Channel,
        state: ChannelState,
        category: discord.Channel = None,
    ):
        # remember if the channel was hoisted
        was_hoisted = self.is_channel_hoisted(channel)
        # set the new channel name, which doubles as its persistent state
        new_name = state.format(self.get_base_name(channel))
        await self.bot.edit_channel(channel, name=new_name)
        # move the channel to the given category, if any
        if category:
            await self.bot.move_channel_to_category(channel, category)
        # sync hoisted channels if this change is relevant to them
        if was_hoisted or self.is_channel_hoisted(channel):
            await self.sync_hoisted_channels()

    async def set_channel_free(self, channel: discord.Channel) -> bool:
        # only busy and stale (not hoisted) channels can become free
        if self.is_channel_busy(channel) or self.is_channel_stale(channel):
            await self.set_channel(channel, self.free_state, self.free_category)
            return True

    async def set_channel_busy(self, channel: discord.Channel) -> bool:
        # any channel that's not already busy can become busy
        if not self.is_channel_busy(channel):
            await self.set_channel(channel, self.busy_state, self.busy_category)
            return True

    async def set_channel_stale(self, channel: discord.Channel) -> bool:
        # only busy channels can become stale
        if self.is_channel_busy(channel):
            await self.set_channel(channel, self.stale_state, self.stale_category)
            return True

    async def set_channel_hoisted(self, channel: discord.Channel) -> bool:
        # only free and stale channels (not busy) can become hoisted
        if self.is_channel_free(channel) or self.is_channel_stale(channel):
            await self.set_channel(channel, self.hoisted_state, self.hoisted_category)
            return True

    async def set_channel_ducked(self, channel: discord.Channel) -> bool:
        # any channel that's not already ducked can be ducked
        if not self.is_channel_ducked(channel):
            await self.set_channel(channel, self.ducked_state, self.busy_category)
            return True

    async def redirect(self, message: discord.Message, reactor: discord.Member):
        author: discord.Member = message.author
        from_channel: discord.Channel = message.channel
        # might as well suggest going straight to a free channel
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

    async def try_hoist_channel(self):
        hoisted_channels = list(self.get_hoisted_channels())
        num_hoisted_channels = len(hoisted_channels)
        # if we've hit the max, don't hoist any more channels
        if num_hoisted_channels < self.max_hoisted_channels:
            # if we're under the min, hoist a free channel or even a stale one
            if num_hoisted_channels < self.min_hoisted_channels:
                channel_to_hoist = self.get_free_channel() or self.get_stale_channel()
                # warn if we ran out of channels
                if not (channel_to_hoist):
                    self.log.warning("No channels available to hoist!")
                    return False
                # warn if we hit a race condition
                if not await self.set_channel_hoisted(channel_to_hoist):
                    self.log.warning("Tried to hoist a channel that wasn't free/stale!")
                    return False
                return True
            # otherwise, if we're just trying to top-off, hoist a free channel
            channel_to_hoist = self.get_free_channel()
            if channel_to_hoist:
                await self.set_channel_hoisted(channel_to_hoist)
                return True

    async def sync_hoisted_channels(self):
        # don't do anything unless we care about hoisted channels
        if self.max_hoisted_channels > 0:
            hoisted_channels = list(self.get_hoisted_channels())
            num_hoisted_channels = len(hoisted_channels)
            delta = self.max_hoisted_channels - num_hoisted_channels
            # recycle channels to top-off the hoisted ones
            if delta > 0:
                for i in range(delta):
                    if not await self.try_hoist_channel():
                        break

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
            if await self.set_channel_free(channel):
                await self.bot.add_reaction(message, self.resolve_emoji)
                await self.bot.mod_log(
                    reactor,
                    f"resolved {channel.mention}",
                    message=message,
                    icon=":white_check_mark:",
                )

        await self.maybe_poll_channels()

    async def on_message(self, message: discord.Message):
        channel: discord.Channel = message.channel

        # only care about managed channels
        if channel in self.channels:
            # resolve: only when the message contains exactly the resolve emoji
            if message.content == str(self.resolve_emoji):
                if await self.set_channel_free(channel):
                    await self.bot.mod_log(
                        message.author,
                        f"resolved {channel.mention}",
                        message=message,
                        icon=":white_check_mark:",
                    )

            # quack
            elif message.content == DUCKED_EMOJI:
                if await self.set_channel_ducked(channel):
                    await self.bot.mod_log(
                        message.author,
                        f"ducked {channel.mention}",
                        message=message,
                        icon=":duck:",
                    )

            # otherwise, mark it as busy
            else:
                await self.set_channel_busy(channel)

        await self.maybe_poll_channels()

    async def poll_channels(self):
        for channel in self.channels:
            # only busy channels can become stale
            if self.is_channel_busy(channel):
                latest_message = await self.bot.get_latest_message(channel)
                # if there's no latest message, then... free it up?
                if not latest_message:
                    await self.set_channel_free(channel)
                    continue
                now: datetime = datetime.utcnow()
                latest: datetime = latest_message.timestamp
                then: datetime = latest + self.delta_until_stale
                if now > then:
                    await self.set_channel_stale(channel)
        # might as well sync hoisted channels just in case
        await self.sync_hoisted_channels()

    async def maybe_poll_channels(self):
        if self.auto_poll:
            # check if enough time has passed for us to poll channels again
            # sort of a hack, because f**k polling tasks
            now: datetime = datetime.utcnow()
            then: datetime = self.last_polled + self.delta_to_poll
            if now > then:
                self.last_polled = now
                await self.poll_channels()
