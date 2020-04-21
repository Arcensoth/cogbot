import asyncio
import logging
import re
import typing

import discord
from discord.ext import commands
from discord.ext.commands import Context

from cogbot import checks
from cogbot.cog_bot import CogBot, ServerId
from cogbot.extensions.helpchat.channel_state import ChannelState
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

    def set_state(self, server: discord.Server, state: HelpChatServerState):
        self.server_state[server.id] = state

    def remove_state(self, server: discord.Server):
        del self.server_state[server.id]

    async def create_state(
        self, server: discord.Server, server_options: dict
    ) -> HelpChatServerState:
        state = HelpChatServerState(self.ext, self.bot, server, **server_options)
        self.set_state(server, state)
        await state.on_ready()
        return state

    async def setup_state(self, server: discord.Server) -> HelpChatServerState:
        server_options = self.server_options[server.id]
        # if options is just a string, use remote/external location
        if isinstance(server_options, str):
            state_address = server_options
            try:
                log.info(
                    f"Loading state data for server {server} from: {state_address}"
                )
                actual_server_options = await self.bot.load_json(state_address)
                log.info(f"Successfully loaded state data for server {server}.")
            except:
                log.exception(
                    f"Failed to load state data for server {server}. Skipping..."
                )
                return
            state = await self.create_state(server, actual_server_options)
        # otherwise, use embedded/local config
        else:
            state = await self.create_state(server, server_options)
        return state

    async def reload_state(self, server: discord.Server, ctx: Context = None):
        # remember and remove the old state object
        old_state = self.get_state(server)
        self.remove_state(server)
        # let people know things are happening
        if ctx:
            old_state.log.info(f"{ctx.message.author} initiated a reload.")
            await old_state.log_to_channel(
                emoji="🔄",
                description=f"initiated a reload. Stand by...",
                message=ctx.message,
                actor=ctx.message.author,
                color=discord.Color.blue(),
            )
            await self.bot.add_reaction(ctx.message, "🤖")
        else:
            old_state.log.info(f"Initiated an automatic reload.")
            await old_state.log_to_channel(
                emoji="🔄",
                description="Initiated an automatic reload. Stand by...",
                color=discord.Color.blue(),
            )
        # create and set the new state object
        old_state.log.info(f"Creating new state object...")
        new_state = None
        try:
            new_state = await self.setup_state(server)
            new_state.log.info(f"Successfully created new state object: {new_state}")
            if ctx:
                await self.bot.add_reaction(ctx.message, "👍")
        except:
            old_state.log.exception(f"Failed to create new state object.")
            await old_state.log_to_channel(
                emoji="🔥",
                description="Reload FAILED! Uh oh!",
                color=discord.Color.red(),
            )
            if ctx:
                await self.bot.add_reaction(ctx.message, "🔥")
            return
        # destroy the old state object
        new_state.log.info(f"Destroying old state object: {old_state}")
        if await old_state.destroy():
            new_state.log.info(f"Successfully destroyed old state object.")
            if ctx:
                await self.bot.add_reaction(ctx.message, "😄")
        else:
            new_state.log.error(f"Failed to destroy old state object.")
            if ctx:
                await self.bot.add_reaction(ctx.message, "😬")
        # let the user know we're done
        if ctx:
            await self.bot.add_reaction(ctx.message, "👌")

    async def set_channel(
        self, ctx: Context, channel: discord.Channel, method: typing.Callable
    ):
        channel: discord.Channel = channel or ctx.message.channel
        state = self.get_state(channel.server)
        if channel in state.channels:
            if channel == ctx.message.channel:
                await self.bot.add_reaction(ctx.message, "🕛")
                await asyncio.sleep(2)
            await method(channel, force=True)
            await self.bot.react_success(ctx)
        else:
            await self.bot.react_neutral(ctx)

    async def on_ready(self):
        # because on_ready can be called more than once
        # and because disconnection might invalidate the client cache
        # (including all existing in-memory objects)
        if self.readied:
            log.warning(
                "Hook on_ready() was called again; previous state objects will be recreated..."
            )
        else:
            self.readied = True
            log.info(f"Identifying servers and their channels for the first time...")
        # construct server state objects for easier context management
        for server_key, server_options in self.options.get("servers", {}).items():
            server = self.bot.get_server_from_key(server_key)
            if not server:
                log.error(f"Skipping unknown server {server_key}.")
                continue
            self.server_options[server.id] = server_options
            # if previous state exists, reload it
            if self.get_state(server):
                await self.bot.mod_log(
                    content=f"Reconnect detected. Reloading help-chats...",
                    icon=":zap:",
                    color=discord.Color.orange(),
                    show_timestamp=False,
                    server=server,
                )
                await self.reload_state(server)
            # otherwise, just setup a new state
            else:
                await self.bot.mod_log(
                    content=f"Boot-up detected. Initializing help-chats...",
                    icon=":bulb:",
                    color=discord.Color.orange(),
                    show_timestamp=False,
                    server=server,
                )
                await self.setup_state(server)

    async def get_channels_check_message(self, state: HelpChatServerState) -> str:
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
        return message

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
    @cmd_helpchat.command(pass_context=True, name="onready")
    async def cmd_helpchat_onready(self, ctx: Context):
        await self.on_ready()

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
    @cmd_helpchat.command(pass_context=True, name="sync")
    async def cmd_helpchat_sync(self, ctx: Context):
        channel: discord.Channel = ctx.message.channel
        state = self.get_state(channel.server)
        await state.sync_all()
        await self.bot.react_success(ctx)

    @checks.is_staff()
    @cmd_helpchat.command(pass_context=True, name="reload")
    async def cmd_helpchat_reload(self, ctx: Context):
        channel: discord.Channel = ctx.message.channel
        server: discord.Server = channel.server
        await self.reload_state(server, ctx)

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
        message = await self.get_channels_check_message(state)
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
        await state.poll()
        await self.bot.react_success(ctx)

    @checks.is_staff()
    @cmd_helpchat.group(pass_context=True, name="set")
    async def cmd_helpchat_set(self, ctx: Context):
        if ctx.invoked_subcommand is None:
            await self.bot.react_question(ctx)

    @checks.is_staff()
    @cmd_helpchat_set.command(pass_context=True, name="free", aliases=["resolved"])
    async def cmd_helpchat_set_free(
        self, ctx: Context, channel: discord.Channel = None
    ):
        state = self.get_state(ctx.message.server)
        await self.set_channel(ctx, channel, state.set_channel_free)

    @checks.is_staff()
    @cmd_helpchat_set.command(pass_context=True, name="busy")
    async def cmd_helpchat_set_busy(
        self, ctx: Context, channel: discord.Channel = None
    ):
        state = self.get_state(ctx.message.server)
        await self.set_channel(ctx, channel, state.set_channel_busy)

    @checks.is_staff()
    @cmd_helpchat_set.command(pass_context=True, name="idle")
    async def cmd_helpchat_set_idle(
        self, ctx: Context, channel: discord.Channel = None
    ):
        state = self.get_state(ctx.message.server)
        await self.set_channel(ctx, channel, state.set_channel_idle)

    @checks.is_staff()
    @cmd_helpchat_set.command(pass_context=True, name="hoisted", aliases=["ask-here"])
    async def cmd_helpchat_set_hoisted(
        self, ctx: Context, channel: discord.Channel = None
    ):
        state = self.get_state(ctx.message.server)
        await self.set_channel(ctx, channel, state.set_channel_hoisted)
