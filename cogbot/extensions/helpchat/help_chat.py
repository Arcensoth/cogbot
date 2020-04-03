import asyncio
import logging
import re
import typing

import discord
from discord.ext import commands
from discord.ext.commands import Context

from cogbot import checks
from cogbot.cog_bot import CogBot, ServerId
from cogbot.extensions.helpchat.help_chat_server_state import HelpChatServerState

log = logging.getLogger(__name__)


class HelpChat:
    def __init__(self, bot: CogBot, ext: str):
        self.bot: CogBot = bot
        self.server_state: typing.Dict[ServerId, HelpChatServerState] = {}
        self.options = self.bot.state.get_extension_state(ext)
        self.server_options: typing.Dict[ServerId, typing.Any] = {}
        self.ext = ext
        self.readied = False

    def get_state(self, server: discord.Server) -> HelpChatServerState:
        return self.server_state.get(server.id)

    async def on_ready(self):
        # because on_ready can be called more than once
        # and because disconnection might invalidate the client cache
        # (including all existing in-memory objects)
        if self.readied:
            log.warning(
                "Hook on_ready() was called again; re-creating state objects..."
            )
            for old_state in self.server_state.values():
                old_state.log.info(f"Destroying old state object...")
                if await old_state.destroy():
                    old_state.log.info(f"Successfully destroyed old state object.")
                else:
                    old_state.log.error(
                        f"Failed to destroy old state object: {old_state}"
                    )
        else:
            log.info(f"Identifying servers and their channels for the first time...")
            self.readied = True
        # construct server state objects for easier context management
        for server_key, server_options in self.options.get("servers", {}).items():
            server = self.bot.get_server_from_key(server_key)
            if not server:
                log.error(f"Skipping unknown server {server_key}.")
                continue
            self.server_options[server.id] = server_options
            if isinstance(server_options, str):
                await self.init_external_server_state(
                    server, server_key, server_options
                )
            else:
                await self.init_server_state(server, server_options)

    async def init_external_server_state(
        self, server: discord.Server, server_key: str, state_address: str
    ):
        try:
            log.info(
                f"Loading state data for server {server_key} from: {state_address}"
            )
            server_options = await self.bot.load_json(state_address)
            log.info(f"Successfully loaded state data for server {server_key}.")
        except:
            log.exception(
                f"Failed to load state data for server {server_key}. Skipping..."
            )
            return
        await self.init_server_state(server, server_options)

    async def init_server_state(self, server: discord.Server, server_options: dict):
        state = HelpChatServerState(self.ext, self.bot, server, **server_options)
        self.server_state[server.id] = state
        await state.on_ready()

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

    async def on_message_delete(self, message: discord.Message):
        # make sure this isn't a DM
        if message.server:
            state = self.get_state(message.server)
            # ignore bot's messages
            if state and message.author != self.bot.user:
                await state.on_message_delete(message)

    @checks.is_staff()
    @commands.group(pass_context=True, name="helpchat", aliases=["hc"], hidden=True)
    async def cmd_helpchat(self, ctx: Context):
        if ctx.invoked_subcommand is None:
            await self.bot.react_question(ctx)

    @checks.is_staff()
    @cmd_helpchat.command(pass_context=True, name="asker")
    async def cmd_helpchat_asker(self, ctx: Context):
        channel: discord.Channel = ctx.message.channel
        state = self.get_state(channel.server)
        asker = await state.get_asker(channel)
        if asker:
            em = discord.Embed(description=f"{asker.mention}")
            await self.bot.send_message(channel, embed=em)
        else:
            await self.bot.react_neutral(ctx)

    @checks.is_staff()
    @cmd_helpchat.command(pass_context=True, name="prompt")
    async def cmd_helpchat_prompt(self, ctx: Context):
        channel: discord.Channel = ctx.message.channel
        state = self.get_state(channel.server)
        await state.send_prompt_message(channel)

    @checks.is_staff()
    @cmd_helpchat.command(pass_context=True, name="reload")
    async def cmd_helpchat_reload(self, ctx: Context):
        channel: discord.Channel = ctx.message.channel
        server: discord.Server = channel.server
        # remember the old state object
        old_state = self.get_state(channel.server)
        # let the user know things are happening
        old_state.log.info(f"Attempting to reload state...")
        await self.bot.add_reaction(ctx.message, "🤖")
        # check if we're even using an external state
        state_address = self.server_options.get(server.id, None)
        if not isinstance(state_address, str):
            old_state.log.warning(f"Attempted to reload non-external state.")
            await self.bot.react_denied(ctx)
            return
        # load server options from the state address
        server_options = None
        old_state.log.info(f"Loading state data from: {state_address}")
        try:
            server_options = await self.bot.load_json(state_address)
            old_state.log.info(f"Successfully loaded state data.")
            await self.bot.add_reaction(ctx.message, "👌")
        except:
            old_state.log.exception(f"Failed to load state data.")
            await self.bot.react_failure(ctx)
            return
        # create and set the new state object
        old_state.log.info(f"Creating new state object...")
        try:
            new_state = HelpChatServerState(
                self.ext, self.bot, server, **server_options
            )
            self.server_state[server.id] = new_state
            await new_state.on_ready()
            old_state.log.info(f"Successfully created new state object.")
            await self.bot.add_reaction(ctx.message, "👍")
        except:
            old_state.log.exception(f"Failed to create new state object.")
            await self.bot.react_failure(ctx)
            return
        # destroy the old state object
        old_state.log.info(f"Destroying old state object...")
        if await old_state.destroy():
            old_state.log.info(f"Successfully destroyed old state object.")
            await self.bot.add_reaction(ctx.message, "😄")
        else:
            old_state.log.error(f"Failed to destroy old state object: {old_state}")
            await self.bot.add_reaction(ctx.message, "😬")

    @checks.is_staff()
    @cmd_helpchat.group(pass_context=True, name="channels")
    async def cmd_helpchat_channels(self, ctx: Context):
        if ctx.invoked_subcommand is None:
            await self.bot.react_question(ctx)

    @checks.is_staff()
    @cmd_helpchat_channels.command(pass_context=True, name="list")
    async def cmd_helpchat_channels_list(self, ctx: Context):
        channel: discord.Channel = ctx.message.channel
        state = self.get_state(channel.server)
        pad_key = 8
        pad_index = 8
        pad_position = 8
        pad_name = 24
        header_cells = [
            "Key".ljust(pad_key),
            "Index".ljust(pad_index),
            "Position".ljust(pad_position),
            "Name".ljust(pad_name),
        ]
        border_cells = [
            "-" * pad_key,
            "-" * pad_index,
            "-" * pad_position,
            "-" * pad_name,
        ]
        if state.persist_asker:
            asker_header = "Asker"
            header_cells.append(asker_header)
            border_cells.append("-" * len(asker_header))
        lines = [" | ".join(header_cells), " | ".join(border_cells)]
        channels_by_position = list(state.channels)
        channels_by_position.sort(key=lambda c: c.position)
        for ch in channels_by_position:
            ch_name = ch.name
            ch_position = ch.position
            ch_key = state.get_channel_key(ch)
            ch_index = state.get_channel_index(ch)
            ch_asker = await state.get_asker(ch)
            ch_cells = [
                str(ch_key).ljust(pad_key),
                str(ch_index).ljust(pad_index),
                str(ch_position).ljust(pad_position),
                str(ch_name).ljust(pad_name),
            ]
            if state.persist_asker:
                ch_cells.append(f"{ch_asker} <{ch_asker.id}>" if ch_asker else "")
            lines.append(" | ".join(ch_cells))
        message = "\n".join(("```", *lines, "```"))
        await self.bot.send_message(channel, message)

    @checks.is_staff()
    @cmd_helpchat_channels.command(pass_context=True, name="check")
    async def cmd_helpchat_channels_check(self, ctx: Context):
        channel: discord.Channel = ctx.message.channel
        await self.bot.add_reaction(ctx.message, "🤖")
        state = self.get_state(channel.server)
        lines = []
        for cached_ch in state.channels:
            actual_ch: discord.Channel = self.bot.get_channel(cached_ch.id)
            # pointing to the same object
            if cached_ch is actual_ch:
                lines.append(f"👌 {cached_ch.name}")
            # different object, same name
            elif cached_ch.name == actual_ch.name:
                lines.append(f"🤔 {cached_ch.name}")
            # different name
            else:
                lines.append(f"🤢 {cached_ch.name} is not {actual_ch.name}")
        message = "\n".join(("```", *lines, "```"))
        await self.bot.send_message(channel, message)

    @checks.is_staff()
    @cmd_helpchat.group(pass_context=True, name="poll")
    async def cmd_helpchat_poll(self, ctx: Context):
        if ctx.invoked_subcommand is None:
            await self.bot.react_question(ctx)

    @checks.is_staff()
    @cmd_helpchat_poll.command(pass_context=True, name="status")
    async def cmd_helpchat_poll_status(self, ctx: Context):
        channel: discord.Channel = ctx.message.channel
        state = self.get_state(channel.server)
        if state.auto_poll:
            task = state.polling_task
            if task:
                pad = 12
                lines = [
                    "_coro:".ljust(pad) + str(getattr(task, "_coro", None)),
                    "_state:".ljust(pad) + str(getattr(task, "_state", None)),
                    "done:".ljust(pad) + str(task.done()),
                    "cancelled:".ljust(pad) + str(task.cancelled()),
                ]
                if task.done():
                    lines.append("exception:".ljust(pad) + str(task.exception()))
                if task.done() and not task.exception():
                    lines.append("result:".ljust(pad) + str(task.result()))
                message = "\n".join(("```", *lines, "```"))
                await self.bot.send_message(channel, message)
            else:
                message = "Polling task is dead! You might want to restart it."
                await self.bot.send_message(channel, message)
        else:
            message = "Auto-polling is disabled on this server."
            await self.bot.send_message(channel, message)

    @checks.is_staff()
    @cmd_helpchat_poll.command(pass_context=True, name="start")
    async def cmd_helpchat_poll_start(self, ctx: Context):
        channel: discord.Channel = ctx.message.channel
        state = self.get_state(channel.server)
        if state.start_polling_task():
            await self.bot.react_success(ctx)
        else:
            await self.bot.react_neutral(ctx)

    @checks.is_staff()
    @cmd_helpchat_poll.command(pass_context=True, name="stop")
    async def cmd_helpchat_poll_stop(self, ctx: Context):
        channel: discord.Channel = ctx.message.channel
        state = self.get_state(channel.server)
        if state.stop_polling_task():
            await self.bot.react_success(ctx)
        else:
            await self.bot.react_neutral(ctx)

    @checks.is_staff()
    @cmd_helpchat_poll.command(pass_context=True, name="now")
    async def cmd_helpchat_poll_now(self, ctx: Context):
        channel: discord.Channel = ctx.message.channel
        state = self.get_state(channel.server)
        await state.poll_channels()
        await self.bot.react_success(ctx)

    @checks.is_staff()
    @cmd_helpchat.command(pass_context=True, name="hoist")
    async def cmd_helpchat_hoist(self, ctx: Context):
        channel: discord.Channel = ctx.message.channel
        state = self.get_state(channel.server)
        await state.sync_hoisted_channels()
        await self.bot.react_success(ctx)

    @checks.is_staff()
    @cmd_helpchat.group(pass_context=True, name="set")
    async def cmd_helpchat_set(self, ctx: Context):
        if ctx.invoked_subcommand is None:
            await self.bot.react_question(ctx)

    @checks.is_staff()
    @cmd_helpchat_set.command(pass_context=True, name="free")
    async def cmd_helpchat_set_free(self, ctx: Context):
        channel: discord.Channel = ctx.message.channel
        state = self.get_state(channel.server)
        if channel in state.channels:
            await asyncio.sleep(1)
            await state.set_channel(channel, state.free_state, state.free_category)
            await self.bot.react_success(ctx)

    @checks.is_staff()
    @cmd_helpchat_set.command(pass_context=True, name="busy")
    async def cmd_helpchat_set_busy(self, ctx: Context):
        channel: discord.Channel = ctx.message.channel
        state = self.get_state(channel.server)
        if channel in state.channels:
            await asyncio.sleep(1)
            await state.set_channel(channel, state.busy_state, state.busy_category)
            await self.bot.react_success(ctx)

    @checks.is_staff()
    @cmd_helpchat_set.command(pass_context=True, name="idle")
    async def cmd_helpchat_set_idle(self, ctx: Context):
        channel: discord.Channel = ctx.message.channel
        state = self.get_state(channel.server)
        if channel in state.channels:
            await asyncio.sleep(1)
            await state.set_channel(channel, state.idle_state, state.idle_category)
            await self.bot.react_success(ctx)

    @checks.is_staff()
    @cmd_helpchat_set.command(pass_context=True, name="hoisted")
    async def cmd_helpchat_set_hoisted(self, ctx: Context):
        channel: discord.Channel = ctx.message.channel
        state = self.get_state(channel.server)
        if channel in state.channels:
            await asyncio.sleep(1)
            await state.set_channel(
                channel, state.hoisted_state, state.hoisted_category
            )
            await self.bot.react_success(ctx)
