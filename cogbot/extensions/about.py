import logging

from discord.ext import commands

from cogbot.cog_bot import CogBot


log = logging.getLogger(__name__)


def _load_authors(repo_url: str):
    log.info('attempting to dynamically load authors...')

    try:
        if repo_url.startswith('https://github.com'):
            import re
            url_pattern = re.compile('https://github.com/(\w*)/(\w*)')
            url_matches = url_pattern.findall(repo_url)
            user = url_matches[0][0]
            repo = url_matches[0][1]
            url = f'https://api.github.com/repos/{user}/{repo}/contributors'
            log.info(f'  from: {url}')

            import urllib.request
            response = urllib.request.urlopen(url)
            content = response.read().decode('utf8')

            import json
            contributors = json.loads(content)
            contributors = sorted(contributors, key=lambda d: -d['contributions'])
            # total_ctbs = sum([ctb['contributions'] for ctb in contributors])
            authors = []
            for ctb in contributors:
                name = ctb['login']
                contribs = ctb['contributions']
                page = f'{repo_url}/commits?author={name}'
                authors.append(f'**{name}** with {contribs} contributions: <{page}>')
                log.info(f'dynamically loaded {len(authors)} authors')

            return authors

        raise ValueError('unrecognized repo url')

    except Exception as e:
        log.info(f'could not load authors dynamically: {e}')


class AboutConfig:
    def __init__(self, **options):
        self.description = options.pop('description', '')
        self.repo_url = options.pop('repo_url', '')
        self.authors = options.pop('authors', _load_authors(self.repo_url))

        message = self.description

        if self.repo_url:
            message += f'\n\nMy code: {self.repo_url}'

        if self.authors:
            author_str = '\n'.join(f'- {author}' for author in self.authors)
            message += f'\n\nMy creators:\n{author_str}'

        self.message = message


class About:
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        options = bot.config.get_extension_options(__name__) if isinstance(bot, CogBot) else {}
        options['description'] = options.get('description', bot.description)
        self.config = AboutConfig(**options)

    @commands.command()
    async def about(self):
        await self.bot.say(self.config.message)


def setup(bot):
    bot.add_cog(About(bot))
