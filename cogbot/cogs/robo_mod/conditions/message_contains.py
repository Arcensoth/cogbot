from cogbot.cogs.robo_mod.robo_mod_condition import RoboModCondition
from cogbot.cogs.robo_mod.robo_mod_trigger import RoboModTrigger


class MessageContainsCondition(RoboModCondition):
    def __init__(self):
        self.content: str
        self.ignore_case: bool

    async def update(self, state: "RoboModServerState", data: dict):
        self.content = data["content"]
        if len(self.content) <= 0:
            raise ValueError("content cannot be empty")
        self.ignore_case = data.get("ignore_case", False)

    async def check(self, trigger: RoboModTrigger) -> bool:
        lhs, rhs = str(trigger.message.content), self.content
        # Short-circuit if LHS is too short to contain RHS.
        if len(lhs) < len(rhs):
            return False
        if self.ignore_case:
            lhs, rhs = lhs.lower(), rhs.lower()
        return rhs in lhs
