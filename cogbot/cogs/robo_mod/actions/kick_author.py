from typing import Optional

from cogbot.cogs.robo_mod.robo_mod_action import RoboModAction
from cogbot.cogs.robo_mod.robo_mod_action_log_entry import RoboModActionLogEntry
from cogbot.cogs.robo_mod.robo_mod_trigger import RoboModTrigger


class KickAuthorAction(RoboModAction):
    async def log(self, trigger: RoboModTrigger) -> Optional[RoboModActionLogEntry]:
        return RoboModActionLogEntry(content=f"{trigger.author.mention} got the 👢!")

    async def apply(self, trigger: RoboModTrigger):
        await trigger.bot.kick(trigger.author)
