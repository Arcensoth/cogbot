from datetime import datetime
from typing import Optional

from discord import Member

from cogbot.cogs.robo_mod.robo_mod_action import RoboModAction
from cogbot.cogs.robo_mod.robo_mod_action_log_entry import RoboModActionLogEntry
from cogbot.cogs.robo_mod.robo_mod_trigger import RoboModTrigger


class LogMemberUnbannedAction(RoboModAction):
    async def log(self, trigger: RoboModTrigger) -> Optional[RoboModActionLogEntry]:
        member: Member = trigger.member
        # Name
        name_str = f"{member}"
        # User ID
        user_id_str = f"{member.id}"
        return RoboModActionLogEntry(
            content=f"{member.mention} was unbanned.",
            fields={"Name": name_str, "User ID": user_id_str},
        )
