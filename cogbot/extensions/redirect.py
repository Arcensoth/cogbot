from datetime import datetime, timedelta

import discord
from discord.iterators import LogsFromIterator

from cogbot.cog_bot import CogBot


class Redirect:
    def __init__(self, bot: CogBot, ext: str):
        self.bot: CogBot = bot
        options = bot.state.get_extension_state(ext)
        self.message_with_channel = options['message_with_channel']
        self.message_without_channel = options['message_without_channel']
        self.channels = options['channels']
        self.emojis = set(options.get('emojis', ['🛴']))
        self.threshold = options.get('threshold', 3600)

    async def get_suggested_channel(self, reaction: discord.Reaction) -> discord.Channel:
        for channel_id in self.channels.get(reaction.message.server.id) or ():
            channel: discord.Channel = self.bot.get_channel(channel_id)
            async for message in self.bot.logs_from(channel, limit=1):
                now: datetime = reaction.message.timestamp
                then: datetime = message.timestamp + timedelta(seconds=self.threshold)
                if now > then:
                    return channel

    async def on_reaction_add(self, reaction: discord.Reaction, user: discord.Member):
        if (user != self.bot) and (reaction.emoji in self.emojis) and (reaction.count == 1):
            suggested_channel = await self.get_suggested_channel(reaction)
            
            if suggested_channel:
                response = self.message_with_channel.format(
                    author=reaction.message.author.mention,
                    channel=suggested_channel.mention
                )

            else:
                response = self.message_without_channel.format(
                    author=reaction.message.author.mention
                )

            await self.bot.send_message(reaction.message.channel, response)
            


def setup(bot):
    bot.add_cog(Redirect(bot, __name__))
