from datetime import datetime
from typing import Optional

from discord import Member

from cogbot.cogs.robo_mod.robo_mod_action import RoboModAction
from cogbot.cogs.robo_mod.robo_mod_action_log_entry import RoboModActionLogEntry
from cogbot.cogs.robo_mod.robo_mod_trigger import RoboModTrigger


class LogMemberLeftAction(RoboModAction):
    async def log(self, trigger: RoboModTrigger) -> Optional[RoboModActionLogEntry]:
        member: Member = trigger.member
        # Name
        name_str = f"{member}"
        # ID
        id_str = f"{member.id}"
        # Member for
        now = datetime.utcnow()
        member_for = now - member.joined_at
        member_for_str = f"{member_for.days} days"
        if member_for.days < 7:
            hh = int(member_for.total_seconds() / 3600)
            mm = int(member_for.total_seconds() / 60) % 60
            member_for_str = f"{hh} hours, {mm} minutes"
        return RoboModActionLogEntry(
            content=f"Goodbye! {member.mention} has left the server.",
            fields={"Name": name_str, "ID": id_str, "Member for": member_for_str},
        )
