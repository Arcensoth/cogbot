from cogbot.cogs.robo_mod.conditions.author_is_not_self import AuthorIsNotSelfCondition
from cogbot.cogs.robo_mod.conditions.message_contains import MessageContainsCondition
from cogbot.cogs.robo_mod.conditions.message_contains_any_of import MessageContainsAnyOfCondition
from cogbot.cogs.robo_mod.conditions.message_has_attachment import MessageHasAttachmentCondition
from cogbot.cogs.robo_mod.conditions.message_has_embed import MessageHasEmbedCondition
from cogbot.cogs.robo_mod.conditions.message_has_embed_or_attachment import (
    MessageHasEmbedOrAttachmentCondition,
)
from cogbot.cogs.robo_mod.conditions.message_is_exactly import MessageIsExactlyCondition
from cogbot.cogs.robo_mod.conditions.message_starts_with import MessageStartsWithCondition
from cogbot.cogs.robo_mod.conditions.reaction_matches import ReactionMatchesCondition
from cogbot.cogs.robo_mod.robo_mod_condition import RoboModCondition
from cogbot.cogs.robo_mod.robo_mod_condition_type import RoboModConditionType

CONDITION_TYPE_TO_FACTORY = {
    RoboModConditionType.MESSAGE_IS_EXACTLY: MessageIsExactlyCondition,
    RoboModConditionType.MESSAGE_STARTS_WITH: MessageStartsWithCondition,
    RoboModConditionType.MESSAGE_CONTAINS: MessageContainsCondition,
    RoboModConditionType.MESSAGE_CONTAINS_ANY_OF: MessageContainsAnyOfCondition,
    RoboModConditionType.MESSAGE_HAS_EMBED: MessageHasEmbedCondition,
    RoboModConditionType.MESSAGE_HAS_ATTACHMENT: MessageHasAttachmentCondition,
    RoboModConditionType.MESSAGE_HAS_EMBED_OR_ATTACHMENT: MessageHasEmbedOrAttachmentCondition,
    RoboModConditionType.REACTION_MATCHES: ReactionMatchesCondition,
    RoboModConditionType.AUTHOR_IS_NOT_SELF: AuthorIsNotSelfCondition,
}


async def make_condition(state: "RoboModServerState", data: dict) -> "RoboModCondition":
    data_copy = {k: v for k, v in data.items()}
    condition_type = RoboModConditionType[data_copy.pop("type")]
    condition_factory = CONDITION_TYPE_TO_FACTORY[condition_type]
    return await condition_factory().init(state, data_copy)
