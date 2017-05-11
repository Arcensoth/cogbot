def gets(iterable, **attrs):
    """ see `discord.utils.get` """
    def predicate(elem):
        for attr, val in attrs.items():
            nested = attr.split('__')
            obj = elem
            for attribute in nested:
                obj = getattr(obj, attribute)

            if obj != val:
                return False
        return True

    return filter(predicate, iterable)
