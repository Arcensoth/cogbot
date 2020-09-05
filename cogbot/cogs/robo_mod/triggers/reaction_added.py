from typing import Optional

from discord import Channel, Member, Message, Reaction

from cogbot.cogs.robo_mod.robo_mod_rule import RoboModRule
from cogbot.cogs.robo_mod.robo_mod_trigger import RoboModTrigger


class ReactionAddedTrigger(RoboModTrigger):
    def __init__(
        self,
        state: "RoboModServerState",
        rule: RoboModRule,
        reaction: Reaction,
        reactor: Member,
    ):
        super().__init__(state, rule)
        self._reaction: Reaction = reaction
        self._reactor: Member = reactor

    @property
    def channel(self) -> Optional[Channel]:
        return self._reaction.message.channel

    @property
    def message(self) -> Optional[Message]:
        return self._reaction.message

    @property
    def reaction(self) -> Optional[Reaction]:
        return self._reaction

    @property
    def author(self) -> Optional[Member]:
        return self._reaction.message.author

    @property
    def actor(self) -> Optional[Member]:
        return self._reactor
