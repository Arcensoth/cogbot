from typing import Type

from discord import Member, Message
from discord.ext import commands
from discord.ext.commands import Context

from cogbot import checks
from cogbot.cogs.abc.base_cog import BaseCog
from cogbot.cogs.join_leave.join_leave_server_state import JoinLeaveServerState


class JoinLeaveCog(BaseCog[JoinLeaveServerState]):
    @property
    def server_state_class(self) -> Type[JoinLeaveServerState]:
        return JoinLeaveServerState

    @commands.command(pass_context=True)
    async def join(self, ctx: Context, *, role_name: str):
        message: Message = ctx.message
        author: Member = message.author
        if isinstance(author, Member):
            state = self.get_server_state(author.server)
            if state:
                await state.join_role(ctx, author, role_name)

    @commands.command(pass_context=True)
    async def leave(self, ctx: Context, *, role_name: str):
        message: Message = ctx.message
        author: Member = message.author
        if isinstance(author, Member):
            state = self.get_server_state(author.server)
            if state:
                await state.leave_role(ctx, author, role_name)

    @commands.command(pass_context=True)
    async def roles(self, ctx: Context):
        message: Message = ctx.message
        author: Member = message.author
        if isinstance(author, Member):
            state = self.get_server_state(author.server)
            if state:
                await state.list_roles(ctx, author)

    @checks.is_staff()
    @commands.command(pass_context=True)
    async def rolereload(self, ctx: Context):
        try:
            await self.reload()
            await self.bot.react_success(ctx)
        except:
            await self.bot.react_failure(ctx)
