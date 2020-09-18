from typing import Dict, List, Optional, Set

from discord import Color

from cogbot.cogs.robo_mod.robo_mod_rule import RoboModRule
from cogbot.cogs.robo_mod.robo_mod_trigger_type import RoboModTriggerType
from cogbot.types import ChannelId, RoleId


class RoboModOptions:
    def __init__(self,):
        self.rules: List[RoboModRule]
        self.rules_by_name: Dict[str, RoboModRule]
        self.rules_by_trigger_type: Dict[RoboModTriggerType, List[RoboModRule]]
        self.log_channel_id: Optional[ChannelId]
        self.compact_logs: Optional[bool]
        self.log_emoji: Optional[str]
        self.log_icon: Optional[str]
        self.log_color: Optional[Color]
        self.notify_role_ids: Optional[Set[RoleId]]

    @property
    def rule_names(self) -> List[str]:
        return list(self.rules_by_name.keys())

    async def init(self, state: "RoboModServerState", data: dict) -> "RoboModOptions":
        self.rules = [await RoboModRule().init(state, entry) for entry in data["rules"]]

        self.rules_by_name = {}
        self.rules_by_trigger_type = {}
        for rule in self.rules:
            self.rules_by_name[rule.name] = rule
            trigger_type = rule.trigger_type
            if trigger_type not in self.rules_by_trigger_type:
                self.rules_by_trigger_type[trigger_type] = []
            self.rules_by_trigger_type[trigger_type].append(rule)

        state.log.info(f"Registered {len(self.rules)} rules")

        self.log_channel_id = data.get("log_channel", None)

        self.compact_logs = data.get("compact_logs", None)

        self.log_emoji = data.get("log_emoji", None)

        self.log_icon = data.get("log_icon", None)

        raw_log_color = data.get("log_color", None)
        self.log_color = (
            None if raw_log_color is None else state.bot.color_from_hex(raw_log_color)
        )

        raw_notify_roles = data.get("notify_roles", None)
        self.notify_role_ids = (
            None if raw_notify_roles is None else set(raw_notify_roles)
        )

        return self
