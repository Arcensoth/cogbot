from discord.ext import commands
from discord.ext.commands import Context


def is_manager_check(ctx: Context):
    return ctx.message.author.id in ctx.bot.state.managers


def is_manager():
    return commands.check(lambda ctx: is_manager_check(ctx))


def is_staff_check(ctx: Context):
    if is_manager_check(ctx):
        return True

    author_roles = {role.id for role in ctx.message.author.roles}
    author_staff_roles = author_roles.intersection(ctx.bot.state.staff_roles)

    return bool(author_staff_roles)


def is_staff():
    return commands.check(lambda ctx: is_staff_check(ctx))
