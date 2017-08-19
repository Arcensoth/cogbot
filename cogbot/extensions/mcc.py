import json
import logging
import urllib.request

from cogbot import checks
from cogbot.cog_bot import CogBot
from discord.ext import commands
from discord.ext.commands import Context
from discord.ext.commands.errors import *

log = logging.getLogger(__name__)


class MinecraftCommandsConfig:
    DEFAULT_COMMAND_MANIFEST = \
        'https://gist.githubusercontent.com/Arcensoth/0f3f91161352383e65f2259cb4d90230/raw/minecraft_commands.json'
    DEFAULT_COMMAND_PAGE = 'http://minecraft.gamepedia.com/Commands'

    def __init__(self, **options):
        self.command_manifest = options.pop('command_manifest', self.DEFAULT_COMMAND_MANIFEST)
        self.command_page = options.pop('command_page', self.DEFAULT_COMMAND_PAGE)


class MinecraftCommands:
    def __init__(self, bot: CogBot, ext: str):
        self.bot = bot
        options = bot.state.get_extension_state(ext)
        self.config = MinecraftCommandsConfig(**options)
        self.command_messages = {}
        self._reload_commands()

    def _message_lines(self, cmd, data):
        yield '```'

        usage = data.get('usage')

        if usage:
            if not isinstance(usage, list):
                usage = [usage]

            for usage_item in usage:
                yield f'{cmd} {usage_item}'

        else:
            yield cmd

        yield '```'

        see = data.get('see')

        if isinstance(see, str):
            yield f'See: <{see}>'

        elif isinstance(see, list):
            yield 'See:'
            for link in see:
                yield f'    - <{link}>'

        else:
            yield f'See: <{self.config.command_page}#{cmd}>'

    def _reload_commands(self):
        manifest = self.config.command_manifest

        log.info(f'reloading Minecraft commands from: {manifest}')

        response = urllib.request.urlopen(manifest)
        content = response.read().decode('utf8')

        try:
            cmd_data = json.loads(content)
        except Exception as e:
            raise CommandError(f'failed to load command manifest json: {e.args[0]}')

        self.command_messages = {cmd: '\n'.join(self._message_lines(cmd, data)) for cmd, data in cmd_data.items()}

        log.info(f'finished loading {len(cmd_data)} commands')

    async def mcc(self, ctx: Context, command: str):
        if command not in self.command_messages:
            raise CommandNotFound(f'no such Minecraft command "{command}"')
        await self.bot.say(self.command_messages[command])

    async def mccreload(self, ctx: Context):
        try:
            self._reload_commands()
            await self.bot.react_success(ctx)
        except:
            await self.bot.react_failure(ctx)

    @commands.command(pass_context=True, name='mcc')
    async def cmd_mcc(self, ctx: Context, *, command: str):
        await self.mcc(ctx, command)

    @checks.is_manager()
    @commands.command(pass_context=True, name='mccreload', hidden=True)
    async def cmd_mccreload(self, ctx):
        await self.mccreload(ctx)


def setup(bot):
    bot.add_cog(MinecraftCommands(bot, __name__))
