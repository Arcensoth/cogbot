import logging
import re
import typing
import urllib.parse
import urllib.request
from datetime import datetime
from xml.etree import ElementTree

from discord import Embed
from discord.ext import commands
from discord.ext.commands import Context

from cogbot.cog_bot import CogBot

log = logging.getLogger(__name__)


class JiraReport:
    def __init__(
            self, id_: int, key: str, base_url: str, url: str, title: str, description: str,
            created_on: datetime, resolved_on: datetime, reporter: str, assignee: str,
            status: str, status_icon_url: str, resolution: str, versions: list, fix_version: str,
            votes: int, watches: int, category: str, priority: str):
        self.id = id_
        self.key = key
        self.base_url = base_url
        self.url = url
        self.title = title
        self.description = description
        self.created_on = created_on
        self.resolved_on = resolved_on
        self.reporter = reporter
        self.assignee = assignee
        self.status = status
        self.status_icon_url = status_icon_url
        self.resolution = resolution
        self.versions = versions
        self.fix_version = fix_version
        self.votes = votes
        self.watches = watches
        self.category = category
        self.priority = priority

    @property
    def since_version(self) -> str:
        return self.versions[0] if (len(self.versions) > 0) else 'Unknown'


class JiraConfig:
    def __init__(self, **options):
        self.base_url = options['base_url']
        self.default_project = str(options['default_project']).upper()


class Jira:
    ID_PATTERN_STR = r'^(\d+)$'
    ID_PATTERN = re.compile(ID_PATTERN_STR, re.IGNORECASE)

    BUG_PATTERN_STR = r'^(\w+)-(\d+)$'
    BUG_PATTERN = re.compile(BUG_PATTERN_STR, re.IGNORECASE)

    URL_PATTERN_STR = r'^(\w+\:\/\/.+)\/browse\/(\w+)-(\d+)$'
    URL_PATTERN = re.compile(URL_PATTERN_STR, re.IGNORECASE)

    REPORT_FIELDS = (
        'link',
        'description',
        'key',
        'summary',
        'status',
        'resolution',
        'assignee',
        'reporter',
        'created',
        'resolved',
        'version',
        'fixVersion',
        'votes',
        'watches',

        # Category
        'customfield_11901',

        # Priority
        'customfield_12200',
    )

    REQUEST_ARGS = '&'.join(f'field={field}' for field in REPORT_FIELDS)

    def __init__(self, bot: CogBot, ext: str):
        self.bot = bot
        self.config = JiraConfig(**bot.state.get_extension_state(ext))

    def fetch_report(self, base_url: str, report_project: str, report_id: int) -> JiraReport:
        report_no = f'{report_project}-{report_id}'

        url = f'{base_url}/si/jira.issueviews:issue-xml/' \
            f'{report_no}/{report_no}.xml?{self.REQUEST_ARGS}'

        log.info(f'Requesting JIRA report XML from: {url}')

        response = urllib.request.urlopen(url)
        content = response.read().decode('utf8')

        # access child 'channel' at index 0
        # and then access child 'item' at index 5
        # this is disguesting
        root = ElementTree.fromstring(content)[0][5]

        # let's make our own thing to clean this up
        raw = {}

        for child in root:
            if child.tag not in raw:
                raw[child.tag] = []
            raw[child.tag].append(child)

        link_tag = raw.get('link')[0]
        description_tag = raw.get('description', [None])[0]
        key_tag = raw.get('key')[0]
        summary_tag = raw.get('summary', [None])[0]
        status_tag = raw.get('status', [None])[0]
        resolution_tag = raw.get('resolution', [None])[0]
        assignee_tag = raw.get('assignee', [None])[0]
        reporter_tag = raw.get('reporter', [None])[0]
        created_tag = raw.get('created')[0]
        resolved_tag = raw.get('resolved', [None])[0]
        version_tags = raw.get('version', [])
        # TODO fix once we figure out why the api doesn't return fixVersion
        fix_version_tag = raw.get('fix_version', [None])[0]
        votes_tag = raw.get('votes')[0]
        watches_tag = raw.get('watches')[0]

        category = None
        priority = None
        custom_fields = raw.get('customfields', [None])[0]
        for custom_field in custom_fields or ():
            custom_field_id = custom_field.get('id')

            # Category
            if custom_field_id == 'customfield_11901':
                category = custom_field[1][0].text

            # Priority
            elif custom_field_id == 'customfield_12200':
                priority = custom_field[1][0].text

        id_ = key_tag.attrib['id']
        key = key_tag.text
        url = link_tag.text
        title = summary_tag.text if (summary_tag is not None) else None
        description = description_tag.text if (description_tag is not None) else None
        created_on = datetime.strptime(created_tag.text, '%a, %d %b %Y %H:%M:%S %z')
        resolved_on = datetime.strptime(resolved_tag.text, '%a, %d %b %Y %H:%M:%S %z') if (
                resolved_tag is not None) else None
        reporter = reporter_tag.text if (reporter_tag is not None) else None
        assignee = assignee_tag.text if (assignee_tag is not None) else None
        status = status_tag.text if (status_tag is not None) else None
        status_icon_url = status_tag.attrib['iconUrl']
        resolution = resolution_tag.text if (resolution_tag is not None) else None
        versions = [v.text for v in version_tags]
        fix_version = fix_version_tag.text if (fix_version_tag is not None) else None
        votes_int = int(votes_tag.text)
        watches_int = int(watches_tag.text)

        return JiraReport(
            id_=id_, key=key, base_url=base_url, url=url, title=title, description=description,
            created_on=created_on, resolved_on=resolved_on, reporter=reporter, assignee=assignee,
            status=status, status_icon_url=status_icon_url, resolution=resolution,
            versions=versions, fix_version=fix_version, votes=votes_int, watches=watches_int,
            category=category, priority=priority)

    def get_report(self, query: str) -> typing.Optional[JiraReport]:
        id_match = self.ID_PATTERN.match(query)
        bug_match = self.BUG_PATTERN.match(query)
        url_match = self.URL_PATTERN.match(query)

        base_url = self.config.base_url

        if id_match:
            report_project = self.config.default_project
            report_id = id_match.groups()[0]
            return self.fetch_report(base_url, report_project, report_id)

        elif bug_match:
            report_project = str(bug_match.groups()[0]).upper()
            report_id = bug_match.groups()[1]
            return self.fetch_report(base_url, report_project, report_id)

        elif url_match:
            base_url = url_match.groups()[0]
            report_project = str(url_match.groups()[1]).upper()
            report_id = url_match.groups()[2]
            return self.fetch_report(base_url, report_project, report_id)

    @commands.command(pass_context=True, aliases=['mojira', 'bug'])
    async def jira(self, ctx: Context, *, query: str):
        report = self.get_report(query)
        
        if report:
            favicon_url = f'{report.base_url}/favicon.png'
            em = Embed(title=report.title, url=report.url, colour=0xDB1F29)
            em.set_thumbnail(url=report.status_icon_url)
            em.set_author(name=report.key, url=report.url, icon_url=favicon_url)
            em.add_field(name='Assigned to', value=report.assignee)
            em.add_field(name='Reported by', value=report.reporter)
            em.add_field(name='Created on', value=report.created_on.strftime('%Y-%m-%d') if report.created_on else 'Unknown')

            if report.category:
                em.add_field(name='Category', value=report.category)

            if report.priority:
                em.add_field(name='Priority', value=report.priority)

            if report.resolution == 'Unresolved':
                em.add_field(name='Status', value=report.status)
                em.add_field(name='Since version', value=report.since_version)
                em.add_field(name='Votes', value=str(report.votes))
            else:
                em.add_field(name='Resolution', value=report.resolution)
                em.add_field(name='Resolved on', value=report.resolved_on.strftime('%Y-%m-%d') if report.resolved_on else 'Unknown')
                em.add_field(name='Since version', value=report.since_version)
                if report.versions:
                    em.add_field(name='Affects version', value=report.versions[-1])
                if report.fix_version:
                    em.add_field(name='Fix version', value=report.fix_version)
                    
            await self.bot.say(f'<{report.url}>', embed=em)

        else:
            search_url = urllib.parse.urlencode({'searchString': query})
            url = ''.join((self.config.base_url, '/secure/QuickSearch.jspa?', search_url))
            await self.bot.say(url)


def setup(bot):
    bot.add_cog(Jira(bot, __name__))
