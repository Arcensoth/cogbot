import logging

from discord.ext import commands
from discord.ext.commands import Context
from discord.ext.commands.errors import *

from cogbot.cog_bot_config import CogBotConfig

log = logging.getLogger(__name__)


class CogBot(commands.Bot):
    def __init__(self, config: CogBotConfig, **options):
        super().__init__(
            command_prefix=config.command_prefix,
            description=config.description,
            help_attrs=config.help_attrs,
            **options)

        self.config = config

        if self.config.extensions:
            self.load_extensions(*self.config.extensions)
        else:
            log.info('no extensions to load')

        log.info('initialization successful')

    def load_extensions(self, *extensions):
        log.info(f'loading {len(extensions)} extensions...')
        for ext in extensions:
            log.info(f'loading extension {ext}...')
            try:
                self.load_extension(ext)
            except Exception as e:
                log.warning(f'failed to load extension {ext} because: {e.__class__.__name__}: {e}')
        log.info(f'finished loading extensions')

    def unload_extensions(self, *extensions):
        log.info(f'unloading {len(extensions)} extensions...')
        for ext in extensions:
            log.info(f'unloading extension {ext}...')
            try:
                self.unload_extension(ext)
            except Exception as e:
                log.warning(f'failed to unload extension {ext} because: {e.__class__.__name__}: {e}')
        log.info(f'finished unloading extensions')

    async def send_error(self, ctx: Context, destination, error: CommandError):
        place = '' if ctx.message.server is None else f' on **{ctx.message.server}**'
        reply = f'There was a problem with your command{place}: *{error.args[0]}*'
        await self.send_message(destination, reply)

    async def on_ready(self):
        log.info(f'logged in as {self.user.name} (id {self.user.id})')
        # call on_ready() for extensions
        # TODO this is gross, clean it up with an ABC or something
        for cog_name, cog in self.cogs.items():
            on_ready_fn = getattr(cog, 'on_ready', None)
            if on_ready_fn:
                await on_ready_fn()

    async def on_message(self, message):
        if (message.author != self.user) \
                and message.server is not None \
                and message.content.startswith(self.command_prefix):
            log.info(f'[{message.server}/{message.author}] {message.content}')
            await super().on_message(message)

    async def on_command_error(self, e: CommandError, ctx: Context):
        log.warning(f'[{ctx.message.server}/{ctx.message.author}] {e.__class__.__name__}: {e.args[0]}')

        error = e.original if isinstance(e, CommandInvokeError) else e

        if isinstance(error, CommandNotFound):
            await self.react_question(ctx)

        elif isinstance(error, CheckFailure):
            await self.react_denied(ctx)

        elif isinstance(error, CommandOnCooldown):
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
