import discord
from discord.ext import commands
from discord.ext.commands import CommandError, Context

from cogbot.cog_bot import CogBot


class Quote:
    def __init__(self, bot: CogBot, ext: str):
        self.bot: CogBot = bot
        options = bot.state.get_extension_state(ext)
        self.emojis = set(options.get('emojis', ['🗒']))

    async def on_reaction_add(self, reaction: discord.Reaction, user: discord.Member):
        if (user != self.bot) and (reaction.emoji in self.emojis):
            await self.bot.remove_reaction(reaction.message, reaction.emoji, user)
            await self.quote_message(destination=reaction.message.channel, message=reaction.message, quoter=user)

    async def get_message_from_args(self, ctx: Context, message: str, channel: str) -> discord.Message:
        # message is a link
        if message.startswith(('http://', 'https://')):
            tokens = message.split('/')
            channel_id = tokens[-2]
            message_id = tokens[-1]

        # message is an id, channel is a #ref
        elif channel and channel.startswith('<#') and channel.endswith('>'):
            message_id = message
            channel_id = channel[2:-1]

        # message is an id, channel is an id
        else:
            message_id = message
            channel_id = channel

        channel: discord.Channel = self.bot.get_channel(channel_id)

        # assert quoter has read permissions in channel
        quoter: discord.Member = ctx.message.author
        quoter_permissions: discord.Permissions = quoter.permissions_in(channel)
        can_quote = quoter_permissions.read_messages and quoter_permissions.read_message_history
        if not can_quote:
            raise CommandError('Cannot quote inaccessible message')

        message: discord.Message = await self.bot.get_message(channel, message_id)

        return message

    async def quote_message(
            self, destination: discord.channel, message: discord.Message, quoter: discord.Member,
            mention: bool = False):
        author: discord.Member = message.author
        server: discord.Server = message.server
        channel: discord.Channel = message.channel

        quote_name = f'{author.display_name} ({author.name}#{author.discriminator}) in #{channel}:'
        quote_link = f'https://discordapp.com/channels/{server.id}/{channel.id}/{message.id}'

        em = discord.Embed(description=message.clean_content)
        em.set_author(name=quote_name, icon_url=author.avatar_url)

        content = ((author.mention + ' ') if mention else '') + quote_link

        sent_message: discord.Message = await self.bot.send_message(destination, content, embed=em)

        # edit-mention the quoter for tracking purposes
        new_content = quoter.mention + ' ' + sent_message.content

        await self.bot.edit_message(sent_message, new_content=new_content)

    async def quote(self, ctx: Context, message: str, channel: str = None, mention: bool = False):
        channel = channel or ctx.message.channel.id

        try:
            message_to_quote = await self.get_message_from_args(ctx, message, channel)
        except:
            await self.bot.react_question(ctx)
            return

        try:
            await self.quote_message(
                destination=ctx.message.channel, message=message_to_quote, quoter=ctx.message.author, mention=mention)
        except:
            await self.bot.react_failure(ctx)

    @commands.command(pass_context=True, name='quote')
    async def cmd_quote(self, ctx: Context, message: str, channel: str = None):
        await self.quote(ctx, message, channel)

    @commands.command(pass_context=True, name='quotem', aliases=['reply'])
    async def cmd_quotem(self, ctx: Context, message: str, channel: str = None):
        await self.quote(ctx, message, channel, mention=True)


def setup(bot):
    bot.add_cog(Quote(bot, __name__))
