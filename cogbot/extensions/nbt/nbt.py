import logging

import nbtlib
from discord.ext import commands
from discord.ext.commands import Context

from cogbot.extensions.nbt.schema import SchemaValidationError
from . import schemas

log = logging.getLogger(__name__)

SCHEMAS = {
    'entity': schemas.entity.entity,
    'entity.area_effect_cloud': schemas.entity.area_effect_cloud,
    'aec': schemas.entity.area_effect_cloud,
    'common.effect': schemas.common.effect,
}


class NBT:
    def __init__(self, bot):
        self.bot = bot
        self.available_schemas_message = \
            'Available schemas (use `*` to skip):\n' + '```' + ', '.join(SCHEMAS.keys()) + '```'
        self.schema_messages = {
            schemastr: '```' + '\n'.join((f'{k}: {v.__name__}' for k, v in schema.schema.items())) + '```'
            for schemastr, schema in SCHEMAS.items()}

    async def nbt(self, ctx: Context, schemastr: str, nbtstring: str):
        try:
            nbtobj = nbtlib.parse_nbt(nbtstring)

            if schemastr == '*':
                pass

            elif schemastr in SCHEMAS:
                schema = SCHEMAS[schemastr]

                try:
                    schema(nbtobj)

                except SchemaValidationError as e:
                    await self.bot.add_reaction(ctx.message, u'❌')
                    await self.bot.send_message(ctx.message.channel, f'Invalid schema: {str(e)}')
                    return

            else:
                await self.bot.add_reaction(ctx.message, u'❓')
                await self.bot.send_message(ctx.message.channel, f'Unknown schema `{schemastr}`')
                return

            await self.bot.add_reaction(ctx.message, u'✅')

        except ValueError as e:
            await self.bot.add_reaction(ctx.message, u'❗')
            await self.bot.send_message(ctx.message.channel, f'Invalid NBT: {str(e)}')

        except:
            log.exception('An unexpected error occurred while parsing NBT: {}'.format(nbtstring))
            await self.bot.add_reaction(ctx.message, u'💩')

    @commands.command(pass_context=True, name='nbt')
    async def cmd_nbt(self, ctx: Context, schema: str = None, *, nbtstring: str = None):
        if nbtstring:
            await self.nbt(ctx, schema, nbtstring)
        elif schema:
            schema_message = self.schema_messages.get(schema)
            if not schema_message:
                await self.bot.add_reaction(ctx.message, u'❓')
                await self.bot.send_message(ctx.message.channel, f'Unknown schema `{schema}`')
                return
            await self.bot.send_message(ctx.message.channel, schema_message)
        else:
            await self.bot.send_message(ctx.message.channel, self.available_schemas_message)


def setup(bot):
    bot.add_cog(NBT(bot))
