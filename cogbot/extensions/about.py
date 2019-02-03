import logging

from cogbot import checks
from discord.ext import commands
from discord.ext.commands import Context

from cogbot.cog_bot import CogBot

log = logging.getLogger(__name__)

BASE_REPOS = [
    "https://github.com/Arcensoth/cogbot",
    "https://github.com/Rapptz/discord.py"
]


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
        self.about_message = ''

    async def make_about_message(self):
        parts = [
            f'About {self.bot.user.mention}:',
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

            managers_str = '**Managed by**:\n    - ' + '\n    - '.join(m for m in managers)
            parts.append(managers_str)

        actual_repos = self.config.repos + BASE_REPOS

        repos_str = '**Powered by**:\n    - <' + '>\n    - <'.join(repo for repo in actual_repos) + '>'
        parts.append(repos_str)

        about_message = '\n\n'.join(parts)

        return about_message

    async def reload_about_message(self):
        log.info('reloading about message...')
        self.about_message = await self.make_about_message()
        log.info('about message has been reloaded')

    async def on_ready(self):
        await self.reload_about_message()

    @commands.group(pass_context=True, name='about')
    async def cmd_about(self, ctx: Context):
        if ctx.invoked_subcommand is None:
            message = await self.bot.say('_')
            await self.bot.edit_message(message, f'{ctx.message.author.mention} {self.about_message}')

    @checks.is_manager()
    @cmd_about.command(pass_context=True, name='reload', hidden=True)
    async def cmd_about_reload(self, ctx: Context):
        await self.reload_about_message()
        await self.bot.react_success(ctx)


def setup(bot):
    bot.add_cog(About(bot, __name__))
