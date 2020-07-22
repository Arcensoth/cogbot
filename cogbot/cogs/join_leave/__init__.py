from cogbot.cogs.join_leave.join_leave_cog import JoinLeaveCog


def setup(bot):
    bot.add_cog(JoinLeaveCog(__name__, bot))
