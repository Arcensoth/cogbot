from typing import List, Optional, Set

from discord import Color

from cogbot.cogs.robo_mod.actions import make_action
from cogbot.cogs.robo_mod.conditions import make_condition
from cogbot.cogs.robo_mod.robo_mod_action import RoboModAction
from cogbot.cogs.robo_mod.robo_mod_condition import RoboModCondition
from cogbot.cogs.robo_mod.robo_mod_trigger import RoboModTrigger
from cogbot.cogs.robo_mod.robo_mod_trigger_type import RoboModTriggerType
from cogbot.types import ChannelId, RoleId


class RoboModRule:
    def __init__(self):
        self.name: str
        self.description: str
        self.log_icon: Optional[str]
        self.log_color: Optional[Color]
        self.log_channel_id: Optional[ChannelId]
        self.notify_role_ids: Optional[Set[RoleId]]
        self.trigger_type: RoboModTriggerType
        self.conditions: List[RoboModCondition]
        self.actions: List[RoboModAction]

    async def init(self, state: "RoboModServerState", data: dict) -> "RoboModRule":
        self.name = data["name"]

        self.description = data["description"]

        self.log_icon = data.get("log_icon", None)

        raw_log_color = data.get("log_color", None)
        self.log_color = (
            None if raw_log_color is None else state.bot.color_from_hex(raw_log_color)
        )

        self.log_channel_id = data.get("log_channel", None)

        raw_notify_roles = data.get("notify_roles", None)
        self.notify_role_ids = (
            None if raw_notify_roles is None else set(raw_notify_roles)
        )

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
            await action.apply_and_log(trigger)

    async def run(self, trigger: RoboModTrigger):
        """ Run the rule, applying all actions if all conditions pass. """
        if await self.check_conditions(trigger):
            await self.apply_actions(trigger)
