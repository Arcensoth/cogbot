import logging
import mccq.errors
from discord.ext import commands
from discord.ext.commands import Context
from mccq.query_manager import QueryManager
from mccq.version_database import VersionDatabase

from cogbot import checks
from cogbot.cog_bot import CogBot

log = logging.getLogger(__name__)


class MCCQExtensionState:
    # default to effectively no limit
    DEFAULT_COOLDOWN_RATE = 100
    DEFAULT_COOLDOWN_PER = 1

    def __init__(self, **options):
        # REQUIRED
        # path to server-generated data, structured like:
        # `<database>/<version>/generated/reports/commands.json`
        # can be a local filesystem folder or an internet url
        self.database = options['database']

        # path to the file containing nothing but the version of the generated files
        self.version_file = options.get('version_file', 'VERSION.txt')

        # labels to print instead of database keys
        self.version_labels = options.get('version_labels', {})

        # make sure a database is defined
        if not self.database:
            raise ValueError('A versions database location must be defined')

        # version whitelist, disabled if empty
        self.version_whitelist = tuple(options.get('version_whitelist', []))

        last_version = self.version_whitelist[-1] if self.version_whitelist else None

        # versions to render in the output by default
        # if not specified, defaults to the last whitelist entry
        self.show_versions = tuple(options.get('show_versions', [last_version] if last_version else ()))

        # url format to provide a help link, if any
        # the placeholder `{command}` will be replaced by the base command
        self.help_url = options.get('help_url', None)

        # max lines of results, useful to prevent potential chat spam
        self.max_results = options.get('max_results', None)

        # rate limiting
        self.cooldown_rate = options.get('cooldown_rate', self.DEFAULT_COOLDOWN_RATE)
        self.cooldown_per = options.get('cooldown_per', self.DEFAULT_COOLDOWN_PER)


class MCCQExtension:
    def __init__(self, bot: CogBot, ext: str):
        self.bot = bot
        self.state = MCCQExtensionState(**bot.state.get_extension_state(ext))
        self.query_manager = QueryManager(
            database=VersionDatabase(
                uri=self.state.database,
                version_file=self.state.version_file,
                whitelist=self.state.version_whitelist),
            show_versions=self.state.show_versions)

        # TODO fix hack
        self.cmd_mcc._buckets._cooldown.rate = self.state.cooldown_rate
        self.cmd_mcc._buckets._cooldown.per = self.state.cooldown_per

    def get_version_label(self, version: str) -> str:
        actual_version = self.query_manager.database.get_actual_version(version) or version
        return self.state.version_labels.get(version, version).format(version=version, actual=actual_version)

    async def mcc(self, ctx: Context, command: str):
        try:
            # get a copy of the parsed arguments so we can tell the user about them
            arguments = QueryManager.parse_query_arguments(command)

            # get the command results to render
            full_results = self.query_manager.results_from_arguments(arguments)
            num_full_results = sum(len(lines) for lines in full_results.values())

            # trim results, if enabled
            results = full_results
            num_trimmed_results = 0
            if self.state.max_results and (num_full_results > self.state.max_results):
                num_trimmed_results = num_full_results - self.state.max_results
                results = {}
                num_results = 0
                for version, lines in full_results.items():
                    results[version] = []
                    for line in lines:
                        results[version].append(line)
                        num_results += 1
                        if num_results == self.state.max_results:
                            break

        except mccq.errors.ArgumentParserFailed:
            log.info('Failed to parse arguments for the command: {}'.format(command))
            await self.bot.add_reaction(ctx.message, u'🤢')
            return

        except mccq.errors.NoVersionsAvailable:
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
            paragraphs = ('\n'.join(('# {}'.format(self.get_version_label(version)), *lines)) for version, lines in results.items())
            command_text = '\n'.join(paragraphs)

        # otherwise, if all versions rendered just 1 command, render one line per version (compact)
        else:
            command_text = '\n'.join(
                '{}  # {}'.format(lines[0], self.get_version_label(version)) for version, lines in results.items() if lines)

        # if results were trimmed, make note of them
        if num_trimmed_results:
            command_text += '\n# ... trimmed {} results'.format(num_trimmed_results)

        # render the full code section
        code_section = '```python\n{}\n```'.format(command_text)

        help_section = None

        # don't bother with the help link unless it's been configured
        if self.state.help_url:
            base_commands = set()
            for lines in results.values():
                for line in lines:
                    base_commands.add(line.split(maxsplit=1)[0])

            # only post the help link if we can unambiguously determine the base command
            base_command = tuple(base_commands)[0] if (len(base_commands) == 1) else None
            if base_command:
                help_section = ''.join(('<', self.state.help_url.format(command=base_command), '>'))

        # leave out blank sections
        message = '\n'.join(section for section in (code_section, help_section) if section is not None)

        # sometimes the message is too big to send
        try:
            await self.bot.send_message(ctx.message.channel, message)
        except:
            num_full_results = sum(len(lines) for lines in results.values())
            log.exception('Something went wrong while trying to respond with {} results ({} characters)'.format(
                num_full_results, len(message)))
            await self.bot.add_reaction(ctx.message, u'😬')

    async def reload(self):
        self.query_manager.reload()

    async def mccreload(self, ctx: Context):
        try:
            await self.reload()

        except:
            log.exception('An unexpected error occurred while reloading commands')
            await self.bot.add_reaction(ctx.message, u'🤯')
            return

        await self.bot.react_success(ctx)

    @commands.cooldown(
        MCCQExtensionState.DEFAULT_COOLDOWN_RATE, MCCQExtensionState.DEFAULT_COOLDOWN_PER, commands.BucketType.user)
    @commands.command(pass_context=True, name='mccq', aliases=['mcc'], help=QueryManager.ARGUMENT_PARSER.format_help())
    async def cmd_mcc(self, ctx: Context, *, command: str):
        await self.mcc(ctx, command)

    @checks.is_manager()
    @commands.command(pass_context=True, name='mccqreload', aliases=['mccreload'], hidden=True)
    async def cmd_mccreload(self, ctx):
        await self.mccreload(ctx)


def setup(bot):
    bot.add_cog(MCCQExtension(bot, __name__))
