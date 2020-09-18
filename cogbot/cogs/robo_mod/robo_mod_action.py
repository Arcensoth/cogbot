from abc import ABC
from typing import Optional

from cogbot.cogs.robo_mod.robo_mod_action_log_entry import RoboModActionLogEntry
from cogbot.cogs.robo_mod.robo_mod_trigger import RoboModTrigger
from cogbot.lib.dict_repr import DictRepr


class RoboModAction(ABC, DictRepr):
    async def init(self, state: "RoboModServerState", data: dict) -> "RoboModAction":
        """ Initialize the instance asynchronously, and return itself. """
        await self.update(state, data)
        return self

    async def apply_and_log(self, trigger: RoboModTrigger):
        await self.apply(trigger)
        await self.maybe_log(trigger)

    async def maybe_log(self, trigger: RoboModTrigger):
        log_entry = await self.log(trigger)
        if log_entry:
            await log_entry.do_log(trigger)

    # NOTE #override
    async def log(self, trigger: RoboModTrigger) -> Optional[RoboModActionLogEntry]:
        """ Return a log entry for this action, if any. """

    # NOTE #override
    async def update(self, state: "RoboModServerState", data: dict):
        """ Initialize the instance asynchronously. """

    # NOTE #override
    async def apply(self, trigger: RoboModTrigger):
        """ Apply the action. """
