import logging
from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from discord import Member, Message, Reaction, Server

from cogbot.cog_bot import CogBot

O = TypeVar("O")


class BaseCogServerState(ABC, Generic[O]):
    def __init__(self, ext: str, bot: CogBot, server_id: str, raw_options: dict):
        self.ext: str = ext
        self.bot: CogBot = bot
        self.server_id: str = server_id
        self.raw_options: dict = raw_options
        self.server: Server
        self.log: logging.Logger
        self.options: O

    async def base_setup(self):
        self.server = self.bot.get_server(self.server_id)
        self.log = logging.getLogger(f"{self.server}:{self.ext}")
        self.options = await self.create_options()
        await self.setup()

    async def base_teardown(self):
        await self.teardown()

    async def setup(self):
        """ Optional override to handle server state setup. """

    async def teardown(self):
        """ Optional override to handle server state teardown. """

    async def on_reaction(self, reaction: Reaction, reactor: Member):
        """ Optional override to handle reaction events. """

    async def on_message(self, message: Message):
        """ Optional override to handle message events. """

    async def on_message_delete(self, message: Message):
        """ Optional override to handle deleted message events. """

    async def on_member_join(self, member: Member):
        """ Optional override to handle member join events. """

    async def on_member_remove(self, member: Member):
        """ Optional override to handle member remove events. """

    async def on_member_ban(self, member: Member):
        """ Optional override to handle member ban events. """

    async def on_member_unban(self, server: Server, member: Member):
        """ Optional override to handle member unban events. """

    @abstractmethod
    async def create_options(self) -> O:
        """ Create and return an arbitrary options object, used to encapsulate extension-specific
        configuration. Because this method is async, all async bot methods are available here. """
