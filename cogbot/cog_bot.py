import logging
from typing import List

from discord import User, Message, Channel, Server, Member
from discord.ext import commands
from discord.ext.commands import Context
from discord.ext.commands.errors import *

from cogbot import utils
from cogbot.cog_bot_state import CogBotState

log = logging.getLogger(__name__)


class CogBot(commands.Bot):
    def __init__(self, state: CogBotState, **options):
        super().__init__(
            command_prefix=state.command_prefix,
            description=state.description,
            help_attrs=state.help_attrs,
            **options)

        self.state = state

        # A queue of messages to send after login.
        self.queued_messages = []

        if self.state.extensions:
            self.load_extensions(*self.state.extensions)
        else:
            log.info('No extensions to load')

        log.info('Initialization successful')

    def queue_message(self, dest_getter, dest_id, content):
        self.queued_messages.append((dest_getter, dest_id, content))

    def load_extensions(self, *extensions):
        log.info(f'Loading {len(extensions)} extensions...')
        for ext in extensions:
            log.info(f'Loading extension {ext}...')
            try:
                self.load_extension(ext)
            except Exception as e:
                log.warning(f'Failed to load extension {ext} because: {e.__class__.__name__}: {e}')
        log.info(f'Finished loading extensions')

    def unload_extensions(self, *extensions):
        log.info(f'Unloading {len(extensions)} extensions...')
        for ext in extensions:
            log.info(f'Unloading extension {ext}...')
            try:
                self.unload_extension(ext)
            except Exception as e:
                log.warning(f'Failed to unload extension {ext} because: {e.__class__.__name__}: {e}')
        log.info(f'Finished unloading extensions')

    def get_server_members_from_username(self, server: Server, name):
        if len(name) > 5 and name[-5] == '#':
            potential_discriminator = name[-4:]
            results = utils.gets(server.members, name=name[:-5], discriminator=potential_discriminator)
            if results:
                yield from results

    def get_server_members_named(self, server: Server, name):
        """ see `discord.Server.get_member_named()` """
        name_lower = name.lower()

        def pred(m: Member):
            return name_lower in (m.nick or '').lower() or name_lower in m.name.lower()

        return filter(pred, server.members)

    async def disambiguate_user(self, ctx: Context, user_obj):
        """ Attempt to disambiguate a single user from the given object. If multiple potential resuilts are found, raise
         an exception and print the candidates. """

        message: Message = ctx.message
        server: Server = message.server
        channel: Channel = message.channel

        # Return immediately if the object is already a user.
        if isinstance(user_obj, User):
            return user_obj

        elif isinstance(user_obj, str):
            # Attempt to extract id from mention.
            id_from_mention = None
            if user_obj.startswith('<@') and user_obj.endswith('>'):
                id_from_mention = user_obj[2:-1]

            # Attempt to resolve from id.
            try:
                user_from_id = await self.get_user_info(id_from_mention or user_obj)
                if user_from_id:
                    return user_from_id
            except:
                pass

            # Attempt to resolve from username (name + discriminator).
            users_from_username: List[User] = list(self.get_server_members_from_username(server, user_obj))

            # If we found exactly one user from the username, we have successfully disambiguated.
            if len(users_from_username) == 1:
                return users_from_username[0]

            # Otherwise we'll need to look through nick/display names and have the author provide an id.
            else:
                users_from_name = list(self.get_server_members_named(server, user_obj))

            if users_from_name:
                users_str = \
                    '\n'.join((f'  - {user.name}#{user.discriminator} <**{user.id}**>' for user in users_from_name))
                reply = f'{message.author.mention} Please be more specific about the user by providing their id:' \
                        f'\n{users_str}'
                await self.send_message(channel, reply)
                raise BadArgument(f'Cannot disambiguate user from: {user_obj}')

            # Otherwise, if no users were found, back out.
            await self.send_message(channel, f'{message.author.mention} No such user.')
            raise BadArgument(f'Cannot resolve user from: {user_obj}')

    async def send_error(self, ctx: Context, destination, error: CommandError):
        place = '' if ctx.message.server is None else f' on **{ctx.message.server}**'
        reply = f'There was a problem with your command{place}: *{error.args[0]}*'
        await self.send_message(destination, reply)

    async def on_ready(self):
        log.info(f'Logged in as {self.user.name} (id {self.user.id})')
        # Send any queued messages.
        if self.queued_messages:
            log.info(f'Sending {len(self.queued_messages)} queued messages...')
            for dest_getter, dest_id, content in self.queued_messages:
                dest = await dest_getter(dest_id)
                await self.send_message(dest, content)

    async def on_message(self, message):
        if (message.author != self.user) \
                and message.server is not None \
                and message.content.startswith(self.command_prefix):
            log.info(f'[{message.server}/{message.author}] {message.content}')
            await super().on_message(message)

    async def on_command_error(self, e: CommandError, ctx: Context):
        log.warning(f'[{ctx.message.server}/{ctx.message.author}] {e.__class__.__name__}: {e.args[0]}')

        error = e.original if isinstance(e, CommandInvokeError) else e

        if isinstance(error, CommandNotFound):
            await self.react_question(ctx)

        elif isinstance(error, CheckFailure):
            await self.react_denied(ctx)

        elif isinstance(error, CommandOnCooldown):
            await self.react_cooldown(ctx)

        # Keep this one last because some others subclass it.
        elif isinstance(error, CommandError):
            await self.react_failure(ctx)

        else:
            await self.react_poop(ctx)

    async def react_success(self, ctx: Context):
        await self.add_reaction(ctx.message, u'✔')

    async def react_neutral(self, ctx: Context):
        await self.add_reaction(ctx.message, u'➖')

    async def react_question(self, ctx: Context):
        await self.add_reaction(ctx.message, u'❓')

    async def react_failure(self, ctx: Context):
        await self.add_reaction(ctx.message, u'❗')

    async def react_denied(self, ctx: Context):
        await self.add_reaction(ctx.message, u'🚫')

    async def react_cooldown(self, ctx: Context):
        await self.add_reaction(ctx.message, u'⏳')

    async def react_poop(self, ctx: Context):
        await self.add_reaction(ctx.message, u'💩')
