from discord import Member, Message, Reaction, Server
from discord.ext.commands import Context

from cogbot.cogs.abc.base_cog import BaseCogServerState
from cogbot.cogs.robo_mod.robo_mod_options import RoboModOptions
from cogbot.cogs.robo_mod.robo_mod_trigger_type import RoboModTriggerType
from cogbot.cogs.robo_mod.triggers import make_trigger


class RoboModServerState(BaseCogServerState[RoboModOptions]):
    async def create_options(self) -> RoboModOptions:
        return await RoboModOptions().init(self, self.raw_options)

    async def list_rules(self, ctx: Context, author: Member):
        lines = []
        for rule in self.options.rules:
            lines.append(f"[{rule.name}] {rule.description}")
            lines.append(f"  Trigger type: {rule.trigger_type.name}")
            lines.append(f"  Conditions:")
            for condition in rule.conditions:
                lines.append(f"    - {condition}")
            lines.append(f"  Actions:")
            for action in rule.actions:
                lines.append(f"    - {action}")
        lines_str = "\n".join(lines)
        await self.bot.say(f"{author.mention} Rules:\n```\n{lines_str}\n```")

    async def do_trigger(self, trigger_type: RoboModTriggerType, **kwargs):
        rules = self.options.rules_by_trigger_type.get(trigger_type, [])
        for rule in rules:
            trigger = await make_trigger(self, rule, trigger_type, **kwargs)
            await rule.run(trigger)

    async def on_message(self, message: Message):
        await self.do_trigger(RoboModTriggerType.MESSAGE_SENT, message=message)

    async def on_message_delete(self, message: Message):
        await self.do_trigger(RoboModTriggerType.MESSAGE_DELETED, message=message)

    async def on_reaction(self, reaction: Reaction, reactor: Member):
        await self.do_trigger(
            RoboModTriggerType.REACTION_ADDED, reaction=reaction, reactor=reactor
        )

    async def on_member_join(self, member: Member):
        await self.do_trigger(RoboModTriggerType.MEMBER_JOINED, member=member)

    async def on_member_remove(self, member: Member):
        await self.do_trigger(RoboModTriggerType.MEMBER_LEFT, member=member)

    async def on_member_ban(self, member: Member):
        await self.do_trigger(RoboModTriggerType.MEMBER_BANNED, member=member)

    async def on_member_unban(self, server: Server, member: Member):
        await self.do_trigger(
            RoboModTriggerType.MEMBER_UNBANNED, server=server, member=member
        )
