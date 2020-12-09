from typing import List

from cogbot.cogs.robo_mod.robo_mod_condition import RoboModCondition
from cogbot.cogs.robo_mod.robo_mod_trigger import RoboModTrigger


class ReactionMatchesCondition(RoboModCondition):
    def __init__(self):
        self.reactions: List[str] = None
        self.first_only: bool = False

    async def update(self, state: "RoboModServerState", data: dict):
        self.reactions = data["reactions"]
        if len(self.reactions) <= 0:
            raise ValueError("reactions cannot be empty")
        self.first_only = data.get("first_only", False)

    async def check(self, trigger: RoboModTrigger) -> bool:
        if self.first_only and trigger.reaction.count != 1:
            return False
        reaction = str(trigger.reaction.emoji)
        for r in self.reactions:
            if r == reaction:
                return True
        return False
