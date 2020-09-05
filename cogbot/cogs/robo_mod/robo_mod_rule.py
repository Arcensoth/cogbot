from typing import List

from cogbot.cogs.robo_mod.actions import make_action
from cogbot.cogs.robo_mod.conditions import make_condition
from cogbot.cogs.robo_mod.robo_mod_action import RoboModAction
from cogbot.cogs.robo_mod.robo_mod_condition import RoboModCondition
from cogbot.cogs.robo_mod.robo_mod_trigger import RoboModTrigger
from cogbot.cogs.robo_mod.robo_mod_trigger_type import RoboModTriggerType


class RoboModRule:
    def __init__(self):
        self.name: str
        self.description: str
        self.trigger_type: RoboModTriggerType
        self.conditions: List[RoboModCondition]
        self.actions: List[RoboModAction]

    async def init(self, state: "RoboModServerState", data: dict) -> "RoboModRule":
        self.name = data["name"]
        self.description = data["description"]
        self.trigger_type = RoboModTriggerType[data["trigger_type"]]
        self.conditions = [
            await make_condition(state, entry) for entry in data["conditions"]
        ]
        self.actions = [await make_action(state, entry) for entry in data["actions"]]
        return self

    async def check_conditions(self, trigger: RoboModTrigger) -> bool:
        """ Check whether all of this rule's conditions pass. """
        for condition in self.conditions:
            if not await condition.check(trigger):
                return False
        return True

    async def apply_actions(self, trigger: RoboModTrigger):
        """ Apply all of this rule's actions. """
        for action in self.actions:
            await action.apply(trigger)

    async def run(self, trigger: RoboModTrigger):
        """ Run the rule, applying all actions if all conditions pass. """
        if await self.check_conditions(trigger):
            await self.apply_actions(trigger)
