from typing import TYPE_CHECKING, Optional

from cogbot.cogs.robo_mod.robo_mod_action import RoboModAction
from cogbot.cogs.robo_mod.robo_mod_action_log_entry import RoboModActionLogEntry
from cogbot.cogs.robo_mod.robo_mod_trigger import RoboModTrigger

if TYPE_CHECKING:
    from cogbot.cogs.robo_mod.robo_mod_server_state import RoboModServerState


class LogCustomAction(RoboModAction):
    def __init__(self):
        self.content: str = None

    async def update(self, state: "RoboModServerState", data: dict):
        self.content = data["content"]

    async def log(self, trigger: RoboModTrigger) -> Optional[RoboModActionLogEntry]:
        return RoboModActionLogEntry(
            content=self.content.format(
                actor=trigger.actor,
                author=trigger.author,
                channel=trigger.channel,
                member=trigger.member,
                message=trigger.message,
                reaction=trigger.reaction,
            )
        )
