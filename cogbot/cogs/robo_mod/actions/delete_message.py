from typing import Optional

from discord import Member

from cogbot.cogs.robo_mod.robo_mod_action import RoboModAction
from cogbot.cogs.robo_mod.robo_mod_action_log_entry import RoboModActionLogEntry
from cogbot.cogs.robo_mod.robo_mod_trigger import RoboModTrigger


class DeleteMessageAction(RoboModAction):
    async def log(self, trigger: RoboModTrigger) -> Optional[RoboModActionLogEntry]:
        member: Member = trigger.member
        # Name
        name_str = f"{member}"
        # User ID
        user_id_str = f"{member.id}"
        # NOTE We don't need these fields because they're included in the quote.
        # Channel
        # channel_str = f"{trigger.channel}"
        # Channel ID
        # channel_id_str = f"{trigger.channel.id}"
        # Message ID
        # message_id_str = f"{trigger.message.id}"
        return RoboModActionLogEntry(
            content=f"Deleted a message from {trigger.author.mention}.",
            fields={
                "Name": name_str,
                "User ID": user_id_str,
                # "Channel": channel_str,
                # "Channel ID": channel_id_str,
                # "Message ID": message_id_str,
            },
            quote_message=trigger.message,
        )

    async def apply(self, trigger: RoboModTrigger):
        await trigger.bot.delete_message(trigger.message)
