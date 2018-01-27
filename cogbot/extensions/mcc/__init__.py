from cogbot.extensions.mcc.mcc import MinecraftCommands


def setup(bot):
    bot.add_cog(MinecraftCommands(bot, __name__))
