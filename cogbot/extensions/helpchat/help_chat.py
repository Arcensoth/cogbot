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
        # only ready once
        if not self.readied:
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
        await state.on_ready()
        self.server_state[server.id] = state

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

    @checks.is_manager()
    @commands.group(pass_context=True, name="helpchat", aliases=["hc"], hidden=True)
    async def cmd_helpchat(self, ctx: Context):
        if ctx.invoked_subcommand is None:
            await self.bot.react_question(ctx)

    @checks.is_manager()
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
            await new_state.on_ready()
            self.server_state[server.id] = new_state
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

    @checks.is_manager()
    @cmd_helpchat.command(pass_context=True, name="channels")
    async def cmd_helpchat_channels(self, ctx: Context):
        channel: discord.Channel = ctx.message.channel
        state = self.get_state(channel.server)
        pad_name = 24
        pad_position = 8
        pad_key = 8
        lines = [
            " | ".join(
                [
                    "name".ljust(pad_name),
                    "position".ljust(pad_position),
                    "hc-key".ljust(pad_key),
                    "hc-index",
                ]
            ),
            " | ".join(
                [
                    "-" * pad_name,
                    "-" * pad_position,
                    "-" * pad_key,
                    "-" * len("hc-index"),
                ]
            ),
        ]
        channels_by_position = list(state.channels)
        channels_by_position.sort(key=lambda c: c.position)
        for ch in channels_by_position:
            ch_name = ch.name
            ch_position = ch.position
            ch_key = state.get_channel_key(ch)
            ch_index = state.get_channel_index(ch)
            lines.append(
                " | ".join(
                    [
                        str(ch_name).ljust(pad_name),
                        str(ch_position).ljust(pad_position),
                        str(ch_key).ljust(pad_key),
                        str(ch_index),
                    ]
                )
            )
        message = "\n".join(("```", *lines, "```"))
        await self.bot.send_message(channel, message)

    @checks.is_manager()
    @cmd_helpchat.group(pass_context=True, name="poll")
    async def cmd_helpchat_poll(self, ctx: Context):
        if ctx.invoked_subcommand is None:
            await self.bot.react_question(ctx)

    @checks.is_manager()
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

    @checks.is_manager()
    @cmd_helpchat_poll.command(pass_context=True, name="start")
    async def cmd_helpchat_poll_start(self, ctx: Context):
        channel: discord.Channel = ctx.message.channel
        state = self.get_state(channel.server)
        if state.start_polling_task():
            await self.bot.react_success(ctx)
        else:
            await self.bot.react_neutral(ctx)

    @checks.is_manager()
    @cmd_helpchat_poll.command(pass_context=True, name="stop")
    async def cmd_helpchat_poll_stop(self, ctx: Context):
        channel: discord.Channel = ctx.message.channel
        state = self.get_state(channel.server)
        if state.stop_polling_task():
            await self.bot.react_success(ctx)
        else:
            await self.bot.react_neutral(ctx)

    @checks.is_manager()
    @cmd_helpchat_poll.command(pass_context=True, name="now")
    async def cmd_helpchat_poll_now(self, ctx: Context):
        channel: discord.Channel = ctx.message.channel
        state = self.get_state(channel.server)
        await state.poll_channels()
        await self.bot.react_success(ctx)

    @checks.is_manager()
    @cmd_helpchat.command(pass_context=True, name="hoist")
    async def cmd_helpchat_hoist(self, ctx: Context):
        channel: discord.Channel = ctx.message.channel
        state = self.get_state(channel.server)
        await state.sync_hoisted_channels()
        await self.bot.react_success(ctx)

    @checks.is_manager()
    @cmd_helpchat.group(pass_context=True, name="set")
    async def cmd_helpchat_set(self, ctx: Context):
        if ctx.invoked_subcommand is None:
            await self.bot.react_question(ctx)

    @checks.is_manager()
    @cmd_helpchat_set.command(pass_context=True, name="free")
    async def cmd_helpchat_set_free(self, ctx: Context):
        channel: discord.Channel = ctx.message.channel
        state = self.get_state(channel.server)
        if channel in state.channels:
            await asyncio.sleep(1)
            await state.set_channel(channel, state.free_state, state.free_category)
            await self.bot.react_success(ctx)

    @checks.is_manager()
    @cmd_helpchat_set.command(pass_context=True, name="busy")
    async def cmd_helpchat_set_busy(self, ctx: Context):
        channel: discord.Channel = ctx.message.channel
        state = self.get_state(channel.server)
        if channel in state.channels:
            await asyncio.sleep(1)
            await state.set_channel(channel, state.busy_state, state.busy_category)
            await self.bot.react_success(ctx)

    @checks.is_manager()
    @cmd_helpchat_set.command(pass_context=True, name="idle")
    async def cmd_helpchat_set_idle(self, ctx: Context):
        channel: discord.Channel = ctx.message.channel
        state = self.get_state(channel.server)
        if channel in state.channels:
            await asyncio.sleep(1)
            await state.set_channel(channel, state.idle_state, state.idle_category)
            await self.bot.react_success(ctx)

    @checks.is_manager()
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
