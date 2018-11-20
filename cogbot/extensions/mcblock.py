import json
import logging
import typing
import urllib.request

from discord.ext import commands
from discord.ext.commands import CommandError, Context

from cogbot import checks
from cogbot.cog_bot import CogBot

log = logging.getLogger(__name__)

BlockPropertyKey = str
BlockPropertyValue = str
BlockName = str


class BlockProperty:
    def __init__(self, key: BlockPropertyKey, values: typing.Iterable[BlockPropertyValue]):
        self.key = key
        self.values: typing.Tuple[BlockPropertyValue] = tuple(values)


class Block:
    def __init__(self, name: BlockName, properties: typing.Optional[typing.Iterable[BlockProperty]]):
        self.name = name
        self.properties = properties


BlockMap = typing.Dict[BlockName, Block]


class McBlockConfig:
    def __init__(self, **options):
        self.database = options['database']


class McBlock:
    def __init__(self, bot: CogBot, ext: str):
        self.bot: CogBot = bot
        options = bot.state.get_extension_state(ext)
        self.config = McBlockConfig(**options)
        self.block_map: BlockMap = {}

    def reload_data(self):
        log.info('Reloading blocks from: {}'.format(self.config.database))

        response = urllib.request.urlopen(self.config.database)
        content = response.read().decode('utf8')

        try:
            data = json.loads(content)
        except Exception as e:
            raise CommandError('Failed to reload blocks: {}'.format(e))

        block_map: BlockMap = {}
        for block_name, block_obj in data.items():
            raw_properties = block_obj.get('properties', {})
            sorted_pks = sorted(pk for pk in raw_properties.keys())
            block_properties = tuple(BlockProperty(pk, raw_properties[pk]) for pk in sorted_pks)
            block_map[block_name] = Block(
                name=block_name,
                properties=block_properties
            )

        self.block_map = block_map

        log.info('Successfully reloaded {} blocks'.format(len(data)))

    async def on_ready(self):
        self.reload_data()

    def get_block(self, query: str) -> Block:
        return self.block_map.get(query) or self.block_map.get('minecraft:' + query)

    def make_response_lines(self, block: Block) -> typing.Iterable[str]:
        yield block.name
        if block.properties:
            yield ''
            keyjust = 1 + max(len(prop.key) for prop in block.properties)
            for prop in block.properties:
                yield ' '.join(('{}:'.format(prop.key).ljust(keyjust), ', '.join(prop.values)))

    def make_response(self, block: Block) -> str:
        return '```{}```'.format('\n'.join(self.make_response_lines(block)))

    @commands.command(pass_context=True, name='block')
    async def cmd_block(self, ctx: Context, *, query: str):
        block = self.get_block(query)
        if block:
            await self.bot.say(self.make_response(block))
        else:
            await self.bot.add_reaction(ctx.message, u'🤷')

    @checks.is_manager()
    @commands.command(pass_context=True, name='blockreload', hidden=True)
    async def cmd_invitereload(self, ctx: Context):
        try:
            self.reload_data()
            await self.bot.react_success(ctx)
        except:
            await self.bot.react_failure(ctx)


def setup(bot):
    bot.add_cog(McBlock(bot, __name__))
