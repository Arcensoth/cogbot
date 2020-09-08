from typing import Dict, Iterable, List, Optional, Set, Union

from discord import Channel, Color, Message, Role

from cogbot.cogs.robo_mod.robo_mod_trigger import RoboModTrigger
from cogbot.types import ChannelId, RoleId

StrOrIterable = Union[str, Iterable[str]]


class RoboModActionLogEntry:
    def __init__(
        self,
        content: StrOrIterable,
        emoji: str = None,
        icon: str = None,
        color: Color = None,
        channel_id: ChannelId = None,
        compact: bool = None,
        notify_role_ids: Iterable[RoleId] = None,
        quote_message: Message = None,
        fields: Dict[str, str] = None,
    ):
        self._content: StrOrIterable = content
        self.channel_id: Optional[ChannelId] = channel_id
        self.compact: Optional[bool] = compact
        self.emoji: Optional[str] = emoji
        self.icon: Optional[str] = icon
        self.color: Optional[Color] = color
        self.notify_role_ids: Optional[
            Set[RoleId]
        ] = None if notify_role_ids is None else set(notify_role_ids)
        self.quote_message: Optional[Message] = quote_message
        self.fields = fields

    @property
    def content(self) -> str:
        if isinstance(self._content, str):
            return self._content
        lines = [line for line in self._content]
        return "\n".join(lines)

    def get_channel_id(self, trigger: RoboModTrigger) -> ChannelId:
        return (
            self.channel_id
            or trigger.rule.log_channel_id
            or trigger.state.options.log_channel_id
        )

    def get_channel(self, trigger: RoboModTrigger) -> Channel:
        channel_id = self.get_channel_id(trigger)
        if channel_id:
            return trigger.bot.get_channel(channel_id)

    def get_compact(self, trigger: RoboModTrigger) -> bool:
        if self.compact is not None:
            return self.compact
        if trigger.rule.compact_logs is not None:
            return trigger.rule.compact_logs
        if trigger.state.options.compact_logs:
            return trigger.state.options.compact_logs
        return False

    def get_emoji(self, trigger: RoboModTrigger) -> str:
        return self.emoji or trigger.rule.log_emoji or trigger.state.options.log_emoji

    def get_icon(self, trigger: RoboModTrigger) -> str:
        return self.icon or trigger.rule.log_icon or trigger.state.options.log_icon

    def get_color(self, trigger: RoboModTrigger) -> Color:
        return self.color or trigger.rule.log_color or trigger.state.options.log_color

    def get_notify_role_ids(self, trigger: RoboModTrigger) -> List[RoleId]:
        if self.notify_role_ids is not None:
            return self.notify_role_ids
        if trigger.rule.notify_role_ids is not None:
            return trigger.rule.notify_role_ids
        return trigger.state.options.notify_role_ids

    def get_notify_roles(self, trigger: RoboModTrigger) -> List[Role]:
        notify_role_ids = self.get_notify_role_ids(trigger)
        if notify_role_ids:
            return list(trigger.bot.get_roles(trigger.state.server, notify_role_ids))

    def get_title(self, trigger: RoboModTrigger) -> str:
        return trigger.rule.name

    async def do_log(self, trigger: RoboModTrigger):
        channel = self.get_channel(trigger)
        if channel:
            compact = self.get_compact(trigger)
            emoji = self.get_emoji(trigger)
            icon = self.get_icon(trigger)
            color = self.get_color(trigger)
            notify_roles = self.get_notify_roles(trigger)
            title = self.get_title(trigger)
            await trigger.bot.mod_log(
                content=self.content,
                icon=emoji,
                icon_url=icon,
                color=color,
                show_timestamp=True,
                server=trigger.state.server,
                channel=channel,
                notify_roles=notify_roles,
                footer_text=title,
                fields=self.fields,
                compact=compact,
            )
            if self.quote_message:
                await trigger.bot.quote_message(
                    destination=channel, message=trigger.message, exclude_extras=True
                )
