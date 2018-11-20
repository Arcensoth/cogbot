import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict

import feedparser
from dateutil.parser import parse as dateutil_parse
from discord import Channel
from discord.ext import commands
from discord.ext.commands import Context

from cogbot import checks
from cogbot.cog_bot import CogBot

log = logging.getLogger(__name__)


class FeedSubscription:
    def __init__(self, name: str, url: str, recency: int = 0):
        self.name = name
        self.url = url
        self.recency = recency

        self.last_datetime = datetime.now(timezone.utc)
        self.last_titles = {}
        self.last_ids = {}

        if self.recency:
            self.last_datetime -= timedelta(seconds=self.recency)

    def update(self):
        try:
            # parse feed and datetime
            data = feedparser.parse(self.url)
            channel_datetime = dateutil_parse(data.feed.updated).astimezone(timezone.utc)

            # keep a record of last-updated articles to help eliminate duplication
            next_last_titles = set()
            next_last_ids = set()

            # don't bother checking entries unless the entire feed has been updated since our last check
            if channel_datetime > self.last_datetime:

                for entry in data.entries:
                    # try first the published datetime, then updated datetime
                    entry_datetime = dateutil_parse(entry.get('published', entry.updated))
                    entry_id = entry.id or entry.get('id', entry.get('guid'))
                    entry_title = entry.title or entry.get('title')

                    # calculate whether the entry is fresh/new
                    is_fresh = (entry_datetime > self.last_datetime) \
                               and (entry_title not in self.last_titles) \
                               and (entry_id not in self.last_ids)

                    # if it is fresh, add it to the records for the next iteration... and yield
                    if is_fresh:
                        next_last_titles.add(entry_title)
                        next_last_ids.add(entry_id)
                        yield entry

            # update timestamp and records for future iterations
            self.last_datetime = channel_datetime
            self.last_titles = next_last_titles
            self.last_ids = next_last_ids

        except:
            log.exception(f'Failed to parse feed at: {self.url}')


class Feed:
    DEFAULT_POLLING_INTERVAL = 60

    def __init__(self, bot: CogBot, ext: str):
        self.bot = bot

        self.options = bot.state.get_extension_state(ext)

        self.polling_interval: int = self.options.get('polling_interval', self.DEFAULT_POLLING_INTERVAL)

        # Access like so: self.subscriptions[channel_id][name]
        self.subscriptions: Dict[str, Dict[str, FeedSubscription]] = {}

        self.polling_task = None

    async def on_ready(self):
        # Initialize subscriptions.

        # Clear any existing subscriptions.
        self.subscriptions = {}

        raw_subscriptions = self.options.get('subscriptions', {})

        log.info(f'Initializing subscriptions for {len(raw_subscriptions)} channels...')

        for channel_id, v in raw_subscriptions.items():
            channel = self.bot.get_channel(channel_id)
            for name, data in v.items():
                url = data['url']
                recency = data.get('recency')
                try:
                    self._add_feed(channel, name, url, recency)
                except:
                    log.exception(f'Failed to add initial feed {name} at: {url}')

        # Start the polling task, if not already started.
        if not self.polling_task:
            self.polling_task = self.bot.loop.create_task(self._loop_poll())

    async def _loop_poll(self):
        while self.bot.is_logged_in:
            await self.update_all_feeds()
            await asyncio.sleep(self.polling_interval)
        log.info('Bot logged out, polling loop terminated')

    def _add_feed(self, channel: Channel, name: str, url: str, recency: int = None):
        # Don't add the same subscription more than once.
        try:
            if name in self.subscriptions[channel.id]:
                log.warning(
                    f'[{channel.server.name}#{channel.name}] Tried to subscribe to feed {name} more than once at: {sub.url}')
                return
        except:
            pass

        sub = FeedSubscription(name, url, recency)

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
        fresh_entries = tuple(sub.update())
        if fresh_entries:
            log.info(f'Found {len(fresh_entries)} new posts for feed at: {sub.url}')
            for entry in fresh_entries:
                log.info(f'Found an update for feed {name}: {entry.title}')
                message = f'**{entry.title}**\n{entry.link}'
                await self.bot.send_message(channel, message)

    async def add_feed(self, ctx: Context, name: str, url: str, recency: int = None):
        channel = ctx.message.channel
        subs = self.subscriptions.get(channel.id)

        if name not in subs:
            try:
                self._add_feed(channel, name, url, recency)
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
    async def cmd_feed_add(self, ctx: Context, name: str, url: str, recency: int = None):
        await self.add_feed(ctx, name, url, recency)

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
