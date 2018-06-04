from cogbot.extensions.nbt.nbt import NBT


def setup(bot):
    bot.add_cog(NBT(bot))
