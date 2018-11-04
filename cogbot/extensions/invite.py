import json
import logging
import urllib.request

from discord.ext import commands
from discord.ext.commands import CommandError, Context

from cogbot import checks
from cogbot.cog_bot import CogBot

log = logging.getLogger(__name__)


class InviteConfig:
    def __init__(self, **options):
        self.database = options['database']


class Invite:
    def __init__(self, bot: CogBot, ext: str):
        self.bot = bot
        options = bot.state.get_extension_state(ext)
        self.config = InviteConfig(**options)
        self.data = {}
        self.entries_by_server_id = {}
        self.entries_by_name = {}

    @staticmethod
    def _make_entries_by_server_id(raw_entries):
        # case insensitive
        return {str(raw_entry['server_id']).lower(): raw_entry for raw_entry in raw_entries}

    @staticmethod
    def _make_entries_by_name(raw_entries):
        entries = {}
        for raw_entry in raw_entries:
            # case insensitive
            keys = [str(key).lower() for key in raw_entry['keys']]
            for key in keys:
                if key not in entries:
                    entries[key] = []
                entries[key].append(raw_entry)
        return entries

    def get_entry_by_server_id(self, server_id: str):
        return self.entries_by_server_id.get(server_id)

    def get_entries_by_name(self, name: str):
        return self.entries_by_name.get(name.lower())

    def reload_data(self):
        log.info('Reloading invites from: {}'.format(self.config.database))

        response = urllib.request.urlopen(self.config.database)
        content = response.read().decode('utf8')

        try:
            data = json.loads(content)
        except Exception as e:
            raise CommandError('Failed to reload invites: {}'.format(e))

        self.data = data
        self.entries_by_server_id = self._make_entries_by_server_id(data)
        self.entries_by_name = self._make_entries_by_name(data)

        log.info('Successfully reloaded {} invites'.format(len(data)))

    async def on_ready(self):
        self.reload_data()

    @commands.group(pass_context=True, name='invite')
    async def cmd_invite(self, ctx: Context, *, name: str = ''):
        # given name, use it as a key to lookup another server
        if name:
            entries = self.get_entries_by_name(name)
            if entries:
                await self.bot.say('\n'.join(entry['invite'] for entry in entries))
            else:
                await self.bot.add_reaction(ctx.message, u'🤷')

        # no name, lookup current server
        else:
            # check if there's an invite for the current server
            entry = self.get_entry_by_server_id(ctx.message.server.id)
            if entry:
                await self.bot.say(entry['invite'])

            # otherwise can't do anything
            else:
                await self.bot.add_reaction(ctx.message, u'😭')

    @checks.is_manager()
    @commands.command(pass_context=True, name='invitereload', hidden=True)
    async def cmd_invitereload(self, ctx: Context):
        try:
            self.reload_data()
            await self.bot.react_success(ctx)
        except:
            await self.bot.react_failure(ctx)


def setup(bot):
    bot.add_cog(Invite(bot, __name__))
