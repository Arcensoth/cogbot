import json
import logging
import typing
import urllib.request
from datetime import datetime, timedelta

import discord
import discord.http
from discord.ext import commands
from discord.ext.commands import Context
from discord.ext.commands.bot import _get_variable
from discord.ext.commands.errors import *

from cogbot.cog_bot_server_state import CogBotServerState
from cogbot.cog_bot_state import CogBotState
from cogbot.types import ChannelId, RoleId, ServerId, UserId

log = logging.getLogger(__name__)


class MessageReport:
    def __init__(self):
        self.total_messages: typing.Dict[discord.Channel, int] = {}
        self.messages_per_member: typing.Dict[
            discord.Channel, typing.Dict[discord.Member, int]
        ] = {}


class CogBot(commands.Bot):
    def __init__(self, state: CogBotState, **options):
        super().__init__(
            command_prefix=commands.when_mentioned_or(*state.command_prefix),
            description=state.description,
            help_attrs=state.help_attrs,
            **options,
        )

        # global bot state/config
        self.state = state

        # per-server state/config
        self.server_state: typing.Dict[ServerId, CogBotServerState] = {}
        self.server_by_key: typing.Dict[str, discord.Server] = {}

        # Remember when we started.
        self.started_at = datetime.now()

        # A queue of messages to send after login.
        self.queued_messages = []

        if self.state.extensions:
            # skip disabled extensions (those beginning with a `!`)
            enabled_extensions = [
                ext for ext in self.state.extensions if not str(ext).startswith("!")
            ]
            self.load_extensions(*enabled_extensions)
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
            log.info(f"Loading extension: {ext}")
            try:
                self.load_extension(ext)
            except:
                log.exception(f"Failed to load extension: {ext}")
        log.info(f"Finished loading extensions.")

    def unload_extensions(self, *extensions):
        log.info(f"Unloading {len(extensions)} extensions...")
        for ext in extensions:
            log.info(f"Unloading extension: {ext}")
            try:
                self.unload_extension(ext)
            except:
                log.exception(f"Failed to unload extension: {ext}")
        log.info(f"Finished unloading extensions.")

    async def load_json(self, address: str) -> dict:
        if address.startswith(("http://", "https://")):
            response = urllib.request.urlopen(address)
            content = response.read().decode("utf8")
            data = json.loads(content)
        else:
            with open(address, encoding="utf-8") as fp:
                data = json.load(fp)
        return data

    def force_logout(self):
        self._is_logged_in.clear()

    async def send_error(self, ctx: Context, destination, error: CommandError):
        place = "" if ctx.message.server is None else f" on **{ctx.message.server}**"
        reply = f"There was a problem with your command{place}: *{error.args[0]}*"
        await self.send_message(destination, reply)

    def get_server_from_key(self, key: str) -> discord.Server:
        # try first our cache, then fallback to built-in method
        return self.server_by_key.get(key) or self.get_server(key)

    def get_server_state(self, server: discord.Server) -> CogBotServerState:
        return self.server_state.get(server.id)

    def get_server_state_from_key(self, key: str) -> CogBotServerState:
        server = self.get_server_from_key(key)
        if server:
            return self.server_state.get(server.id)

    def make_message_link(self, message: discord.Message) -> str:
        return f"https://discordapp.com/channels/{message.server.id}/{message.channel.id}/{message.id}"

    async def make_message_report(
        self,
        channels: typing.List[discord.Channel],
        members: typing.List[discord.Member],
        since: datetime,
    ) -> MessageReport:
        report = MessageReport()
        for channel in channels:
            report.total_messages[channel] = 0
            messages_per_member = {member: 0 for member in members}
            report.messages_per_member[channel] = messages_per_member
            async for message in self.logs_from(channel, limit=999999999, after=since):
                message: discord.Message
                author: discord.Member = message.author
                report.total_messages[channel] += 1
                if author in messages_per_member:
                    messages_per_member[author] += 1
        return report

    def get_role(self, server: discord.Server, role_id: str) -> discord.Role:
        for role in server.roles:
            if role.id == role_id:
                return role

    async def edit_channel(
        self,
        channel: discord.Channel,
        name: str = None,
        topic: str = None,
        position: int = None,
        category: discord.Channel = None,
        **options,
    ):
        # NOTE hack because this version of discord is older than categories
        payload = dict(**options)
        if name is not None:
            payload["name"] = name
        if topic is not None:
            payload["topic"] = topic
        if position is not None:
            payload["position"] = position
        if category is not None:
            payload["parent_id"] = category.id
        return await self.http.request(
            discord.http.Route(
                "PATCH", "/channels/{channel_id}", channel_id=channel.id
            ),
            json=payload,
        )

    async def move_channel_to_category(
        self, channel: discord.Channel, category: discord.Channel, position: int = None
    ):
        return self.edit_channel(channel, category=category, position=position)

    async def mod_log(
        self,
        member: discord.Member,
        content: str,
        message: discord.Message = None,
        icon: str = None,
        color: int = None,
    ):
        if isinstance(member, discord.Member):
            state = self.get_server_state(member.server)
            if state:
                await state.mod_log(
                    member, content, message=message, icon=icon, color=color
                )

    def as_member_of(self, server: discord.Server) -> discord.Member:
        return server.get_member(self.user.id)

    async def on_ready(self):
        log.info(f"Logged in as {self.user.name} (id {self.user.id})")

        # resolve configured servers
        for server_key, server_options in self.state.servers.items():
            # copy options dict because we need to make modifications
            options = {k: v for k, v in server_options.items()}

            # pop id so we don't send it to the state constructor
            server_id = options.pop("id")

            if server_id:
                server = self.get_server(server_id)
                if server:
                    try:
                        self.server_by_key[server_key] = server
                        state = CogBotServerState(self, server, **options)
                        self.server_state[server_id] = state
                        log.info(
                            f"Successfully configured server {server_key} <{server.id}>: {server}"
                        )
                    except Exception as e:
                        log.exception(
                            f"Failed to configure server {server_key} <{server_id}>"
                        )
                else:
                    log.error(f"Failed to resolve server {server_key} <{server_id}>")
            else:
                log.error(f"Missing server_id for server {server_key}")

        # Send any queued messages.
        if self.queued_messages:
            log.info(f"Sending {len(self.queued_messages)} queued messages...")
            for dest_getter, dest_id, content in self.queued_messages:
                dest = await dest_getter(dest_id)
                await self.send_message(dest, content)

    def is_command(self, message: discord.Message) -> bool:
        for prefix in self.state.command_prefix:
            if message.content.startswith(prefix):
                return True

    def care_about_it(self, message: discord.Message) -> bool:
        # ignore bot's own messages
        if message.author != self.user:
            # must start with one of the command prefixes
            if self.is_command(message):
                return True
            # or mentions the bot
            if self.user in message.mentions:
                return True

    def is_message_younger_than(
        self, message: discord.Message, *args, **kwargs
    ) -> bool:
        now: datetime = datetime.utcnow()
        delta = timedelta(*args, **kwargs)
        then: datetime = message.timestamp + delta
        return now > then

    async def get_latest_message(self, channel: discord.Channel) -> discord.Message:
        async for message in self.logs_from(channel, limit=1):
            return message

    async def is_latest_message(self, message: discord.Message) -> bool:
        latest_message = await self.get_latest_message(message.channel)
        return message.id == latest_message.id

    async def iter_latest_messages(
        self, channels: typing.List[discord.Channel], limit: int = 1
    ) -> typing.Iterable[discord.Message]:
        for channel in channels:
            async for message in self.logs_from(channel, limit=limit):
                yield message

    async def get_latest_messages(
        self, channels: typing.List[discord.Channel], limit: int = 1
    ) -> typing.List[discord.Message]:
        return [m async for m in self.iter_latest_messages(channels, limit=limit)]

    async def on_message(self, message):
        if self.care_about_it(message):
            # listen to anyone on public channels
            if message.server:
                log.info(f"[{message.server}/{message.author}] {message.content}")
                await super().on_message(message)

            # listen only to managers on private (dm) channels
            # .. or anyone, if enabled
            elif self.state.allow_dms or message.author.id in self.state.managers:
                log.info(f"[{message.author}] {message.content}")
                await super().on_message(message)

    async def on_command_error(self, error: CommandError, ctx: Context):
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
            log.exception(
                f"[{ctx.message.server}/{ctx.message.author}] Encountered a command error: {error}",
                exc_info=error,
            )
            await self.react_failure(ctx)

        else:
            log.exception(
                f"[{ctx.message.server}/{ctx.message.author}] Encountered an unknown error:",
                exc_info=error,
            )
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
