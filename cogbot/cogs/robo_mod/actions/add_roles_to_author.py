from typing import List, Set

from discord.role import Role

from cogbot.cogs.robo_mod.robo_mod_action import RoboModAction
from cogbot.cogs.robo_mod.robo_mod_trigger import RoboModTrigger
from cogbot.types import ChannelId, RoleId


class AddRolesToAuthorAction(RoboModAction):
    def __init__(self):
        self.role_ids: Set[RoleId]
        self.log_to_channel: ChannelId

    async def update(self, state: "RoboModServerState", data: dict):
        self.role_ids = set(data["roles"])
        self.log_to_channel = data.get("log_to_channel", None)

    async def apply(self, trigger: RoboModTrigger):
        roles = list(trigger.bot.get_roles(trigger.state.server, self.role_ids))
        await trigger.bot.add_roles(trigger.author, *roles)
        if self.log_to_channel:
            roles_str = " ".join([f"{role.mention}" for role in roles])
            await trigger.bot.send_message(
                trigger.bot.get_channel(self.log_to_channel),
                content=f"The following roles were added to {trigger.author.mention} according to rule `{trigger.rule.name}`: {roles_str}",
            )
