from cogbot.cogs.robo_mod.robo_mod_condition import RoboModCondition
from cogbot.cogs.robo_mod.robo_mod_trigger import RoboModTrigger


class MessageStartsWithCondition(RoboModCondition):
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
        # Short-circuit if LHS is empty or the first character doesn't match RHS.
        if (len(lhs) <= 0) or (lhs[0].lower() != rhs.lower()[0]):
            return False
        if self.ignore_case:
            lhs, rhs = lhs.lower(), rhs.lower()
        return lhs.startswith(rhs)
