from cogbot.extensions.groups.groups import Groups


def setup(bot):
    bot.add_cog(Groups(bot, __name__))
