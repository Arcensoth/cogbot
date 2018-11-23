import json
import logging
import typing
import urllib.request

from discord.ext import commands
from discord.ext.commands import CommandError, Context

from cogbot import checks
from cogbot.cog_bot import CogBot

log = logging.getLogger(__name__)


class FAQEntry:
    def __init__(self, key: str, tags: typing.Iterable[str], message: str, hidden: bool = False):
        self.key: str = str(key)
        self.tags: typing.Set[str] = set(tags)
        self.message: str = str(message)
        self.hidden: bool = hidden


class FaqConfig:
    def __init__(self, **options):
        self.database: str = str(options['database'])


class Faq:
    def __init__(self, bot: CogBot, ext: str):
        self.bot = bot
        self.config = FaqConfig(**bot.state.get_extension_state(ext))
        self.entries_by_key: typing.Dict[str, FAQEntry] = {}
        self.entries_by_tag: typing.Dict[str, typing.List[FAQEntry]] = {}
        self.available_faqs_text = ''

    def extract_tags(self, key: str) -> typing.List[str]:
        return [k[1:] if k.startswith('#') else k for k in key.split()]

    def format_keys(self, keys: typing.Iterable[str]) -> str:
        return ''.join(('`', '`, `'.join(keys), '`'))

    def get_all_keys(self):
        return self.entries_by_key.keys()

    def get_visible_keys(self):
        return (key for key, entry in self.entries_by_key.items() if not entry.hidden)

    def get_entry_by_key(self, key: str) -> FAQEntry:
        return self.entries_by_key.get(key)

    def get_entries_by_tag(self, tag: str) -> typing.List[FAQEntry]:
        return self.entries_by_tag.get(tag)

    def get_entries_by_tags(self, tags: typing.Iterable[str]) -> typing.List[FAQEntry]:
        tags_tuple = tuple(tags)
        tags_set = set(tags_tuple)
        initial_entries = self.get_entries_by_tag(tags_tuple[0])
        # start with all results for the first tag
        # take the intersection of remaining queries
        if initial_entries:
            return [entry for entry in initial_entries if tags_set.issubset(entry.tags)]
        else:
            return []

    def get_entries_cascading(self, key: str) -> typing.List[FAQEntry]:
        # see if there's an exact match
        # if not, split the key into tags and search by those
        entry = self.get_entry_by_key(key)
        if entry:
            return [entry]
        else:
            return self.get_entries_by_tags(key.split())

    def get_entries_strict(self, key: str) -> typing.List[FAQEntry]:
        # only check tags if the key starts with a hashtag
        # otherwise look for the exact key
        if key.startswith('#'):
            return self.get_entries_by_tags(self.extract_tags(key))
        else:
            entry = self.get_entry_by_key(key)
            if entry:
                return [entry]
            else:
                return []

    def reload_data(self):
        log.info('Reloading FAQs from: {}'.format(self.config.database))

        if self.config.database.startswith(('http://', 'https://')):
            try:
                response = urllib.request.urlopen(self.config.database)
                content = response.read().decode('utf8')
                data = json.loads(content)
            except Exception as e:
                raise CommandError('Failed to reload FAQs: {}'.format(e))
        else:
            with open(self.config.database) as fp:
                data = json.load(fp)

        # parse data and precompile messages
        # also create map of tags to entries
        entries_by_key: typing.Dict[FAQEntry] = {}
        entries_by_tag: typing.Dict[typing.List[FAQEntry]] = {}
        for key, raw_entry in data.items():
            # list becomes lines
            raw_message = raw_entry['message']
            message = '\n'.join(raw_message) if isinstance(raw_message, list) else str(raw_message)
            # tags are split by whitespace
            tags = raw_entry.get('tags', '').split()
            hidden = raw_entry.get('hidden')
            entry = FAQEntry(key=key, tags=tags, message=message, hidden=hidden)
            entries_by_key[key] = entry
            for tag in tags:
                if tag not in entries_by_tag:
                    entries_by_tag[tag] = []
                entries_by_tag[tag].append(entry)

        self.entries_by_key = entries_by_key
        self.entries_by_tag = entries_by_tag

        self.available_faqs_text = 'Available FAQs: ' + self.format_keys(sorted(self.get_visible_keys()))

        log.info('Successfully reloaded {} FAQs'.format(len(data)))

    async def on_ready(self):
        self.reload_data()

    @commands.command(pass_context=True, name='faq')
    async def cmd_faq(self, ctx: Context, *, key: str = ''):
        if key:
            entries = self.get_entries_strict(key)
            if entries:
                for entry in entries:
                    await self.bot.say(entry.message)
            else:
                suggest_entries = self.get_entries_by_tags(key.split())
                if suggest_entries:
                    await self.bot.add_reaction(ctx.message, u'🤔')
                    suggest_text = 'Maybe you meant: ' + self.format_keys(entry.key for entry in suggest_entries)
                    await self.bot.say(suggest_text)
                else:
                    await self.bot.add_reaction(ctx.message, u'🤷')

        else:
            await self.bot.say(self.available_faqs_text)

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
