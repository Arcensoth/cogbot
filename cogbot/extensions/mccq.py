import logging

from discord.ext import commands
from discord.ext.commands import Context

from cogbot import checks
from cogbot.cog_bot import CogBot
from mccq import argparser as mccq_argparser
from mccq import errors as mccq_errors
from mccq import utils as mccq_utils
from mccq.mccq import MCCQ

log = logging.getLogger(__name__)


class MCCQExtensionState:
    def __init__(self, **options):
        # REQUIRED
        # path to server-generated data, structured like:
        # `<database>/<version>/generated/reports/commands.json`
        # can be a local filesystem folder or an internet url
        self.database = options['database']

        # make sure a database is defined
        if not self.database:
            raise ValueError('A versions database location must be defined')

        # REQUIRED
        # versions definitions, such as which data parser to use
        self.versions = options['versions']

        # make sure at least one version is defined
        if not self.versions:
            raise ValueError('At least one version must be defined')

        # versions to render in the output; should all be defined
        self.show_versions = options.get('show_versions', [])

        # url format to provide a help link, if any
        # the placeholder `{command}` will be replaced by the base command
        self.help_url = options.pop('help_url', None)

        # can't show versions that haven't been defined
        show_not_defined = set(self.show_versions) - set(self.versions)
        if show_not_defined:
            log.warning('Cannot show versions that have not been defined: {}'.format(', '.join(show_not_defined)))
            self.show_versions = [v for v in self.show_versions if (v not in show_not_defined)]
            log.warning('Overriding versions to show: {}'.format(', '.join(self.show_versions)))

        # warn if there are no versions to show
        if not self.show_versions:
            log.warning('None of the configured versions can be shown: {}'.format(', '.join(show_not_defined)))


class MCCQExtension:
    def __init__(self, bot: CogBot, ext: str):
        self.bot = bot
        self.state = MCCQExtensionState(**bot.state.get_extension_state(ext))
        self.mccq = MCCQ(
            database=self.state.database,
            versions=self.state.versions,
            show_versions=self.state.show_versions,
        )

    async def mcc(self, ctx: Context, command: str):
        try:
            # get a copy of the parsed arguments so we can tell the user about them
            arguments = mccq_utils.parse_mccq_arguments(command)
            results = self.mccq.results_from_arguments(arguments)

        except mccq_errors.ArgumentParserFailedMCCQError:
            log.info('Failed to parse arguments for the command: {}'.format(command))
            await self.bot.add_reaction(ctx.message, u'🤢')
            return

        except mccq_errors.NoVersionsAvailableMCCQError:
            log.info('No versions available for the command: {}'.format(command))
            await self.bot.add_reaction(ctx.message, u'🤐')
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
        help_section = ''.join(('<', help_url.format(command=arguments.command[0]), '>')) if help_url else None

        # leave out blank sections
        message = '\n'.join(section for section in (code_section, help_section) if section is not None)

        # sometimes the message is too big to send
        try:
            await self.bot.send_message(ctx.message.channel, message)
        except:
            num_results = sum(len(lines) for lines in results.values())
            log.exception('Something went wrong while trying to respond with {} results ({} characters)'.format(
                num_results, len(message)))
            await self.bot.add_reaction(ctx.message, u'😬')

    async def reload(self):
        self.mccq.reload(self.state.versions)

    async def mccreload(self, ctx: Context):
        try:
            await self.reload()

        except:
            log.exception('An unexpected error occurred while reloading commands')
            await self.bot.add_reaction(ctx.message, u'🤯')
            return

        await self.bot.react_success(ctx)

    @commands.command(pass_context=True, name='mccq', aliases=['mcc'], help=mccq_argparser.ARGPARSER.format_help())
    async def cmd_mcc(self, ctx: Context, *, command: str):
        await self.mcc(ctx, command)

    @checks.is_manager()
    @commands.command(pass_context=True, name='mccqreload', aliases=['mccreload'], hidden=True)
    async def cmd_mccreload(self, ctx):
        await self.mccreload(ctx)


def setup(bot):
    bot.add_cog(MCCQExtension(bot, __name__))
