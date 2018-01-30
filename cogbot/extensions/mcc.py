import logging

from discord.ext import commands
from discord.ext.commands import Context

from cogbot import checks
from cogbot.cog_bot import CogBot
from mccq import errors as mccq_errors
from mccq.cli import argparser as mccq_argparser
from mccq.cli import utils as mccq_cli_utils
from mccq.mccq import MCCQ

log = logging.getLogger(__name__)


class MinecraftCommandsState:
    DEFAULT_VERSIONS_STORAGE = './versions'

    def __init__(self, **options):
        # system path where server-generated data is located
        # generated data root for <version> looks something like `./versions/<version>/generated/`
        # invoke this command on the server jar to generate data:
        # java -cp minecraft_server.<version>.jar net.minecraft.data.Main --all
        self.versions_storage = options.pop('version_storage', self.DEFAULT_VERSIONS_STORAGE)

        # versions definitions, such as which data parser to use
        self.versions = options.pop('versions', {})

        # versions to render in the output; should all be defined
        self.show_versions = set(options.pop('show_versions', ()))

        # base http url to append root commands and provide a help link
        # compiled as `<help_url><command>` so make sure to include a trailing slash if necessary
        self.help_url = options.pop('help_url', None)

        # can't show versions that haven't been defined
        show_not_defined = self.show_versions - set(self.versions)
        if show_not_defined:
            log.warning('Cannot show versions that have not been defined: {}'.format(', '.join(show_not_defined)))
            self.show_versions -= show_not_defined
            log.warning('Overriding versions to show: {}'.format(', '.join(self.show_versions)))


class MinecraftCommands:
    def __init__(self, bot: CogBot, ext: str):
        self.bot = bot
        self.state = MinecraftCommandsState(**bot.state.get_extension_state(ext))
        self.mccq = MCCQ(
            versions_storage=self.state.versions_storage,
            versions_definition=self.state.versions,
            show_versions=self.state.show_versions,
        )

    async def mcc(self, ctx: Context, command: str):
        try:
            # get a copy of the parsed arguments so we can tell the user about them
            arguments = mccq_cli_utils.parse_mccq_arguments(command)
            results = self.mccq.results_from_arguments(arguments)

        except mccq_errors.ArgumentParserFailedMCCQError:
            log.info('Failed to parse arguments for the command: {}'.format(command))
            await self.bot.add_reaction(ctx.message, u'🤢')
            return

        except mccq_errors.NoVersionsAvailableMCCQError:
            log.info('No versions available for the command: {}'.format(command))
            await self.bot.add_reaction(ctx.message, u'🤐')
            return

        except mccq_errors.NoSuchCommandMCCQError:
            log.info('No such command: {}'.format(command))
            await self.bot.add_reaction(ctx.message, u'🤔')
            return

        except:
            log.exception('An unexpected error occurred while processing the command: {}'.format(command))
            await self.bot.add_reaction(ctx.message, u'🤯')
            return

        if not results:
            # let the user know if there were no results, and short-circuit
            # note this is different from an invalid base command
            await self.bot.add_reaction(ctx.message, u'🤷')
            return

        # if any version produced more than one command, render one paragraph per version
        if next((True for lines in results.values() if len(lines) > 1), False):
            paragraphs = ('\n'.join(('# {}'.format(version), *lines)) for version, lines in results.items())
            command_text = '\n\n'.join(paragraphs)

        # otherwise, if all versions rendered just 1 command, render one line per version (compact)
        else:
            command_text = '\n'.join(
                '{}  # {}'.format(lines[0], version) for version, lines in results.items() if lines)

        # render the full code section
        code_section = '```python\n{}\n```'.format(command_text)

        # render the help url, if enabled
        help_url = self.state.help_url
        help_section = '<{}{}>'.format(help_url, arguments.command[0]) if help_url else None

        # leave out blank sections
        message = '\n'.join(section for section in (code_section, help_section) if section is not None)

        await self.bot.send_message(ctx.message.channel, message)

    async def reload(self):
        self.mccq.reload(self.state.versions)

    async def mccreload(self, ctx: Context):
        try:
            self.reload()

        except:
            log.exception('An unexpected error occurred while reloading commands')
            await self.bot.add_reaction(ctx.message, u'🤯')
            return

        await self.bot.react_success(ctx)

    @commands.command(pass_context=True, name='mcc', help=mccq_argparser.ARGPARSER.format_help())
    async def cmd_mcc(self, ctx: Context, *, command: str):
        await self.mcc(ctx, command)

    @checks.is_manager()
    @commands.command(pass_context=True, name='mccreload', hidden=True)
    async def cmd_mccreload(self, ctx):
        await self.mccreload(ctx)


def setup(bot):
    bot.add_cog(MinecraftCommands(bot, __name__))
