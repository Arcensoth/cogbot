import logging

from cogbot.extensions.groups.error import *


log = logging.getLogger(__name__)


class GroupDirectory(object):
    def __init__(self):
        # accessing role_map[server_id][role_name] gives role_id
        # don't store role object directly (not persistent)
        self._role_map = {}

    @staticmethod
    def _sanitize_group(group: str):
        return group.lower()

    @staticmethod
    def _get_server_role_by_id(server, role_id):
        for role in server.roles:
            if role.id == role_id:
                return role
        raise NoSuchRoleIdError(role_id=role_id)

    @staticmethod
    def _get_server_role_by_sanitized_group(server, sanitized_group):
        for role in server.roles:
            if GroupDirectory._sanitize_group(role.name) == sanitized_group:
                return role
        raise NoSuchRoleNameError(role_name=sanitized_group)

    def groups(self, server):
        if server.id in self._role_map:
            yield from self._role_map[server.id].keys()

    def add_group(self, server, group):
        group = self._sanitize_group(group)

        role = self._get_server_role_by_sanitized_group(server, group)

        if server.id not in self._role_map:
            self._role_map[server.id] = {}

        if group in self._role_map[server.id]:
            raise GroupAlreadyExistsError(group=group)

        self._role_map[server.id][group] = role.id

        log.info(f'{server}: added group {group} (id {role.id})')

    def remove_group(self, server, group):
        group = self._sanitize_group(group)

        if (server.id not in self._role_map) or (group not in self._role_map[server.id]):
            raise NoSuchGroupError(group=group)

        role_id = self._role_map[server.id][group]

        del self._role_map[server.id][group]

        log.info(f'{server}: removed group {group} (id {role_id})')

    def is_role(self, server, group):
        group = self._sanitize_group(group)
        return (server.id in self._role_map) and (group in self._role_map[server.id])

    def get_role(self, server, group):
        group = self._sanitize_group(group)

        if (server.id not in self._role_map) or (group not in self._role_map[server.id]):
            raise NoSuchGroupError(group=group)

        role_id = self._role_map[server.id][group]

        try:
            role = self._get_server_role_by_id(server, role_id)
            return role

        except NoSuchRoleIdError:
            log.warning(f'{server}: locking deleted role {group} (id {role_id})')
            self.remove_group(server, group)
            raise NoSuchGroupError(group=group)

    def get_members(self, server, group):
        group = self._sanitize_group(group)
        role = self.get_role(server, group)
        members = []
        for member in server.members:
            if role in member.roles:
                members.append(member)
        return members
