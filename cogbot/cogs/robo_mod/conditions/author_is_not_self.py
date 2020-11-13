from cogbot.cogs.robo_mod.robo_mod_condition import RoboModCondition
from cogbot.cogs.robo_mod.robo_mod_trigger import RoboModTrigger


class AuthorIsNotSelfCondition(RoboModCondition):
    async def update(self, state: "RoboModServerState", data: dict):
        pass

    async def check(self, trigger: RoboModTrigger) -> bool:
        return trigger.bot.user.id != trigger.author.id
