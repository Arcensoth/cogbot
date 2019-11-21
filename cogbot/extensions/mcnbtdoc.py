import json
import logging
import typing
import urllib.request

import shlex
import argparse

from discord.ext import commands
from discord.ext.commands import CommandError, Context

import discord
from discord import Embed
from discord import Color

from datetime import datetime, timedelta

from cogbot import checks
from cogbot.cog_bot import CogBot

import math

import asyncio

log = logging.getLogger(__name__)

class McNbtDocConfig:
    def __init__(self, **options):
        # Latest NBT database
        self.database = options['database']
        # Version specific database
        self.versions = options['version_database']
        # Time for an interactable embed to be deactivated
        self.active_limit: timedelta = timedelta(seconds=options['ac_limit'])
        # Limit for nuber of fields in an embed (and a `-s` query)
        self.field_limit: int = options['field_limit']
        # Limit for number of entries in a `-ns` query
        self.search_limit: int = options['search_limit']

INTRAVERSABLE = [
    'Byte', 'Short', 'Int', 'Long', 'Float', 'Double',
    'ByteArray', 'IntArray', 'LongArray',
    'Enum',
    'Id'
]

ENUM_VALS = [
    ('Byte', 'byte'), ('Short', 'short'), ('Int', 'int'), ('Long', 'long'),
    ('Float', 'float'), ('Double', 'double'),
    ('String', 'string')
]

NUM_VALS = [
    ('Byte', 'byte'), ('Short', 'short'), ('Int', 'int'), ('Long', 'long'),
    ('Float', 'float'), ('Double', 'double')
]

ARRAY_VALS = [
    ('ByteArray', 'byte'), ('IntArray', 'int'), ('LongArray', 'long')
]

class ErrorCatchingArgumentParser(argparse.ArgumentParser):
    def exit(self, status=0, message=None):
        if status:
            raise Exception()

parser = ErrorCatchingArgumentParser(
    prog='nbt',
    description='Query the NBT schema',
    add_help=False
)
parser.add_argument(
    'type',
    help='The type of the NBT target',
    choices=['item', 'block', 'entity'],
    nargs='?',
    action='store'
)
parser.add_argument(
    'name',
    help='The name of the NBT target. Must be something valid as a minecraft id',
    action='store',
    nargs='?'
)
parser.add_argument(
    '-p',
    '--path',
    dest='path',
    help='The path to the NBT. Should look like abc.def.ghi, where the parts are fields of a compound',
    default=None,
    action='store'
)
parser.add_argument(
    '-v', '--version',
    action='store',
    dest='version',
    help='The minecraft version of the NBT docs'
)
parser.add_argument(
    '-n', '--nbtdoc-path',
    action='store',
    dest='get_path',
    help='Get the nbtdoc path of an NBT item. Should look like abc::def::Ghi'
)
parser.add_argument(
    '-ns', '--nbtdoc-search',
    action='store',
    dest='nbt_search',
    help='Search up an nbtdoc name'
)
parser.add_argument(
    '-s', '--search',
    action='store',
    dest='search',
    help='Search for a compound field name'
)
help_template = '''
Command Help:
{}
Embed Interaction:
🔼: go to the super compound
🔽: go to the child compound that was perviously visited
▶: scroll the page right
◀: scroll the page left
'''

class McNbtDoc:
    '''
    Written specifically for this schema: https://github.com/MrYurihi/mc-nbtdoc
    '''

    def __init__(self, bot: CogBot, ext: str):
        self.bot: CogBot = bot
        options = bot.state.get_extension_state(ext)
        self.config = McNbtDocConfig(**options)
        self.data = {}
        self.version_data = {}
        self.active_embeds: typing.Dict[discord.Server, typing.Dict[str, ActiveEmbed]] = {}
        self.last_poll: datetime = datetime.utcnow()

    def reload_data(self):
        log.info('Reloading NBT schemas from: {}'.format(self.config.database))

        response = urllib.request.urlopen(self.config.database)
        try:
            self.data = json.loads(response.read().decode('utf8'))
            self.version_data = {}
        except Exception as e:
            raise CommandError('Failed to reload NBT schemas: {}'.format(e))

        log.info('Successfully reloaded NBT schemas')

    async def on_ready(self):
        self.reload_data()

    async def get_version(self, version: str, ctx: Context):
        if not version in self.version_data:
            log.info('Loading NBT schemas for version {}'.format(version))
            try:
                url = self.config.versions.format(version)
                res = urllib.request.urlopen(url)
                self.version_data[version] = json.loads(res.read().decode('utf8'))
                return True
            except json.JSONDecodeError as e:
                await self.bot.add_reaction(ctx.message, u'❗')
                raise CommandError('JSON decode error from loading schema at {}'.format(url))
            except urllib.request.URLError as e:
                log.error('URLError when loading schema at {}: {}'.format(url, e))
                return False
        return True

    async def get_from_reg(
        self,
        it: str,
        reg: str,
        ctx: Context,
        path: typing.List[str],
        version: typing.Optional[str] = None
    ):
        if version:
            await self.get_version(version, ctx)
            return await self.walk_from_reg(it, reg, self.version_data[version], path, ctx)
        else:
            return await self.walk_from_reg(it, reg, self.data, path, ctx)
    
    async def walk_from_reg(self, it: str, reg: str, data, path: typing.List[str], ctx: Context):
        registry = data['registries'][reg]
        if not registry:
            await self.bot.add_reaction(ctx.message, u'🤷')
            return None
        
        item = registry[0].get(it)
        if item == None:
            item = registry[1]

        if item == None:
            await self.bot.add_reaction(ctx.message, u'🤷')
            return None
        
        return await self.walk(data, { 'Compound': item }, path, ctx)
    
    async def get_from_path(self, data, curr, path: typing.List[str], ctx: Context):
        if len(path) == 0:
            return curr
        else:
            if 'Compound' in curr or 'Enum' in curr:
                await self.bot.add_reaction(ctx.message, u'❗')
                return None
            else:
                mod = data['module_arena'][curr['Module']]
                if path[0] in mod['children']:
                    return await self.get_from_path(data, mod['children'][path[0]], path[1:], ctx)
                else:
                    await self.bot.add_reaction(ctx.message, u'❌')
                    return None

    async def walk(self, data, curr, path: typing.List[str], ctx: Context):
        if len(path) == 0:
            return curr
        if curr == 'Boolean' or curr == 'String':
            await self.bot.add_reaction(ctx.message, u'❌')
            return None
        if 'Compound' in curr:
            cpd = data['compound_arena'][curr['Compound']]
            if path[0] in cpd['fields']:
                return await self.walk(data, cpd['fields'][path[0]]['nbttype'], path[1:], ctx)
            else:
                if 'supers' in cpd:
                    if cpd['supers'] == None:
                        return None
                    if 'Compound' in cpd['supers']:
                        return await self.walk(
                            data,
                            { 'Compound': cpd['supers']['Compound'] },
                            path,
                            ctx
                        )
                    elif 'Registry' in cpd['supers']:
                        return await self.walk(
                            data,
                            { 'Compound': data.registries[cpd['supers']['Registry']['target']][1] },
                            path,
                            ctx
                        )
                    else:
                        # This shouldn't happen
                        raise CommandError('Unknown key in {}'.format(cpd.supers))
                else:
                    await self.bot.add_reaction(ctx.message, u'🤷')
                    return None
        elif 'List' in curr:
            return await self.walk(data, curr['List']['value_type'], path, ctx)
        elif 'Index' in curr:
            return await self.walk(
                data,
                data['compound_arena'][
                    data['registries'][cpd['supers']['Registry']['target']][1]
                ],
                path,
                ctx
            )
        elif 'Or' in curr:
            for v in curr['Or']:
                val = await self.walk(data, v, path, ctx)
                if val:
                    return val
            await self.bot.add_reaction(ctx.message, u'❌')
            return None
        else:
            await self.bot.add_reaction(ctx.message, u'❌')
            return None

    @commands.command(pass_context=True, name='nbt', help=parser.format_help())
    async def cmd_nbt(self, ctx: Context, *, query: str):
        try:
            args = vars(parser.parse_args(shlex.split(query)))
        except:
            await self.bot.add_reaction(ctx.message, u'💩')
            return
        
        if args['version']:
            if await self.get_version(args['version'], ctx):
                data = self.version_data[args['version']]
            else:
                await self.bot.add_reaction(ctx.message, u'❗')
                return
        else:
            data = self.data
        
        if args['get_path']:
            item = await self.get_from_path(
                data,
                { 'Module': data['root_modules']['minecraft'] },
                args['get_path'].split('::'),
                ctx
            )
            if args['path']:
                path = args['path'].split('.')
            else:
                path = []
            item = await self.walk(data, item, path, ctx)
            title = args['get_path'].split('::')[-1]
        elif args['nbt_search']:
            s = args['nbt_search']
            matches = search_nbt(s, data['root_modules']['minecraft'], [], data)
            if len(matches) == 0:
                await self.bot.add_reaction(ctx.message, u'🤷‍♀️')
                return
            else:
                await self.bot.send_message(
                    ctx.message.channel,
                    'Found {} matches:\n{}{}'.format(
                        len(matches),
                        '\n'.join(['`{}`: {}'.format(
                            '::'.join(k),
                            'Compound' if 'Compound' in v else
                            'Module' if 'Module' in v else
                            'Enum' if 'Enum' in v else None
                        ) for k, v in matches[:self.config.search_limit]]),
                        '\nAnd {} more'.format(len(matches) - self.config.search_limit)
                            if len(matches) > self.config.search_limit else ''
                    )
                )
                return
        elif args['search']:
            matches = search_field(args['search'], data)
            if len(matches) == 0:
                await self.bot.add_reaction(ctx.message, u'🤷‍♀️')
                return
            else:
                await self.bot.send_message(
                    ctx.message.channel,
                    'Found {} matches:\n{}{}'.format(
                        len(matches),
                        '\n'.join([' * {} in `{}` with type {}'.format(
                            fn,
                            '::'.join(cn),
                            format_nbttype(fv['nbttype'], data).replace('\n', '\n    ')
                        ) for cn, fn, fv in matches[:self.config.field_limit]]),
                        '\nAnd {} more'.format(len(matches) - self.config.field_limit)
                            if len(matches) > self.config.field_limit else ''
                    )
                )
                return
        else:
            if not args['type'] or not args['name']:
                await self.bot.add_reaction(ctx.message, u'💩')
                return

            if args['path']:
                path = args['path'].split('.')
            else:
                path = []

            if not args['name'].startswith('minecraft:'):
                name = 'minecraft:{}'.format(args['name'])
            else:
                name = args['name']

            item = await self.get_from_reg(
                name,
                'minecraft:{}'.format(args['type']),
                ctx,
                path,
                version=args['version']
            )
            title = name
            if len(path) > 0:
                title = path[-1]
        ace = ActiveEmbed(None, item, data, self.config.field_limit, title, False, self.config.active_limit)
        if ace.should_scroll():
            msg = 'page {}'.format(ace.get_page_msg())
        else:
            msg = ''
        em = ace.get_embed()
        if em == None:
            await self.bot.add_reaction(ctx.message, u'❌')
            return
        thismsg = await self.bot.send_message(ctx.message.channel, content=msg, embed=em)
        ace.message = thismsg
        if not thismsg.channel.server in self.active_embeds:
            self.active_embeds[thismsg.channel.server] = {}
        self.active_embeds[thismsg.channel.server][str(thismsg.id)] = ace
        ace.remove_task_factory = lambda: remove_ae(
            str(thismsg.id),
            thismsg.channel.server,
            self,
            self.config.active_limit
        )
        ace.change_active()
        if ace.should_scroll():
            ace.is_scrolling = True
            await self.bot.add_reaction(thismsg, u'◀')
            await self.bot.add_reaction(thismsg, u'▶')
        await self.bot.add_reaction(thismsg, u'🔼')
        await self.bot.add_reaction(thismsg, u'🔽')

    @checks.is_manager()
    @commands.command(pass_context=True, name='nbtreload', hidden=True)
    async def cmd_nbtreload(self, ctx: Context):
        try:
            self.reload_data()
            await self.bot.react_success(ctx)
        except:
            await self.bot.react_failure(ctx)
    
    async def on_reaction_add(self, reaction: discord.Reaction, reactor: discord.Member):
        if isinstance(reactor, discord.Member):
            state = self.active_embeds.get(reactor.server, None)
            if state and reactor != self.bot.user:
                await self.bot.remove_reaction(reaction.message, reaction.emoji, reactor)
                if reaction.emoji == u'◀' or reaction.emoji == u'▶':
                    await self.scroll_embed(state, reaction.emoji == u'◀', reaction.message, reaction)
                elif reaction.emoji == u'🔼' or reaction.emoji == u'🔽':
                    await self.ro_embed(state, reaction.emoji == u'🔼', reaction.message, reaction)

    async def scroll_embed(self, state, left: bool, message: discord.Message, re: discord.Reaction):
        em = state.get(str(message.id), None)
        if em == None:
            return
        if left:
            if not em.dec_page():
                return
        else:
            if not em.inc_page():
                return
        await self.bot.edit_message(message, 'page {}'.format(em.get_page_msg()), embed=em.get_embed())

    async def ro_embed(self, state, sup: bool, message: discord.Message, re: discord.Reaction):
        em = state.get(str(message.id), None)
        if em == None:
            return
        if sup:
            if not em.inc_level():
                return
        else:
            if not em.dec_level():
                return
        if em.should_scroll():
            await self.bot.edit_message(
                message,
                new_content='page {}'.format(em.get_page_msg()),
                embed=em.get_embed()
            )
        else:
            await self.bot.edit_message(
                message,
                new_content=' ',
                embed=em.get_embed()
            )
        if em.should_scroll() and not em.is_scrolling:
            em.is_scrolling = True
            await self.bot.add_reaction(message, u'◀')
            await self.bot.add_reaction(message, u'▶')
        elif em.is_scrolling:
            em.is_scrolling = False
            await asyncio.gather(
                self.bot.remove_reaction(message, u'◀', message.server.me),
                self.bot.remove_reaction(message, u'▶', message.server.me)
            )

def format_len(val):
    if val[0] == val[1]:
        return '{}'.format(val[0])
    else:
        return '{} to {}'.format(val[0], val[1])

def format_nbttype(val, data):
    if 'Boolean' == val:
        return 'byte: 0 or 1'
    elif 'String' == val:
        return 'string'
    elif 'Compound' in val:
        return 'Compound `{}`'.format('::'.join(find_index_locs(
            val['Compound'],
            'Compound',
            data['module_arena'][data['root_modules']['minecraft']],
            data,
            []
        )))
    elif 'List' in val:
        if val['List']['length_range'] != None:
            return 'List[{}] with length {}'.format(
                format_nbttype(val['List']['value_type'], data),
                format_len(val['List']['length_range'])
            )
        else:
            return 'List[{}]'.format(format_nbttype(val['List']['value_type'], data))
    elif 'Or' in val:
        if len(val['Or']) == 0:
            return None
        return '({})'.format(' OR '.join([format_nbttype(x, data) for x in val['Or']]))
    elif 'Id' in val:
        return 'Id in {}'.format(val['Id'])
    elif 'Enum' in val:
        enum = data['enum_arena'][val['Enum']]['et']
        for k, n in ENUM_VALS:
            if k in enum:
                if len(enum[k]) == 0:
                    out = 'impossible'
                else:
                    ls = [x['value'] for x in enum[k].values()]
                    if type(ls[0]) is int:
                        ls.sort()
                        ls = [str(x) for x in ls]
                    out = '{}\none of: `{}`'.format(
                        n,
                        '`, `'.join(ls)
                    )
                return '{}\nenum: `{}`'.format(out, '::'.join(find_index_locs(
                    val['Enum'],
                    'Enum',
                    data['module_arena'][data['root_modules']['minecraft']],
                    data,
                    []
                )))
    elif 'Index' in val:
        return 'Values from {} using tag `{}`'.format(
            val['Index']['target'],
            format_nbtpath(val['Index']['path'])
        )
    else:
        for k, n in NUM_VALS:
            if k in val:
                if val[k]['range'] != None:
                    return '{} in {}'.format(
                        n,
                        format_len(val[k]['range'])
                    )
                else:
                    return n
        for k, n in ARRAY_VALS:
            if k in val:
                lct = ' and'
                if val[k]['length_range'] != None:
                    lr = ' with length {}'.format(
                        format_len(val[k]['length_range'])
                    )
                else:
                    lr = ''
                    lct = ''
                if val[k]['value_range'] != None:
                    vr = ' with values in {}'.format(
                        format_len(val[k]['value_range'])
                    )
                    vrt = True
                else:
                    vr = ''
                    lct = ''
                return '{} array{}{}{}'.format(n, vr, lct, lr)

def find_index_locs(idx, ty, module, data, out):
    for k in module['children']:
        v = module['children'][k]
        if ty in v:
            ci = v[ty]
            if ci == idx:
                return [*out, k]
        if 'Module' in v:
            v = find_index_locs(idx, ty, data['module_arena'][v['Module']], data, [*out, k])
            if v != None:
                return v
    return None

def format_nbtpath(p):
    vals = []
    for x in p:
        if x == 'Super':
            vals.append('super')
        else:
            vals.append(x['Child'])
    return '.'.join(vals)

async def remove_ae(ae: str, server: discord.Server, mcnbtdoc: McNbtDoc, dt: timedelta):
    try:
        await asyncio.sleep(dt.total_seconds())
    except asyncio.CancelledError:
        ace = mcnbtdoc.active_embeds[server][ae]
    if ace.no_delete > 0:
        ace.no_delete -= 1
    else:
        del mcnbtdoc.active_embeds[server][ae]

class ActiveEmbed:
    def __init__(
        self,
        m: discord.Message,
        src,
        data,
        fl: int,
        title: str,
        scrolling: bool,
        time_limit: timedelta
    ):
        self.page = 0
        self.level = 0
        self.message = m
        self.tl = time_limit
        self.fl = fl
        self.data = data
        self.cached_embeds: typing.List[ProtoEmbed] = []
        self.cached_nbttype = [src]
        self.title = title
        self.is_scrolling = scrolling
        # Delete counter so multiple queued requests should work out
        self.no_delete = 0
        self.remove_task: typing.Optional[asyncio.Task] = None
        self.remove_task_factory: typing.Optional[typing.Any] = None

    def change_active(self):
        if self.remove_task:
            self.no_delete += 1
            self.remove_task.cancel()
        if self.remove_task_factory:
            self.remove_task = asyncio.get_event_loop().create_task(self.remove_task_factory())

    def get_current_item(self):
        # there should always be at least one
        if len(self.cached_nbttype) == self.level:
            last_item = self.cached_nbttype[self.level - 1]
            if last_item == 'String' or last_item == 'Boolean':
                return None
            elif 'Compound' in last_item:
                cpd = self.data['compound_arena'][last_item['Compound']]
                if cpd['supers'] != None:
                    if 'Compound' in cpd['supers']:
                        self.cached_nbttype.append({ 'Compound': cpd['supers']['Compound'] })
                    elif 'Registry' in cpd['supers']:
                        self.cached_nbttype.append({
                            'Compound': self.data['registries'][cpd['supers']['Registry']['target']][1]
                        })
        elif len(self.cached_nbttype) < self.level:
            raise CommandError("The level is too high")
        if len(self.cached_nbttype) <= self.level:
            return None
        return self.cached_nbttype[self.level]

    def get_embed(self):
        em = self.get_proto_embed()
        if em == None:
            return None
        # Number of regular fields per page
        p_len = max(1, self.fl - len(em.persist_fields))
        fmin = self.page * p_len
        fmax = min(self.page * p_len + p_len, len(em.fields))
        out = Embed(
            title=em.title,
            description=em.desc,
            color=0x00aced
        )
        out.set_author(name=em.author)
        out.set_footer(text=em.footer)
        for x in em.fields[fmin:fmax]:
            out.add_field(name=x.name, value=x.value, inline=x.inline)
        
        for x in em.persist_fields:
            out.add_field(name=x.name, value=x.value, inline=x.inline)

        return out

    def get_proto_embed(self):
        if self.level < len(self.cached_embeds):
            return self.cached_embeds[self.level]
        item = self.get_current_item()
        if item == None:
            return None
        if item == 'String':
            embed = ProtoEmbed(title=self.title, author='string')
        elif item == 'Boolean':
            embed = ProtoEmbed(title=self.title, author='byte', description='0 or 1')
        elif 'Compound' in item:
            cpd = self.data['compound_arena'][item['Compound']]
            embed = ProtoEmbed(title=self.title, desc=cpd['description'])
            embed.footer = '::'.join(find_index_locs(
                item['Compound'],
                'Compound',
                self.data['module_arena'][self.data['root_modules']['minecraft']],
                self.data,
                []
            ))
            for k, v in cpd['fields'].items():
                nbttype = format_nbttype(v['nbttype'], self.data)
                if nbttype == None:
                    continue
                embed.fields.append(
                    ProtoEmbedField(
                        name='`{}`'.format(k),
                        value='{}\n\n{}'.format(
                            v['description'],
                            nbttype
                        )
                    )
                )
                embed.fields.sort(key=lambda x: x.name)
            if cpd['supers'] != None:
                if 'Compound' in cpd['supers']:
                    embed.persist_fields.append(
                        ProtoEmbedField(
                            name='__**Super Compound**__',
                            value='`' + '::'.join(find_index_locs(
                                cpd['supers']['Compound'],
                                'Compound',
                                self.data['module_arena'][self.data['root_modules']['minecraft']],
                                self.data,
                                []
                            )) + '`',
                            inline=False
                        )
                    )
                elif 'Registry' in cpd['supers']:
                    vals = []
                    for x in cpd['supers']['Registry']['path']:
                        if x == 'Super':
                            vals.append('super')
                        else:
                            vals.append(x['Child'])
                    embed.persist_fields.append(
                        ProtoEmbedField(
                            name='__*Super Compound**__',
                            value='Values from {} using tag `{}`'.format(
                                cpd['supers']['Registry']['target'],
                                '.'.join(vals)
                            ),
                            inline=False
                        )
                    )
        elif 'Enum' in item:
            en = self.data['enum_arena'][item['Enum']]
            embed = ProtoEmbed(title=self.title, desc=en['description'])
            embed.footer = '::'.join(find_index_locs(
                item['Enum'],
                'Enum',
                self.data['module_arena'][self.data['root_modules']['minecraft']],
                self.data,
                []
            ))
            enum = en['et']
            for k, n in ENUM_VALS:
                if k in enum:
                    embed.author = n
                    ls = [(key, x['description'], x['value']) for key, x in enum[k].items()]
                    if type(ls[0][2]) is int:
                        ls = [(name, desc, str(x)) for name, desc, x in sorted(ls, key=lambda v: v[2])]
                    else:
                        ls.sort(key=lambda v: v[2])
                    for name, desc, v in ls:
                        embed.fields.append(ProtoEmbedField(name=name, value='{}\n{}'.format(desc, v)))
        elif 'List' in item:
            embed = ProtoEmbed(title=self.title)
            embed.persist_fields.append(
                ProtoEmbedField(
                    name='List Item Type',
                    value=format_nbttype(item['List']['value_type'], self.data)
                )
            )
            if item['List']['length_range']:
                embed.persist_fields.append(
                    ProtoEmbedField(
                        name='Length Range',
                        value=format_len(item['List']['length_range'], item['List']['length_range'])
                    )
                )
        elif 'Index' in item:
            embed = ProtoEmbed(title=self.title)
            embed.persist_fields.append(
                ProtoEmbedField(name='Target Registry', value=item['Index']['target'])
            )
            embed.persist_fields.append(
                ProtoEmbedField(name='NBT Data Path', value=format_nbtpath(item['Index']['path']))
            )
        elif 'Id' in item:
            embed = ProtoEmbed(title=self.title)
            embed.persist_fields.append(
                ProtoEmbedField(name='Target Registry', value=item['Id'])
            )
        elif 'Or' in item:
            embed = ProtoEmbed(title=self.title)
            for x in item['Or']:
                embed.fields.append(
                    ProtoEmbedField(name='', value=format_nbttype(x, data))
                )
                embed.fields.sort(key=lambda x: x.name)
        else:
            embed = ProtoEmbed(title=self.title)
            for k, n in NUM_VALS:
                if k in item:
                    embed.author = n
                    if item[k]['range'] != None:
                        embed.persist_fields.append(
                            ProtoEmbed(
                                name='Value Range',
                                value=format_len(item[k]['range'])
                            )
                        )
            for k, n in ARRAY_VALS:
                if k in item:
                    embed.author = '{} array'.format(n)
                    if item[k]['length_range'] != None:
                        embed.persist_fields.append(
                            ProtoEmbed(
                                name='Length Range',
                                value=format_len(item[k]['length_range'])
                            )
                        )
                    
                    if item[k]['value_range'] != None:
                        embed.persist_fields.append(
                            ProtoEmbed(
                                name='Value Range',
                                value=format_len(item[k]['value_range'])
                            )
                        )
        self.cached_embeds.append(embed)
        return embed

    def get_page_msg(self):
        em = self.get_proto_embed()
        p_len = max(1, self.fl - len(em.persist_fields))
        return '{}/{}'.format(
            self.page + 1,
            math.ceil(len(em.fields) / p_len)
        )
    
    def inc_page(self):
        self.change_active()
        pem = self.get_proto_embed()
        if (self.page + 1) * (self.fl - len(pem.persist_fields)) >= len(pem.fields):
            return False
        else:
            self.page += 1
            return True
    
    def dec_page(self):
        self.change_active()
        if self.page <= 0:
            return False
        else:
            self.page -= 1
            return True

    def inc_level(self):
        self.change_active()
        self.level += 1
        if self.get_proto_embed() == None:
            self.level -= 1
            return False
        else:
            self.page = 0
            return True
    
    def dec_level(self):
        self.change_active()
        if self.level <= 0:
            return False
        else:
            self.level -= 1
            self.page = 0
            return True

    def should_scroll(self):
        pe = self.get_proto_embed()
        if pe == None:
            return False
        flen = len(pe.fields)
        pflen = len(pe.persist_fields)
        out = (flen + pflen) > self.fl
        return out

class ProtoEmbedField:
    def __init__(self, *, name: str, value: str, inline=True):
        self.name = name
        self.value = value
        self.inline = inline

class ProtoEmbed:
    def __init__(self, *, title='', desc='', footer='', author='', fields=None, persist_fields=None):
        self.title = title
        self.desc = desc
        self.footer = footer
        self.author = author
        if fields == None:
            self.fields = []
        else:
            self.fields = fields
        if persist_fields == None:
            self.persist_fields = []
        else:
            self.persist_fields = fields

def search_nbt(val: str, module: int, mpath: typing.List[str], data):
    out = []
    for k, v in data['module_arena'][module]['children'].items():
        if val.lower() in k.lower():
            out.append(([*mpath, k], v))
        if 'Module' in v:
            out.extend(search_nbt(val, v['Module'], [*mpath, k], data))
    return out

def search_field(val: str, data):
    out = []
    for i, x in enumerate(data['compound_arena']):
        for k, v in x['fields'].items():
            if val.lower() in k.lower():
                out.append((
                    find_index_locs(
                        i,
                        'Compound',
                        data['module_arena'][data['root_modules']['minecraft']],
                        data,
                        []
                    ),
                    k,
                    v
                ))
    return out


def setup(bot):
    bot.add_cog(McNbtDoc(bot, __name__))
