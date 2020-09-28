from typing import Optional

from discord import Channel, Member, Message

from cogbot.cogs.robo_mod.robo_mod_rule import RoboModRule
from cogbot.cogs.robo_mod.robo_mod_trigger import RoboModTrigger


class MessageEditedTrigger(RoboModTrigger):
    def __init__(
        self,
        state: "RoboModServerState",
        rule: RoboModRule,
        before: Message,
        after: Message,
    ):
        super().__init__(state, rule)
        self._before: Message = before
        self._after: Message = after

    @property
    def channel(self) -> Optional[Channel]:
        return self._after.channel

    @property
    def message(self) -> Optional[Message]:
        return self._after

    @property
    def author(self) -> Optional[Member]:
        return self._after.author

    @property
    def actor(self) -> Optional[Member]:
        return self._after.author

    @property
    def member(self) -> Optional[Member]:
        return self._after.author
