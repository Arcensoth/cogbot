import logging

from discord.ext import commands
from discord.ext.commands import Context
from discord.ext.commands.errors import *

from cogbot import checks
from cogbot.cog_bot import CogBot
from cogbot.extensions.groups.error import *
from cogbot.extensions.groups.group_directory import GroupDirectory

log = logging.getLogger(__name__)


class GroupsConfig:
    DEFAULT_COOLDOWN_RATE = 5
    DEFAULT_COOLDOWN_PER = 60

    def __init__(self, **options):
        self.cooldown_rate = options.pop('cooldown_rate', self.DEFAULT_COOLDOWN_RATE)
        self.cooldown_per = options.pop('cooldown_per', self.DEFAULT_COOLDOWN_PER)
        self.server_groups = options.pop('server_groups', {})


class Groups:
    def __init__(self, bot: CogBot, ext: str):
        self.bot = bot

        options = bot.state.get_extension_state(ext)
        self.config = GroupsConfig(**options)

        # TODO fix hack
        self.cmd_groups._buckets._cooldown.rate = self.config.cooldown_rate
        self.cmd_groups._buckets._cooldown.per = self.config.cooldown_per

        self._group_directory = GroupDirectory()

    async def on_ready(self):
        # Load initial groups after the bot has made associations with servers.
        # TODO sometimes runs multiple times, figure out a better way
        for server_id, groups in self.config.server_groups.items():
            server = self.bot.get_server(server_id)
            if server_id not in self._group_directory._role_map:
                for group in groups:
                    self._group_directory.add_group(server, group)

    async def add_group(self, ctx: Context, group: str):
        try:
            self._group_directory.add_group(ctx.message.server, group)
            log.info(f'[{ctx.message.server}/{ctx.message.author}] added group "{group}"')
            await self.bot.react_success(ctx)

        except NoSuchRoleNameError:
            raise UserInputError(f'tried to add group "{group}" without a role')

        except GroupAlreadyExistsError:
            raise UserInputError(f'tried to add pre-existing group "{group}"')

    async def remove_group(self, ctx: Context, group: str):
        try:
            self._group_directory.remove_group(ctx.message.server, group)
            log.info(f'[{ctx.message.server}/{ctx.message.author}] removed group "{group}"')
            await self.bot.react_success(ctx)

        except NoSuchGroupError:
            raise UserInputError(f'tried to remove non-existent group "{group}"')

    async def join_group(self, ctx: Context, group: str):
        try:
            role = self._group_directory.get_role(ctx.message.server, group)

            if role in ctx.message.author.roles:
                raise UserInputError(f'tried to join pre-joined group "{group}"')

            else:
                await self.bot.add_roles(ctx.message.author, role)
                log.info(f'[{ctx.message.server}/{ctx.message.author}] joined group "{group}"')
                await self.bot.react_success(ctx)

        except NoSuchGroupError:
            raise UserInputError(f'tried to join non-existent group "{group}"')

    async def leave_group(self, ctx: Context, group: str):
        try:
            role = self._group_directory.get_role(ctx.message.server, group)

            if role not in ctx.message.author.roles:
                raise UserInputError(f'tried to leave un-joined group "{group}"')

            else:
                await self.bot.remove_roles(ctx.message.author, role)
                log.info(f'[{ctx.message.server}/{ctx.message.author}] left group "{group}"')
                await self.bot.react_success(ctx)

        except NoSuchGroupError:
            raise UserInputError(f'cannot leave non-existent group "{group}"')

    async def list_groups(self, ctx: Context):
        groups = list(self._group_directory.groups(ctx.message.server))
        groups_str = ', '.join([('**' + group + '**') for group in groups])

        if groups:
            reply = f'Available groups: {groups_str}'

        else:
            reply = f'No groups available.'

        await self.bot.send_message(ctx.message.channel, reply)

    async def list_group_members(self, ctx: Context, group: str):
        try:
            members = self._group_directory.get_members(ctx.message.server, group)
            members_str = ', '.join([member.name for member in members])
            log.info('-> group members: ' + members_str)

            if members:
                reply = f'Group **{group}** has members: {members_str}'

            else:
                reply = f'Group **{group}** has no members.'

        except NoSuchGroupError:
            log.warning('-> group does not exist')
            reply = f'Group **{group}** does not exist.'

        await self.bot.send_message(ctx.message.channel, reply)

    @commands.cooldown(GroupsConfig.DEFAULT_COOLDOWN_RATE, GroupsConfig.DEFAULT_COOLDOWN_PER, commands.BucketType.user)
    @commands.group(pass_context=True, name='groups')
    async def cmd_groups(self, ctx: Context):
        if ctx.invoked_subcommand is None:
            await self.list_groups(ctx)

    @cmd_groups.command(pass_context=True, name='list')
    async def cmd_groups_list(self, ctx: Context, group: str = None):
        if group:
            await self.list_group_members(ctx, group)
        else:
            await self.list_groups(ctx)

    @cmd_groups.command(pass_context=True, name='join')
    async def cmd_groups_join(self, ctx: Context, group: str):
        await self.join_group(ctx, group)

    @cmd_groups.command(pass_context=True, name='leave')
    async def cmd_groups_leave(self, ctx: Context, group: str):
        await self.leave_group(ctx, group)

    @checks.is_moderator()
    @cmd_groups.command(pass_context=True, name='add', hidden=True)
    async def cmd_groups_add(self, ctx: Context, group: str):
        await self.add_group(ctx, group)

    @checks.is_moderator()
    @cmd_groups.command(pass_context=True, name='remove', hidden=True)
    async def cmd_groups_remove(self, ctx: Context, group: str):
        await self.remove_group(ctx, group)
