from typing import TYPE_CHECKING, List

import discord
from cogbot.cogs.robo_mod.robo_mod_action import RoboModAction
from cogbot.cogs.robo_mod.robo_mod_trigger import RoboModTrigger

if TYPE_CHECKING:
    from cogbot.cogs.robo_mod.robo_mod_server_state import RoboModServerState


class AddReactionsAction(RoboModAction):
    def __init__(self):
        self.reactions: List[str] = None

    async def update(self, state: "RoboModServerState", data: dict):
        raw_reactions = data["reactions"]
        if len(raw_reactions) <= 0:
            raise ValueError("reactions cannot be empty")
        self.reactions = [state.bot.get_emoji(state.server, r) for r in raw_reactions]

    async def apply(self, trigger: RoboModTrigger):
        for r in self.reactions:
            await trigger.bot.add_reaction(trigger.message, r)
