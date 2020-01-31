import logging
import typing

from discord import Member, Server
from discord.ext import commands
from discord.ext.commands import Context
from discord.http import Route

from cogbot import checks
from cogbot.cog_bot import CogBot

log = logging.getLogger(__name__)


class Proto:
    def __init__(self, bot: CogBot, ext: str):
        self.bot: CogBot = bot
        self.options = bot.state.get_extension_state(ext)
        self.server_map: typing.Dict[str, Server] = {}
        self.bot_roles = {}

    async def on_ready(self):
        # load server map
        server_map = {}
        for server_key, server_obj in self.options["servers"].items():
            server_id = server_obj["id"]
            server = self.bot.get_server(server_id)
            if server:
                server_map[server_key] = server
            else:
                log.warning(
                    "Could not resolve server {} <{}>".format(server_key, server_id)
                )
        self.server_map = server_map

        # load bot roles

        role_id_to_role = {}
        bot_roles = {}

        for server_key, role_ids in self.options["bot_roles"].items():
            server = self.server_map.get(server_key)

            if not server:
                log.warning("Skipping unknown server {}".format(server_key))
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
                log.warning(
                    "Removing bot-only roles from {}#{}: {}".format(
                        member.name,
                        member.discriminator,
                        ", ".join(
                            "{} <{}>".format(role.name, role.id) for role in bad_roles
                        ),
                    )
                )
                await self.bot.remove_roles(member, *bad_roles)

    @checks.is_staff()
    @commands.command(pass_context=True, hidden=True)
    async def allpos(self, ctx: Context):
        sorted_channels = list(ctx.message.server.channels)
        sorted_channels.sort(key=lambda c: c.position)
        await self.bot.send_message(
            ctx.message.channel,
            "".join(
                ("```", "\n".join(f"{c.position}: {c}" for c in sorted_channels), "```")
            ),
        )

    @checks.is_staff()
    @commands.command(pass_context=True, hidden=True)
    async def getpos(self, ctx: Context):
        await self.bot.send_message(
            ctx.message.channel,
            f"Channel is in position {ctx.message.channel.position}",
        )

    @checks.is_staff()
    @commands.command(pass_context=True, hidden=True)
    async def setpos(self, ctx: Context, position: int):
        channel = ctx.message.channel
        old_position = channel.position
        await self.bot.move_channel(channel, position)
        new_position = channel.position
        await self.bot.send_message(
            channel, f"Moved channel from position {old_position} to {new_position}"
        )

    @checks.is_staff()
    @commands.command(pass_context=True, hidden=True)
    async def setcat(self, ctx: Context, category_id: str, position: int = None):
        await self.bot.move_channel_to_category(
            ctx.message.channel, self.bot.get_channel(category_id), position
        )
        await self.bot.react_success(ctx)


def setup(bot):
    bot.add_cog(Proto(bot, __name__))
