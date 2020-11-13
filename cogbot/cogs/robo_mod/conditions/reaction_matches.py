from typing import List
from cogbot.cogs.robo_mod.robo_mod_condition import RoboModCondition
from cogbot.cogs.robo_mod.robo_mod_trigger import RoboModTrigger


class ReactionMatchesCondition(RoboModCondition):
    def __init__(self):
        self.reactions: List[str] = None

    async def update(self, state: "RoboModServerState", data: dict):
        self.reactions = data["reactions"]
        if len(self.reactions) <= 0:
            raise ValueError("reactions cannot be empty")

    async def check(self, trigger: RoboModTrigger) -> bool:
        reaction = str(trigger.reaction.emoji)
        for r in self.reactions:
            if r == reaction:
                return True
        return False
