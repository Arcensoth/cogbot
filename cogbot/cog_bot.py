import logging
from datetime import datetime

import discord
from discord.ext import commands
from discord.ext.commands import Context
from discord.ext.commands.bot import _get_variable
from discord.ext.commands.errors import *

from cogbot.cog_bot_state import CogBotState

log = logging.getLogger(__name__)


class CogBot(commands.Bot):
    def __init__(self, state: CogBotState, **options):
        super().__init__(
            command_prefix=commands.when_mentioned_or(*state.command_prefix),
            description=state.description,
            help_attrs=state.help_attrs,
            **options,
        )

        self.state = state

        # Remember when we started.
        self.started_at = datetime.now()

        # Channel to log mod messages to.
        self.mod_log_channel = None

        # A queue of messages to send after login.
        self.queued_messages = []

        if self.state.extensions:
            self.load_extensions(*self.state.extensions)
        else:
            log.info("No extensions to load")

        log.info("Initialization successful")

    def get_emoji(self, server: discord.Server, emoji: str):
        if emoji.startswith("<"):
            for e in server.emojis:
                if str(e) == emoji:
                    return e
        return emoji

    async def reply(self, content, *args, **kwargs):
        author = kwargs.pop("author", _get_variable("_internal_author"))
        destination = kwargs.pop("destination", _get_variable("_internal_channel"))
        fmt = f"@{author.display_name} {content}"

        extensions = ("delete_after",)
        params = {k: kwargs.pop(k, None) for k in extensions}

        coro = self.send_message(destination, fmt, *args, **kwargs)
        sent_message = await self._augmented_msg(coro, **params)

        fmt2 = f"{author.mention} {content}"

        return await self.edit_message(sent_message, new_content=fmt2)

    def queue_message(self, dest_getter, dest_id, content):
        self.queued_messages.append((dest_getter, dest_id, content))

    def load_extensions(self, *extensions):
        log.info(f"Loading {len(extensions)} extensions...")
        for ext in extensions:
            log.info(f"Loading extension {ext}...")
            try:
                self.load_extension(ext)
            except Exception as e:
                log.exception(f"Failed to load extension {ext}")
        log.info(f"Finished loading extensions")

    def unload_extensions(self, *extensions):
        log.info(f"Unloading {len(extensions)} extensions...")
        for ext in extensions:
            log.info(f"Unloading extension {ext}...")
            try:
                self.unload_extension(ext)
            except Exception as e:
                log.exception(f"Failed to unload extension {ext}")
        log.info(f"Finished unloading extensions")

    def force_logout(self):
        self._is_logged_in.clear()

    async def send_error(self, ctx: Context, destination, error: CommandError):
        place = "" if ctx.message.server is None else f" on **{ctx.message.server}**"
        reply = f"There was a problem with your command{place}: *{error.args[0]}*"
        await self.send_message(destination, reply)

    async def mod_log(
        self, ctx: Context, content: str, destination: discord.Channel = None
    ):
        await self.send_message(
            destination or self.mod_log_channel or ctx.message.author,
            f"[{ctx.message.author}] {content}",
        )

    async def on_ready(self):
        log.info(f"Logged in as {self.user.name} (id {self.user.id})")

        # Resolve mod log channel.
        self.mod_log_channel = (
            self.get_channel(self.state.mod_log) if self.state.mod_log else None
        )
        if self.mod_log_channel:
            log.info(f"Resolved mod log channel: #{self.mod_log_channel}")
        else:
            log.warning(f"No mod log configured!")

        # Send any queued messages.
        if self.queued_messages:
            log.info(f"Sending {len(self.queued_messages)} queued messages...")
            for dest_getter, dest_id, content in self.queued_messages:
                dest = await dest_getter(dest_id)
                await self.send_message(dest, content)

    def care_about_it(self, message: discord.Message):
        # ignore bot's own messages
        if message.author != self.user:
            # must start with one of the command prefixes
            for prefix in self.state.command_prefix:
                if message.content.startswith(prefix):
                    return True

            # or mentions the bot
            if self.user in message.mentions:
                return True

        return False

    async def on_message(self, message):
        if self.care_about_it(message):
            # listen to anyone on public channels
            if message.server:
                log.info(f"[{message.server}/{message.author}] {message.content}")
                await super().on_message(message)

            # listen only to managers on private (dm) channels
            elif message.author.id in self.state.managers:
                log.info(f"[{message.author}] {message.content}")
                await super().on_message(message)

    async def on_command_error(self, error: CommandError, ctx: Context):
        log.exception(
            f"[{ctx.message.server}/{ctx.message.author}] {error.__class__.__name__}: {error.args[0]}",
            exc_info=error,
        )

        inner_error = error.original if isinstance(error, CommandInvokeError) else error

        if isinstance(inner_error, CommandNotFound):
            if self.state.react_to_unknown_commands:
                await self.react_question(ctx)

        elif isinstance(inner_error, CheckFailure):
            if self.state.react_to_check_failures:
                await self.react_denied(ctx)

        elif isinstance(inner_error, CommandOnCooldown):
            if self.state.react_to_command_cooldowns:
                await self.react_cooldown(ctx)

        # Keep this one last because some others subclass it.
        elif isinstance(inner_error, CommandError):
            await self.react_failure(ctx)

        else:
            await self.react_poop(ctx)

    async def react_success(self, ctx: Context):
        await self.add_reaction(ctx.message, "✔")

    async def react_neutral(self, ctx: Context):
        await self.add_reaction(ctx.message, "➖")

    async def react_question(self, ctx: Context):
        await self.add_reaction(ctx.message, "❓")

    async def react_failure(self, ctx: Context):
        await self.add_reaction(ctx.message, "❗")

    async def react_denied(self, ctx: Context):
        await self.add_reaction(ctx.message, "🚫")

    async def react_cooldown(self, ctx: Context):
        await self.add_reaction(ctx.message, "⏳")

    async def react_poop(self, ctx: Context):
        await self.add_reaction(ctx.message, "💩")
