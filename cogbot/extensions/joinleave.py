import logging
import typing

import discord
from discord.ext import commands

from cogbot.cog_bot import CogBot, RoleId

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

    async def join(
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

    async def leave(
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


class JoinLeave:
    def __init__(self, bot: CogBot, ext: str):
        self.bot: CogBot = bot
        self.server_state: typing.Dict[discord.Server, JoinLeaveServerState] = {}
        self.options = self.bot.state.get_extension_state(ext)

    def get_state(self, server: discord.Server) -> JoinLeaveServerState:
        return self.server_state.get(server)

    async def on_ready(self):
        for server_key, server_options in self.options.get("servers", {}).items():
            server = self.bot.get_server_from_key(server_key)
            if server:
                state = JoinLeaveServerState(self.bot, server, **server_options)
                self.server_state[server] = state

    @commands.command(pass_context=True)
    async def join(self, ctx: commands.Context, *, role_name: str):
        message: discord.Message = ctx.message
        author: discord.Member = message.author
        if isinstance(author, discord.Member):
            state = self.get_state(author.server)
            if state:
                await state.join(ctx, author, role_name)

    @commands.command(pass_context=True)
    async def leave(self, ctx: commands.Context, *, role_name: str):
        message: discord.Message = ctx.message
        author: discord.Member = message.author
        if isinstance(author, discord.Member):
            state = self.get_state(author.server)
            if state:
                await state.leave(ctx, author, role_name)


def setup(bot):
    bot.add_cog(JoinLeave(bot, __name__))
