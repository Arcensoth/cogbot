import asyncio
import logging
import datetime
import time
from typing import Dict

import feedparser
from discord import Channel
from discord.ext import commands
from discord.ext.commands import Context

from cogbot import checks
from cogbot.cog_bot import CogBot

log = logging.getLogger(__name__)


def struct_time_to_datetime(ts: time.struct_time) -> datetime.datetime:
    return datetime.datetime.fromtimestamp(time.mktime(ts))


class FeedSubscription:
    DEFAULT_LAST_TIMESTAMP = datetime.datetime.now()

    def __init__(self, url: str, last_datetime: datetime.datetime = DEFAULT_LAST_TIMESTAMP):
        self.url = url
        self.last_datetime = last_datetime

    def update(self):
        try:
            data = feedparser.parse(self.url)
            channel_datetime = struct_time_to_datetime(data.feed.updated_parsed)
            num_updates = 0

            # Only bother checking entries if the feed has been updated.
            if channel_datetime > self.last_datetime:
                for entry in data.entries:
                    # Try first for the published timestamp, then for the updated timestamp.
                    entry_datetime = struct_time_to_datetime(entry.get('published_parsed', entry.updated_parsed))
                    # Yield the entry only if it has been updated since our last update.
                    if entry_datetime > self.last_datetime:
                        num_updates += 1
                        yield entry
                self.last_datetime = channel_datetime

            if num_updates > 0:
                log.info(f'Updated {num_updates} entries for feed at: {self.url}')

        except:
            log.exception(f'Failed to parse feed at: {self.url}')


class Feed:
    DEFAULT_POLLING_INTERVAL = 60
    DEFAULT_FEED_RECENCY = 0

    def __init__(self, bot: CogBot, ext: str):
        self.bot = bot

        self.options = bot.state.get_extension_state(ext)

        self.polling_interval: int = self.options.get('polling_interval', self.DEFAULT_POLLING_INTERVAL)
        self.feed_recency: int = self.options.get('feed_recency', self.DEFAULT_FEED_RECENCY)

        # Access like so: self.subscriptions[channel_id][name]
        self.subscriptions: Dict[str, Dict[str, FeedSubscription]] = {}

        self.polling_task = None

    async def on_ready(self):
        # Initialize subscriptions.

        raw_subscriptions: Dict[str, Dict[str, str]] = self.options.get('subscriptions', {})

        log.info(f'Initializing subscriptions for {len(raw_subscriptions)} channels...')

        for channel_id, v in raw_subscriptions.items():
            channel = self.bot.get_channel(channel_id)
            for name, url in v.items():
                try:
                    self._add_feed(channel, name, url)
                except:
                    log.exception(f'Failed to add initial feed {name} at: {url}')

        # Start the polling task.
        self.polling_task = self.bot.loop.create_task(self._loop_poll())

    async def _loop_poll(self):
        while self.bot.is_logged_in:
            await self.update_all_feeds()
            await asyncio.sleep(self.polling_interval)
        log.info('Bot logged out, polling loop terminated')

    def _add_feed(self, channel: Channel, name: str, url: str):
        last_datetime = None
        if self.feed_recency:
            last_datetime = datetime.datetime.now() - datetime.timedelta(seconds=self.feed_recency)

        sub = FeedSubscription(url, last_datetime)

        if channel.id not in self.subscriptions:
            self.subscriptions[channel.id] = {}

        subs = self.subscriptions[channel.id]

        log.info(f'[{channel.server.name}#{channel.name}] Subscribing to feed {name} at: {sub.url}')

        subs[name] = sub

    def _remove_feed(self, channel: Channel, name: str):
        subs = self.subscriptions[channel.id]
        sub = subs[name]

        log.info(f'[{channel.server.name}#{channel.name}] Unsubscribing from feed {name} at: {sub.url}')

        del subs[name]

    async def _update_feed(self, channel: Channel, name: str):
        subs = self.subscriptions[channel.id]
        sub = subs[name]

        for entry in sub.update():
            log.info(f'Found an update for feed {name}: {entry.title}')
            message = f'**{entry.title}**\n{entry.link}'
            await self.bot.send_message(channel, message)

    async def add_feed(self, ctx: Context, name: str, url: str):
        channel = ctx.message.channel
        subs = self.subscriptions.get(channel.id)

        if name not in subs:
            try:
                self._add_feed(channel, name, url)
                await self.bot.react_success(ctx)
            except:
                log.exception(f'Failed to add new feed {name} at: {url}')
                await self.bot.react_failure(ctx)
        else:
            await self.bot.react_neutral(ctx)

    async def remove_feed(self, ctx: Context, name: str):
        channel = ctx.message.channel
        subs = self.subscriptions.get(channel.id)

        if name in subs:
            self._remove_feed(channel, name)
            await self.bot.react_success(ctx)

        else:
            await self.bot.react_neutral(ctx)

    async def list_feeds(self, ctx: Context):
        channel = ctx.message.channel
        subs = self.subscriptions.get(channel.id)

        if subs:
            subs_str = '\n'.join([f'  - {name}: {sub.url}' for name, sub in subs.items()])
            reply = f'Subscribed feeds:\n{subs_str}'

        else:
            reply = f'No subscribed feeds.'

        await self.bot.send_message(ctx.message.channel, reply)

    async def update_feeds(self, ctx: Context, *names):
        """ Update only the given feeds for the channel in context. """
        channel = ctx.message.channel
        for name in names:
            await self._update_feed(channel, name)
        await self.bot.react_success(ctx)

    async def update_all_feeds(self):
        """ Update all feeds for all channels. """
        for channel_id, subs in self.subscriptions.items():
            channel = self.bot.get_channel(channel_id)
            for name, sub in subs.items():
                await self._update_feed(channel, name)

    @checks.is_manager()
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
