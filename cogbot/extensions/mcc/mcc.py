import json
import logging
import os

from discord.ext import commands
from discord.ext.commands import Context

from cogbot import checks
from cogbot.cog_bot import CogBot
from cogbot.extensions.mcc.parsers.v1_minecraft_commands_parser import V1MinecraftCommandsParser

log = logging.getLogger(__name__)


class MinecraftCommandsState:
    DEFAULT_VERSIONS_STORAGE_PATH = './versions'
    DEFAULT_COLLAPSE_THRESHOLD = 4

    def __init__(self, **options):
        # system path where server-generated data is located
        # generated data root for <version> looks something like `./versions/<version>/generated/`
        # invoke this command on the server jar to generate data:
        # java -cp minecraft_server.<version>.jar net.minecraft.data.Main --all
        self.versions_storage_path = options.pop('version_storage_path', self.DEFAULT_VERSIONS_STORAGE_PATH)

        # version definitions, such as which data parser to use
        self.versions = options.pop('versions', {})

        # versions to load and make available (planned: pass `-v <version>` for a specific version)
        # all versions to load should be defined in `versions`
        self.load_versions = set(options.pop('load_versions', ()))

        # versions to render in the output
        # all versions to show should be listed in `load_versions`
        self.show_versions = set(options.pop('show_versions', ()))

        # number of subcommands that cause a parent command to render `...` instead of expanding all subcommands
        # so a threshold of 4 means that a command with 4 subcommands will be compacted into `command ...` instead
        # warning: high threshold may be slow and/or cause errors as messages become large
        self.collapse_threshold = options.pop('collapse_threshold', self.DEFAULT_COLLAPSE_THRESHOLD)

        # base http url to append root commands and provide a help link
        # compiled as `<help_url><command>` so make sure to include a trailing slash if necessary
        self.help_url = options.pop('help_url', None)

        # can't load versions that haven't been defined with a parser
        load_not_defined = self.load_versions - set(self.versions)
        if load_not_defined:
            log.warning('Cannot load versions that have not been defined: {}'.format(', '.join(load_not_defined)))
            self.load_versions -= load_not_defined
            log.warning('Overriding versions to load: {}'.format(', '.join(self.load_versions)))

        # can't show versions that haven't been loaded
        show_not_loaded = self.show_versions - self.load_versions
        if show_not_loaded:
            log.warning('Cannot show versions that have not been loaded: {}'.format(', '.join(show_not_loaded)))
            self.show_versions -= show_not_loaded
            log.warning('Overriding versions to show: {}'.format(', '.join(self.show_versions)))


class MinecraftCommands:
    def __init__(self, bot: CogBot, ext: str):
        self.bot = bot
        self.state = MinecraftCommandsState(**bot.state.get_extension_state(ext))
        self.data = {}
        self.parsers = {
            # v1: for all 1.13 snapshots so far (18w01a to 18w03b)
            'v1': V1MinecraftCommandsParser()
        }

    async def on_ready(self):
        await self.reload()

    def command_lines_from_data(self, data: dict, depth: int = 1):
        relevant = data.get('relevant')
        command = data.get('command')
        children = data.get('children', {})
        population = data.get('population', 0)

        # only render relevant commands
        # all executable commands should render: `scoreboard players list`, `scoreboard players list <target>`
        # all chainable (redirect) commands should render: `execute as <entity> -> execute ...`
        # other commands should generally not render: `scoreboard`, `scoreboard players`, etc
        if relevant:
            yield command

        # determine whether to expand the command into subcommands
        # if any of the following are true, continue expansion:
        #   1. depth has not reached 0
        #   2. collapse threshold has not been reached
        #   3. only one subcommand to expand
        # note that depth = 1 is useful here because we always want to expand at least one level of subcommands
        if (depth > 0) or (population < self.state.collapse_threshold) or (len(children) < 2):
            for child in children.values():
                yield from self.command_lines_from_data(child, depth - 1)

        # otherwise render a collapsed form
        else:
            yield ' '.join((command, '...'))

    def command_lines(self, version: str, command: str):
        data = self.data[version]

        # recursively position ourselves at the deepest subcommand that matches the given input
        for t in command.split():
            try:
                data = data['children'][t]
            except:
                break

        # from there, start rendering subcommands
        yield from self.command_lines_from_data(data)

    async def mcc(self, ctx: Context, command: str):
        paras = []

        for version in self.state.show_versions:
            try:
                para = tuple(self.command_lines(version, command))
                # only 1 command? put the version right after it on the same line
                if len(para) == 1:
                    paras.append(('{}  # {}'.format(para[0], version),))
                # multiple commands? put the version at the top
                elif len(para) > 1:
                    paras.append(('# {}'.format(version), *para))
                # otherwise something went wrong (shouldn't happen)
                else:
                    raise ValueError()
            except:
                message = 'Unable to get version {} info for command: {}'.format(version, command)
                log.info(message)
                continue

        # if all versions rendered just 1 command, don't put newlines between them
        # otherwise, if at least one version render multiple commands, make some space between versions
        compact = not tuple(len(para) > 1 for para in paras).count(True)
        para_sep = '\n' if compact else '\n\n'
        code_section = '```python\n{}\n```'.format(para_sep.join('\n'.join(line for line in para) for para in paras))

        # render the help url, if enabled
        help_url = self.state.help_url
        help_section = '<{}{}>'.format(help_url, command.split(maxsplit=1)[0]) if help_url else None

        # leave out blank sections
        message = '\n'.join(section for section in (code_section, help_section) if section is not None)

        await self.bot.send_message(ctx.message.channel, message)

    async def reload(self, ctx: Context = None):
        self.data = {}

        for version in self.state.load_versions:
            data_path = os.path.join(
                self.state.versions_storage_path, version,
                'generated', 'reports', 'commands.json')

            log.info('Loading commands for version {} from: {}'.format(version, data_path))

            try:
                with open(data_path) as fp:
                    raw = json.load(fp)
            except Exception:
                log.exception('Failed to load data file for version {}'.format(version))
                continue

            try:
                parser = self.parsers[self.state.versions[version]['parser']]
            except Exception:
                log.exception('No parser configured for version {}'.format(version))
                continue

            try:
                self.data[version] = parser.parse(raw)
            except Exception:
                log.exception('Failed to parse commands for version {}'.format(version))

        message = 'Loaded commands for {} versions: {}'.format(len(self.data.keys()), ', '.join(self.data))
        log.info(message)
        if ctx:
            await self.bot.send_message(ctx.message.channel, message)

    async def mccreload(self, ctx: Context):
        try:
            await self.reload(ctx)
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
