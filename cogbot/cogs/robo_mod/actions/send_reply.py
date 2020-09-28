from cogbot.cogs.robo_mod.robo_mod_action import RoboModAction
from cogbot.cogs.robo_mod.robo_mod_trigger import RoboModTrigger


class SendReplyAction(RoboModAction):
    def __init__(self):
        self.content: str = None
        self.include_mention: bool = None

    async def update(self, state: "RoboModServerState", data: dict):
        self.content = data["content"]
        self.include_mention = data.get("include_mention", False)

    async def apply(self, trigger: RoboModTrigger):
        content = self.content
        if self.include_mention:
            content = f"{trigger.actor.mention} {content}"
        await trigger.bot.send_message(trigger.channel, content=content)
