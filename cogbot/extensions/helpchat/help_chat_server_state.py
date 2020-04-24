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

SECONDS_UNTIL_IDLE = 1800
SECONDS_TO_POLL = 60
PREEMPTIVE_CACHE_SIZE = 10

RELOCATE_EMOJI = "➡️"
RENAME_EMOJI = "📛"
RESTORE_EMOJI = "♻️"
RESOLVE_EMOJI = "✅"
REMIND_EMOJI = "🎗️"

HOISTED_EMOJI = "👋"
BUSY_EMOJI = "💬"
IDLE_EMOJI = "⏰"
ANSWERED_EMOJI = "✅"
DUCKED_EMOJI = "🦆"

HOISTED_NAME = "ask-here-{key}"
BUSY_NAME = "busy-question-{key}"
IDLE_NAME = "idle-question-{key}"
ANSWERED_NAME = "answered-question-{key}"
DUCKED_NAME = "duck-session-{key}"

HOISTED_DESCRIPTION = (
    "Have a question? This channel does not have an ongoing discussion. Ask here!"
)
BUSY_DESCRIPTION = (
    "A question has been asked in this channel and discussion is ongoing."
    " New questions should go in another channel."
)
IDLE_DESCRIPTION = (
    "A question has been asked in this channel but discussion has gone idle."
    " New questions should still go in another channel."
)
ANSWERED_DESCRIPTION = (
    "A question has been asked in this channel and an answer has been given."
    " New questions should still go in another channel."
)
DUCKED_DESCRIPTION = (
    "A question has been asked in this channel and the asker appears to be"
    " talking themselves through a solution."
)

LOG_RELOCATED_EMOJI = RELOCATE_EMOJI
LOG_RENAMED_EMOJI = RENAME_EMOJI
LOG_RESTORED_EMOJI = RESTORE_EMOJI
LOG_RESOLVED_EMOJI = RESOLVE_EMOJI
LOG_REMINDED_EMOJI = REMIND_EMOJI
LOG_DUCKED_EMOJI = DUCKED_EMOJI
LOG_BUSIED_FROM_HOISTED_EMOJI = HOISTED_EMOJI
LOG_BUSIED_FROM_ANSWERED_EMOJI = "🙊"
LOG_FAKE_OUT_EMOJI = "🙈"

LOG_RELOCATED_COLOR = "#3B88C3"
LOG_RENAMED_COLOR = "#DD2E44"
LOG_RESTORED_COLOR = "#3E721D"
LOG_RESOLVED_COLOR = "#77B255"
LOG_REMINDED_COLOR = "#9B59B6"
LOG_DUCKED_COLOR = "#C77538"
LOG_BUSIED_FROM_HOISTED_COLOR = "#FFDC5D"
LOG_BUSIED_FROM_ANSWERED_COLOR = "#BF6952"
LOG_FAKE_OUT_COLOR = "#BF6952"

PROMPT_COLOR = "#00ACED"

MENTION_PATTERN = re.compile(r"<@\!?(\w+)>")


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
        relocate_message_with_channel: str,
        relocate_message_without_channel: str,
        reminder_message: str = None,
        fake_out_message: str = None,
        log_channel: str = None,
        seconds_until_idle: int = SECONDS_UNTIL_IDLE,
        seconds_to_poll: int = SECONDS_TO_POLL,
        preemptive_cache_size: int = PREEMPTIVE_CACHE_SIZE,
        hoisted_category: str = None,
        busy_category: str = None,
        idle_category: str = None,
        answered_category: str = None,
        min_hoisted_channels: int = 0,
        max_hoisted_channels: int = 0,
        relocate_emoji: str = RELOCATE_EMOJI,
        rename_emoji: str = RENAME_EMOJI,
        restore_emoji: str = RESTORE_EMOJI,
        resolve_emoji: str = RESOLVE_EMOJI,
        remind_emoji: str = REMIND_EMOJI,
        hoisted_emoji: str = HOISTED_EMOJI,
        busy_emoji: str = BUSY_EMOJI,
        idle_emoji: str = IDLE_EMOJI,
        answered_emoji: str = ANSWERED_EMOJI,
        ducked_emoji: str = DUCKED_EMOJI,
        answered_name: str = ANSWERED_NAME,
        busy_name: str = BUSY_NAME,
        idle_name: str = IDLE_NAME,
        hoisted_name: str = HOISTED_NAME,
        ducked_name: str = DUCKED_NAME,
        answered_description: str = ANSWERED_DESCRIPTION,
        busy_description: str = BUSY_DESCRIPTION,
        idle_description: str = IDLE_DESCRIPTION,
        hoisted_description: str = HOISTED_DESCRIPTION,
        ducked_description: str = DUCKED_DESCRIPTION,
        persist_asker: bool = False,
        renamed_asker_role: str = None,
        role_that_can_rename: str = None,
        ignored_role: str = None,
        log_relocated_emoji: str = LOG_RELOCATED_EMOJI,
        log_renamed_emoji: str = LOG_RENAMED_EMOJI,
        log_restored_emoji: str = LOG_RESTORED_EMOJI,
        log_resolved_emoji: str = LOG_RESOLVED_EMOJI,
        log_reminded_emoji: str = LOG_REMINDED_EMOJI,
        log_ducked_emoji: str = LOG_DUCKED_EMOJI,
        log_busied_from_hoisted_emoji: str = LOG_BUSIED_FROM_HOISTED_EMOJI,
        log_busied_from_answered_emoji: str = LOG_BUSIED_FROM_ANSWERED_EMOJI,
        log_fake_out_emoji: str = LOG_FAKE_OUT_EMOJI,
        log_relocated_color: str = LOG_RELOCATED_COLOR,
        log_renamed_color: str = LOG_RENAMED_COLOR,
        log_restored_color: str = LOG_RESTORED_COLOR,
        log_resolved_color: str = LOG_RESOLVED_COLOR,
        log_reminded_color: str = LOG_REMINDED_COLOR,
        log_ducked_color: str = LOG_DUCKED_COLOR,
        log_busied_from_hoisted_color: str = LOG_BUSIED_FROM_HOISTED_COLOR,
        log_busied_from_answered_color: str = LOG_BUSIED_FROM_ANSWERED_COLOR,
        log_fake_out_color: str = LOG_FAKE_OUT_COLOR,
        resolve_with_reaction: bool = False,
        prompt_message: str = None,
        prompt_color: str = PROMPT_COLOR,
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

        self.log_channel: discord.Channel = self.bot.get_channel(
            log_channel
        ) if log_channel else None

        self.log.info(f"Identified {len(self.channels)} help channels.")

        self.relocate_message_with_channel: str = relocate_message_with_channel
        self.relocate_message_without_channel: str = relocate_message_without_channel
        self.reminder_message: str = reminder_message
        self.fake_out_message: str = fake_out_message

        self.seconds_until_idle: int = seconds_until_idle
        self.seconds_to_poll: int = seconds_to_poll

        self.min_hoisted_channels: int = min_hoisted_channels
        self.max_hoisted_channels: int = max(min_hoisted_channels, max_hoisted_channels)

        self.relocate_emoji: typing.Union[str, discord.Emoji] = self.bot.get_emoji(
            self.server, relocate_emoji
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

        self.hoisted_category: discord.Channel = self.bot.get_channel(
            hoisted_category
        ) if hoisted_category else None

        self.busy_category: discord.Channel = self.bot.get_channel(
            busy_category
        ) if busy_category else None

        self.idle_category: discord.Channel = self.bot.get_channel(
            idle_category
        ) if idle_category else None

        self.answered_category: discord.Channel = self.bot.get_channel(
            answered_category
        ) if answered_category else None

        self.log.info(f"Identified hoisted category: {self.hoisted_category}")
        self.log.info(f"Identified busy category: {self.busy_category}")
        self.log.info(f"Identified idle category: {self.idle_category}")
        self.log.info(f"Identified answered category: {self.answered_category}")

        self.hoisted_emoji: str = hoisted_emoji
        self.busy_emoji: str = busy_emoji
        self.idle_emoji: str = idle_emoji
        self.answered_emoji: str = answered_emoji
        self.ducked_emoji: str = ducked_emoji

        self.hoisted_name: str = hoisted_name
        self.busy_name: str = busy_name
        self.idle_name: str = idle_name
        self.answered_name: str = answered_name
        self.ducked_name: str = ducked_name

        self.hoisted_description: str = hoisted_description
        self.busy_description: str = busy_description
        self.idle_description: str = idle_description
        self.answered_description: str = answered_description
        self.ducked_description: str = ducked_description

        self.persist_asker: bool = persist_asker

        self.renamed_asker_role: discord.Role = self.bot.get_role(
            self.server, renamed_asker_role
        )

        self.log.info(f"Identified renamed asker role: {self.renamed_asker_role}")

        self.role_that_can_rename: discord.Role = self.bot.get_role(
            self.server, role_that_can_rename
        )

        self.log.info(f"Identified role that can rename: {self.role_that_can_rename}")

        self.ignored_role: discord.Role = self.bot.get_role(self.server, ignored_role)

        self.log.info(f"Identified ignored role: {self.ignored_role}")

        self.log_relocated_emoji: str = log_relocated_emoji
        self.log_renamed_emoji: str = log_renamed_emoji
        self.log_restored_emoji: str = log_restored_emoji
        self.log_resolved_emoji: str = log_resolved_emoji
        self.log_reminded_emoji: str = log_reminded_emoji
        self.log_ducked_emoji: str = log_ducked_emoji
        self.log_busied_from_hoisted_emoji: str = log_busied_from_hoisted_emoji
        self.log_busied_from_answered_emoji: str = log_busied_from_answered_emoji
        self.log_fake_out_emoji: str = log_fake_out_emoji

        self.log_relocated_color: str = self.bot.color_from_hex(log_relocated_color)
        self.log_renamed_color: str = self.bot.color_from_hex(log_renamed_color)
        self.log_restored_color: str = self.bot.color_from_hex(log_restored_color)
        self.log_resolved_color: str = self.bot.color_from_hex(log_resolved_color)
        self.log_reminded_color: str = self.bot.color_from_hex(log_reminded_color)
        self.log_ducked_color: str = self.bot.color_from_hex(log_ducked_color)
        self.log_busied_from_hoisted_color: str = self.bot.color_from_hex(
            log_busied_from_hoisted_color
        )
        self.log_busied_from_answered_color: str = self.bot.color_from_hex(
            log_busied_from_answered_color
        )
        self.log_fake_out_color: str = self.bot.color_from_hex(log_fake_out_color)

        self.resolve_with_reaction: bool = resolve_with_reaction

        self.prompt_message: str = "\n".join(prompt_message) if isinstance(
            prompt_message, list
        ) else prompt_message

        self.prompt_color: int = self.bot.color_from_hex(prompt_color)

        self.log_verbose_usernames: bool = log_verbose_usernames

        self.preemptive_cache_size: bool = preemptive_cache_size

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

        self.auto_poll: bool = auto_poll

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
        if self.is_channel_answered(channel):
            return self.answered_state
        if self.is_channel_ducked(channel):
            return self.ducked_state

    def is_channel(self, channel: discord.Channel, channel_state: ChannelState) -> bool:
        return channel_state.matches(channel)

    def is_channel_hoisted(self, channel: discord.Channel) -> bool:
        return self.is_channel(channel, self.hoisted_state)

    def is_channel_busy(self, channel: discord.Channel) -> bool:
        return self.is_channel(channel, self.busy_state) or self.is_channel_ducked(
            channel
        )

    def is_channel_idle(self, channel: discord.Channel) -> bool:
        return self.is_channel(channel, self.idle_state)

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

    async def get_oldest_answered_channel(self) -> discord.Channel:
        return await self.get_oldest_channel(self.answered_state)

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
        asker: discord.Member = None,
    ) -> str:
        description = state.format_description(channel, asker)
        if self.persist_asker and asker:
            return "\n".join((description, "", "Current asker:", asker.mention))
        else:
            return description

    def log_username(self, user: discord.User) -> str:
        if self.log_verbose_usernames:
            return f"{user.mention} ({user})"
        return user.mention

    async def get_asker(self, channel: discord.Channel) -> discord.Member:
        server: discord.Server = channel.server
        if channel.topic:
            topic_lines = str(channel.topic).splitlines()
            last_line = topic_lines[-1]
            mention_match = MENTION_PATTERN.match(last_line)
            if mention_match:
                (user_id,) = mention_match.groups()
                try:
                    member = server.get_member(user_id)
                    return member
                except Exception:
                    self.log.exception(f"Failed to identify asker in {channel}")

    async def set_asker(self, channel: discord.Channel, asker: discord.Member):
        state = self.get_channel_state(channel)
        new_topic = self.build_channel_description(channel, state, asker=asker)
        try:
            await self.bot.edit_channel(channel, topic=new_topic)
        except Exception:
            self.log.exception(f"Failed to name channel {channel} after asker: {asker}")

    async def delete_asker(self, channel: discord.Channel):
        old_asker = await self.get_asker(channel)
        if old_asker:
            state = self.get_channel_state(channel)
            description = state.format_description(channel)
            try:
                await self.bot.edit_channel(channel, topic=description or "")
            except Exception:
                self.log.exception(f"Failed to delete asker in {channel}")

    async def sync_channel_positions(self):
        # go in reverse in case the positions were reverted and will cause cascading
        for ch in reversed(self.channels):
            expected_position = (self.get_channel_index(ch) + 1) * 100
            if expected_position != ch.position:
                await self.bot.edit_channel(ch, position=expected_position)

    async def sync_idle_channels(self):
        for channel in self.channels:
            # only busy channels can become idle
            if self.is_channel_busy(channel):
                latest_message = await self.bot.get_latest_message(channel)
                # if there's no latest message, then... set it as answered?
                if not latest_message:
                    await self.set_channel_answered(channel)
                    continue
                now: datetime = datetime.utcnow()
                latest: datetime = latest_message.timestamp
                then: datetime = latest + self.delta_until_idle
                if now > then:
                    await self.set_channel_idle(channel)

    async def sync_hoisted_channels(self):
        # don't do anything unless we care about hoisted channels
        if self.max_hoisted_channels > 0:
            delta = self.max_hoisted_channels - self.num_hoisted_channels
            # recycle channels to top-off the hoisted ones
            if delta > 0:
                for i in range(delta):
                    if not await self.try_hoist_channel():
                        break

    async def sync_all(self):
        await self.sync_channel_positions()
        await self.sync_idle_channels()
        await self.sync_hoisted_channels()

    async def set_channel(
        self, channel: discord.Channel, state: ChannelState, asker: discord.User = None
    ):
        # if askers are enabled, and one was not provided, find it ourselves
        if self.persist_asker and not asker:
            asker = await self.get_asker(channel)
        # set the new channel name, which doubles as its persistent state
        channel_key = self.get_channel_key(channel)
        if asker and self.renamed_asker_role in asker.roles:
            new_name = state.format_name(key=channel_key, channel=channel)
        else:
            new_name = state.format_name(key=channel_key, channel=channel, asker=asker)
        # determine the new topic based on state
        new_topic = self.build_channel_description(channel, state, asker=asker)
        # update the channel-in-question's category (parent)
        await self.bot.edit_channel(
            channel, name=new_name, topic=new_topic, category=state.category
        )
        # always sync hoisted channels
        await self.sync_hoisted_channels()

    async def set_channel_hoisted(
        self, channel: discord.Channel, force: bool = False
    ) -> bool:
        # only idle channels and answered (not busy) channels can become hoisted
        # and only if we're under the max amount
        # ... unless we're forcing (e.g. with a command)
        if force or (
            (self.num_hoisted_channels < self.max_hoisted_channels)
            and (self.is_channel_answered(channel) or self.is_channel_idle(channel))
        ):
            if self.persist_asker:
                await self.delete_asker(channel)
            await self.set_channel(channel, self.hoisted_state)
            await self.send_prompt_message(channel)
            return True

    async def set_channel_busy(
        self, channel: discord.Channel, force: bool = False, asker: discord.User = None
    ) -> bool:
        # any channel that's not already busy can become busy
        if force or not self.is_channel_busy(channel):
            await self.set_channel(channel, self.busy_state, asker=asker)
            return True

    async def set_channel_idle(
        self, channel: discord.Channel, force: bool = False
    ) -> bool:
        # only busy channels can become idle
        if force or self.is_channel_busy(channel):
            await self.set_channel(channel, self.idle_state)
            return True

    async def set_channel_answered(
        self, channel: discord.Channel, force: bool = False
    ) -> bool:
        # only busy and idle (not hoisted) channels can become answered
        if force or self.is_channel_busy(channel) or self.is_channel_idle(channel):
            await self.set_channel(channel, self.answered_state)
            return True

    async def set_channel_ducked(
        self, channel: discord.Channel, force: bool = False
    ) -> bool:
        # any channel that's not already ducked can be ducked
        if force or not self.is_channel_ducked(channel):
            await self.set_channel(channel, self.ducked_state)
            return True

    async def reset_channel(self, channel: discord.Channel):
        state = self.get_channel_state(channel)
        await self.set_channel(channel, state)

    async def reset_all(self):
        for channel in self.channels:
            await self.reset_channel(channel)

    async def is_channel_prompted(self, channel: discord.Channel) -> bool:
        # check if the latest message is the hoisted message prompt
        # we do this by comparing the color of the embed strip
        # and, if that matches, the first few characters of text
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

    async def send_prompt_message(self, channel: discord.Channel):
        # send hoisted message, if any, in the newly-hoisted channel
        # ... but only if it's not already the most recent message
        # (this can happen if someone deletes their message)
        if self.prompt_message and not await self.is_channel_prompted(channel):
            em = discord.Embed(description=self.prompt_message, color=self.prompt_color)
            await self.bot.send_message(channel, embed=em)

    async def maybe_duck_channel(
        self, channel: discord.Channel, message: discord.Message
    ):
        author: discord.Member = message.author
        # if askers are enabled, then the asker must also be the ducker
        if self.persist_asker:
            asker = await self.get_asker(channel)
            if asker.id != author.id:
                return False
        # if askers are not enabled, then make sure to short-circuit ignored users
        elif self.ignored_role in author.roles:
            return False
        # the last 10 messages in the channel must all be from the ducker
        async for m in self.bot.iter_latest_messages(channels=[channel], limit=10):
            if author.id != m.author.id:
                return False
        # if we get here, we can duck the channel
        if await self.set_channel_ducked(channel):
            await self.log_to_channel(
                emoji=self.log_ducked_emoji,
                description=f"ducked {channel.mention}",
                message=message,
                color=self.log_ducked_color,
            )

    async def relocate(self, message: discord.Message, reactor: discord.Member):
        author: discord.Member = message.author
        from_channel: discord.Channel = message.channel
        # prefer relocating to hoisted channels over answered ones
        # in theory, the only way an answered channel would be chosen is if
        # hoisted channels are disabled altogether
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
            response = self.relocate_message_with_channel.format(
                author=author,
                reactor=reactor,
                from_channel=from_channel,
                to_channel=to_channel,
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

    async def remind(self, message: discord.Message, reactor: discord.Member):
        channel: discord.Channel = message.channel
        author: discord.Member = message.author
        # send the message
        await self.bot.send_message(
            channel,
            content=self.reminder_message.format(
                user=author,
                resolve_emoji=self.resolve_emoji,
                resolve_emoji_raw=f"`:{self.resolve_emoji.name}:`",
            ),
        )
        # create a log entry
        await self.log_to_channel(
            emoji=self.log_reminded_emoji,
            description=f"reminded {self.log_username(author)} in {channel.mention}",
            message=message,
            actor=reactor,
            color=self.log_reminded_color,
        )

    async def rename_asker(
        self, channel: discord.Channel, actor: discord.Member
    ) -> discord.Member:
        # 1. must have asker's enabled
        # 2. must have enabled renamed_asker_role and role_that_can_rename
        # 3. actor must have role_that_can_rename (permission)
        # 4. asker must be recorded and not have role_that_can_rename (immunity)
        if (
            self.persist_asker
            and self.renamed_asker_role
            and self.role_that_can_rename
            and self.role_that_can_rename in actor.roles
        ):
            asker = await self.get_asker(channel)
            if asker and self.role_that_can_rename not in asker.roles:
                await self.bot.add_roles(asker, self.renamed_asker_role)
                await self.reset_channel(channel)
                return asker

    async def restore_asker(
        self, channel: discord.Channel, actor: discord.Member
    ) -> discord.Member:
        if (
            self.persist_asker
            and self.renamed_asker_role
            and self.role_that_can_rename
            and self.role_that_can_rename in actor.roles
        ):
            asker = await self.get_asker(channel)
            if asker and self.renamed_asker_role in asker.roles:
                await self.bot.remove_roles(asker, self.renamed_asker_role)
                await self.reset_channel(channel)
                return asker

    async def try_hoist_channel(self):
        # if we've hit the max, don't hoist any more channels
        if self.num_hoisted_channels < self.max_hoisted_channels:
            # always try to get the oldest answered channel first
            channel_to_hoist = await self.get_oldest_answered_channel()
            # if there weren't any available, but we're under the min...
            if (not channel_to_hoist) and (
                self.num_hoisted_channels < self.min_hoisted_channels
            ):
                # ... then try to get an idle one instead
                channel_to_hoist = await self.get_oldest_idle_channel()
                # warn if we can't replenish min channels
                if not channel_to_hoist:
                    self.log.warning(
                        f"No channels available to replenish the minimum amount of {self.min_hoisted_channels}!"
                    )
            if channel_to_hoist:
                return await self.set_channel_hoisted(channel_to_hoist)

    async def on_ready(self):
        self.log.info("Readying state...")
        # add the latest x messages from every channel into the client cache
        # so that discord.py will care about any reactions applied to it
        # we use this for the resolved and reminder emoji actions
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
        # sync everything, immediately
        await self.sync_all()
        # let people know we're ready
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
        # relocate: only on the first of a reaction on a fresh human message
        if (
            reaction.emoji == self.relocate_emoji
            and reaction.count == 1
            and author != self.bot.user
        ):
            if self.ignored_role in reactor.roles:
                return
            await self.relocate(message, reactor)
            await self.bot.add_reaction(message, self.relocate_emoji)
        # rename: only on the first of a reaction on a fresh human message
        elif (
            reaction.emoji == self.rename_emoji
            and reaction.count == 1
            and author != self.bot.user
        ):
            if self.ignored_role in reactor.roles:
                return
            affected_asker = await self.rename_asker(channel, reactor)
            if affected_asker:
                await self.bot.add_reaction(message, self.rename_emoji)
                await self.log_to_channel(
                    emoji=self.log_renamed_emoji,
                    description=f"renamed {channel.mention} from {affected_asker.mention}",
                    message=message,
                    actor=reactor,
                    color=self.log_renamed_color,
                )
        # restore: only on the first of a reaction on a fresh human message
        elif (
            reaction.emoji == self.restore_emoji
            and reaction.count == 1
            and author != self.bot.user
        ):
            if self.ignored_role in reactor.roles:
                return
            affected_asker = await self.restore_asker(channel, reactor)
            if affected_asker:
                await self.bot.add_reaction(message, self.restore_emoji)
                await self.log_to_channel(
                    emoji=self.log_restored_emoji,
                    description=f"restored {channel.mention} to {affected_asker.mention}",
                    message=message,
                    actor=reactor,
                    color=self.log_restored_color,
                )
        # resolve: only when enabled and for the last message of a managed channel
        elif (
            reaction.emoji == self.resolve_emoji
            and self.resolve_with_reaction
            and channel in self.channels
            and await self.bot.is_latest_message(
                message, limit=self.preemptive_cache_size
            )
        ):
            # ignored users cannot resolve, unless it's their own channel
            if self.ignored_role in reactor.roles:
                # short-circuit if askers are not enabled
                if not self.persist_asker:
                    return
                # short-circuit if the reactor is not the asker
                asker = await self.get_asker(channel)
                if reactor.id != asker.id:
                    return
            if await self.set_channel_answered(channel):
                await self.bot.add_reaction(message, self.resolve_emoji)
                await self.log_to_channel(
                    emoji=self.log_resolved_emoji,
                    description=f"resolved {channel.mention}",
                    message=message,
                    actor=reactor,
                    color=self.log_resolved_color,
                )
        # remind: on the first reaction to any human message in a managed channel
        elif (
            reaction.emoji == self.remind_emoji
            and reaction.count == 1
            and author != self.bot.user
            and channel in self.channels
        ):
            if self.ignored_role in reactor.roles:
                return
            await self.remind(message, reactor)
            await self.bot.add_reaction(message, self.remind_emoji)

    async def on_message(self, message: discord.Message):
        channel: discord.Channel = message.channel
        author: discord.Member = message.author
        # only care about managed channels
        if channel in self.channels:
            # resolve: only when the message contains exactly the resolve emoji
            if message.content == str(self.resolve_emoji):
                # ignored users cannot resolve, unless it's their own channel
                if self.ignored_role in author.roles:
                    # short-circuit if askers are not enabled
                    if not self.persist_asker:
                        return
                    # short-circuit if the author is not the asker
                    asker = await self.get_asker(channel)
                    if author.id != asker.id:
                        return
                if await self.set_channel_answered(channel):
                    await self.log_to_channel(
                        emoji=self.log_resolved_emoji,
                        description=f"resolved {channel.mention}",
                        message=message,
                        color=self.log_resolved_color,
                    )
            # rename: only when the message contains exactly the rename emoji
            elif message.content == str(self.rename_emoji):
                if self.ignored_role in author.roles:
                    return
                affected_asker = await self.rename_asker(channel, author)
                if affected_asker:
                    await self.log_to_channel(
                        emoji=self.log_renamed_emoji,
                        description=f"renamed {channel.mention} from {affected_asker.mention}",
                        message=message,
                        color=self.log_renamed_color,
                    )
            # restore: only when the message contains exactly the restore emoji
            elif message.content == str(self.restore_emoji):
                if self.ignored_role in author.roles:
                    return
                affected_asker = await self.restore_asker(channel, author)
                if affected_asker:
                    await self.log_to_channel(
                        emoji=self.log_restored_emoji,
                        description=f"restored {channel.mention} to {affected_asker.mention}",
                        message=message,
                        color=self.log_restored_color,
                    )
            # quack
            elif message.content == str(self.ducked_emoji):
                await self.maybe_duck_channel(channel, message)
            # otherwise, mark it as busy
            else:
                # take a different action depending on current channel state
                prior_state: ChannelState = self.get_channel_state(channel)
                # if hoisted: update asker, change to busy, and log
                if prior_state == self.hoisted_state:
                    await self.set_channel_busy(channel, asker=author)
                    await self.log_to_channel(
                        emoji=self.log_busied_from_hoisted_emoji,
                        description=f"asked in {channel.mention}",
                        message=message,
                        color=self.log_busied_from_hoisted_color,
                    )
                # if answered: change to busy and log
                elif prior_state == self.answered_state:
                    await self.set_channel_busy(channel)
                    await self.log_to_channel(
                        emoji=self.log_busied_from_answered_emoji,
                        description=f"re-opened {channel.mention}",
                        message=message,
                        color=self.log_busied_from_answered_color,
                    )
                # otherwise (idle): just change to busy without logging
                else:
                    await self.set_channel_busy(channel)

    async def on_message_delete(self, message: discord.Message):
        channel: discord.Channel = message.channel
        author: discord.Member = message.author
        # only care about managed channels
        if channel in self.channels:
            # only care about busy/idle channels
            if self.is_channel_busy(channel) or self.is_channel_idle(channel):
                # do we need to remind the user to resolve the channel?
                # if the most recent message is now the prompy; probably yes
                if await self.is_channel_prompted(channel):
                    # ping the user with a message, if configured
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
                    # automatically set the channel as answered
                    await self.set_channel_answered(channel)
                    # create a log entry
                    await self.log_to_channel(
                        emoji=self.log_fake_out_emoji,
                        description=f"faked-out {channel.mention}",
                        message=sent_message,
                        actor=author,
                        color=self.log_fake_out_color,
                    )

    async def destroy(self) -> bool:
        return self.stop_polling_task()
