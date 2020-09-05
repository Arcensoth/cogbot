from cogbot.cogs.robo_mod.robo_mod_condition import RoboModCondition
from cogbot.cogs.robo_mod.robo_mod_trigger import RoboModTrigger


class MessageHasAttachmentCondition(RoboModCondition):
    def __init__(self):
        self.min_count: int

    async def update(self, state: "RoboModServerState", data: dict):
        self.min_count = data.get("min_count", 1)

    async def check(self, trigger: RoboModTrigger) -> bool:
        return len(trigger.message.attachments) >= self.min_count
