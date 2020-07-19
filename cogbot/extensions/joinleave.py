import logging
import typing

import discord
from discord.ext import commands

from cogbot import checks
from cogbot.cog_bot import CogBot, RoleId, ServerId

log = logging.getLogger(__name__)


class JoinLeaveRoleEntry:
    def __init__(self, role_id: RoleId, name: str, aliases: typing.List[str]):
        self.role_id: RoleId = role_id
        self.name: str = name
        self.aliases: typing.List[str] = [alias.lower() for alias in aliases]


class JoinLeaveServerState:
    def __init__(
        self,
        bot: CogBot,
        server: discord.Server,
        roles: typing.List[JoinLeaveRoleEntry],
    ):
        self.bot: CogBot = bot
        self.server: discord.Server = server
        self.role_entries: typing.List[JoinLeaveRoleEntry] = [
            JoinLeaveRoleEntry(**raw_role_entry) for raw_role_entry in roles
        ]
        self.role_entry_from_alias: typing.Dict[str, JoinLeaveRoleEntry] = {}
        for role_entry in self.role_entries:
            for role_alias in role_entry.aliases:
                self.role_entry_from_alias[role_alias] = role_entry

    async def on_init(self):
        log.info(
            f"Registered {len(self.role_entries)} self-assignable roles with {len(self.role_entry_from_alias)} aliases"
        )

    async def on_destroy(self):
        pass

    async def join_role(
        self, ctx: commands.Context, author: discord.Member, role_alias: str
    ):
        try:
            role_entry = self.role_entry_from_alias[role_alias.lower()]
            role = self.bot.get_role(self.server, role_entry.role_id)
            await self.bot.add_roles(author, role)
            await self.bot.say(f"{author.mention} has joined {role}")
        except:
            log.info(f"{author} failed to join the role: {role_alias}")
            await self.bot.react_question(ctx)

    async def leave_role(
        self, ctx: commands.Context, author: discord.Member, role_alias: str
    ):
        try:
            role_entry = self.role_entry_from_alias[role_alias]
            role = self.bot.get_role(self.server, role_entry.role_id)
            await self.bot.remove_roles(author, role)
            await self.bot.say(f"{author.mention} has left {role}")
        except:
            log.info(f"{author} failed to leave the role: {role_alias}")
            await self.bot.react_question(ctx)

    async def list_roles(self, ctx: commands.Context):
        role_lines = [
            f"{role_entry.role_id}  {role_entry.name}"
            for role_entry in self.role_entries
        ]
        roles_str = "\n".join(role_lines)
        await self.bot.say(f"Available self-assignable roles:\n```\n{roles_str}\n```")


class JoinLeave:
    def __init__(self, bot: CogBot, ext: str):
        self.bot: CogBot = bot
        self.ext: str = ext
        self.server_state: typing.Dict[ServerId, JoinLeaveServerState] = {}
        self.options = self.bot.state.get_extension_state(ext)
        self.server_options: typing.Dict[ServerId, typing.Any] = {}

    def get_state(self, server: discord.Server) -> JoinLeaveServerState:
        return self.server_state.get(server.id)

    def set_state(self, server: discord.Server, state: JoinLeaveServerState):
        self.server_state[server.id] = state

    def remove_state(self, server: discord.Server):
        if server.id in self.server_state:
            del self.server_state[server.id]

    async def create_state(
        self, server: discord.Server, server_options: dict
    ) -> JoinLeaveServerState:
        state = JoinLeaveServerState(self.bot, server, **server_options)
        self.set_state(server, state)
        await state.on_init()
        return state

    async def setup_state(self, server: discord.Server) -> JoinLeaveServerState:
        server_options = self.server_options[server.id]
        # if options is just a string, use remote/external location
        if isinstance(server_options, str):
            state_address = server_options
            try:
                log.info(
                    f"Loading state data for server {server} extension {self.ext} from: {state_address}"
                )
                actual_server_options = await self.bot.load_json(state_address)
                log.info(
                    f"Successfully loaded state data for server {server} extension {self.ext}"
                )
            except:
                log.exception(
                    f"Failed to load state data for server {server} extension {self.ext}; skipping..."
                )
                return
            state = await self.create_state(server, actual_server_options)
        # otherwise, use embedded/local config
        else:
            state = await self.create_state(server, server_options)
        return state

    async def reload(self):
        # destroy all existing server states
        for server_id, state in self.server_state.items():
            await state.on_destroy()
        # setup new server states
        for server_key, server_options in self.options.get("servers", {}).items():
            server = self.bot.get_server_from_key(server_key)
            if not server:
                log.error(f"Skipping unknown server {server_key}.")
                continue
            self.server_options[server.id] = server_options
            await self.setup_state(server)

    async def on_ready(self):
        await self.reload()

    @commands.command(pass_context=True)
    async def join(self, ctx: commands.Context, *, role_name: str):
        message: discord.Message = ctx.message
        author: discord.Member = message.author
        if isinstance(author, discord.Member):
            state = self.get_state(author.server)
            if state:
                await state.join_role(ctx, author, role_name)

    @commands.command(pass_context=True)
    async def leave(self, ctx: commands.Context, *, role_name: str):
        message: discord.Message = ctx.message
        author: discord.Member = message.author
        if isinstance(author, discord.Member):
            state = self.get_state(author.server)
            if state:
                await state.leave_role(ctx, author, role_name)

    @checks.is_staff()
    @commands.command(pass_context=True)
    async def roles(self, ctx: commands.Context):
        message: discord.Message = ctx.message
        author: discord.Member = message.author
        if isinstance(author, discord.Member):
            state = self.get_state(author.server)
            if state:
                await state.list_roles(ctx)

    @checks.is_staff()
    @commands.command(pass_context=True)
    async def rolereload(self, ctx: commands.Context):
        try:
            await self.reload()
            await self.bot.react_success(ctx)
        except:
            await self.bot.react_failure(ctx)


def setup(bot):
    bot.add_cog(JoinLeave(bot, __name__))
