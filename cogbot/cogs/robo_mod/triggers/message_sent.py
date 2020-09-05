from typing import Optional

from discord import Channel, Member, Message

from cogbot.cogs.robo_mod.robo_mod_rule import RoboModRule
from cogbot.cogs.robo_mod.robo_mod_trigger import RoboModTrigger


class MessageSentTrigger(RoboModTrigger):
    def __init__(
        self, state: "RoboModServerState", rule: RoboModRule, message: Message
    ):
        super().__init__(state, rule)
        self._message: Message = message

    @property
    def channel(self) -> Optional[Channel]:
        return self._message.channel

    @property
    def message(self) -> Optional[Message]:
        return self._message

    @property
    def author(self) -> Optional[Member]:
        return self._message.author

    @property
    def actor(self) -> Optional[Member]:
        return self._message.author
