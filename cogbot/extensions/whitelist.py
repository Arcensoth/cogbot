import logging
import typing

import discord

from cogbot.cog_bot import CogBot

log = logging.getLogger(__name__)


class Proto:
    def __init__(self, bot: CogBot, ext: str):
        self.bot: CogBot = bot
        self.options = bot.state.get_extension_state(ext)

    def get_role(self, server: discord.Server, role_id) -> discord.Role:
        for r in server.roles:
            if r.id == role_id:
                return r

    async def on_member_join(self, member: discord.Member):
        server: discord.Server = member.server
        whitelist = self.options.get(server.id, {}).get("whitelist", [])
        if member.id in whitelist:
            role_id = self.options.get(server.id, {}).get("role", [])
            role = self.get_role(server, role_id)
            log.info("Adding role {} to whitelisted member {}".format(role, member))
            await self.bot.add_roles(member, role)


def setup(bot):
    bot.add_cog(Proto(bot, __name__))
