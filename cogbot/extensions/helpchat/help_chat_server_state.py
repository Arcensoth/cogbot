import asyncio
import collections
import logging
import random
import typing
from datetime import datetime, timedelta

import discord

from cogbot.cog_bot import ChannelId, CogBot
from cogbot.extensions.helpchat.channel_state import ChannelState

PROMPT_COLOR = "#00ACED"

RELOCATE_EMOJI = "➡️"
RENAME_EMOJI = "📛"
RESOLVE_EMOJI = "✅"
REMIND_EMOJI = "🎗️"

FREE_EMOJI = "✅"
BUSY_EMOJI = "💬"
IDLE_EMOJI = "⏰"
HOISTED_EMOJI = "👋"
DUCKED_EMOJI = "🦆"

LOG_RELOCATED_EMOJI = RELOCATE_EMOJI
LOG_RENAMED_EMOJI = RENAME_EMOJI
LOG_RESOLVED_EMOJI = RESOLVE_EMOJI
LOG_REMINDED_EMOJI = REMIND_EMOJI
LOG_DUCKED_EMOJI = DUCKED_EMOJI
LOG_BUSIED_FROM_HOISTED_EMOJI = HOISTED_EMOJI
LOG_BUSIED_FROM_FREE_EMOJI = "🙊"
LOG_FAKE_OUT_EMOJI = "🙈"

LOG_RELOCATED_COLOR = "#3B88C3"
LOG_RENAMED_COLOR = "#DD2E44"
LOG_RESOLVED_COLOR = "#77B255"
LOG_REMINDED_COLOR = "#9B59B6"
LOG_DUCKED_COLOR = "#C77538"
LOG_BUSIED_FROM_HOISTED_COLOR = "#FFDC5D"
LOG_BUSIED_FROM_FREE_COLOR = "#BF6952"
LOG_FAKE_OUT_COLOR = "#BF6952"


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
        channel_description: str = "",
        log_channel: str = None,
        seconds_until_idle: int = 1800,
        seconds_to_poll: int = 60,
        free_category: str = None,
        busy_category: str = None,
        idle_category: str = None,
        hoisted_category: str = None,
        min_hoisted_channels: int = 0,
        max_hoisted_channels: int = 0,
        relocate_emoji: str = RELOCATE_EMOJI,
        rename_emoji: str = RENAME_EMOJI,
        resolve_emoji: str = RESOLVE_EMOJI,
        remind_emoji: str = REMIND_EMOJI,
        free_emoji: str = FREE_EMOJI,
        busy_emoji: str = BUSY_EMOJI,
        idle_emoji: str = IDLE_EMOJI,
        hoisted_emoji: str = HOISTED_EMOJI,
        ducked_emoji: str = DUCKED_EMOJI,
        free_format: str = "free-chat-{key}",
        busy_format: str = "busy-chat-{key}",
        idle_format: str = "idle-chat-{key}",
        hoisted_format: str = "ask-here-{key}",
        ducked_format: str = "duck-chat-{key}",
        persist_asker: bool = False,
        renamed_asker_role: str = None,
        log_relocated_emoji: str = LOG_RELOCATED_EMOJI,
        log_rename_emoji: str = LOG_RENAMED_EMOJI,
        log_resolved_emoji: str = LOG_RESOLVED_EMOJI,
        log_reminded_emoji: str = LOG_REMINDED_EMOJI,
        log_ducked_emoji: str = LOG_DUCKED_EMOJI,
        log_busied_from_free_emoji: str = LOG_BUSIED_FROM_FREE_EMOJI,
        log_busied_from_hoisted_emoji: str = LOG_BUSIED_FROM_HOISTED_EMOJI,
        log_fake_out_emoji: str = LOG_FAKE_OUT_EMOJI,
        log_relocated_color: str = LOG_RELOCATED_COLOR,
        log_renamed_color: str = LOG_RENAMED_COLOR,
        log_resolved_color: str = LOG_RESOLVED_COLOR,
        log_reminded_color: str = LOG_REMINDED_COLOR,
        log_ducked_color: str = LOG_DUCKED_COLOR,
        log_busied_from_free_color: str = LOG_BUSIED_FROM_FREE_COLOR,
        log_busied_from_hoisted_color: str = LOG_BUSIED_FROM_HOISTED_COLOR,
        log_fake_out_color: str = LOG_FAKE_OUT_COLOR,
        resolve_with_reaction: bool = False,
        prompt_message: str = None,
        prompt_color: str = PROMPT_COLOR,
        log_verbose_usernames: bool = False,
        preemptive_cache_size: int = 10,
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
        self.channel_description: str = channel_description

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

        self.resolve_emoji: typing.Union[str, discord.Emoji] = self.bot.get_emoji(
            self.server, resolve_emoji
        )

        self.remind_emoji: typing.Union[str, discord.Emoji] = self.bot.get_emoji(
            self.server, remind_emoji
        )

        self.free_category: discord.Channel = self.bot.get_channel(
            free_category
        ) if free_category else None

        self.busy_category: discord.Channel = self.bot.get_channel(
            busy_category
        ) if busy_category else None

        self.idle_category: discord.Channel = self.bot.get_channel(
            idle_category
        ) if idle_category else None

        self.hoisted_category: discord.Channel = self.bot.get_channel(
            hoisted_category
        ) if hoisted_category else None

        self.log.info(f"Identified free category: {self.free_category}")
        self.log.info(f"Identified busy category: {self.busy_category}")
        self.log.info(f"Identified idle category: {self.idle_category}")
        self.log.info(f"Identified hoisted category: {self.hoisted_category}")

        self.free_emoji: str = free_emoji
        self.busy_emoji: str = busy_emoji
        self.idle_emoji: str = idle_emoji
        self.hoisted_emoji: str = hoisted_emoji
        self.ducked_emoji: str = ducked_emoji

        self.free_format: str = free_format
        self.busy_format: str = busy_format
        self.idle_format: str = idle_format
        self.hoisted_format: str = hoisted_format
        self.ducked_format: str = ducked_format

        self.persist_asker: bool = persist_asker

        self.renamed_asker_role: discord.Role = self.bot.get_role(
            self.server, renamed_asker_role
        )

        self.log.info(f"Identified renamed asker role: {self.renamed_asker_role}")

        self.log_relocated_emoji: str = log_relocated_emoji
        self.log_rename_emoji: str = log_rename_emoji
        self.log_resolved_emoji: str = log_resolved_emoji
        self.log_reminded_emoji: str = log_reminded_emoji
        self.log_ducked_emoji: str = log_ducked_emoji
        self.log_busied_from_free_emoji: str = log_busied_from_free_emoji
        self.log_busied_from_hoisted_emoji: str = log_busied_from_hoisted_emoji
        self.log_fake_out_emoji: str = log_fake_out_emoji

        self.log_relocated_color: str = self.bot.color_from_hex(log_relocated_color)
        self.log_renamed_color: str = self.bot.color_from_hex(log_renamed_color)
        self.log_resolved_color: str = self.bot.color_from_hex(log_resolved_color)
        self.log_reminded_color: str = self.bot.color_from_hex(log_reminded_color)
        self.log_ducked_color: str = self.bot.color_from_hex(log_ducked_color)
        self.log_busied_from_free_color: str = self.bot.color_from_hex(
            log_busied_from_free_color
        )
        self.log_busied_from_hoisted_color: str = self.bot.color_from_hex(
            log_busied_from_hoisted_color
        )
        self.log_fake_out_color: str = self.bot.color_from_hex(log_fake_out_color)

        self.resolve_with_reaction: bool = resolve_with_reaction

        self.prompt_message: str = "\n".join(prompt_message) if isinstance(
            prompt_message, list
        ) else prompt_message

        self.prompt_color: int = self.bot.color_from_hex(prompt_color)

        self.log_verbose_usernames: bool = log_verbose_usernames

        self.preemptive_cache_size: bool = preemptive_cache_size

        self.free_state: ChannelState = ChannelState(
            self.free_emoji, self.free_format, self.free_category
        )
        self.busy_state: ChannelState = ChannelState(
            self.busy_emoji, self.busy_format, self.busy_category
        )
        self.idle_state: ChannelState = ChannelState(
            self.idle_emoji, self.idle_format, self.idle_category
        )
        self.hoisted_state: ChannelState = ChannelState(
            self.hoisted_emoji, self.hoisted_format, self.hoisted_category
        )
        self.ducked_state: ChannelState = ChannelState(
            self.ducked_emoji, self.ducked_format, self.busy_category
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
        if self.is_channel_free(channel):
            return self.free_state
        if self.is_channel_busy(channel):
            return self.busy_state
        if self.is_channel_idle(channel):
            return self.idle_state
        if self.is_channel_hoisted(channel):
            return self.hoisted_state
        if self.is_channel_ducked(channel):
            return self.ducked_state

    def is_channel(self, channel: discord.Channel, channel_state: ChannelState) -> bool:
        return channel_state.matches(channel)

    def is_channel_free(self, channel: discord.Channel) -> bool:
        return self.is_channel(channel, self.free_state)

    def is_channel_busy(self, channel: discord.Channel) -> bool:
        return self.is_channel(channel, self.busy_state) or self.is_channel_ducked(
            channel
        )

    def is_channel_idle(self, channel: discord.Channel) -> bool:
        return self.is_channel(channel, self.idle_state)

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

    def get_idle_channels(self) -> discord.Channel:
        return self.get_channels(self.idle_state)

    def get_hoisted_channels(self) -> discord.Channel:
        return self.get_channels(self.hoisted_state)

    def get_random_channel(self, state: ChannelState) -> discord.Channel:
        channels = list(self.get_channels(state))
        if channels:
            random.shuffle(channels)
            return channels[0]

    def get_random_free_channel(self) -> discord.Channel:
        return self.get_random_channel(self.free_state)

    def get_random_busy_channel(self) -> discord.Channel:
        return self.get_random_channel(self.busy_state)

    def get_random_idle_channel(self) -> discord.Channel:
        return self.get_random_channel(self.idle_state)

    def get_random_hoisted_channel(self) -> discord.Channel:
        return self.get_random_channel(self.hoisted_state)

    async def get_oldest_channel(self, state: ChannelState) -> discord.Channel:
        channels: typing.List[discord.Channel] = list(self.get_channels(state))
        latest_messages = await self.bot.get_latest_messages(channels)
        if latest_messages:
            latest_messages.sort(key=lambda message: message.timestamp)
            oldest_channel = latest_messages[0].channel
            return oldest_channel

    async def get_oldest_free_channel(self) -> discord.Channel:
        return await self.get_oldest_channel(self.free_state)

    async def get_oldest_busy_channel(self) -> discord.Channel:
        return await self.get_oldest_channel(self.busy_state)

    async def get_oldest_idle_channel(self) -> discord.Channel:
        return await self.get_oldest_channel(self.idle_state)

    async def get_oldest_hoisted_channel(self) -> discord.Channel:
        return await self.get_oldest_channel(self.hoisted_state)

    def get_channel_key(self, channel: discord.Channel) -> str:
        channel_entry: HelpChatChannelEntry = self.channel_map.get(channel)
        if channel_entry:
            return channel_entry.key

    def get_channel_index(self, channel: discord.Channel) -> str:
        channel_entry: HelpChatChannelEntry = self.channel_map.get(channel)
        if channel_entry:
            return channel_entry.index

    def log_username(self, user: discord.User) -> str:
        if self.log_verbose_usernames:
            return f"{user.mention} ({user})"
        return user.mention

    async def get_asker(self, channel: discord.Channel) -> discord.Member:
        if channel.topic:
            topic_lines = str(channel.topic).splitlines()
            last_line = topic_lines[-1]
            try:
                member = channel.server.get_member(last_line)
                return member
            except:
                pass

    async def set_asker(self, channel: discord.Channel, asker: discord.Member):
        new_lines = self.channel_description.split("\n")
        new_lines.append(str(asker.id))
        new_topic = "\n".join(new_lines)
        try:
            await self.bot.edit_channel(channel, topic=new_topic)
        except Exception:
            self.log.exception(f"Failed to name channel after asker: {asker}")

    async def delete_asker(self, channel: discord.Channel):
        old_asker = await self.get_asker(channel)
        if old_asker:
            try:
                await self.bot.edit_channel(channel, topic=self.channel_description)
            except Exception:
                self.log.exception(f"Failed to delete asker in channel: {channel}")

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
                # if there's no latest message, then... free it up?
                if not latest_message:
                    await self.set_channel_free(channel)
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
        # if no asker was provided, and we care, look it up ourselves
        if self.persist_asker and not asker:
            asker = await self.get_asker(channel)
        # set the new channel name, which doubles as its persistent state
        # also move it to the new category, if supplied
        # use the asker, if available, unless they're being ignored
        channel_key = self.get_channel_key(channel)
        if asker and self.renamed_asker_role in asker.roles:
            new_name = state.format(key=channel_key)
        else:
            new_name = state.format(key=channel_key, asker=asker)
        # update the channel-in-question's category (parent)
        await self.bot.edit_channel(channel, name=new_name, category=state.category)
        # always sync hoisted channels
        await self.sync_hoisted_channels()

    async def set_channel_free(
        self, channel: discord.Channel, force: bool = False
    ) -> bool:
        # only busy and idle (not hoisted) channels can become free
        if force or self.is_channel_busy(channel) or self.is_channel_idle(channel):
            await self.set_channel(channel, self.free_state)
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

    async def set_channel_hoisted(
        self, channel: discord.Channel, force: bool = False
    ) -> bool:
        # only free and idle channels (not busy) can become hoisted
        # and only if we're under the max amount
        # ... unless we're forcing (e.g. with a command)
        if force or (
            (self.num_hoisted_channels < self.max_hoisted_channels)
            and (self.is_channel_free(channel) or self.is_channel_idle(channel))
        ):
            if self.persist_asker:
                await self.delete_asker(channel)
            await self.set_channel(channel, self.hoisted_state)
            await self.send_prompt_message(channel)
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
            if (
                em_color == self.prompt_color
                and em_description
                and em_description[:20] == self.prompt_message[:20]
            ):
                return True

    async def send_prompt_message(self, channel: discord.Channel):
        # send hoisted message, if any, in the newly-hoisted channel
        # ... but only if it's not already the most recent message
        # (this can happen if someone deletes their message)
        if self.prompt_message and not await self.is_channel_prompted(channel):
            em = discord.Embed(description=self.prompt_message, color=self.prompt_color)
            await self.bot.send_message(channel, embed=em)

    async def relocate(self, message: discord.Message, reactor: discord.Member):
        author: discord.Member = message.author
        from_channel: discord.Channel = message.channel
        # prefer relocating to hoisted channels over free ones
        # in theory, the only way a free channel would be chosen is if hoisted
        # channels are disabled altogether
        to_channel = self.get_random_hoisted_channel() or self.get_random_free_channel()
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

    async def flag_renamed_asker(self, channel: discord.Channel) -> bool:
        if self.persist_asker:
            asker = await self.get_asker(channel)
            if self.renamed_asker_role:
                await self.bot.add_roles(asker, self.renamed_asker_role)
            await self.reset_channel(channel)
            return True

    async def try_hoist_channel(self):
        # if we've hit the max, don't hoist any more channels
        if self.num_hoisted_channels < self.max_hoisted_channels:
            # always try to get the oldest free channel first
            channel_to_hoist = await self.get_oldest_free_channel()
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
            await self.relocate(message, reactor)
            await self.bot.add_reaction(message, self.relocate_emoji)
        # rename: only on the first of a reaction on a fresh human message
        elif (
            reaction.emoji == self.rename_emoji
            and reaction.count == 1
            and author != self.bot.user
        ):
            if await self.flag_renamed_asker(channel):
                await self.bot.add_reaction(message, self.rename_emoji)
                await self.log_to_channel(
                    emoji=self.log_rename_emoji,
                    description=f"renamed {channel.mention}",
                    message=message,
                    color=self.log_renamed_color,
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
            if await self.set_channel_free(channel):
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
            await self.remind(message, reactor)
            await self.bot.add_reaction(message, self.remind_emoji)

    async def on_message(self, message: discord.Message):
        channel: discord.Channel = message.channel
        author: discord.Member = message.author
        # only care about managed channels
        if channel in self.channels:
            # resolve: only when the message contains exactly the resolve emoji
            if message.content == str(self.resolve_emoji):
                if await self.set_channel_free(channel):
                    await self.log_to_channel(
                        emoji=self.log_resolved_emoji,
                        description=f"resolved {channel.mention}",
                        message=message,
                        color=self.log_resolved_color,
                    )
            # rename: only when the message contains exactly the rename emoji
            elif message.content == str(self.rename_emoji):
                if await self.flag_renamed_asker(channel):
                    await self.log_to_channel(
                        emoji=self.log_rename_emoji,
                        description=f"renamed {channel.mention}",
                        message=message,
                        color=self.log_renamed_color,
                    )
            # quack
            elif message.content == str(self.ducked_emoji):
                if await self.set_channel_ducked(channel):
                    await self.log_to_channel(
                        emoji=self.log_ducked_emoji,
                        description=f"ducked {channel.mention}",
                        message=message,
                        color=self.log_ducked_color,
                    )
            # otherwise, mark it as busy
            else:
                # take a different action depending on current channel state
                prior_state: ChannelState = self.get_channel_state(channel)
                # if hoisted: update asker, change to busy, and log
                if prior_state == self.hoisted_state:
                    if self.persist_asker:
                        await self.set_asker(channel, author)
                    await self.set_channel_busy(channel, asker=author)
                    await self.log_to_channel(
                        emoji=self.log_busied_from_hoisted_emoji,
                        description=f"asked in {channel.mention}",
                        message=message,
                        color=self.log_busied_from_hoisted_color,
                    )
                # if free: change to busy and log
                elif prior_state == self.free_state:
                    await self.set_channel_busy(channel)
                    await self.log_to_channel(
                        emoji=self.log_busied_from_free_emoji,
                        description=f"re-opened {channel.mention}",
                        message=message,
                        color=self.log_busied_from_free_color,
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
                    # free-up the channel automatically
                    await self.set_channel_free(channel)
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
