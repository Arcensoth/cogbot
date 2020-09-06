from enum import Enum


class RoboModActionType(Enum):
    SEND_REPLY = "SEND_REPLY"
    DELETE_MESSAGE = "DELETE_MESSAGE"
    KICK_AUTHOR = "KICK_AUTHOR"
    ADD_ROLES_TO_AUTHOR = "ADD_ROLES_TO_AUTHOR"
    LOG_MEMBER_JOINED = "LOG_MEMBER_JOINED"
    LOG_MEMBER_LEFT = "LOG_MEMBER_LEFT"
