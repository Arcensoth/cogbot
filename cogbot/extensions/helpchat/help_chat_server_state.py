import asyncio
import collections
import logging
import random
import re
import typing
from datetime import datetime, timedelta

import discord

from cogbot.cog_bot import ChannelId, CogBot
from cogbot.extensions.helpchat.channel_state import ChannelState

PROMPT_COLOR = "#00ACED"

# 10 minutes by default allows room for a channel to transition out of busy, and
# immediately back in to busy, without being rate-limited.
SECONDS_TO_THROTTLE = 600

SECONDS_UNTIL_IDLE = 1800
SECONDS_TO_POLL = 60
PREEMPTIVE_CACHE_SIZE = 10

RATE_LIMIT_EMOJI = "⏳"

RELOCATE_EMOJI = "➡️"
REASSIGN_EMOJI = "🏷️"
RENAME_EMOJI = "📛"
RESTORE_EMOJI = "♻️"
REMIND_EMOJI = "🎗️"
RESOLVE_EMOJI = "✅"

HOISTED_EMOJI = "👋"
BUSY_EMOJI = "💬"
IDLE_EMOJI = "⏰"
PENDING_EMOJI = "🔔"
ANSWERED_EMOJI = "✅"
DUCKED_EMOJI = "🦆"

HOISTED_NAME = "ask-here-{key}"
BUSY_NAME = "busy-question-{key}"
IDLE_NAME = "idle-question-{key}"
PENDING_NAME = "pending-question-{key}"
ANSWERED_NAME = "answered-question-{key}"
DUCKED_NAME = "duck-session-{key}"

HOISTED_DESCRIPTION = (
    f"**Ask here** \\{HOISTED_EMOJI}"
    "\n\n"
    "Have a question? This channel does not have an ongoing discussion. Ask here!"
)
BUSY_DESCRIPTION = (
    f"**Busy** \\{BUSY_EMOJI}"
    "\n\n"
    "A question has been asked in this channel and discussion is ongoing."
    "\n\n"
    "**New questions should go in an ask-here channel.**"
)
IDLE_DESCRIPTION = (
    f"**Idle** \\{IDLE_EMOJI}"
    "\n\n"
    "A question has been asked in this channel but discussion has gone idle."
    " This channel may be reused if there are no answered or pending channels remaining."
    "\n\n"
    "**New questions should go in an ask-here channel.**"
)
PENDING_DESCRIPTION = (
    f"**Pending** \\{PENDING_EMOJI}"
    "\n\n"
    "A question has been asked in this channel and an answer has been proposed."
    " This channel may be reused if there are no answered channels remaining."
    "\n\n"
    "**New questions should go in an ask-here channel.**"
)
ANSWERED_DESCRIPTION = (
    f"**Answered** \\{ANSWERED_EMOJI}"
    "\n\n"
    "A question has been asked in this channel and an answer has been accepted."
    " This channel may be reused to replenish the number of hoisted channels."
    "\n\n"
    "**New questions should go in an ask-here channel.**"
)
DUCKED_DESCRIPTION = (
    f"**Ducked** \\{DUCKED_EMOJI}"
    "\n\n"
    "A question has been asked in this channel and the asker appears to be talking"
    " themselves through a solution."
    "\n\n"
    "**New questions should go in an ask-here channel.**"
)

LOG_RELOCATED_EMOJI = RELOCATE_EMOJI
LOG_REASSIGNED_EMOJI = REASSIGN_EMOJI
LOG_RENAMED_EMOJI = RENAME_EMOJI
LOG_RESTORED_EMOJI = RESTORE_EMOJI
LOG_REMINDED_EMOJI = REMIND_EMOJI
LOG_RESOLVED_EMOJI = RESOLVE_EMOJI
LOG_DUCKED_EMOJI = DUCKED_EMOJI
LOG_BUSIED_FROM_HOISTED_EMOJI = HOISTED_EMOJI
LOG_BUSIED_FROM_PENDING_EMOJI = "🛎️"
LOG_BUSIED_FROM_ANSWERED_EMOJI = "🙊"
LOG_FAKE_OUT_EMOJI = "🙈"
LOG_ANSWERED_FROM_PENDING_EMOJI = PENDING_EMOJI
LOG_HOISTED_FROM_PENDING_EMOJI = PENDING_EMOJI
LOG_HOISTED_FROM_IDLE_EMOJI = IDLE_EMOJI
LOG_NO_CHANNELS_TO_HOIST_EMOJI = "🚒"

LOG_RELOCATED_COLOR = "#3B88C3"
LOG_REASSIGNED_COLOR = "#FFD983"
LOG_RENAMED_COLOR = "#DD2E44"
LOG_RESTORED_COLOR = "#3E721D"
LOG_REMINDED_COLOR = "#9B59B6"
LOG_RESOLVED_COLOR = "#77B255"
LOG_DUCKED_COLOR = "#C77538"
LOG_BUSIED_FROM_HOISTED_COLOR = "#FFDC5D"
LOG_BUSIED_FROM_PENDING_COLOR = "#FFAC33"
LOG_BUSIED_FROM_ANSWERED_COLOR = "#BF6952"
LOG_FAKE_OUT_COLOR = "#BF6952"
LOG_ANSWERED_FROM_PENDING_COLOR = "#41BEA4"
LOG_HOISTED_FROM_PENDING_COLOR = "#FFAC33"
LOG_HOISTED_FROM_IDLE_COLOR = "#FFAC33"
LOG_NO_CHANNELS_TO_HOIST_COLOR = "#DD2E44"

CHANNEL_TOPIC_TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"
CHANNEL_TOPIC_TIMESTAMP_PREFIX = "Last update: "
CHANNEL_TOPIC_ASKER_PREFIX = "Current asker: "

MENTION_PATTERN = re.compile(r"<@\!?(\w+)>")

StringOrStrings = typing.Union[str, typing.List[str]]


def flatten_string(s: StringOrStrings) -> str:
    return "\n".join(s) if isinstance(s, list) else s


class ChannelUpdateTooSoon(Exception):
    def __init__(self, next_update: datetime):
        self.next_update = next_update


class HelpChatChannelEntry:
    def __init__(self, key: str, index: int):
        self.key: str = key
        self.index: int = index


class HelpChatServerState:
    def __init__(
        self,
        ext: str,
        bot: CogBot,
        server: discord.Server,
        channels: typing.List[dict],
        log_channel: str = None,
        relocate_message_with_channel: StringOrStrings = None,
        relocate_message_without_channel: StringOrStrings = None,
        reminder_message: StringOrStrings = None,
        fake_out_message: StringOrStrings = None,
        prompt_message: StringOrStrings = None,
        prompt_color: str = PROMPT_COLOR,
        second_to_throttle: int = SECONDS_TO_THROTTLE,
        seconds_until_idle: int = SECONDS_UNTIL_IDLE,
        seconds_to_poll: int = SECONDS_TO_POLL,
        preemptive_cache_size: int = PREEMPTIVE_CACHE_SIZE,
        min_hoisted_channels: int = 0,
        max_hoisted_channels: int = 0,
        rate_limit_emoji: str = RATE_LIMIT_EMOJI,
        # action emoji
        relocate_emoji: str = RELOCATE_EMOJI,
        reassign_emoji: str = REASSIGN_EMOJI,
        rename_emoji: str = RENAME_EMOJI,
        restore_emoji: str = RESTORE_EMOJI,
        remind_emoji: str = REMIND_EMOJI,
        resolve_emoji: str = RESOLVE_EMOJI,
        # state emoji
        hoisted_emoji: str = HOISTED_EMOJI,
        busy_emoji: str = BUSY_EMOJI,
        idle_emoji: str = IDLE_EMOJI,
        pending_emoji: str = PENDING_EMOJI,
        answered_emoji: str = ANSWERED_EMOJI,
        ducked_emoji: str = DUCKED_EMOJI,
        # state name
        hoisted_name: str = HOISTED_NAME,
        busy_name: str = BUSY_NAME,
        idle_name: str = IDLE_NAME,
        pending_name: str = PENDING_NAME,
        answered_name: str = ANSWERED_NAME,
        ducked_name: str = DUCKED_NAME,
        # state description
        hoisted_description: StringOrStrings = HOISTED_DESCRIPTION,
        busy_description: StringOrStrings = BUSY_DESCRIPTION,
        idle_description: StringOrStrings = IDLE_DESCRIPTION,
        pending_description: StringOrStrings = PENDING_DESCRIPTION,
        answered_description: StringOrStrings = ANSWERED_DESCRIPTION,
        ducked_description: StringOrStrings = DUCKED_DESCRIPTION,
        # state category
        hoisted_category: str = None,
        busy_category: str = None,
        idle_category: str = None,
        pending_category: str = None,
        answered_category: str = None,
        # log emoji
        log_relocated_emoji: str = LOG_RELOCATED_EMOJI,
        log_reassigned_emoji: str = LOG_REASSIGNED_EMOJI,
        log_renamed_emoji: str = LOG_RENAMED_EMOJI,
        log_restored_emoji: str = LOG_RESTORED_EMOJI,
        log_reminded_emoji: str = LOG_REMINDED_EMOJI,
        log_resolved_emoji: str = LOG_RESOLVED_EMOJI,
        log_ducked_emoji: str = LOG_DUCKED_EMOJI,
        log_busied_from_hoisted_emoji: str = LOG_BUSIED_FROM_HOISTED_EMOJI,
        log_busied_from_pending_emoji: str = LOG_BUSIED_FROM_PENDING_EMOJI,
        log_busied_from_answered_emoji: str = LOG_BUSIED_FROM_ANSWERED_EMOJI,
        log_fake_out_emoji: str = LOG_FAKE_OUT_EMOJI,
        log_answered_from_pending_emoji: str = LOG_ANSWERED_FROM_PENDING_EMOJI,
        log_hoisted_from_pending_emoji: str = LOG_HOISTED_FROM_PENDING_EMOJI,
        log_hoisted_from_idle_emoji: str = LOG_HOISTED_FROM_IDLE_EMOJI,
        log_no_channels_to_hoist_emoji: str = LOG_NO_CHANNELS_TO_HOIST_EMOJI,
        # log color
        log_relocated_color: str = LOG_RELOCATED_COLOR,
        log_reassigned_color: str = LOG_REASSIGNED_COLOR,
        log_renamed_color: str = LOG_RENAMED_COLOR,
        log_restored_color: str = LOG_RESTORED_COLOR,
        log_reminded_color: str = LOG_REMINDED_COLOR,
        log_resolved_color: str = LOG_RESOLVED_COLOR,
        log_ducked_color: str = LOG_DUCKED_COLOR,
        log_busied_from_hoisted_color: str = LOG_BUSIED_FROM_HOISTED_COLOR,
        log_busied_from_pending_color: str = LOG_BUSIED_FROM_PENDING_COLOR,
        log_busied_from_answered_color: str = LOG_BUSIED_FROM_ANSWERED_COLOR,
        log_fake_out_color: str = LOG_FAKE_OUT_COLOR,
        log_answered_from_pending_color: str = LOG_ANSWERED_FROM_PENDING_COLOR,
        log_hoisted_from_pending_color: str = LOG_HOISTED_FROM_PENDING_COLOR,
        log_hoisted_from_idle_color: str = LOG_HOISTED_FROM_IDLE_COLOR,
        log_no_channels_to_hoist_color: str = LOG_NO_CHANNELS_TO_HOIST_COLOR,
        # roles
        helper_role: str = None,
        ignored_role: str = None,
        renamed_role: str = None,
        # toggles
        persist_asker: bool = False,
        log_verbose_usernames: bool = False,
        auto_poll: bool = True,
        **kwargs,
    ):
        self.log: logging.Logger = logging.getLogger(f"{ext}:{server.name}")

        self.bot: CogBot = bot
        self.server: discord.Server = server

        self.channel_map: typing.Dict[
            discord.Channel, HelpChatServerState
        ] = collections.OrderedDict()

        for index, channel_dict in enumerate(channels):
            channel_id: int = channel_dict["id"]
            channel_key: str = channel_dict["key"]
            channel: discord.Channel = self.bot.get_channel(channel_id)
            channel_entry = HelpChatChannelEntry(channel_key, index)
            self.channel_map[channel] = channel_entry

        self.channels: typing.List[discord.Channel] = list(self.channel_map.keys())

        self.log.info(f"Identified {len(self.channels)} help channels.")

        self.log_channel: discord.Channel = self.bot.get_channel(
            log_channel
        ) if log_channel else None

        if self.log_channel:
            self.log.info(f"Identified log channel: {self.log_channel}")
        elif log_channel:
            self.log.warning(f"Unable to identify log channeL: {log_channel}")
        else:
            self.log.warning(f"No log channel was provided.")

        self.relocate_message_with_channel: str = flatten_string(
            relocate_message_with_channel
        )
        self.relocate_message_without_channel: str = flatten_string(
            relocate_message_without_channel
        )

        self.reminder_message: str = flatten_string(reminder_message)
        self.fake_out_message: str = flatten_string(fake_out_message)

        self.prompt_message: str = flatten_string(prompt_message)

        self.prompt_color: int = self.bot.color_from_hex(prompt_color)

        self.second_to_throttle: int = second_to_throttle
        self.channel_update_delta = timedelta(seconds=self.second_to_throttle)

        self.seconds_until_idle: int = seconds_until_idle
        self.seconds_to_poll: int = seconds_to_poll

        self.preemptive_cache_size: bool = preemptive_cache_size

        self.min_hoisted_channels: int = min_hoisted_channels
        self.max_hoisted_channels: int = max(min_hoisted_channels, max_hoisted_channels)

        self.rate_limit_emoji: typing.Union[str, discord.Emoji] = self.bot.get_emoji(
            self.server, rate_limit_emoji
        )

        # @@ Init action emoji
        self.relocate_emoji: typing.Union[str, discord.Emoji] = self.bot.get_emoji(
            self.server, relocate_emoji
        )
        self.reassign_emoji: typing.Union[str, discord.Emoji] = self.bot.get_emoji(
            self.server, reassign_emoji
        )
        self.rename_emoji: typing.Union[str, discord.Emoji] = self.bot.get_emoji(
            self.server, rename_emoji
        )
        self.restore_emoji: typing.Union[str, discord.Emoji] = self.bot.get_emoji(
            self.server, restore_emoji
        )
        self.resolve_emoji: typing.Union[str, discord.Emoji] = self.bot.get_emoji(
            self.server, resolve_emoji
        )
        self.remind_emoji: typing.Union[str, discord.Emoji] = self.bot.get_emoji(
            self.server, remind_emoji
        )

        # @@ Init channel state emoji
        self.hoisted_emoji: str = hoisted_emoji
        self.busy_emoji: str = busy_emoji
        self.idle_emoji: str = idle_emoji
        self.pending_emoji: str = pending_emoji
        self.answered_emoji: str = answered_emoji
        self.ducked_emoji: str = ducked_emoji

        # @@ Init channel state names
        self.hoisted_name: str = hoisted_name
        self.busy_name: str = busy_name
        self.idle_name: str = idle_name
        self.pending_name: str = pending_name
        self.answered_name: str = answered_name
        self.ducked_name: str = ducked_name

        # @@ Init channel state descriptions
        self.hoisted_description: str = flatten_string(hoisted_description)
        self.busy_description: str = flatten_string(busy_description)
        self.idle_description: str = flatten_string(idle_description)
        self.pending_description: str = flatten_string(pending_description)
        self.answered_description: str = flatten_string(answered_description)
        self.ducked_description: str = flatten_string(ducked_description)

        # @@ Init channel state categories

        self.hoisted_category: discord.Channel = self.bot.get_channel(
            hoisted_category
        ) if hoisted_category else None
        self.log.info(f"Identified hoisted category: {self.hoisted_category}")

        self.busy_category: discord.Channel = self.bot.get_channel(
            busy_category
        ) if busy_category else None
        self.log.info(f"Identified busy category: {self.busy_category}")

        self.idle_category: discord.Channel = self.bot.get_channel(
            idle_category
        ) if idle_category else None
        self.log.info(f"Identified idle category: {self.idle_category}")

        self.pending_category: discord.Channel = self.bot.get_channel(
            pending_category
        ) if pending_category else None
        self.log.info(f"Identified pending category: {self.pending_category}")

        self.answered_category: discord.Channel = self.bot.get_channel(
            answered_category
        ) if answered_category else None
        self.log.info(f"Identified answered category: {self.answered_category}")

        # @@ Create channel state objects
        self.hoisted_state: ChannelState = ChannelState(
            self.hoisted_emoji,
            self.hoisted_name,
            self.hoisted_description,
            self.hoisted_category,
        )
        self.busy_state: ChannelState = ChannelState(
            self.busy_emoji, self.busy_name, self.busy_description, self.busy_category
        )
        self.idle_state: ChannelState = ChannelState(
            self.idle_emoji, self.idle_name, self.idle_description, self.idle_category
        )
        self.pending_state: ChannelState = ChannelState(
            self.pending_emoji,
            self.pending_name,
            self.pending_description,
            self.pending_category,
        )
        self.answered_state: ChannelState = ChannelState(
            self.answered_emoji,
            self.answered_name,
            self.answered_description,
            self.answered_category,
        )
        self.ducked_state: ChannelState = ChannelState(
            self.ducked_emoji,
            self.ducked_name,
            self.ducked_description,
            self.busy_category,
        )

        # @@ Init log emjoi
        self.log_relocated_emoji: str = log_relocated_emoji
        self.log_reassigned_emoji: str = log_reassigned_emoji
        self.log_renamed_emoji: str = log_renamed_emoji
        self.log_restored_emoji: str = log_restored_emoji
        self.log_resolved_emoji: str = log_resolved_emoji
        self.log_reminded_emoji: str = log_reminded_emoji
        self.log_ducked_emoji: str = log_ducked_emoji
        self.log_busied_from_hoisted_emoji: str = log_busied_from_hoisted_emoji
        self.log_busied_from_pending_emoji: str = log_busied_from_pending_emoji
        self.log_busied_from_answered_emoji: str = log_busied_from_answered_emoji
        self.log_fake_out_emoji: str = log_fake_out_emoji
        self.log_answered_from_pending_emoji: str = log_answered_from_pending_emoji
        self.log_hoisted_from_pending_emoji: str = log_hoisted_from_pending_emoji
        self.log_hoisted_from_idle_emoji: str = log_hoisted_from_idle_emoji
        self.log_no_channels_to_hoist_emoji: str = log_no_channels_to_hoist_emoji

        # @@ Init log colors
        self.log_relocated_color: str = self.bot.color_from_hex(log_relocated_color)
        self.log_reassigned_color: str = self.bot.color_from_hex(log_reassigned_color)
        self.log_renamed_color: str = self.bot.color_from_hex(log_renamed_color)
        self.log_restored_color: str = self.bot.color_from_hex(log_restored_color)
        self.log_resolved_color: str = self.bot.color_from_hex(log_resolved_color)
        self.log_reminded_color: str = self.bot.color_from_hex(log_reminded_color)
        self.log_ducked_color: str = self.bot.color_from_hex(log_ducked_color)
        self.log_busied_from_hoisted_color: str = self.bot.color_from_hex(
            log_busied_from_hoisted_color
        )
        self.log_busied_from_pending_color: str = self.bot.color_from_hex(
            log_busied_from_pending_color
        )
        self.log_busied_from_answered_color: str = self.bot.color_from_hex(
            log_busied_from_answered_color
        )
        self.log_fake_out_color: str = self.bot.color_from_hex(log_fake_out_color)
        self.log_answered_from_pending_color: str = self.bot.color_from_hex(
            log_answered_from_pending_color
        )
        self.log_hoisted_from_pending_color: str = self.bot.color_from_hex(
            log_hoisted_from_pending_color
        )
        self.log_hoisted_from_idle_color: str = self.bot.color_from_hex(
            log_hoisted_from_idle_color
        )
        self.log_no_channels_to_hoist_color: str = self.bot.color_from_hex(
            log_no_channels_to_hoist_color
        )

        # @@ Identify roles

        self.helper_role: discord.Role = self.bot.get_role(self.server, helper_role)
        self.log.info(f"Identified helper role: {self.helper_role}")

        self.ignored_role: discord.Role = self.bot.get_role(self.server, ignored_role)
        self.log.info(f"Identified ignored role: {self.ignored_role}")

        self.renamed_role: discord.Role = self.bot.get_role(self.server, renamed_role)
        self.log.info(f"Identified renamed role: {self.renamed_role}")

        # @@ Init toggles
        self.persist_asker: bool = persist_asker
        self.log_verbose_usernames: bool = log_verbose_usernames
        self.auto_poll: bool = auto_poll

        ## @@ Rate limiting stuff
        self.throttle_notif_cache: typing.Dict[ChannelId, datetime] = {}

        # @@ Setup polling task
        self.polling_task: asyncio.Task = None
        self.delta_until_idle = timedelta(seconds=self.seconds_until_idle)
        if self.auto_poll:
            self.start_polling_task()
        else:
            self.log.warning("Auto-polling is DISABLED.")

    @property
    def polling_task_str(self) -> str:
        return str(getattr(self.polling_task, "_coro", None))

    @property
    def num_hoisted_channels(self) -> int:
        return len(list(self.get_hoisted_channels()))

    async def log_to_channel(
        self,
        emoji: str,
        description: str,
        message: discord.Message = None,
        actor: discord.Member = None,
        color: discord.Color = discord.Embed.Empty,
    ):
        if not self.log_channel:
            return
        parts = [emoji]
        actor = actor or (message.author if message else None)
        if actor:
            parts.append(self.log_username(actor))
        parts.append(description)
        if message:
            message_link = self.bot.make_message_link(message)
            parts.append(f"[(View)]({message_link})")
        em = discord.Embed(color=color, description=" ".join(parts))
        await self.bot.send_message(self.log_channel, embed=em)

    def start_polling_task(self):
        if not self.polling_task or self.polling_task.done():
            # not already running
            self.log.info(
                f"Channels will be polled every {self.seconds_to_poll} seconds."
            )
            self.polling_task = asyncio.get_event_loop().create_task(
                self.polling_loop()
            )
            self.log.info(f"Created polling task: {self.polling_task_str}")
            return True

    def stop_polling_task(self):
        if self.polling_task and not self.polling_task.done():
            # running; can be cancelled
            self.polling_task.cancel()
            return True

    async def polling_loop(self):
        while not self.bot.is_closed:
            try:
                await asyncio.sleep(self.seconds_to_poll)
                await self.poll()
            except asyncio.CancelledError:
                self.log.warning(
                    f"Polling task {self.polling_task_str} was cancelled; breaking from loop..."
                )
                break
            except:
                self.log.exception(
                    f"Polling task {self.polling_task_str} encountered an error; ignoring..."
                )

    async def poll(self):
        self.log.debug(f"Polling {len(self.channels)} channels...")
        await self.sync_all()

    def get_channel_state(self, channel: discord.Channel) -> ChannelState:
        if self.is_channel_hoisted(channel):
            return self.hoisted_state
        if self.is_channel_busy(channel):
            return self.busy_state
        if self.is_channel_idle(channel):
            return self.idle_state
        if self.is_channel_pending(channel):
            return self.pending_state
        if self.is_channel_answered(channel):
            return self.answered_state
        if self.is_channel_ducked(channel):
            return self.ducked_state

    def is_channel(self, channel: discord.Channel, channel_state: ChannelState) -> bool:
        return channel_state.matches(channel)

    def is_channel_hoisted(self, channel: discord.Channel) -> bool:
        return self.is_channel(channel, self.hoisted_state)

    def is_channel_busy(self, channel: discord.Channel) -> bool:
        # Note that a ducked channel is technically also a busy channel.
        return self.is_channel(channel, self.busy_state) or self.is_channel_ducked(
            channel
        )

    def is_channel_idle(self, channel: discord.Channel) -> bool:
        return self.is_channel(channel, self.idle_state)

    def is_channel_pending(self, channel: discord.Channel) -> bool:
        return self.is_channel(channel, self.pending_state)

    def is_channel_answered(self, channel: discord.Channel) -> bool:
        return self.is_channel(channel, self.answered_state)

    def is_channel_ducked(self, channel: discord.Channel) -> bool:
        return self.is_channel(channel, self.ducked_state)

    def get_channels(self, state: ChannelState) -> typing.Iterable[discord.Channel]:
        for channel in self.channels:
            if self.is_channel(channel, state):
                yield channel

    def get_hoisted_channels(self) -> discord.Channel:
        return self.get_channels(self.hoisted_state)

    def get_busy_channels(self) -> discord.Channel:
        return self.get_channels(self.busy_state)

    def get_idle_channels(self) -> discord.Channel:
        return self.get_channels(self.idle_state)

    def get_pending_channels(self) -> discord.Channel:
        return self.get_channels(self.pending_state)

    def get_answered_channels(self) -> discord.Channel:
        return self.get_channels(self.answered_state)

    def get_random_channel(self, state: ChannelState) -> discord.Channel:
        channels = list(self.get_channels(state))
        if channels:
            random.shuffle(channels)
            return channels[0]

    def get_random_hoisted_channel(self) -> discord.Channel:
        return self.get_random_channel(self.hoisted_state)

    def get_random_busy_channel(self) -> discord.Channel:
        return self.get_random_channel(self.busy_state)

    def get_random_idle_channel(self) -> discord.Channel:
        return self.get_random_channel(self.idle_state)

    def get_random_pending_channel(self) -> discord.Channel:
        return self.get_random_channel(self.pending_state)

    def get_random_answered_channel(self) -> discord.Channel:
        return self.get_random_channel(self.answered_state)

    async def get_oldest_channel(self, state: ChannelState) -> discord.Channel:
        channels: typing.List[discord.Channel] = list(self.get_channels(state))
        latest_messages = await self.bot.get_latest_messages(channels)
        if latest_messages:
            latest_messages.sort(key=lambda message: message.timestamp)
            oldest_channel = latest_messages[0].channel
            return oldest_channel

    async def get_oldest_hoisted_channel(self) -> discord.Channel:
        return await self.get_oldest_channel(self.hoisted_state)

    async def get_oldest_busy_channel(self) -> discord.Channel:
        return await self.get_oldest_channel(self.busy_state)

    async def get_oldest_idle_channel(self) -> discord.Channel:
        return await self.get_oldest_channel(self.idle_state)

    async def get_oldest_pending_channel(self) -> discord.Channel:
        return await self.get_oldest_channel(self.pending_state)

    async def get_oldest_answered_channel(self) -> discord.Channel:
        return await self.get_oldest_channel(self.answered_state)

    async def get_hoistable_channel(self, state: ChannelState) -> discord.Channel:
        # Go from oldest channel to newest, based on the timestap of the latest
        # message. Take the first channel that has passed its update threshold,
        # plus some, so that we can be reasonably sure it has the capacity to
        # transition states twice in quick succession.
        channels: typing.List[discord.Channel] = list(self.get_channels(state))
        latest_messages = await self.bot.get_latest_messages(channels)
        now = datetime.utcnow()
        if latest_messages:
            latest_messages.sort(key=lambda message: message.timestamp)
            for message in latest_messages:
                channel = message.channel
                last_update = self.get_last_update_timestamp(channel)
                # If the channel does not have a last update recorded, just use
                # the timestamp of the latest message as a fall-back.
                if not last_update:
                    last_update = message.timestamp
                can_hoist_at = last_update + self.channel_update_delta
                can_hoist_now = can_hoist_at < now
                if can_hoist_now:
                    return channel

    async def get_hoistable_idle_channel(self) -> discord.Channel:
        return await self.get_hoistable_channel(self.idle_state)

    async def get_hoistable_pending_channel(self) -> discord.Channel:
        return await self.get_hoistable_channel(self.pending_state)

    async def get_hoistable_answered_channel(self) -> discord.Channel:
        return await self.get_hoistable_channel(self.answered_state)

    def get_channel_key(self, channel: discord.Channel) -> str:
        channel_entry: HelpChatChannelEntry = self.channel_map.get(channel)
        if channel_entry:
            return channel_entry.key

    def get_channel_index(self, channel: discord.Channel) -> str:
        channel_entry: HelpChatChannelEntry = self.channel_map.get(channel)
        if channel_entry:
            return channel_entry.index

    def build_channel_description(
        self,
        channel: discord.Channel,
        state: ChannelState,
        timestamp: datetime,
        asker: discord.Member = None,
    ) -> str:
        timestamp_str = timestamp.strftime(CHANNEL_TOPIC_TIMESTAMP_FORMAT)
        description = state.format_description(channel, asker)
        # store the last update timestamp
        description += f"\n\n{CHANNEL_TOPIC_TIMESTAMP_PREFIX}{timestamp_str}"
        # store the asker, if enabled
        if self.persist_asker and asker:
            description += f"\n\n{CHANNEL_TOPIC_ASKER_PREFIX}{asker.mention}"
        return description

    def log_username(self, user: discord.User) -> str:
        if self.log_verbose_usernames:
            return f"{user.mention} ({user})"
        return user.mention

    def get_last_update_timestamp(self, channel: discord.Channel) -> datetime:
        if channel.topic:
            topic_lines = str(channel.topic).splitlines()
            line_with_timestamp = None
            for line in reversed(topic_lines):
                if line.startswith(CHANNEL_TOPIC_TIMESTAMP_PREFIX):
                    line_with_timestamp = line
                    break
            if line_with_timestamp:
                text_with_timestamp = line_with_timestamp[
                    len(CHANNEL_TOPIC_TIMESTAMP_PREFIX) :
                ]
                try:
                    timestamp = datetime.strptime(
                        text_with_timestamp, CHANNEL_TOPIC_TIMESTAMP_FORMAT
                    )
                    return timestamp
                except:
                    pass

    def get_next_update_timestamp(self, channel: discord.Channel) -> datetime:
        last_update = self.get_last_update_timestamp(channel)
        # If no timestamp has been recorded yet, just return something that's
        # guaranteed to be old enough.
        if not last_update:
            return datetime.utcnow() - self.channel_update_delta
        next_update = last_update + self.channel_update_delta
        return next_update

    async def get_asker(self, channel: discord.Channel) -> discord.Member:
        if channel.topic:
            topic_lines = str(channel.topic).splitlines()
            line_with_asker = None
            for line in reversed(topic_lines):
                if line.startswith(CHANNEL_TOPIC_ASKER_PREFIX):
                    line_with_asker = line
                    break
            if line_with_asker:
                text_with_asker = line_with_asker[len(CHANNEL_TOPIC_ASKER_PREFIX) :]
                mention_match = MENTION_PATTERN.match(text_with_asker)
                if mention_match:
                    (user_id,) = mention_match.groups()
                    server: discord.Server = channel.server
                    member = server.get_member(user_id)
                    return member

    async def set_asker(
        self, channel: discord.Channel, asker: discord.Member
    ) -> discord.Member:
        # Just force-set the channel with the new asker.
        state = self.get_channel_state(channel)
        await self.set_channel(channel, state, asker=asker)
        return asker

    async def sync_channel_positions(self):
        # Go in reverse in case the positions were reverted. Otherwise, this
        # could cause a cascading effect where channels fold over one another.
        for ch in reversed(self.channels):
            expected_position = (self.get_channel_index(ch) + 1) * 100
            if expected_position != ch.position:
                await self.bot.edit_channel(ch, position=expected_position)

    async def sync_idle_channels(self):
        for channel in self.channels:
            state = self.get_channel_state(channel)
            # Busy channels can become idle; and, instead of becoming idle,
            # pending channels will automatically be assumed answered.
            if state in (self.busy_state, self.pending_state):
                latest_message = await self.bot.get_latest_message(channel)
                # If there's no latest message, then... set it as answered?
                if not latest_message:
                    try:
                        await self.set_channel_answered(channel)
                    except ChannelUpdateTooSoon:
                        pass
                    continue
                now: datetime = datetime.utcnow()
                latest: datetime = latest_message.timestamp
                then: datetime = latest + self.delta_until_idle
                if now > then:
                    # Busy channels become idle.
                    if state == self.busy_state:
                        try:
                            await self.set_channel_idle(channel)
                        except ChannelUpdateTooSoon:
                            pass
                    # Pending channels become answered.
                    elif state == self.pending_state:
                        try:
                            if await self.set_channel_answered(channel):
                                await self.log_to_channel(
                                    emoji=self.log_answered_from_pending_emoji,
                                    description=f"{channel.mention} remained inactive and was automatically resolved",
                                    color=self.log_answered_from_pending_color,
                                )
                        except ChannelUpdateTooSoon:
                            pass

    async def sync_hoisted_channels(self):
        # Don't do anything unless we care about hoisted channels.
        if self.max_hoisted_channels > 0:
            delta = self.max_hoisted_channels - self.num_hoisted_channels
            # Recycle available channels to top-off the hoisted ones.
            if delta > 0:
                for i in range(delta):
                    if not await self.try_hoist_channel():
                        break

    async def sync_all(self):
        await self.sync_channel_positions()
        await self.sync_idle_channels()
        await self.sync_hoisted_channels()

    async def set_channel(
        self,
        channel: discord.Channel,
        state: ChannelState,
        ignore_throttling: bool = False,
        asker: typing.Union[discord.User, bool] = None,
        clear_asker: bool = False,
    ):
        now = datetime.utcnow()
        # If we're not ignoring throttling, make sure it's not too soon for the
        # channel to update again.
        if not ignore_throttling:
            next_update = self.get_next_update_timestamp(channel)
            if next_update > now:
                raise ChannelUpdateTooSoon(next_update)
        # If askers are enabled, one was not provided, and we have not been
        # asked to clear the asker, then determine the asker automatically.
        if self.persist_asker and (not asker) and (not clear_asker):
            asker = await self.get_asker(channel)
        # Set the new channel name, which doubles as its persistent state.
        channel_key = self.get_channel_key(channel)
        if asker and self.renamed_role in asker.roles:
            new_name = state.format_name(key=channel_key, channel=channel)
        else:
            new_name = state.format_name(key=channel_key, channel=channel, asker=asker)
        # Determine the new topic based on the new channel state.
        new_topic = self.build_channel_description(
            channel, state, timestamp=now, asker=asker
        )
        # Determine the new category as well.
        new_category = state.category
        # And finally, it's time to update the channel all in one go.
        await self.bot.edit_channel(
            channel, name=new_name, topic=new_topic, category=new_category
        )

    async def set_channel_hoisted(
        self,
        channel: discord.Channel,
        force: bool = False,
        ignore_throttling: bool = False,
    ) -> bool:
        # All of answered, pending, and idle channels can become hoisted when we
        # need to top-off the hoisted channels, each with their own priority.
        # ... unless we're forcing (for example, with an admin command).
        # The reason we have more strict checks here is to try and protect from
        # a variety of async race conditions.
        if force or (
            (self.num_hoisted_channels < self.max_hoisted_channels)
            and (
                self.is_channel_answered(channel)
                or self.is_channel_pending(channel)
                or self.is_channel_idle(channel)
            )
        ):
            # Hoist the channel and clear the asker.
            await self.set_channel(
                channel,
                self.hoisted_state,
                ignore_throttling=ignore_throttling,
                clear_asker=True,
            )
            # Attempt to send the prompt message. We do this after, because we
            # can't be certain the channel actually became hoisted.
            await self.maybe_send_prompt_message(channel)
            return True

    async def set_channel_busy(
        self,
        channel: discord.Channel,
        force: bool = False,
        ignore_throttling: bool = False,
        asker: discord.User = None,
    ) -> bool:
        # Any channel that's not already busy can become busy.
        if force or not self.is_channel_busy(channel):
            await self.set_channel(
                channel,
                self.busy_state,
                ignore_throttling=ignore_throttling,
                asker=asker,
            )
            await self.sync_hoisted_channels()
            return True

    async def set_channel_idle(
        self, channel: discord.Channel, force: bool = False
    ) -> bool:
        # Only busy channels can become idle.
        if force or self.is_channel_busy(channel):
            await self.set_channel(channel, self.idle_state)
            return True

    async def set_channel_pending(
        self, channel: discord.Channel, force: bool = False
    ) -> bool:
        # Both busy and idle channels can become pending.
        if force or self.is_channel_busy(channel) or self.is_channel_idle(channel):
            await self.set_channel(channel, self.pending_state)
            return True

    async def set_channel_answered(
        self,
        channel: discord.Channel,
        force: bool = False,
        ignore_throttling: bool = False,
    ) -> bool:
        # All of busy, idle, and pending channels can become answered.
        # Note that hoisted channels cannot go directly to answered, as this
        # would be redundant.
        if (
            force
            or self.is_channel_busy(channel)
            or self.is_channel_idle(channel)
            or self.is_channel_pending(channel)
        ):
            await self.set_channel(
                channel, self.answered_state, ignore_throttling=ignore_throttling
            )
            return True

    async def set_channel_ducked(
        self, channel: discord.Channel, force: bool = False
    ) -> bool:
        # Only busy channels can become ducked.
        if force or self.is_channel_busy(channel):
            await self.set_channel(channel, self.ducked_state)
            return True

    async def reset_channel(
        self, channel: discord.Channel, ignore_throttling: bool = False
    ):
        # Managed channels with an unknown state (perhaps due to outdated
        # emoji) will be considered answered.
        state = self.get_channel_state(channel) or self.answered_state
        await self.set_channel(channel, state, ignore_throttling=ignore_throttling)

    async def reset_all(self):
        for channel in self.channels:
            try:
                await self.reset_channel(channel)
            except ChannelUpdateTooSoon:
                pass

    async def is_channel_prompted(self, channel: discord.Channel) -> bool:
        # Check if the latest message is the hoisted message prompt. We do this
        # by comparing the color of the embed strip and, if that matches, the
        # first few characters of text as well.
        latest_message: discord.Message = await self.bot.get_latest_message(channel)
        if latest_message.author == self.bot.user and latest_message.embeds:
            latest_embed: discord.Embed = latest_message.embeds[0]
            em_color = latest_embed.get("color", None)
            em_description = latest_embed.get("description", None)
            return (
                em_color == self.prompt_color.value
                and em_description
                and em_description[:20] == self.prompt_message[:20]
            )

    async def maybe_send_prompt_message(self, channel: discord.Channel) -> bool:
        # Send hoisted message, if any, into the newly-hoisted channel - but
        # only if it's not already the most recent message (which can happen if
        # someone fakes-out the channel by deleting their own message).
        if self.prompt_message and not await self.is_channel_prompted(channel):
            em = discord.Embed(description=self.prompt_message, color=self.prompt_color)
            await self.bot.send_message(channel, embed=em)
            return True

    async def maybe_duck_channel(
        self, channel: discord.Channel, message: discord.Message
    ):
        author: discord.Member = message.author
        # If askers are enabled, then the asker must also be the ducker.
        if self.persist_asker:
            asker = await self.get_asker(channel)
            if asker.id != author.id:
                return False
        # Otherwise, if askers are not enabled, short-circuit ignored users...
        # because then there's no way to tell if they're the true asker.
        elif self.ignored_role in author.roles:
            return False
        # Regardless of whether askers are enabled, the last 10 messages in the
        # channel must all be from the ducker.
        async for m in self.bot.iter_latest_messages(channels=[channel], limit=10):
            if author.id != m.author.id:
                return False
        # Finally, if we get all the way here, we can duck the channel.
        try:
            if await self.set_channel_ducked(channel):
                await self.bot.add_reaction(message, self.ducked_emoji)
                await self.log_to_channel(
                    emoji=self.log_ducked_emoji,
                    description=f"ducked {channel.mention}",
                    message=message,
                    color=self.log_ducked_color,
                )
        except ChannelUpdateTooSoon as ex:
            await self.notify_throttling(ex, message)

    async def notify_throttling(
        self, ex: ChannelUpdateTooSoon, message: discord.Message
    ):
        channel: discord.Channel = message.channel
        now = datetime.utcnow()
        last_notif = self.throttle_notif_cache.get(channel.id, None)
        do_notif = True
        if last_notif:
            next_notif = last_notif + timedelta(seconds=self.second_to_throttle)
            # either the next notification hasn't happened yet,
            # or it hasn't happened during this rate-limiting cycle yet
            do_notif = (next_notif <= now) or (next_notif < ex.next_update)
        if do_notif:
            self.throttle_notif_cache[channel.id] = now
            delta = ex.next_update - now
            minutes = delta.seconds // 60
            seconds = delta.seconds % 60
            response = f"This channel is being rate-limited, please try again in {minutes}m {seconds}s."
            await self.bot.send_message(
                channel, f"{message.author.mention} {self.rate_limit_emoji} {response}"
            )
            await self.bot.add_reaction(message, self.rate_limit_emoji)

    async def relocate(self, message: discord.Message, reactor: discord.Member):
        author: discord.Member = message.author
        from_channel: discord.Channel = message.channel
        # Short-circuit if no relocate message is defined.
        if not self.relocate_message_without_channel:
            return
        # Prefer relocating to hoisted channels over answered ones. In theory,
        # the only way an answered channel would be chosen is if hoisted
        # channels are disabled altogether.
        to_channel = (
            self.get_random_hoisted_channel() or self.get_random_answered_channel()
        )
        if to_channel:
            await self.log_to_channel(
                emoji=self.log_relocated_emoji,
                description=f"relocated {self.log_username(author)} from {from_channel.mention} to {to_channel.mention}",
                message=message,
                actor=reactor,
                color=self.log_relocated_color,
            )
            # Fall-back if a "relocate message with channel" is not defined.
            if self.relocate_message_with_channel:
                response = self.relocate_message_with_channel.format(
                    author=author,
                    reactor=reactor,
                    from_channel=from_channel,
                    to_channel=to_channel,
                )
            else:
                response = self.relocate_message_without_channel.format(
                    author=author, reactor=reactor, from_channel=from_channel
                )
        else:
            await self.log_to_channel(
                emoji=self.log_relocated_emoji,
                description=f"relocated {self.log_username(author)} from {from_channel.mention}",
                message=message,
                actor=reactor,
                color=self.log_relocated_color,
            )
            response = self.relocate_message_without_channel.format(
                author=author, reactor=reactor, from_channel=from_channel
            )
        await self.bot.send_message(message.channel, response)

    async def remind(self, channel: discord.Channel, member: discord.Member) -> bool:
        # Attempt to set the channel to pending.
        if await self.set_channel_pending(channel):
            # If that works, send the reminder message to the user.
            await self.bot.send_message(
                channel,
                content=self.reminder_message.format(
                    user=member,
                    resolve_emoji=self.resolve_emoji,
                    resolve_emoji_raw=f"`:{self.resolve_emoji.name}:`",
                ),
            )
            return True

    async def remind_asker(
        self, channel: discord.Channel, actor: discord.Member
    ) -> discord.Member:
        # If askers are enabled...
        if self.persist_asker:
            asker = await self.get_asker(channel)
            # And the channel has an asker...
            if asker:
                # Then remind the asker.
                if await self.remind(channel, asker):
                    return asker

    async def reassign_asker(
        self, channel: discord.Channel, new_asker: discord.Member, actor: discord.Member
    ) -> typing.Tuple[discord.Member, discord.Member]:
        # Attempt to change the asker of the channel.
        # 1. Must have askers enabled
        # 2. Must have a helper role defined
        # 3. Actor must have the asker role
        if (
            self.persist_asker
            and self.helper_role
            and (self.helper_role in actor.roles)
        ):
            old_asker = await self.get_asker(channel)
            if await self.set_asker(channel, new_asker):
                # Return the old asker (if there was one), as well as the new one so
                # that we at least know that reassignment was successful.
                return (old_asker, new_asker)
        return (None, None)

    async def rename_asker(
        self, channel: discord.Channel, actor: discord.Member
    ) -> discord.Member:
        # Attempt to rename the channel and start disregarding the asker's name.
        # 1. Must have askers enabled
        # 2. Must have a renamed role defined
        # 3. Must have a helper role defined
        # 4. Actor must have the helper role
        if (
            self.persist_asker
            and self.renamed_role
            and self.helper_role
            and (self.helper_role in actor.roles)
        ):
            asker = await self.get_asker(channel)
            # 5. Asker must exist
            # 6. Asker must not have the helper role (immunity)
            # 7. Asker must not already have the renamed role
            if (
                asker
                and (self.helper_role not in asker.roles)
                and (self.renamed_role not in asker.roles)
            ):
                await self.bot.add_roles(asker, self.renamed_role)
                await self.reset_channel(channel, ignore_throttling=True)
                return asker

    async def restore_asker(
        self, channel: discord.Channel, actor: discord.Member
    ) -> discord.Member:
        # Attempt to restore the channel name and stop disregarding the asker's name.
        # 1. Must have askers enabled
        # 2. Must have a renamed role defined
        # 3. Must have a helper role defined
        # 4. Actor must have the helper role
        if (
            self.persist_asker
            and self.renamed_role
            and self.helper_role
            and (self.helper_role in actor.roles)
        ):
            asker = await self.get_asker(channel)
            # 5. Asker must exist
            # 6. Asker must have the renamed role in order to remove it
            if asker and (self.renamed_role in asker.roles):
                await self.bot.remove_roles(asker, self.renamed_role)
                await self.reset_channel(channel, ignore_throttling=True)
                return asker

    async def do_relocate(
        self, channel: discord.Channel, message: discord.Message, actor: discord.Member
    ):
        if self.ignored_role in actor.roles:
            return
        await self.relocate(message, actor)
        await self.bot.add_reaction(message, self.relocate_emoji)

    async def do_reassign(
        self, channel: discord.Channel, message: discord.Message, actor: discord.Member
    ):
        if self.ignored_role in actor.roles:
            return
        try:
            old_asker, new_asker = await self.reassign_asker(
                channel, new_asker=message.author, actor=actor
            )
            if old_asker:
                await self.bot.add_reaction(message, self.reassign_emoji)
                await self.log_to_channel(
                    emoji=self.log_reassigned_emoji,
                    description=f"reassigned {channel.mention} from {self.log_username(old_asker)} to {self.log_username(new_asker)}",
                    message=message,
                    actor=actor,
                    color=self.log_reassigned_color,
                )
            elif new_asker:
                await self.bot.add_reaction(message, self.reassign_emoji)
                await self.log_to_channel(
                    emoji=self.log_reassigned_emoji,
                    description=f"reassigned {channel.mention} to {self.log_username(new_asker)}",
                    message=message,
                    actor=actor,
                    color=self.log_reassigned_color,
                )
        except ChannelUpdateTooSoon as ex:
            await self.notify_throttling(ex, message)

    async def do_resolve(
        self, channel: discord.Channel, message: discord.Message, actor: discord.Member
    ):
        # Ignored users cannot resolve, unless it's their own channel.
        if self.ignored_role in actor.roles:
            # Short-circuit if askers are not enabled.
            if not self.persist_asker:
                return
            # Short-circuit if the actor is not the asker.
            asker = await self.get_asker(channel)
            if actor.id != asker.id:
                return
        # Otherwise, we can attempt to set the channel as answered.
        try:
            if await self.set_channel_answered(channel, ignore_throttling=True):
                await self.bot.add_reaction(message, self.resolve_emoji)
                await self.log_to_channel(
                    emoji=self.log_resolved_emoji,
                    description=f"resolved {channel.mention}",
                    message=message,
                    actor=actor,
                    color=self.log_resolved_color,
                )
        except ChannelUpdateTooSoon as ex:
            await self.notify_throttling(ex, message)

    async def do_remind(
        self, channel: discord.Channel, message: discord.Message, actor: discord.Member
    ):
        if self.ignored_role in actor.roles:
            return
        try:
            affected_asker = await self.remind_asker(channel, actor)
            if affected_asker:
                await self.bot.add_reaction(message, self.remind_emoji)
                await self.log_to_channel(
                    emoji=self.log_reminded_emoji,
                    description=f"reminded {self.log_username(affected_asker)} in {channel.mention}",
                    message=message,
                    actor=actor,
                    color=self.log_reminded_color,
                )
        except ChannelUpdateTooSoon as ex:
            await self.notify_throttling(ex, message)

    async def do_rename(
        self, channel: discord.Channel, message: discord.Message, actor: discord.Member
    ):
        if self.ignored_role in actor.roles:
            return
        try:
            affected_asker = await self.rename_asker(channel, actor)
            if affected_asker:
                await self.bot.add_reaction(message, self.rename_emoji)
                await self.log_to_channel(
                    emoji=self.log_renamed_emoji,
                    description=f"renamed {channel.mention} from {affected_asker.mention}",
                    message=message,
                    actor=actor,
                    color=self.log_renamed_color,
                )
        except ChannelUpdateTooSoon as ex:
            await self.notify_throttling(ex, message)

    async def do_restore(
        self, channel: discord.Channel, message: discord.Message, actor: discord.Member
    ):
        if self.ignored_role in actor.roles:
            return
        try:
            affected_asker = await self.restore_asker(channel, actor)
            if affected_asker:
                await self.bot.add_reaction(message, self.restore_emoji)
                await self.log_to_channel(
                    emoji=self.log_restored_emoji,
                    description=f"restored {channel.mention} to {affected_asker.mention}",
                    message=message,
                    actor=actor,
                    color=self.log_restored_color,
                )
        except ChannelUpdateTooSoon as ex:
            await self.notify_throttling(ex, message)

    async def try_hoist_channel(self):
        # If we've hit the max, don't hoist any more channels.
        if self.num_hoisted_channels < self.max_hoisted_channels:
            # Always try to get the oldest answered channel first.
            channel_to_hoist = await self.get_hoistable_answered_channel()
            # If there weren't any answered channels available, but we're
            # under the min, then we'll consider pending and idle channels.
            if (not channel_to_hoist) and (
                self.num_hoisted_channels < self.min_hoisted_channels
            ):
                # Prioritize pending channels over idle ones, as the former are
                # more likely to have an acceptable answer.
                channel_to_hoist = await self.get_hoistable_pending_channel()
                if channel_to_hoist:
                    # Log when we recycle a pending channel.
                    await self.log_to_channel(
                        emoji=self.log_hoisted_from_pending_emoji,
                        description=f"Pending channel {channel_to_hoist.mention} was hoisted because no answered channels were available",
                        color=self.log_hoisted_from_pending_color,
                    )
                else:
                    channel_to_hoist = await self.get_hoistable_idle_channel()
                    # Or when we recycle an idle channel.
                    if channel_to_hoist:
                        await self.log_to_channel(
                            emoji=self.log_hoisted_from_idle_emoji,
                            description=f"Idle channel {channel_to_hoist.mention} was hoisted because no answered or pending channels were available",
                            color=self.log_hoisted_from_idle_color,
                        )
                # Warn if we still haven't found a channel to recycle.
                if not channel_to_hoist:
                    warning_text = f"No channels available to replenish the minimum amount of {self.min_hoisted_channels} hoisted channels!"
                    self.log.warning(warning_text)
                    await self.log_to_channel(
                        emoji=self.log_no_channels_to_hoist_emoji,
                        description=warning_text,
                        color=self.log_no_channels_to_hoist_color,
                    )
            # Otherwise, if we're still meeting the min, we're fine even if we
            # don't have another channel to hoist.
            if channel_to_hoist:
                try:
                    return await self.set_channel_hoisted(
                        channel_to_hoist, ignore_throttling=True
                    )
                except ChannelUpdateTooSoon:
                    return None

    async def on_ready(self):
        self.log.info("Readying state...")
        # Add the latest X messages from every channel into the client cache
        # so that discord.py will care about any reactions applied to them.
        # We do this so that emoji actions on recent messages will be seen.
        try:
            messages_to_cache = await self.bot.get_latest_messages(
                self.channels, limit=self.preemptive_cache_size
            )
            self.bot.connection.messages.extend(messages_to_cache)
            self.log.info(
                f"Preemptively cached the {self.preemptive_cache_size} most recent messages across {len(self.channels)} managed channels. ({len(messages_to_cache)} total)"
            )
        except:
            self.log.exception("Failed to cache messages preemptively:")
        # Sync all channels. Avoid resetting them and triggerring their cooldown immediately.
        await self.sync_all()
        # Let people know we're ready.
        self.log.info("Help-chat initialization complete!")
        await self.log_to_channel(
            emoji="👍",
            description="Help-chat initialization complete!",
            color=self.bot.color_from_hex("#272A2D"),
        )

    async def on_reaction(self, reaction: discord.Reaction, reactor: discord.Member):
        message: discord.Message = reaction.message
        channel: discord.Channel = message.channel
        author: discord.Member = message.author
        # @@ RELOCATE
        # On the first reaction to a *human* message in *any* channel.
        if (
            reaction.emoji == self.relocate_emoji
            and reaction.count == 1
            and author != self.bot.user
        ):
            await self.do_relocate(channel, message, reactor)
        # @@ REASSIGN
        # On the first reaction to a *human* message in a *managed* channel.
        elif (
            reaction.emoji == self.reassign_emoji
            and reaction.count == 1
            and author != self.bot.user
            and channel in self.channels
        ):
            await self.do_reassign(channel, message, reactor)
        # @@ RESOLVE
        # On the first reaction to a *recent* message in a *managed* channel.
        elif (
            reaction.emoji == self.resolve_emoji
            and reaction.count == 1
            and channel in self.channels
            and await self.bot.is_latest_message(
                message, limit=self.preemptive_cache_size
            )
        ):
            await self.do_resolve(channel, message, reactor)
        # @@ REMIND
        # On the first reaction to a *human* message in a *managed* channel.
        elif (
            reaction.emoji == self.remind_emoji
            and reaction.count == 1
            and author != self.bot.user
            and channel in self.channels
        ):
            await self.do_remind(channel, message, reactor)
        # @@ RENAME
        # On the first reaction to *any* message in a *managed* channel.
        elif (
            reaction.emoji == self.rename_emoji
            and reaction.count == 1
            and channel in self.channels
        ):
            await self.do_rename(channel, message, reactor)
        # @@ RESTORE
        # On the first reaction to any message in a managed channel.
        elif (
            reaction.emoji == self.restore_emoji
            and reaction.count == 1
            and channel in self.channels
        ):
            await self.do_restore(channel, message, reactor)

    async def on_message(self, message: discord.Message):
        channel: discord.Channel = message.channel
        author: discord.Member = message.author
        # Some actions may vary depending on the prior channel state.
        prior_state: ChannelState = self.get_channel_state(channel)
        # Unlike with reactions, we only care about managed channels here.
        if channel in self.channels:
            # @@ RESOLVE
            # Only when the message contains exactly the resolve emoji.
            if message.content == str(self.resolve_emoji):
                await self.do_resolve(channel, message, author)
            # @@ REMIND
            # Only when the message contains exactly the remind emoji.
            elif message.content == str(self.remind_emoji):
                await self.do_remind(channel, message, author)
            # @@ RENAME
            # Only when the message contains exactly the rename emoji.
            elif message.content == str(self.rename_emoji):
                await self.do_rename(channel, message, author)
            # @@ RESTORE
            # Only when the message contains exactly the restore emoji.
            elif message.content == str(self.restore_emoji):
                await self.do_restore(channel, message, author)
            # @@ DUCK
            # Only when the message contains exactly the ducked emoji.
            elif message.content == str(self.ducked_emoji):
                await self.maybe_duck_channel(channel, message)
            # @@ MESSAGE: HOISTED
            # Update asker, change to busy, and log.
            elif prior_state == self.hoisted_state:
                try:
                    await self.set_channel_busy(
                        channel, ignore_throttling=True, asker=author
                    )
                    await self.log_to_channel(
                        emoji=self.log_busied_from_hoisted_emoji,
                        description=f"asked in {channel.mention}",
                        message=message,
                        color=self.log_busied_from_hoisted_color,
                    )
                except ChannelUpdateTooSoon as ex:
                    await self.notify_throttling(ex, message)
            # @@ MESSAGE: PENDING
            # *Maybe* change to busy and log.
            elif prior_state == self.pending_state:
                # If asker's are enabled, only the asker can cause a change in
                # state from pending. Short-circuit if it's somebody else.
                if self.persist_asker:
                    asker = await self.get_asker(channel)
                    if author.id != asker.id:
                        return
                try:
                    await self.set_channel_busy(channel)
                    await self.log_to_channel(
                        emoji=self.log_busied_from_pending_emoji,
                        description=f"responded in {channel.mention}",
                        message=message,
                        color=self.log_busied_from_pending_color,
                    )
                except ChannelUpdateTooSoon as ex:
                    await self.notify_throttling(ex, message)
            # @@ MESSAGE: ANSWERED
            # Change to busy and log.
            elif prior_state == self.answered_state:
                try:
                    # Don't ignore throttling here, because we want to ignore it
                    # on resolving instead.
                    await self.set_channel_busy(channel)
                    await self.log_to_channel(
                        emoji=self.log_busied_from_answered_emoji,
                        description=f"re-opened {channel.mention}",
                        message=message,
                        color=self.log_busied_from_answered_color,
                    )
                except ChannelUpdateTooSoon as ex:
                    await self.notify_throttling(ex, message)
            # @@ ANYTHING ELSE (BUSY, IDLE)
            # Just change to busy without logging.
            else:
                try:
                    await self.set_channel_busy(channel)
                except ChannelUpdateTooSoon as ex:
                    await self.notify_throttling(ex, message)

    async def on_message_delete(self, message: discord.Message):
        channel: discord.Channel = message.channel
        author: discord.Member = message.author
        # Again, we only care about managed channels here.
        if channel in self.channels:
            # Furthermore, we only care about busy/idle channels.
            if self.is_channel_busy(channel) or self.is_channel_idle(channel):
                # Do we need to nag the user about resolving the channel first?
                # If the most recent message is now the prompt; probably yes.
                if await self.is_channel_prompted(channel):
                    # Ping the user with a message, if configured.
                    sent_message = None
                    if self.fake_out_message:
                        sent_message = await self.bot.send_message(
                            channel,
                            content=self.fake_out_message.format(
                                user=author,
                                resolve_emoji=self.resolve_emoji,
                                resolve_emoji_raw=f"`:{self.resolve_emoji.name}:`",
                            ),
                        )
                    else:
                        sent_message = None
                    # Automatically set the channel as answered... if it's not too soon.
                    try:
                        await self.set_channel_answered(channel)
                    except ChannelUpdateTooSoon as ex:
                        if sent_message:
                            await self.notify_throttling(ex, sent_message)
                    # And create a log entry for this.
                    await self.log_to_channel(
                        emoji=self.log_fake_out_emoji,
                        description=f"faked-out {channel.mention}",
                        message=sent_message,
                        actor=author,
                        color=self.log_fake_out_color,
                    )

    async def destroy(self) -> bool:
        return self.stop_polling_task()
