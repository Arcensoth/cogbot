from cogbot.cogs.robo_mod.robo_mod_rule import RoboModRule
from cogbot.cogs.robo_mod.robo_mod_trigger import RoboModTrigger
from cogbot.cogs.robo_mod.robo_mod_trigger_type import RoboModTriggerType
from cogbot.cogs.robo_mod.triggers.member_banned import MemberBannedTrigger
from cogbot.cogs.robo_mod.triggers.member_joined import MemberJoinedTrigger
from cogbot.cogs.robo_mod.triggers.member_left import MemberLeftTrigger
from cogbot.cogs.robo_mod.triggers.member_unbanned import MemberUnbannedTrigger
from cogbot.cogs.robo_mod.triggers.message import MessageTrigger
from cogbot.cogs.robo_mod.triggers.message_deleted import MessageDeletedTrigger
from cogbot.cogs.robo_mod.triggers.message_edited import MessageEditedTrigger
from cogbot.cogs.robo_mod.triggers.message_sent import MessageSentTrigger
from cogbot.cogs.robo_mod.triggers.reaction_added import ReactionAddedTrigger

TRIGGER_TYPE_TO_FACTORY = {
    RoboModTriggerType.MEMBER_JOINED: MemberJoinedTrigger,
    RoboModTriggerType.MEMBER_LEFT: MemberLeftTrigger,
    RoboModTriggerType.MEMBER_BANNED: MemberBannedTrigger,
    RoboModTriggerType.MEMBER_UNBANNED: MemberUnbannedTrigger,
    RoboModTriggerType.MESSAGE_SENT: MessageSentTrigger,
    RoboModTriggerType.MESSAGE_DELETED: MessageDeletedTrigger,
    RoboModTriggerType.MESSAGE_EDITED: MessageEditedTrigger,
    RoboModTriggerType.MESSAGE: MessageTrigger,
    RoboModTriggerType.REACTION_ADDED: ReactionAddedTrigger,
}


async def make_trigger(
    state: "RoboModServerState",
    rule: RoboModRule,
    trigger_type: RoboModTriggerType,
    **kwargs
) -> "RoboModTrigger":
    trigger_factory = TRIGGER_TYPE_TO_FACTORY[trigger_type]
    return trigger_factory(state, rule, **kwargs)
