from datetime import datetime, timedelta
from typing import Optional

from cogbot.cogs.robo_mod.robo_mod_condition import RoboModCondition
from cogbot.cogs.robo_mod.robo_mod_trigger import RoboModTrigger


class AuthorAccountAgeCondition(RoboModCondition):
    def __init__(self):
        self.more_than: Optional[timedelta] = None
        self.less_than: Optional[timedelta] = None

    async def update(self, state: "RoboModServerState", data: dict):
        # more_than
        raw_more_than = data.get("more_than", None)
        if raw_more_than is not None:
            self.more_than = timedelta(**raw_more_than)
        # less_than
        raw_less_than = data.get("less_than", None)
        if raw_less_than is not None:
            self.less_than = timedelta(**raw_less_than)

    async def check(self, trigger: RoboModTrigger) -> bool:
        now = datetime.utcnow()
        created_at = trigger.author.created_at
        if created_at is None:
            return False
        age = now - created_at
        is_older = (self.more_than is None) or (age > self.more_than)
        is_younger = (self.less_than is None) or (age < self.less_than)
        return is_older and is_younger
