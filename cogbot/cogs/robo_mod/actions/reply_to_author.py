from cogbot.cogs.robo_mod.robo_mod_action import RoboModAction
from cogbot.cogs.robo_mod.robo_mod_trigger import RoboModTrigger


class ReplyToAuthorAction(RoboModAction):
    def __init__(self):
        self.content: str = None

    async def update(self, state: "RoboModServerState", data: dict):
        self.content = data["content"]

    async def apply(self, trigger: RoboModTrigger):
        content = f"{trigger.author.mention} {self.content}"
        await trigger.bot.send_message(trigger.channel, content=content)
