import logging
import typing

import discord

from cogbot.cog_bot import CogBot

log = logging.getLogger(__name__)


class NickServerState:
    def __init__(self, bot: CogBot, server: discord.Server, enabled: bool = False):
        self.bot: CogBot = bot
        self.server: discord.Server = server
        self.enabled: bool = enabled


class Nick:
    def __init__(self, bot: CogBot, ext: str):
        self.bot: CogBot = bot
        self.server_state: typing.Dict[discord.Server, NickServerState] = {}
        self.options = self.bot.state.get_extension_state(ext)

    def get_state(self, server: discord.Server) -> NickServerState:
        return self.server_state.get(server)

    async def on_ready(self):
        # construct server state objects for easier context management
        for server_key, server_options in self.options.get("servers", {}).items():
            server = self.bot.get_server_from_key(server_key)
            if server:
                state = NickServerState(self.bot, server, **server_options)
                self.server_state[server] = state

    def needs_correction(self, nick: str) -> bool:
        return nick and nick.startswith("!")

    async def on_member_update(self, before: discord.Member, after: discord.Member):
        state = self.get_state(after.server)
        if state and state.enabled and self.needs_correction(after.nick):
            log.info(f"Correcting member nickname: {after.nick}")
            try:
                await self.bot.change_nickname(after, f"\u17b5{after.nick}")
            except:
                log.info(f"Couldn't correct member's nickname: {after.nick}")


def setup(bot):
    bot.add_cog(Nick(bot, __name__))
