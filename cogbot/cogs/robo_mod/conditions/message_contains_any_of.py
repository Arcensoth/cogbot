import unicodedata
from typing import Any, Dict, Set

from cogbot.cogs.robo_mod.robo_mod_condition import RoboModCondition
from cogbot.cogs.robo_mod.robo_mod_trigger import RoboModTrigger


class MessageContainsAnyOfCondition(RoboModCondition):
    def __init__(self):
        self.matches: Set[str] = None
        self.ignore_case: bool = None
        self.normalization_form: str = None
        self.normalize_unicode: bool = None

    def normalize(self, s: str) -> str:
        return unicodedata.normalize(self.normalization_form, s)

    async def update(self, state: "RoboModServerState", data: dict):
        matches = set(data["matches"])

        ignore_case = data.get("ignore_case", False)
        if ignore_case:
            matches = set(match.lower() for match in matches)
        self.ignore_case = ignore_case

        normalization_form = data.get("normalization_form", "NFKD")
        self.normalization_form = normalization_form

        normalize_unicode = data.get("normalize_unicode", False)
        if normalize_unicode:
            matches = set(self.normalize(match) for match in matches)
            self.normalize_unicode = normalize_unicode

        if len(matches) <= 0:
            raise ValueError("matches cannot be empty")

        self.matches = matches

    async def check(self, trigger: RoboModTrigger) -> bool:
        for match in self.matches:
            msg = str(trigger.message.content)
            # Short-circuit if msg is too short to contain match.
            if len(msg) < len(match):
                continue
            if self.ignore_case:
                msg = msg.lower()
            if self.normalize_unicode:
                msg = self.normalize(msg)
            if match in msg:
                return True
        return False
