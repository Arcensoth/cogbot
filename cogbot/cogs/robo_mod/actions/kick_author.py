from cogbot.cogs.robo_mod.robo_mod_action import RoboModAction
from cogbot.cogs.robo_mod.robo_mod_trigger import RoboModTrigger


class KickAuthorAction(RoboModAction):
    def __init__(self):
        pass

    async def update(self, state: "RoboModServerState", data: dict):
        pass

    async def apply(self, trigger: RoboModTrigger):
        await trigger.bot.kick(trigger.author)
        await trigger.bot.send_message(trigger.channel, content=f"{trigger.author.mention} got the 👢!")