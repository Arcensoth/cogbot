import itertools
import json
import logging
import typing
import urllib.request

import discord
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
        self.invites_by_server_id: typing.Dict[str, discord.Invite] = {}
        self.invites_by_tag: typing.Dict[str, typing.Set[discord.Invite]] = {}

    async def reload_data(self):
        log.info('Reloading invites from: {}'.format(self.config.database))

        response = urllib.request.urlopen(self.config.database)
        content = response.read().decode('utf8')

        try:
            data = json.loads(content)
        except Exception as e:
            raise CommandError('Failed to reload invites: {}'.format(e))

        # dynamically reload servers using the invites
        invites_by_server_id = {}
        invites_by_tag = {}
        for raw_entry in data:
            invite_url = raw_entry['invite']
            invite: discord.Invite = await self.bot.get_invite(invite_url)
            server: discord.Server = invite.server
            server_id = server.id
            invites_by_server_id[server_id] = invite
            raw_tags: str = raw_entry.get('tags')
            if raw_tags:
                for tag in raw_tags.lower().split():
                    if tag not in invites_by_tag:
                        invites_by_tag[tag] = set()
                    invites_by_tag[tag].add(invite)

        self.invites_by_server_id = invites_by_server_id
        self.invites_by_tag = invites_by_tag

        log.info('Successfully reloaded {} invites'.format(len(invites_by_server_id)))

    def get_invites_by_tag(self, tag: str) -> typing.Set[discord.Invite]:
        return self.invites_by_tag.get(tag, set())
    
    def get_invites_by_tags(self, tags: str) -> typing.Set[discord.Invite]:
        results = [self.get_invites_by_tag(tag) for tag in tags.split()]
        result = set().union(*results)
        return result

    def get_invite_by_server_id(self, server_id: str) -> discord.Invite:
        return self.invites_by_server_id.get(server_id)

    async def on_ready(self):
        await self.reload_data()

    @commands.group(pass_context=True, name='invite')
    async def cmd_invite(self, ctx: Context, *, tags: str = ''):
        # given tags, use them to look-up servers by tag
        if tags:
            invites = self.get_invites_by_tags(tags)
            if invites:
                await self.bot.say('\n'.join(invite.url for invite in invites))
            else:
                await self.bot.add_reaction(ctx.message, u'🤷')

        # no name, lookup current server
        else:
            # check if there's an invite for the current server
            invite: discord.Invite = self.get_invite_by_server_id(ctx.message.server.id)
            if invite:
                await self.bot.say(invite.url)

            # otherwise can't do anything
            else:
                await self.bot.add_reaction(ctx.message, u'😭')

    @commands.command(pass_context=True, name='invites')
    async def cmd_invites(self, ctx: Context):
        message = '\n'.join(invite.url for invite in self.invites_by_server_id.values())
        await self.bot.say(message)

    @checks.is_manager()
    @commands.command(pass_context=True, name='invitereload', hidden=True)
    async def cmd_invitereload(self, ctx: Context):
        try:
            await self.reload_data()
            await self.bot.react_success(ctx)
        except:
            await self.bot.react_failure(ctx)


def setup(bot):
    bot.add_cog(Invite(bot, __name__))
