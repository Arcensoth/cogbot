from abc import ABC, abstractmethod

from cogbot.cogs.robo_mod.robo_mod_trigger import RoboModTrigger


class RoboModAction(ABC):
    def __str__(self) -> str:
        return f"<{self.__class__.__name__} #{id(self)}>"

    def __repr__(self) -> str:
        return str(self)

    async def init(self, state: "RoboModServerState", data: dict) -> "RoboModAction":
        """ Initialize the instance asynchronously, and return itself. """
        await self.update(state, data)
        return self

    @abstractmethod
    async def update(self, state: "RoboModServerState", data: dict):
        """ Initialize the instance asynchronously. """

    @abstractmethod
    async def apply(self, trigger: RoboModTrigger):
        """ Apply the action. """
