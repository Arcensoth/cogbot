from enum import Enum


class RoboModConditionType(Enum):
    MESSAGE_IS_EXACTLY = "MESSAGE_IS_EXACTLY"
    MESSAGE_STARTS_WITH = "MESSAGE_STARTS_WITH"
    MESSAGE_CONTAINS = "MESSAGE_CONTAINS"
    MESSAGE_CONTAINS_ANY_OF = "MESSAGE_CONTAINS_ANY_OF"
    MESSAGE_HAS_EMBED = "MESSAGE_HAS_EMBED"
    MESSAGE_HAS_ATTACHMENT = "MESSAGE_HAS_ATTACHMENT"
    MESSAGE_HAS_EMBED_OR_ATTACHMENT = "MESSAGE_HAS_EMBED_OR_ATTACHMENT"
    MESSAGE_CONTAINS_EXTERNAL_MEDIA = "MESSAGE_CONTAINS_EXTERNAL_MEDIA"
    REACTION_MATCHES = "REACTION_MATCHES"
    AUTHOR_IS_NOT_SELF = "AUTHOR_IS_NOT_SELF"
    AUTHOR_ACCOUNT_AGE = "AUTHOR_ACCOUNT_AGE"
    AUTHOR_HAS_BEEN_MEMBER_FOR = "AUTHOR_HAS_BEEN_MEMBER_FOR"
