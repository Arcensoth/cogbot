import json
import logging
import urllib.request

from discord.ext import commands
from discord.ext.commands import CommandError, Context

from cogbot import checks
from cogbot.cog_bot import CogBot

log = logging.getLogger(__name__)

BASE_REPOS = [
    "https://github.com/Arcensoth/cogbot",
    "https://github.com/Rapptz/discord.py"
]

CONTRIBUTORS_FILE = "https://raw.githubusercontent.com/Arcensoth/cogbot/master/CONTRIBUTORS.json"


class AboutConfig:
    def __init__(self, **options):
        self.description = options.pop('description', '')
        self.repos = options.pop('repos', [])


class About:
    def __init__(self, bot: CogBot, ext: str):
        self.bot = bot
        options = bot.state.get_extension_state(ext)
        options['description'] = options.get('description', bot.description)
        self.config = AboutConfig(**options)

    async def make_about_message(self, ctx: Context):
        parts = [
            self.config.description
        ]

        if self.bot.state.managers:
            managers = []

            for manager in self.bot.state.managers:
                try:
                    manager_user = await self.bot.get_user_info(manager)
                    manager_mention = manager_user.mention
                except:
                    manager_mention = manager
                managers.append(manager_mention)

            managers_str = '**Managers**:\n    - ' + '\n    - '.join(managers)
            parts.append(managers_str)

        contributors_data = {}
        contributors = []

        try:
            response = urllib.request.urlopen(CONTRIBUTORS_FILE)
            content = response.read().decode('utf8')
            contributors_data  = json.loads(content)
        except Exception as e:
            raise CommandError('Failed to load contributors: {}'.format(e))

        for contrib_data in contributors_data:
            try:
                contrib_name = contrib_data.get('name')
                contrib_tag = contrib_data.get('tag')
                contrib_id = contrib_data.get('id')
                contrib_member = ctx.message.channel.server.get_member(contrib_id)
                if contrib_member:
                    contributors.append(contrib_member.mention)
                else:
                    contributors.append(contrib_tag or contrib_name)
            except:
                log.error(f'Failed to resolve contributor: {contrib_data}')

        if contributors:
            contributors_str = '**Contributors**:\n    - ' + '\n    - '.join(contributors)
            parts.append(contributors_str)

        actual_repos = self.config.repos + BASE_REPOS

        repos_str = '**Repositories**:\n    - <' + '>\n    - <'.join(repo for repo in actual_repos) + '>'
        parts.append(repos_str)

        about_message = '\n\n'.join(parts)

        return about_message

    @commands.group(pass_context=True, name='about')
    async def cmd_about(self, ctx: Context):
        if ctx.invoked_subcommand is None:
            text = await self.make_about_message(ctx)
            message = await self.bot.say('🤖')
            await self.bot.edit_message(message, text)


def setup(bot):
    bot.add_cog(About(bot, __name__))
