import logging

from discord.ext import commands
from discord.ext.commands import Context
from discord.ext.commands.errors import *

from cogbot.cog_bot_state import CogBotState

log = logging.getLogger(__name__)


class CogBot(commands.Bot):
    def __init__(self, state: CogBotState, **options):
        super().__init__(
            command_prefix=state.command_prefix,
            description=state.description,
            help_attrs=state.help_attrs,
            **options)

        self.state = state

        # A queue of messages to send after login.
        self.queued_messages = []

        if self.state.extensions:
            self.load_extensions(*self.state.extensions)
        else:
            log.info('No extensions to load')

        log.info('Initialization successful')

    def queue_message(self, dest_getter, dest_id, content):
        self.queued_messages.append((dest_getter, dest_id, content))

    def load_extensions(self, *extensions):
        log.info(f'Loading {len(extensions)} extensions...')
        for ext in extensions:
            log.info(f'Loading extension {ext}...')
            try:
                self.load_extension(ext)
            except Exception as e:
                log.exception(f'Failed to load extension {ext}')
        log.info(f'Finished loading extensions')

    def unload_extensions(self, *extensions):
        log.info(f'Unloading {len(extensions)} extensions...')
        for ext in extensions:
            log.info(f'Unloading extension {ext}...')
            try:
                self.unload_extension(ext)
            except Exception as e:
                log.exception(f'Failed to unload extension {ext}')
        log.info(f'Finished unloading extensions')

    def force_logout(self):
        self._is_logged_in.clear()

    async def send_error(self, ctx: Context, destination, error: CommandError):
        place = '' if ctx.message.server is None else f' on **{ctx.message.server}**'
        reply = f'There was a problem with your command{place}: *{error.args[0]}*'
        await self.send_message(destination, reply)

    async def on_ready(self):
        log.info(f'Logged in as {self.user.name} (id {self.user.id})')
        # Send any queued messages.
        if self.queued_messages:
            log.info(f'Sending {len(self.queued_messages)} queued messages...')
            for dest_getter, dest_id, content in self.queued_messages:
                dest = await dest_getter(dest_id)
                await self.send_message(dest, content)

    async def on_message(self, message):
        if (message.author != self.user) and message.content.startswith(self.command_prefix):
            # listen to anyone on public channels
            if message.server:
                log.info(f'[{message.server}/{message.author}] {message.content}')
                await super().on_message(message)

            # listen only to managers on private (dm) channels
            elif message.author.id in self.state.managers:
                log.info(f'[{message.author}] {message.content}')
                await super().on_message(message)

    async def on_command_error(self, e: CommandError, ctx: Context):
        log.warning(f'[{ctx.message.server}/{ctx.message.author}] {e.__class__.__name__}: {e.args[0]}')

        error = e.original if isinstance(e, CommandInvokeError) else e

        if isinstance(error, CommandNotFound):
            if self.state.react_to_unknown_commands:
                await self.react_question(ctx)

        elif isinstance(error, CheckFailure):
            await self.react_denied(ctx)

        elif isinstance(error, CommandOnCooldown):
            if self.state.react_to_command_cooldowns:
                await self.react_cooldown(ctx)

        # Keep this one last because some others subclass it.
        elif isinstance(error, CommandError):
            await self.react_failure(ctx)

        else:
            await self.react_poop(ctx)

    async def react_success(self, ctx: Context):
        await self.add_reaction(ctx.message, u'✔')

    async def react_neutral(self, ctx: Context):
        await self.add_reaction(ctx.message, u'➖')

    async def react_question(self, ctx: Context):
        await self.add_reaction(ctx.message, u'❓')

    async def react_failure(self, ctx: Context):
        await self.add_reaction(ctx.message, u'❗')

    async def react_denied(self, ctx: Context):
        await self.add_reaction(ctx.message, u'🚫')

    async def react_cooldown(self, ctx: Context):
        await self.add_reaction(ctx.message, u'⏳')

    async def react_poop(self, ctx: Context):
        await self.add_reaction(ctx.message, u'💩')
