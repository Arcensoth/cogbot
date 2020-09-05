from typing import Dict, List

from cogbot.cogs.robo_mod.robo_mod_rule import RoboModRule
from cogbot.cogs.robo_mod.robo_mod_trigger_type import RoboModTriggerType


class RoboModOptions:
    def __init__(self,):
        self.rules: List[RoboModRule]
        self.rules_by_trigger_type: Dict[RoboModTriggerType, List[RoboModRule]]

    async def init(self, state: "RoboModServerState", data: dict) -> "RoboModOptions":
        self.rules = [await RoboModRule().init(state, entry) for entry in data["rules"]]

        self.rules_by_trigger_type = {}
        for rule in self.rules:
            trigger_type = rule.trigger_type
            if trigger_type not in self.rules_by_trigger_type:
                self.rules_by_trigger_type[trigger_type] = []
            self.rules_by_trigger_type[trigger_type].append(rule)

        state.log.info(f"Registered {len(self.rules)} rules")

        return self
