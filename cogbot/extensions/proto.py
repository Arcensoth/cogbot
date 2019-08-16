import logging
import typing

from discord import Member, Server

from cogbot.cog_bot import CogBot

log = logging.getLogger(__name__)


class Proto:
    def __init__(self, bot: CogBot, ext: str):
        self.bot: CogBot = bot
        self.options = bot.state.get_extension_state(ext)
        self.server_map: typing.Dict[str: Server] = {}
        self.bot_roles = {}

    async def on_ready(self):
        # load server map
        server_map = {}
        for server_key, server_obj in self.options['servers'].items():
            server_id = server_obj['id']
            server = self.bot.get_server(server_id)
            if server:
                server_map[server_key] = server
            else:
                log.warning('Could not resolve server {} <{}>'.format(server_key, server_id))
        self.server_map = server_map

        # load bot roles

        role_id_to_role = {}
        bot_roles = {}

        for server_key, role_ids in self.options['bot_roles'].items():
            server = self.server_map.get(server_key)

            if not server:
                log.warning('Skipping unknown server {}'.format(server_key))
                continue

            bot_roles[server] = set()

            # map roles (why isn't this in discord.py?)
            role_id_to_role[server] = {role.id: role for role in server.roles}

            for role_id in role_ids:
                role = role_id_to_role[server][role_id]
                bot_roles[server].add(role)

        self.bot_roles = bot_roles

    async def on_member_update(self, member_before: Member, member: Member):
        if (not member.bot) and (member.server in self.bot_roles):
            bad_roles = self.bot_roles[member.server].intersection(member.roles)
            if bad_roles:
                log.warning('Removing bot-only roles from {}#{}: {}'.format(
                    member.name, member.discriminator, ', '.join('{} <{}>'.format(role.name, role.id) for role in bad_roles)))
                await self.bot.remove_roles(member, *bad_roles)


def setup(bot):
    bot.add_cog(Proto(bot, __name__))
