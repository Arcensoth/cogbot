import json
import logging
import typing
import urllib.request

from discord.ext import commands
from discord.ext.commands import CommandError, Context

from cogbot import checks
from cogbot.cog_bot import CogBot

log = logging.getLogger(__name__)

NbtNode = typing.Dict


class McNbtPathsConfig:
    def __init__(self, **options):
        self.database = options['database']


class McNbtPaths:
    """
    Written specifically for this schema: https://github.com/MrYurihi/mc-nbt-paths
    """

    def __init__(self, bot: CogBot, ext: str):
        self.bot: CogBot = bot
        options = bot.state.get_extension_state(ext)
        self.config = McNbtPathsConfig(**options)
        self.data: typing.Dict[str, NbtNode] = {}

    def reload_data(self):
        log.info('Reloading NBT schemas from: {}'.format(self.config.database))

        response = urllib.request.urlopen(self.config.database)
        content = response.read().decode('utf8')

        try:
            data = json.loads(content)
        except Exception as e:
            raise CommandError('Failed to reload NBT schemas: {}'.format(e))

        self.data = data

        log.info('Successfully reloaded {} NBT schemas'.format(len(data)))

    async def on_ready(self):
        self.reload_data()

    def get_node(self, query: str) -> NbtNode:
        # try a bunch of things by cascading through common queries
        return self.data.get(query) \
               or self.data.get(query + '.json') \
               or self.data.get('ref/' + query + '.json') \
               or self.data.get('entity/' + query + '.json') \
               or self.data.get('block/' + query + '.json')

    def key_to_query(self, key: str) -> str:
        return key.split('/')[-1][:-5]

    def make_response_lines(self, query: str) -> typing.Iterable[str]:
        node = self.get_node(query)

        children = node.get('children', {}).items()
        keyjust = 1 + max(len(key) for key, child in children)
        kindjust = 2 + max(len(child.get('type', '')) for key, child in children)

        for key, child in children:
            kind = child.get('type')
            description = child.get('description')
            # TODO recurse compounds and lists
            if kind and description:
                yield ' '.join(('({})'.format(kind).ljust(kindjust), '{}:'.format(key).ljust(keyjust), description))
            elif kind:
                yield ' '.join(('({})'.format(kind).ljust(kindjust), '{}:'.format(key)))

        refkeys = node.get('child_ref', ())
        if refkeys:
            yield ''
            for refkey in refkeys:
                yield '+ ' + self.key_to_query(refkey)

    def make_response(self, query: str) -> str:
        return '```{}```'.format('\n'.join(self.make_response_lines(query)))

    @commands.command(pass_context=True, name='nbt')
    async def cmd_nbt(self, ctx: Context, *, query: str):
        if self.get_node(query):
            await self.bot.say(self.make_response(query))
        else:
            await self.bot.add_reaction(ctx.message, u'🤷')

    @checks.is_manager()
    @commands.command(pass_context=True, name='nbtreload', hidden=True)
    async def cmd_invitereload(self, ctx: Context):
        try:
            self.reload_data()
            await self.bot.react_success(ctx)
        except:
            await self.bot.react_failure(ctx)


def setup(bot):
    bot.add_cog(McNbtPaths(bot, __name__))
