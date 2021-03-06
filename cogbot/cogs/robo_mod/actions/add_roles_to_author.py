from typing import List, Optional, Set

from discord import Member, Role

from cogbot.cogs.robo_mod.robo_mod_action import RoboModAction
from cogbot.cogs.robo_mod.robo_mod_action_log_entry import RoboModActionLogEntry
from cogbot.cogs.robo_mod.robo_mod_trigger import RoboModTrigger
from cogbot.types import RoleId


class AddRolesToAuthorAction(RoboModAction):
    def __init__(self):
        self.role_ids: Set[RoleId] = None

    async def update(self, state: "RoboModServerState", data: dict):
        self.role_ids = set(data["roles"])

    async def log(self, trigger: RoboModTrigger) -> Optional[RoboModActionLogEntry]:
        member: Member = trigger.member
        # Name
        name_str = f"{member}"
        # User ID
        user_id_str = f"{member.id}"
        # Roles
        roles = self.get_roles(trigger)
        roles_str = " ".join([f"{role.mention}" for role in roles])
        plural = "roles" if len(roles) > 1 else "role"
        return RoboModActionLogEntry(
            content=f"Added {plural} {roles_str} to {trigger.author.mention}.",
            fields={"Name": name_str, "User ID": user_id_str},
        )

    async def apply(self, trigger: RoboModTrigger):
        roles = self.get_roles(trigger)
        await trigger.bot.add_roles(trigger.author, *roles)

    def get_roles(self, trigger: RoboModTrigger) -> List[Role]:
        return list(trigger.bot.get_roles(trigger.state.server, self.role_ids))
