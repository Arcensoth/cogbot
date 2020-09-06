import logging
import typing
from datetime import datetime

import discord

from cogbot.types import ChannelId, RoleId

log = logging.getLogger(__name__)


class CogBotServerState:
    def __init__(self, bot, server: discord.Server, log_channel: ChannelId = None):
        self.bot = bot
        self.server: discord.Server = server

        # resolve log channel
        self.log_channel: discord.Channel = None
        if log_channel:
            self.log_channel = self.bot.get_channel(log_channel)
            if not self.log_channel:
                log.warning(
                    f"[{self.server}] Failed to resolve log channel <{log_channel}>"
                )

    async def mod_log(
        self,
        member: discord.Member = None,
        content: str = None,
        message: discord.Message = None,
        icon: str = None,
        title: str = None,
        icon_url: str = None,
        color: int = None,
        show_timestamp: bool = True,
        channel: discord.Channel = None,
        footer_text: str = None,
        notify_roles: typing.Iterable[discord.Role] = None,
        fields: typing.Dict[str, str] = None,
    ):
        actual_channel = channel or self.log_channel
        if self.log_channel:
            color = color or discord.Embed.Empty

            description_parts = []
            if member:
                description_parts.append(str(member.mention))
            if content:
                description_parts.append(content)
            description = " ".join(description_parts)

            if message:
                message_link = self.bot.make_message_link(message)
                icon = icon or ":arrow_right:"
                icon = f"[{icon}]({message_link})"

            if icon and not title:
                description = f"{icon} {description}"

            em = discord.Embed(description=description, color=color)

            if title:
                em.set_author(name=title, icon_url=icon_url)

            if fields:
                for field_name, field_value in fields.items():
                    em.add_field(name=field_name, value=field_value, inline=False)

            if show_timestamp:
                em.timestamp = datetime.utcnow()

            if footer_text:
                em.set_footer(text=footer_text, icon_url=icon_url)
            elif member and message:
                em.set_footer(
                    text=f"{member} in #{message.channel}", icon_url=member.avatar_url
                )
            elif member:
                em.set_footer(text=f"{member}", icon_url=member.avatar_url)

            outside_content = None
            if notify_roles:
                roles_mention_str = " ".join(
                    [f"{role.mention}" for role in notify_roles]
                )
                outside_content = f"{roles_mention_str}"

            await self.bot.send_message(
                actual_channel, content=outside_content, embed=em
            )
