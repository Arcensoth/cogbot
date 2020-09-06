from datetime import datetime
from typing import Optional

from discord import Member

from cogbot.cogs.robo_mod.robo_mod_action import RoboModAction
from cogbot.cogs.robo_mod.robo_mod_action_log_entry import RoboModActionLogEntry
from cogbot.cogs.robo_mod.robo_mod_trigger import RoboModTrigger


class LogMemberJoinedAction(RoboModAction):
    async def log(self, trigger: RoboModTrigger) -> Optional[RoboModActionLogEntry]:
        member: Member = trigger.member
        # Name
        name_str = f"{member}"
        # ID
        id_str = f"{member.id}"
        # Joined on
        joined_on_str = member.joined_at.strftime("%Y/%m/%d at %H:%M:%S UTC")
        # Account age
        now = datetime.utcnow()
        account_age = now - member.created_at
        account_age_str = f"{account_age.days} days"
        if account_age.days < 7:
            hh = int(account_age.total_seconds() / 3600)
            mm = int(account_age.total_seconds() / 60) % 60
            account_age_str = f"{hh} hours, {mm} minutes"
        return RoboModActionLogEntry(
            content=f"Hello! {member.mention} has joined the server.",
            fields={
                "Name": name_str,
                "ID": id_str,
                "Joined on": joined_on_str,
                "Account age": account_age_str,
            },
        )
