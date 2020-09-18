from abc import ABC, abstractmethod

from cogbot.cogs.robo_mod.robo_mod_trigger import RoboModTrigger
from cogbot.lib.dict_repr import DictRepr


class RoboModCondition(ABC, DictRepr):
    async def init(self, state: "RoboModServerState", data: dict) -> "RoboModCondition":
        """ Initialize the instance asynchronously, and return itself. """
        await self.update(state, data)
        return self

    @abstractmethod
    async def update(self, state: "RoboModServerState", data: dict):
        """ Initialize the instance asynchronously. """

    @abstractmethod
    async def check(self, trigger: RoboModTrigger) -> bool:
        """ Check whether the condition passes. """
