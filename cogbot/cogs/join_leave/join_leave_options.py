from typing import Dict, List, Type

from cogbot.types import RoleId

# TODO Use dataclasses for the options object hierarchy (requires Python 3.7+). #enhance


class JoinLeaveOptionsRoleEntry:
    def __init__(self):
        self.role_id: RoleId
        self.name: str
        self.aliases: List[str]

    async def init(
        self, state: "JoinLeaveServerState", data: dict
    ) -> "JoinLeaveOptionsRoleEntry":
        self.role_id = data["role_id"]
        self.name = data["name"]
        self.aliases = [alias.lower() for alias in data["aliases"]]
        return self


class JoinLeaveOptions:
    def __init__(self,):
        self.role_entries: List[JoinLeaveOptionsRoleEntry]
        self.role_entry_from_alias: Dict[str, JoinLeaveOptionsRoleEntry]

    async def init(
        self, state: "JoinLeaveServerState", data: dict
    ) -> "JoinLeaveOptions":
        self.role_entries = [
            await JoinLeaveOptionsRoleEntry().init(state, entry)
            for entry in data["roles"]
        ]

        self.role_entry_from_alias = {}
        for role_entry in self.role_entries:
            for role_alias in role_entry.aliases:
                self.role_entry_from_alias[role_alias] = role_entry

        state.log.info(
            f"Registered {len(self.role_entries)} self-assignable roles with {len(self.role_entry_from_alias)} aliases"
        )

        return self
