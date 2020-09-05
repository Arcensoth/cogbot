import asyncio

from cogbot.cogs.robo_mod.robo_mod_condition import RoboModCondition
from cogbot.cogs.robo_mod.robo_mod_trigger import RoboModTrigger


class MessageHasEmbedOrAttachmentCondition(RoboModCondition):
    def __init__(self):
        self.min_count: int
        self.delay: int

    async def update(self, state: "RoboModServerState", data: dict):
        self.min_count = data.get("min_count", 1)
        self.delay = data.get("delay", 0)

    async def check(self, trigger: RoboModTrigger) -> bool:
        # Optionally give the client cache some time to update.
        if self.delay > 0:
            await asyncio.sleep(self.delay / 1000)
        count_embeds = len(trigger.message.embeds)
        count_attachments = len(trigger.message.attachments)
        count = count_embeds + count_attachments
        return count >= self.min_count
