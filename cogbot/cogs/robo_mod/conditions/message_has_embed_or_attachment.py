from cogbot.cogs.robo_mod.robo_mod_condition import RoboModCondition
from cogbot.cogs.robo_mod.robo_mod_trigger import RoboModTrigger


class MessageHasEmbedOrAttachmentCondition(RoboModCondition):
    def __init__(self):
        self.min_count: int

    async def update(self, state: "RoboModServerState", data: dict):
        self.min_count = data.get("min_count", 1)

    async def check(self, trigger: RoboModTrigger) -> bool:
        count_embeds = len(trigger.message.embeds)
        count_attachments = len(trigger.message.attachments)
        count = count_embeds + count_attachments
        return count >= self.min_count
