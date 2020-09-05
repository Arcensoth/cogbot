from typing import Set

from cogbot.cogs.robo_mod.robo_mod_condition import RoboModCondition
from cogbot.cogs.robo_mod.robo_mod_trigger import RoboModTrigger


class MessageContainsAnyOfCondition(RoboModCondition):
    def __init__(self):
        self.matches: Set[str]
        self.ignore_case: bool

    async def update(self, state: "RoboModServerState", data: dict):
        matches = set(data["matches"])
        ignore_case = data.get("ignore_case", False)
        if ignore_case:
            matches = set(match.lower() for match in matches)
        if len(matches) <= 0:
            raise ValueError("matches cannot be empty")
        self.matches = matches
        self.ignore_case = ignore_case

    async def check(self, trigger: RoboModTrigger) -> bool:
        for match in self.matches:
            msg = str(trigger.message.content)
            # Short-circuit if msg is too short to contain match.
            if len(msg) < len(match):
                continue
            if self.ignore_case:
                msg = msg.lower()
            if match in msg:
                return True
        return False
