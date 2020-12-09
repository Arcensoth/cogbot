import logging
import typing
from datetime import datetime, timedelta

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
        free_for_all: int = None,
    ):
        self.bot: CogBot = bot
        self.server: discord.Server = server
        self.roles: typing.List[discord.Role] = [
            self.bot.get_role(server, role_id) for role_id in roles
        ]
        self.emoji: typing.List[str] = emoji
        self.free_for_all: typing.Optional[timedelta] = timedelta(
            seconds=free_for_all
        ) if free_for_all is not None else None

    async def clean_up(self, reaction: discord.Reaction, reactor: discord.Member):
        message: discord.Message = reaction.message
        await self.bot.delete_message(message)
        await self.bot.mod_log(
            member=reactor,
            content=f"deleted a bot message from {message.channel.mention}",
            icon=":wastebasket:",
        )

    async def should_clean_up(self, reaction: discord.Reaction, reactor: discord.Member) -> bool:
        message: discord.Message = reaction.message
        author: discord.Member = message.author
        # check if this is one of the bot's messages and we care about the emoji
        if author == self.bot.user and reaction.emoji in self.emoji:
            # check if the free for all is enabled and the message is recent enough
            if self.free_for_all is not None:
                delta: timedelta = datetime.utcnow() - message.timestamp
                if delta <= self.free_for_all:
                    return True
            # check if the user has one of the elevated roles
            matching_roles = set(reactor.roles).intersection(self.roles)
            if matching_roles:
                return True
        return False

    async def on_reaction(self, reaction: discord.Reaction, reactor: discord.Member):
        if await self.should_clean_up(reaction, reactor):
            await self.clean_up(reaction, reactor)


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

    async def on_reaction_add(self, reaction: discord.Reaction, reactor: discord.Member):
        # make sure this isn't a DM
        if isinstance(reactor, discord.Member):
            state = self.get_state(reactor.server)
            # ignore bot's reactions
            if state and reactor != self.bot.user:
                await state.on_reaction(reaction, reactor)


def setup(bot):
    bot.add_cog(Custodian(bot, __name__))
