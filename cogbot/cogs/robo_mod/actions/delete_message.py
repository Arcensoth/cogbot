from typing import List, Set

from discord.role import Role

from cogbot.cogs.robo_mod.robo_mod_action import RoboModAction
from cogbot.cogs.robo_mod.robo_mod_trigger import RoboModTrigger
from cogbot.types import ChannelId, RoleId


class DeleteMessageAction(RoboModAction):
    def __init__(self):
        self.log_to_channel: ChannelId
        self.notify_role_ids: Set[RoleId]

    async def update(self, state: "RoboModServerState", data: dict):
        self.log_to_channel = data.get("log_to_channel", None)
        self.notify_role_ids = set(data.get("notify_roles", []))

    async def apply(self, trigger: RoboModTrigger):
        if self.log_to_channel:
            content = f"The following message from {trigger.author.mention} was deleted according to rule `{trigger.rule.name}`:"
            if self.notify_role_ids:
                notify_roles = list(
                    trigger.bot.get_roles(trigger.state.server, self.notify_role_ids)
                )
                roles_mention_str = " ".join(
                    [f"{role.mention}" for role in notify_roles]
                )
                content = f"{roles_mention_str} {content}"
            await trigger.bot.quote_message(
                destination=trigger.bot.get_channel(self.log_to_channel),
                message=trigger.message,
                content=content,
                text_only=True,
            )
        await trigger.bot.delete_message(trigger.message)
