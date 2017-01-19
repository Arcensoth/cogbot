import logging

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
        self.host = options.pop('host', '')
        self.repos = options.pop('repos', [])


class About:
    def __init__(self, bot: CogBot, ext: str):
        self.bot = bot
        options = bot.config.get_extension_options(ext)
        options['description'] = options.get('description', bot.description)
        self.config = AboutConfig(**options)
        self.about_message = ''

    async def make_about_message(self):
        parts = [self.config.description]

        if self.config.host:
            try:
                host_user = await self.bot.get_user_info(self.config.host)
                host_mention = host_user.mention
            except:
                host_mention = self.config.host

            host_str = f'**My host**: {host_mention}'
            parts.append(host_str)

        actual_repos = self.config.repos + BASE_REPOS

        repos_str = '**My code**:\n- ' + '\n- '.join(repo for repo in actual_repos)
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
            await self.bot.say(self.about_message)

    @cmd_about.command(pass_context=True, name='reload')
    async def cmd_about_reload(self, ctx: Context):
        await self.reload_about_message()
        await self.bot.react_success(ctx)


def setup(bot):
    bot.add_cog(About(bot, __name__))
