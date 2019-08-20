import typing
from datetime import datetime, timedelta

import discord
from discord.iterators import LogsFromIterator

from cogbot.cog_bot import CogBot


class HelpChat:
    def __init__(self, bot: CogBot, ext: str):
        self.bot: CogBot = bot
        options = bot.state.get_extension_state(ext)
        self.message_with_channel = options["message_with_channel"]
        self.message_without_channel = options["message_without_channel"]
        self.channels = options["channels"]
        self.threshold = options.get("threshold", 3600)
        self.redirect_emoji = options.get("redirect_emoji", "🛴")
        self.mark_free_emoji = options.get("mark_free_emoji", "✅")
        self.mark_busy_emoji = options.get("mark_busy_emoji", "💬")
        self.free_prefix = options.get("free_prefix", "✅")
        self.busy_prefix = options.get("busy_prefix", "💬")

    def get_managed_channel_ids_for_server(self, server: discord.Server) -> typing.List:
        return self.channels.get(server.id, [])

    def get_managed_channels_for_server(
        self, server: discord.Server
    ) -> typing.List[discord.Channel]:
        return [
            self.bot.get_channel(channel_id)
            for channel_id in self.get_managed_channel_ids_for_server(server)
        ]

    def is_managed_channel(self, channel: discord.Channel) -> bool:
        return channel.id in self.get_managed_channel_ids_for_server(channel.server)

    def is_channel_free(self, channel: discord.Channel) -> bool:
        return self.is_managed_channel(channel) and channel.name.startswith(
            self.free_prefix
        )

    def is_channel_busy(self, channel: discord.Channel) -> bool:
        return self.is_managed_channel(channel) and channel.name.startswith(
            self.busy_prefix
        )

    async def is_channel_stale(self, now: datetime, channel: discord.Channel) -> bool:
        async for message in self.bot.logs_from(channel, limit=1):
            then: datetime = message.timestamp + timedelta(seconds=self.threshold)
            if now > then:
                return True
        return False

    async def get_free_channel(self, server: discord.Server) -> discord.Channel:
        for channel in self.get_managed_channels_for_server(server):
            if self.is_channel_free(channel):
                return channel

    async def redirect(self, message: discord.Message):
        free_channel = await self.get_free_channel(message.server)
        if free_channel:
            response = self.message_with_channel.format(
                author=message.author.mention, channel=free_channel.mention
            )
        else:
            response = self.message_without_channel.format(
                author=message.author.mention
            )
        await self.bot.send_message(message.channel, response)

    async def try_mark_free(self, channel: discord.Channel):
        if self.is_channel_busy(channel):
            await self.bot.edit_channel(
                channel, name=self.free_prefix + channel.name[len(self.busy_prefix) :]
            )

    async def try_mark_busy(self, channel: discord.Channel):
        if self.is_channel_free(channel):
            await self.bot.edit_channel(
                channel, name=self.busy_prefix + channel.name[len(self.free_prefix) :]
            )

    async def on_reaction_add(
        self, reaction: discord.Reaction, reactor: discord.Member
    ):
        if reactor != self.bot and reaction.count == 1:
            # redirect author to a free channel
            if reaction.emoji == self.redirect_emoji:
                await self.redirect(reaction.message)
            # mark channel as free, if applicable
            if reaction.emoji == self.mark_free_emoji:
                await self.try_mark_free(reaction.message.channel)
            # mark channel as busy, if applicable
            if reaction.emoji == self.mark_busy_emoji:
                await self.try_mark_busy(reaction.message.channel)

    async def on_message(self, message: discord.Message):
        # mark channel as busy, if applicable
        await self.try_mark_busy(message.channel)


def setup(bot):
    bot.add_cog(HelpChat(bot, __name__))
