import typing

import discord

DEFAULT_NAME = "{emoji}help-chat-{index}"


class ChannelState:
    def __init__(self, emoji: str, name: str = DEFAULT_NAME):
        self.emoji: str = emoji
        self.name = name

    def format(self, name: str = None, first: bool = False) -> str:
        return self.name.format(emoji=self.emoji, name=name)

    def matches(self, channel: discord.Channel) -> bool:
        return channel.name.startswith(self.emoji)
