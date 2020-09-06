from cogbot.cogs.robo_mod.actions.add_roles_to_author import AddRolesToAuthorAction
from cogbot.cogs.robo_mod.actions.delete_message import DeleteMessageAction
from cogbot.cogs.robo_mod.actions.kick_author import KickAuthorAction
from cogbot.cogs.robo_mod.actions.log_member_banned import LogMemberBannedAction
from cogbot.cogs.robo_mod.actions.log_member_joined import LogMemberJoinedAction
from cogbot.cogs.robo_mod.actions.log_member_left import LogMemberLeftAction
from cogbot.cogs.robo_mod.actions.log_member_unbanned import LogMemberUnbannedAction
from cogbot.cogs.robo_mod.actions.send_reply import SendReplyAction
from cogbot.cogs.robo_mod.robo_mod_action import RoboModAction
from cogbot.cogs.robo_mod.robo_mod_action_type import RoboModActionType

ACTION_TYPE_TO_FACTORY = {
    RoboModActionType.SEND_REPLY: SendReplyAction,
    RoboModActionType.DELETE_MESSAGE: DeleteMessageAction,
    RoboModActionType.KICK_AUTHOR: KickAuthorAction,
    RoboModActionType.ADD_ROLES_TO_AUTHOR: AddRolesToAuthorAction,
    RoboModActionType.LOG_MEMBER_JOINED: LogMemberJoinedAction,
    RoboModActionType.LOG_MEMBER_LEFT: LogMemberLeftAction,
    RoboModActionType.LOG_MEMBER_BANNED: LogMemberBannedAction,
    RoboModActionType.LOG_MEMBER_UNBANNED: LogMemberUnbannedAction,
}


async def make_action(state: "RoboModServerState", data: dict) -> "RoboModAction":
    data_copy = {k: v for k, v in data.items()}
    action_type = RoboModActionType[data_copy.pop("type")]
    action_factory = ACTION_TYPE_TO_FACTORY[action_type]
    return await action_factory().init(state, data_copy)
