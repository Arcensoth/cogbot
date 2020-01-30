import logging
import typing

import discord

from cogbot.cog_bot import CogBot, ServerId
from cogbot.extensions.helpchat.help_chat_server_state import HelpChatServerState

log = logging.getLogger(__name__)


class HelpChat:
    def __init__(self, bot: CogBot, ext: str):
        self.bot: CogBot = bot
        self.server_state: typing.Dict[ServerId, HelpChatServerState] = {}
        self.options = self.bot.state.get_extension_state(ext)

    def get_state(self, server: discord.Server) -> HelpChatServerState:
        return self.server_state.get(server.id)

    async def on_ready(self):
        # construct server state objects for easier context management
        for server_key, server_options in self.options.get("servers", {}).items():
            server = self.bot.get_server_from_key(server_key)
            if server:
                state = HelpChatServerState(self.bot, server, **server_options)
                self.server_state[server.id] = state

    async def on_reaction_add(
        self, reaction: discord.Reaction, reactor: discord.Member
    ):
        # make sure this isn't a DM
        if isinstance(reactor, discord.Member):
            state = self.get_state(reactor.server)
            # ignore bot's reactions
            if state and reactor != self.bot.user:
                await state.on_reaction(reaction, reactor)

    async def on_message(self, message: discord.Message):
        # make sure this isn't a DM
        if message.server:
            state = self.get_state(message.server)
            # ignore bot's messages
            if state and message.author != self.bot.user:
                await state.on_message(message)
