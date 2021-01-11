from cogbot.cogs.robo_mod.robo_mod_condition import RoboModCondition
from cogbot.cogs.robo_mod.robo_mod_trigger import RoboModTrigger
from discord import Message


class MessageContainsExternalMediaCondition(RoboModCondition):
    def __init__(self):
        self.ignore_links: bool = False
        self.ignore_embeds: bool = False
        self.ignore_attachments: bool = False

    @staticmethod
    def does_message_contain_links(message: Message) -> bool:
        return ("http://" in message.content) or ("https://" in message.content)

    @staticmethod
    def does_message_contain_embeds(message: Message) -> bool:
        return bool(message.embeds) and len(message.embeds) > 0

    @staticmethod
    def does_message_contain_attachments(message: Message) -> bool:
        return bool(message.attachments) and len(message.attachments) > 0

    def check_links(self, trigger: RoboModTrigger) -> bool:
        return (not self.ignore_links) and self.does_message_contain_links(trigger.message)

    def check_embeds(self, trigger: RoboModTrigger) -> bool:
        return (not self.ignore_embeds) and self.does_message_contain_embeds(trigger.message)

    def check_attachments(self, trigger: RoboModTrigger) -> bool:
        return (not self.ignore_attachments) and self.does_message_contain_attachments(
            trigger.message
        )

    async def update(self, state: "RoboModServerState", data: dict):
        self.ignore_links = data.get("ignore_links", False)
        self.ignore_embeds = data.get("ignore_embeds", False)
        self.ignore_attachments = data.get("ignore_attachments", False)

    async def check(self, trigger: RoboModTrigger) -> bool:
        check_links = self.check_links(trigger)
        check_embeds = self.check_embeds(trigger)
        check_attachments = self.check_attachments(trigger)
        return check_links or check_embeds or check_attachments
