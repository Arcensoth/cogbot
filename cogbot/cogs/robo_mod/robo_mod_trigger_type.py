from enum import Enum


class RoboModTriggerType(Enum):
    MESSAGE_SENT = "MESSAGE_SENT"
    MESSAGE_DELETED = "MESSAGE_DELETED"
    REACTION_ADDED = "REACTION_ADDED"
