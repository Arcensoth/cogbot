from cogbot.extensions.helpchat.help_chat import HelpChat


def setup(bot):
    bot.add_cog(HelpChat(bot, __name__))
