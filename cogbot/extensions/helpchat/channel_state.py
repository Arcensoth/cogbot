import typing

import discord


class ChannelState:
    def __init__(self, emoji: str, name_format: str, category: discord.Channel):
        self.emoji: str = emoji
        self.name_format: str = name_format
        self.category: discord.Channel = category

    def format(self, key: str, asker: discord.User = None) -> str:
        return self.emoji + self.name_format.format(
            key=key, asker=asker.name if asker else "someone"
        )

    def matches(self, channel: discord.Channel) -> bool:
        return channel.name.startswith(self.emoji)
