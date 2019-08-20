import asyncio
import logging
import typing
from datetime import datetime, timedelta

import discord
from discord.iterators import LogsFromIterator

from cogbot.cog_bot import CogBot

log = logging.getLogger(__name__)


class HelpChat:
    def __init__(self, bot: CogBot, ext: str):
        self.bot: CogBot = bot
        options = bot.state.get_extension_state(ext)
        self.message_with_channel = options["message_with_channel"]
        self.message_without_channel = options["message_without_channel"]
        self.channels = options["channels"]
        self.stale_time = options.get("stale_time", 3600)
        self.redirect_emoji = options.get("redirect_emoji", "🛴")
        self.mark_free_emoji = options.get("mark_free_emoji", "✅")
        self.free_prefix = options.get("free_prefix", "✅")
        self.busy_prefix = options.get("busy_prefix", "💬")
        self.stale_prefix = options.get("stale_prefix", "⏰")

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
        return channel.name.startswith(self.free_prefix)

    def is_channel_busy(self, channel: discord.Channel) -> bool:
        return channel.name.startswith(self.busy_prefix)

    def is_channel_stale(self, channel: discord.Channel) -> bool:
        return channel.name.startswith(self.stale_prefix)

    async def poll_for_stale_channels(self):
        while not self.bot.is_closed:
            for server_id in self.channels:
                server: discord.Server = self.bot.get_server(server_id)
                if server:
                    for channel in self.get_managed_channels_for_server(server):
                        if self.is_channel_busy(channel):
                            now: datetime = datetime.utcnow()
                            delta = timedelta(seconds=self.stale_time)
                            async for message in self.bot.logs_from(channel, limit=1):
                                then: datetime = message.timestamp + delta
                            if now > then:
                                await self.bot.edit_channel(
                                    channel,
                                    name=self.stale_prefix
                                    + channel.name[len(self.busy_prefix) :],
                                )
            await asyncio.sleep(10)

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

    async def mark_channel_free(self, channel: discord.Channel):
        if self.is_channel_busy(channel):
            await self.bot.edit_channel(
                channel, name=self.free_prefix + channel.name[len(self.busy_prefix) :]
            )
        elif self.is_channel_stale(channel):
            await self.bot.edit_channel(
                channel, name=self.free_prefix + channel.name[len(self.stale_prefix) :]
            )

    async def mark_channel_busy(self, channel: discord.Channel):
        if self.is_channel_free(channel):
            await self.bot.edit_channel(
                channel, name=self.busy_prefix + channel.name[len(self.free_prefix) :]
            )
        elif self.is_channel_stale(channel):
            await self.bot.edit_channel(
                channel, name=self.busy_prefix + channel.name[len(self.stale_prefix) :]
            )

    async def on_ready(self):
        await self.poll_for_stale_channels()

    async def on_reaction_add(
        self, reaction: discord.Reaction, reactor: discord.Member
    ):
        if reactor != self.bot and reaction.count == 1:
            # redirect author to a free channel
            if reaction.emoji == self.redirect_emoji:
                await self.redirect(reaction.message)

    async def on_message(self, message: discord.Message):
        if self.is_managed_channel(message.channel):
            # free up the channel
            if message.content == self.mark_free_emoji:
                await self.mark_channel_free(message.channel)
                # await self.bot.add_reaction(message, self.mark_free_emoji)
            # otherwise mark it as busy
            else:
                await self.mark_channel_busy(message.channel)


def setup(bot):
    bot.add_cog(HelpChat(bot, __name__))
