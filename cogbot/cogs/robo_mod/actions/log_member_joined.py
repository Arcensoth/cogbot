from typing import Optional

from cogbot.cogs.robo_mod.robo_mod_action import RoboModAction
from cogbot.cogs.robo_mod.robo_mod_action_log_entry import RoboModActionLogEntry
from cogbot.cogs.robo_mod.robo_mod_trigger import RoboModTrigger


class LogMemberJoinedAction(RoboModAction):
    async def log(self, trigger: RoboModTrigger) -> Optional[RoboModActionLogEntry]:
        return RoboModActionLogEntry(
            content=f"Hello! Member {trigger.actor.mention} has joined the server."
        )
