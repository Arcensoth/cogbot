from typing import Optional

from discord import Member, Server

from cogbot.cogs.robo_mod.robo_mod_rule import RoboModRule
from cogbot.cogs.robo_mod.robo_mod_trigger import RoboModTrigger


class MemberUnbannedTrigger(RoboModTrigger):
    def __init__(
        self,
        state: "RoboModServerState",
        rule: RoboModRule,
        server: Server,
        member: Member,
    ):
        super().__init__(state, rule)
        self._server: Server = server
        self._member: Member = member

    @property
    def member(self) -> Optional[Member]:
        return self._member
