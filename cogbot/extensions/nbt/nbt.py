import logging

from discord.ext import commands
from discord.ext.commands import Context

import nbtlib
import cogbot.extensions.nbt.errors

log = logging.getLogger(__name__)


class NBT:
    def __init__(self, bot):
        self.bot = bot
        self.available_schemas_message = \
            'Available schemas:\n' + '```' + ', '.join(schemas.entities.MAP.keys()) + '```'
        self.schema_messages = {
            schemastr: '```' + '\n'.join(
                tuple(f'*Everything from: {p.__name__}' for p in schema.inherit)
                + tuple(f'{k}: {v.__name__}' for k, v in schema.schema.items())
            ) + '```'
            for schemastr, schema in schemas.entities.MAP.items()}

    async def nbt(self, ctx: Context, nbtstring: str, schemastr: str = None):
        try:
            nbtobj = nbtlib.parse_nbt(nbtstring)

            if schemastr in schemas.entities.MAP:
                schema = schemas.entities.MAP[schemastr]

                try:
                    schema(nbtobj)

                except cogbot.extensions.nbt.errors.SchemaValidationError as e:
                    await self.bot.add_reaction(ctx.message, u'❌')
                    await self.bot.send_message(ctx.message.channel, f'Invalid schema: {str(e)}')
                    return

            elif schemastr:
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
    async def cmd_nbt(self, ctx: Context, *, nbtstring: str = ''):
        schema = None

        if not nbtstring.startswith('{'):
            tokens = nbtstring.split()
            schema = tokens[0] if len(tokens) > 0 else None
            nbtstring = tokens[1] if len(tokens) > 1 else None

        if nbtstring:
            await self.nbt(ctx, nbtstring, schema)
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
