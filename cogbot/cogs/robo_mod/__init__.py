from cogbot.cogs.robo_mod.robo_mod_cog import RoboModCog


def setup(bot):
    bot.add_cog(RoboModCog(__name__, bot))
