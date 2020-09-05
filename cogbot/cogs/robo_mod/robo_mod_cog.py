from typing import Type

from discord import Member, Message
from discord.ext import commands
from discord.ext.commands import Context

from cogbot import checks
from cogbot.cogs.abc.base_cog import BaseCog
from cogbot.cogs.robo_mod.robo_mod_server_state import RoboModServerState


class RoboModCog(BaseCog[RoboModServerState]):
    @property
    def server_state_class(self) -> Type[RoboModServerState]:
        return RoboModServerState

    @checks.is_staff()
    @commands.group(name="robomod", aliases=["rb"], hidden=True, pass_context=True)
    async def cmd_robomod(self, ctx: Context):
        pass

    @cmd_robomod.command(name="rules", pass_context=True)
    async def cmd_robomod_rules(self, ctx: Context):
        message: Message = ctx.message
        author: Member = message.author
        if isinstance(author, Member):
            state = self.get_server_state(author.server)
            if state:
                await state.list_rules(ctx, author)

    @cmd_robomod.command(name="reload", pass_context=True)
    async def cmd_robomod_reload(self, ctx: Context):
        try:
            await self.reload()
            await self.bot.react_success(ctx)
        except:
            await self.bot.react_failure(ctx)
