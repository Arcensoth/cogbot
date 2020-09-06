from cogbot.cogs.robo_mod.robo_mod_action import RoboModAction
from cogbot.cogs.robo_mod.robo_mod_action_log_entry import RoboModActionLogEntry
from cogbot.cogs.robo_mod.robo_mod_trigger import RoboModTrigger


class DeleteMessageAction(RoboModAction):
    def __init__(self):
        pass

    async def update(self, state: "RoboModServerState", data: dict):
        pass

    async def log(self, trigger: RoboModTrigger) -> RoboModActionLogEntry:
        return RoboModActionLogEntry(
            content=f"Deleted a message from {trigger.author.mention}.",
            quote_message=trigger.message,
        )

    async def apply(self, trigger: RoboModTrigger):
        await trigger.bot.delete_message(trigger.message)
