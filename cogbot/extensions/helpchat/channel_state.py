import typing

import discord


class ChannelState:
    def __init__(
        self,
        emoji: str,
        name_format: str,
        description_format: str,
        category: discord.Channel,
    ):
        self.emoji: str = emoji
        self.name_format: str = name_format
        self.description_format: str = description_format
        self.category: discord.Channel = category

    def format_name(
        self, key: str, channel: discord.Channel, asker: discord.User = None
    ) -> str:
        return self.emoji + self.name_format.format(
            key=key, channel=channel, asker=asker.name if asker else "someone"
        )

    def format_description(
        self, channel: discord.Channel, asker: discord.User = None
    ) -> str:
        return self.description_format.format(channel=channel, asker=asker)

    def matches(self, channel: discord.Channel) -> bool:
        return channel.name.startswith(self.emoji)
