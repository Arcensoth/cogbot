import argparse
import json
import logging
import os
import re
import shlex

from discord.ext import commands
from discord.ext.commands import CommandError, Context

from cogbot import checks
from cogbot.cog_bot import CogBot
from cogbot.extensions.mcc.parsers.v1_minecraft_commands_parser import V1MinecraftCommandsParser

log = logging.getLogger(__name__)

argparser = argparse.ArgumentParser(
    'mcc',
    description='Minecraft command query program. Inspired by the in-game help command, with added features like '
                'version reporting and expandable regex search.',
    add_help=False)

argparser.add_argument(
    '-t', '--types', action='store_true', help='whether to include argument types')

argparser.add_argument(
    '-e', '--explode', action='store_true', help='whether to expand all subcommands, regardless of capacity')

argparser.add_argument(
    '-c', '--capacity', type=int, default=4, help='maximum number of subcommands to render before collapsing')

argparser.add_argument(
    '-v', '--version', action='append', help='which version(s) to use for the command (repeatable)')

argparser.add_argument(
    'command', nargs='+', help='the command query')


class MinecraftCommandsState:
    DEFAULT_VERSIONS_STORAGE_PATH = './versions'

    def __init__(self, **options):
        # system path where server-generated data is located
        # generated data root for <version> looks something like `./versions/<version>/generated/`
        # invoke this command on the server jar to generate data:
        # java -cp minecraft_server.<version>.jar net.minecraft.data.Main --all
        self.versions_storage_path = options.pop('version_storage_path', self.DEFAULT_VERSIONS_STORAGE_PATH)

        # version definitions, such as which data parser to use
        self.versions = options.pop('versions', {})

        # versions to load and make available
        # all versions to load should be defined in `versions`
        self.load_versions = set(options.pop('load_versions', ()))

        # versions to render in the output
        # all versions to show should be listed in `load_versions`
        self.show_versions = set(options.pop('show_versions', ()))

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

        # instantiate a copy of each supported parser
        self.parsers = {
            # v1: for all 1.13 snapshots so far (18w01a to 18w03b)
            'v1': V1MinecraftCommandsParser()
        }

    async def on_ready(self):
        await self.reload()

    def _command_lines_from_node(
            self, node: dict,
            types: bool = False, explode: bool = False, capacity: int = 4):
        children = node.get('children', {})
        population = node.get('population')
        relevant = node.get('relevant')
        command = node.get('command_t' if types else 'command')
        collapsed = node.get('collapsed_t' if types else 'collapsed', command)

        # only render relevant commands
        # all executable commands should render: `scoreboard players list`, `scoreboard players list <target>`
        # all chainable (redirect) commands should render: `execute as <entity> -> execute ...`
        # other commands should generally not render: `scoreboard`, `scoreboard players`, etc
        if relevant:
            yield command

        # determine whether to expand the command into subcommands
        # if any of the following are true, continue expansion:
        #   1. collapse threshold has not been reached
        #   2. only one subcommand to expand
        if explode or (population <= capacity) or (len(children) < 2):
            for child in children.values():
                yield from self._command_lines_from_node(child, types=types, explode=explode, capacity=capacity)

        # otherwise render a collapsed form
        else:
            yield collapsed

    def _command_lines_recursive(
            self, node: dict, token: str, tokens: tuple,
            types: bool = None, explode: bool = None, capacity: int = None):
        search_children = ()

        if token:
            # use regex to search for the key in the patternized token
            # special case shortcut where a provided single '.' becomes '.*'
            pattern = '^{}$'.format('.*' if token == '.' else token)
            search_children = tuple(
                child for child_key, child in node.get('children', {}).items()
                if re.match(pattern, child_key, re.IGNORECASE))

        # branch: search all matching children recursively (depth-first) for subcommands
        if search_children:
            next_token = tokens[0] if tokens else ()
            next_tokens = tokens[1:] if len(tokens) > 1 else ()
            for child in search_children:
                yield from self._command_lines_recursive(
                    child, next_token, next_tokens, types=types, explode=explode, capacity=capacity)

        # leaf: no children to branch to, no token to search, start rendering commands from here
        elif not token:
            yield from self._command_lines_from_node(node, types=types, explode=explode, capacity=capacity)

    def command_lines(
            self, version: str, token: str, tokens: tuple,
            types: bool = None, explode: bool = None, capacity: int = None):
        # make sure the command exists before anything else
        next_node = self.data[version]['children'][token]

        # determine root token and tokens to start recursion
        next_token = tokens[0] if tokens else ()
        next_tokens = tokens[1:] if len(tokens) > 1 else ()

        # recursively yield all subcommands that match the given input
        yield from self._command_lines_recursive(
            next_node, next_token, next_tokens, types=types, explode=explode, capacity=capacity)

    async def mcc(self, ctx: Context, command: str):
        # split into tokens using shell-like syntax (preserve quoted substrings)
        try:
            parsed_args = argparser.parse_args(shlex.split(command))

            mc_command = parsed_args.command[0]  # required
            mc_args = tuple(parsed_args.command[1:] if len(parsed_args.command) > 1 else ())

            show_versions = set(parsed_args.version or self.state.show_versions).intersection(self.state.load_versions)

            capacity = parsed_args.capacity
            explode = parsed_args.explode
            types = parsed_args.types

        except:
            raise CommandError('failed to parse arguments for mcc')

        if not show_versions:
            await self.bot.add_reaction(ctx.message, u'😭')
            return

        version_lines = {}

        for version in show_versions:
            try:
                lines = list(self.command_lines(
                    version, mc_command, mc_args, types=types, explode=explode, capacity=capacity))
                if lines:
                    version_lines[version] = lines
                else:
                    raise ValueError('somehow got no command lines')
            except:
                log.exception('Unable to get version {} info for command: {} {}'.format(version, mc_command, mc_args))
                continue

        # let the user know if there were no results
        if not version_lines:
            await self.bot.add_reaction(ctx.message, u'🤷')
            return

        # if any version produced more than one command, render one paragraph per version
        if next((True for lines in version_lines.values() if len(lines) > 1), False):
            paragraphs = ('\n'.join(('# {}'.format(version), *lines)) for version, lines in version_lines.items())
            command_text = '\n\n'.join(paragraphs)

        # otherwise, if all versions rendered just 1 command, render one line per version (compact)
        else:
            command_text = '\n'.join('{}  # {}'.format(lines[0], version) for version, lines in version_lines.items())

        # render the full code section
        code_section = '```python\n{}\n```'.format(command_text)

        # render the help url, if enabled
        help_url = self.state.help_url
        help_section = '<{}{}>'.format(help_url, mc_command) if help_url else None

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
            await self.bot.send_message(ctx.message.channel, ' '.join((ctx.message.author.mention, message)))

    async def mccreload(self, ctx: Context):
        try:
            await self.reload(ctx)
            await self.bot.react_success(ctx)
        except:
            await self.bot.react_failure(ctx)

    @commands.command(pass_context=True, name='mcc', help=argparser.format_help())
    async def cmd_mcc(self, ctx: Context, *, command: str):
        await self.mcc(ctx, command)

    @checks.is_manager()
    @commands.command(pass_context=True, name='mccreload', hidden=True)
    async def cmd_mccreload(self, ctx):
        await self.mccreload(ctx)
