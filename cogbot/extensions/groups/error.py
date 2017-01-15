class GroupDirectoryError(Exception):
    pass


class NoSuchRoleIdError(GroupDirectoryError):
    def __init__(self, *args, role_id, **kwargs):
        super().__init__(*args, **kwargs)
        self.role_id = role_id


class NoSuchRoleNameError(GroupDirectoryError):
    def __init__(self, *args, role_name, **kwargs):
        super().__init__(*args, **kwargs)
        self.role_name = role_name


class GroupDirectoryGroupError(GroupDirectoryError):
    def __init__(self, *args, group, **kwargs):
        super().__init__(*args, **kwargs)
        self.group = group


class NoSuchGroupError(GroupDirectoryGroupError):
    pass


class GroupAlreadyExistsError(GroupDirectoryGroupError):
    pass
