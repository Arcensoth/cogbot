from abc import ABC
from typing import Optional

from discord import Channel, Member, Message, Reaction

from cogbot.cog_bot import CogBot
from cogbot.lib.dict_repr import DictRepr


class RoboModTrigger(ABC, DictRepr):
    def __init__(self, state: "RoboModServerState", rule: "RoboModRule"):
        self.state: "RoboModServerState" = state
        self.rule: "RoboModRule" = rule

    @property
    def bot(self) -> CogBot:
        return self.state.bot

    @property
    def channel(self) -> Optional[Channel]:
        """ Return the relevant channel, if any. """
        pass

    @property
    def message(self) -> Optional[Message]:
        """ Return the relevant message, if any. """
        pass

    @property
    def reaction(self) -> Optional[Reaction]:
        pass

    @property
    def author(self) -> Optional[Member]:
        """ Return the relevant author, if any. """
        pass

    @property
    def actor(self) -> Optional[Member]:
        """ Return the acting user, if any. """
        pass

    @property
    def member(self) -> Optional[Member]:
        """ Return the member-in-question, if any. """
        pass
