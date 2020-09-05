from abc import ABC, abstractmethod

from cogbot.cogs.robo_mod.robo_mod_trigger import RoboModTrigger


class RoboModCondition(ABC):
    def __str__(self) -> str:
        return f"<{self.__class__.__name__} #{id(self)}>"

    def __repr__(self) -> str:
        return str(self)

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
