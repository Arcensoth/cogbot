import json
import logging
import urllib.request

from discord.ext import commands
from discord.ext.commands import CommandError, Context

from cogbot import checks
from cogbot.cog_bot import CogBot

log = logging.getLogger(__name__)


class FaqConfig:
    def __init__(self, **options):
        self.database = options['database']


class Faq:
    def __init__(self, bot: CogBot, ext: str):
        self.bot = bot
        options = bot.state.get_extension_state(ext)
        self.config = FaqConfig(**options)
        self.data = {}

    def get_answer_by_key(self, key: str):
        return self.data.get(key)

    def get_all_keys(self):
        return self.data.keys()

    def reload_data(self):
        log.info('Reloading FAQs from: {}'.format(self.config.database))

        response = urllib.request.urlopen(self.config.database)
        content = response.read().decode('utf8')

        try:
            data = json.loads(content)
        except Exception as e:
            raise CommandError('Failed to reload FAQs: {}'.format(e))

        self.data = data

        log.info('Successfully reloaded {} FAQs'.format(len(data)))

    async def on_ready(self):
        self.reload_data()

    @commands.command(pass_context=True, name='faq')
    async def cmd_faq(self, ctx: Context, *, key: str = ''):
        if key:
            answer = self.get_answer_by_key(key)
            if answer:
                await self.bot.say(answer)
            else:
                await self.bot.add_reaction(ctx.message, u'🤷')

        else:
            await self.bot.say(', '.join(self.get_all_keys()))

    @checks.is_manager()
    @commands.command(pass_context=True, name='faqreload', hidden=True)
    async def cmd_faqreload(self, ctx: Context):
        try:
            self.reload_data()
            await self.bot.react_success(ctx)
        except:
            await self.bot.react_failure(ctx)


def setup(bot):
    bot.add_cog(Faq(bot, __name__))
