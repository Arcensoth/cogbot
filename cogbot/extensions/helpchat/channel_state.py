import typing

import discord


class ChannelState:
    def __init__(self, emoji: str, name_format: str):
        self.emoji: str = emoji
        self.name_format: str = name_format

    def format(self, key: str = None, first: bool = False) -> str:
        return self.emoji +  self.name_format.format(key=key)

    def matches(self, channel: discord.Channel) -> bool:
        return channel.name.startswith(self.emoji)
