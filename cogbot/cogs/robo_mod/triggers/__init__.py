from cogbot.cogs.robo_mod.robo_mod_rule import RoboModRule
from cogbot.cogs.robo_mod.robo_mod_trigger import RoboModTrigger
from cogbot.cogs.robo_mod.robo_mod_trigger_type import RoboModTriggerType
from cogbot.cogs.robo_mod.triggers.message_deleted import MessageDeletedTrigger
from cogbot.cogs.robo_mod.triggers.message_sent import MessageSentTrigger
from cogbot.cogs.robo_mod.triggers.reaction_added import ReactionAddedTrigger

TRIGGER_TYPE_TO_FACTORY = {
    RoboModTriggerType.MESSAGE_SENT: MessageSentTrigger,
    RoboModTriggerType.MESSAGE_DELETED: MessageDeletedTrigger,
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
