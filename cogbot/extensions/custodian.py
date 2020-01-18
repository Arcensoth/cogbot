import logging
import typing

import discord

from cogbot.cog_bot import CogBot, RoleId

log = logging.getLogger(__name__)


class CustodianServerState:
    def __init__(
        self,
        bot: CogBot,
        server: discord.Server,
        roles: typing.List[RoleId],
        emoji: typing.List[str] = ["❌"],
    ):
        self.bot: CogBot = bot
        self.server: discord.Server = server
        self.roles: typing.List[discord.Role] = [
            self.bot.get_role(server, role_id) for role_id in roles
        ]
        self.emoji: typing.List[str] = emoji

    async def on_reaction(self, reaction: discord.Reaction, reactor: discord.Member):
        # check if this is one of the emoji we care about
        if reaction.emoji in self.emoji:
            # check if the user has one of the elevated roles
            matching_roles = set(reactor.roles).intersection(self.roles)
            if matching_roles:
                await self.bot.delete_message(reaction.message)


class Custodian:
    def __init__(self, bot: CogBot, ext: str):
        self.bot: CogBot = bot
        self.server_state: typing.Dict[discord.Server, CustodianServerState] = {}
        self.options = self.bot.state.get_extension_state(ext)

    def get_state(self, server: discord.Server) -> CustodianServerState:
        return self.server_state.get(server)

    async def on_ready(self):
        for server_key, server_options in self.options.get("servers", {}).items():
            server = self.bot.get_server_from_key(server_key)
            if server:
                state = CustodianServerState(self.bot, server, **server_options)
                self.server_state[server] = state

    async def on_reaction_add(
        self, reaction: discord.Reaction, reactor: discord.Member
    ):
        # make sure this isn't a DM
        if isinstance(reactor, discord.Member):
            state = self.get_state(reactor.server)
            # ignore bot's reactions
            if state and reactor != self.bot.user:
                await state.on_reaction(reaction, reactor)


def setup(bot):
    bot.add_cog(Custodian(bot, __name__))
