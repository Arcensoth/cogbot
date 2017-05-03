import logging
import threading

import asyncio
import feedparser
from discord import Channel
from discord.ext import commands
from discord.ext.commands import Context
from typing import Dict

from cogbot.cog_bot import CogBot

log = logging.getLogger(__name__)


class FeedSubscription:
    def __init__(self, url: str):
        self.url: str = url

        # Grab the initial timestamp.
        data = feedparser.parse(self.url)
        self.timestamp = data.feed.updated_parsed

    def update(self):
        data = feedparser.parse(self.url)
        # Only bother checking entries if the feed has been updated.
        if data.feed.updated_parsed > self.timestamp:
            for entry in data.entries:
                # Yield the entry only if it has been updated since our last update.
                if entry.updated_parsed > self.timestamp:
                    yield entry
            self.timestamp = data.feed.updated_parsed


class Feed:
    DEFAULT_POLLING_INTERVAL = 60

    def __init__(self, bot: CogBot, ext: str):
        self.bot = bot

        self.options = bot.config.get_extension_options(ext)

        self.polling_interval: str = self.options.pop('polling_interval', self.DEFAULT_POLLING_INTERVAL)

        # Access like so: self.subscriptions[channel_id][name]
        self.subscriptions: Dict[str, Dict[str, FeedSubscription]] = {}

        # TODO use purely asyncio, not threading, if possible

        self.stop_event = threading.Event()

        event_loop = asyncio.get_event_loop()

        def loop():
            while not self.stop_event.wait(self.polling_interval):
                event_loop.call_soon_threadsafe(asyncio.async, self._update_feeds())

        self.polling_thread = threading.Thread(target=loop)

    async def on_ready(self):
        # Initialize subscriptions.

        raw_subscriptions: Dict[str, Dict[str, str]] = self.options.pop('subscriptions', {})

        log.info(f'Initializing subscriptions for {len(raw_subscriptions)} channels...')

        for channel_id, v in raw_subscriptions.items():
            channel = self.bot.get_channel(channel_id)
            for name, url in v.items():
                self._add_feed(channel, name, url)

        # Start the feed polling thread.
        self.polling_thread.start()

    def _add_feed(self, channel: Channel, name: str, url: str):
        sub = FeedSubscription(url)

        if channel.id not in self.subscriptions:
            self.subscriptions[channel.id] = {}

        subs = self.subscriptions[channel.id]

        log.info(f'[{channel.server.name}#{channel.name}] Subscribing to feed "{name}" at: {sub.url}')

        subs[name] = sub

    def _remove_feed(self, channel: Channel, name: str):
        subs = self.subscriptions[channel.id]
        sub = subs[name]

        log.info(f'[{channel.server.name}#{channel.name}] Unsubscribing from feed "{name}" at: {sub.url}')

        del subs[name]

    async def _update_feed(self, channel: Channel, name: str):
        subs = self.subscriptions[channel.id]
        sub = subs[name]

        for entry in sub.update():
            message = f'**{entry.title}**\n{entry.link}'
            await self.bot.send_message(channel, message)

    async def _update_feeds(self):
        for channel_id, subs in self.subscriptions.items():
            channel = self.bot.get_channel(channel_id)
            for name, sub in subs.items():
                await self._update_feed(channel, name)

    async def add_feed(self, ctx: Context, name: str, url: str):
        channel = ctx.message.channel
        subs = self.subscriptions[channel.id]

        if name not in subs:
            self._add_feed(channel, name, url)
            await self.bot.react_success(ctx)

        else:
            await self.bot.react_neutral(ctx)

    async def remove_feed(self, ctx: Context, name: str):
        channel = ctx.message.channel
        subs = self.subscriptions[channel.id]

        if name in subs:
            self._remove_feed(channel, name)
            await self.bot.react_success(ctx)

        else:
            await self.bot.react_neutral(ctx)

    async def list_feeds(self, ctx: Context):
        channel = ctx.message.channel
        subs = self.subscriptions[channel.id]

        if subs:
            subs_str = '\n'.join([f'  - {name}: {sub.url}' for name, sub in subs.items()])
            reply = f'Subscribed feeds:\n{subs_str}'

        else:
            reply = f'No subscribed feeds.'

        await self.bot.send_message(ctx.message.channel, reply)

    async def update_feeds(self, ctx: Context, *names):
        channel = ctx.message.channel
        for name in names:
            await self._update_feed(channel, name)
        await self.bot.react_success(ctx)

    @commands.group(pass_context=True, name='feed')
    async def cmd_feed(self, ctx: Context):
        if ctx.invoked_subcommand is None:
            await self.list_feeds(ctx)

    @cmd_feed.command(pass_context=True, name='add')
    async def cmd_feed_add(self, ctx: Context, name: str, url: str):
        await self.add_feed(ctx, name, url)

    @cmd_feed.command(pass_context=True, name='remove')
    async def cmd_feed_remove(self, ctx: Context, name: str):
        await self.remove_feed(ctx, name)

    @cmd_feed.command(pass_context=True, name='list')
    async def cmd_feed_list(self, ctx: Context):
        await self.list_feeds(ctx)

    @cmd_feed.command(pass_context=True, name='update')
    async def cmd_feed_update(self, ctx: Context, *names):
        if not names:
            channel = ctx.message.channel
            subs = self.subscriptions[channel.id]
            names = subs.keys()
        await self.update_feeds(ctx, *names)


def setup(bot):
    bot.add_cog(Feed(bot, __name__))
