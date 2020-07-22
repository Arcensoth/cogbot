import logging
from abc import ABC, abstractmethod
from typing import Dict, Generic, Type, TypeVar, Union

from discord import Member, Message, Reaction, Server

from cogbot.cog_bot import CogBot
from cogbot.cogs.abc.base_cog_server_state import BaseCogServerState
from cogbot.types import ServerId

ResolvedOptions = Dict
RawOptions = Union[ResolvedOptions, str]


S = TypeVar("S", bound=BaseCogServerState)


class BaseCog(ABC, Generic[S]):
    def __init__(self, ext: str, bot: CogBot):
        self.ext: str = ext
        self.bot: CogBot = bot
        self.options = self.bot.state.get_extension_state(ext)
        self.server_state_by_id: Dict[ServerId, S] = {}
        self.log = logging.getLogger(self.ext)

    def get_server_state(self, server: Server) -> S:
        return self.server_state_by_id.get(server.id)

    def set_server_state(self, server: Server, state: S):
        if server.id in self.server_state_by_id:
            raise KeyError(f"State for server {server} already exists")
        self.server_state_by_id[server.id] = state

    async def create_server_state(self, server: Server, options: ResolvedOptions) -> S:
        server_id = server.id
        state = self.server_state_class(self.ext, self.bot, server_id, options)
        await state.base_setup()
        return state

    async def resolve_options(
        self, server: Server, options: RawOptions
    ) -> ResolvedOptions:
        # if options is a string, use external options
        if isinstance(options, str):
            options_address = options
            self.log.info(
                f"Loading state data for server {server} extension {self.ext} from: {options_address}"
            )
            resolved_options = await self.bot.load_json(options_address)
            self.log.info(
                f"Successfully loaded state data for server {server} extension {self.ext}"
            )
        # otherwise, we must be using inline options
        elif isinstance(options, dict):
            resolved_options = options
        else:
            raise ValueError(f"Invalid server options: not a dict or str")
        return resolved_options

    async def setup_state(self, server: Server, options: RawOptions):
        try:
            resolved_options = await self.resolve_options(server, options)
            state = await self.create_server_state(server, resolved_options)
            self.set_server_state(server, state)
        except:
            self.log.exception(
                f"Failed to setup state for server {server} extension {self.ext}"
            )

    async def init_states(self):
        raw_servers = self.options.get("servers", {})
        for server_key, options in raw_servers.items():
            server_key: str
            options: RawOptions
            server = self.bot.get_server_from_key(server_key)
            if not server:
                self.log.error(f"Skipping unknown server: {server_key}")
                continue
            await self.setup_state(server, options)

    async def clear_states(self):
        for state in self.server_state_by_id.values():
            state: S
            await state.base_teardown()
        self.server_state_by_id.clear()

    async def reload(self):
        await self.clear_states()
        await self.init_states()

    async def on_ready(self):
        # reload server states
        await self.reload()

    async def on_reaction_add(self, reaction: Reaction, reactor: Member):
        # make sure this isn't a DM
        if isinstance(reactor, Member):
            state = self.get_server_state(reaction.message.server)
            # ignore bot's reactions
            if state and reactor != self.bot.user:
                await state.on_reaction(reaction, reactor)

    async def on_message(self, message: Message):
        # make sure this isn't a DM
        if message.server:
            state = self.get_server_state(message.server)
            # ignore bot's messages
            if state and message.author != self.bot.user:
                await state.on_message(message)

    async def on_message_delete(self, message: Message):
        # make sure this isn't a DM
        if message.server:
            state = self.get_server_state(message.server)
            # ignore bot's messages
            if state and message.author != self.bot.user:
                await state.on_message_delete(message)

    @property
    @abstractmethod
    def server_state_class(self) -> Type[S]:
        """ Return the class itself responsible for creating the server state object. """
        # TODO Can this be determined automatically? #enhance
