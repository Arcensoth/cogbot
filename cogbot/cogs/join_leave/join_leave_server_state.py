from discord import Member, Role
from discord.ext.commands import Context

from cogbot.cogs.abc.base_cog import BaseCogServerState
from cogbot.cogs.join_leave.join_leave_options import JoinLeaveOptions


class JoinLeaveServerState(BaseCogServerState[JoinLeaveOptions]):
    async def create_options(self) -> JoinLeaveOptions:
        return await JoinLeaveOptions().init(self, self.raw_options)

    async def join_role(self, ctx: Context, author: Member, role_alias: str):
        try:
            role_entry = self.options.role_entry_from_alias[role_alias.lower()]
            role = self.bot.get_role(self.server, role_entry.role_id)
            await self.bot.add_roles(author, role)
            await self.bot.say(f"{author.mention} has joined {role}")
        except:
            self.log.info(f"{author} failed to join the role: {role_alias}")
            await self.bot.react_question(ctx)

    async def leave_role(self, ctx: Context, author: Member, role_alias: str):
        try:
            role_entry = self.options.role_entry_from_alias[role_alias]
            role = self.bot.get_role(self.server, role_entry.role_id)
            await self.bot.remove_roles(author, role)
            await self.bot.say(f"{author.mention} has left {role}")
        except:
            self.log.info(f"{author} failed to leave the role: {role_alias}")
            await self.bot.react_question(ctx)

    async def list_roles(self, ctx: Context, author: Member):
        role_lines = []
        for role_entry in self.options.role_entries:
            role: Role = self.bot.get_role(self.server, role_entry.role_id)
            role_lines.append(f"{role}")
            role_aliases = role_entry.aliases
            first_role_alias = role_aliases[0]
            other_role_aliases = role_aliases[1:]
            role_aliases_line = f"  >join {first_role_alias}"
            if other_role_aliases:
                other_role_aliases_str = " or ".join(
                    f'"{role_alias}"' for role_alias in other_role_aliases
                )
                role_aliases_line = f"{role_aliases_line} (or {other_role_aliases_str})"
            role_lines.append(role_aliases_line)
        roles_str = "\n".join(role_lines)
        await self.bot.say(
            f"{author.mention} Available self-assignable roles:\n```\n{roles_str}\n```"
        )
