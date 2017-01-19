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
            log.info(f'loading {len(self.config.extensions)} extensions...')
            for ext in self.config.extensions:
                log.info(f'  -> {ext}')
                try:
                    self.load_extension(ext)
                except Exception as e:
                    log.error(f'    -> failed to load extension due to: {e.args[0]}')

        else:
            log.info('no extensions to load')

        log.info('initialization successful')

    async def send_help(self, ctx: Context, destination):
        pages = self.formatter.format_help_for(ctx, ctx.command)

        if destination is None or (self.pm_help is None and sum(map(lambda l: len(l), pages)) > 1000):
            destination = ctx.message.author

        for page in pages:
            await self.send_message(destination, page)

    async def send_error(self, ctx: Context, destination, error: CommandError):
        place = '' if ctx.message.server is None else f' on **{ctx.message.server}**'
        reply = f'There was a problem with your command{place}: *{error.args[0]}*'
        await self.send_message(destination, reply)
        await self.send_help(ctx, destination)

    async def on_ready(self):
        log.info(f'logged in as {self.user.name} (id {self.user.id})')
        # call on_ready() for extensions
        # TODO this is gross, clean it up with an ABC or something
        for cog_name, cog in self.cogs.items():
            on_ready_fn = getattr(cog, 'on_ready', None)
            if on_ready_fn:
                await on_ready_fn()

    async def on_message(self, message):
        if (message.author != self.user) and message.content.startswith(self.command_prefix):
            log.info(f'[{message.server}/{message.author}] {message.content}')
            await super().on_message(message)

    async def on_command_error(self, e: CommandError, ctx: Context):
        log.warning(f'[{ctx.message.server}/{ctx.message.author}] {e.__class__.__name__}: {e.args[0]}')

        error = e.original if isinstance(e, CommandInvokeError) else e

        if isinstance(error, CommandNotFound):
            await self.send_error(ctx, ctx.message.author, error)
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
