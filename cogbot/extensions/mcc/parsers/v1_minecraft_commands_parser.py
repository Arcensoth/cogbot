from cogbot.extensions.mcc.parsers.minecraft_commands_parser import MinecraftCommandsParser


class V1MinecraftCommandsParser(MinecraftCommandsParser):
    def _build(self, key: str, node: dict, command: str):
        type_ = node['type']
        executable = node.get('executable')
        redirect = node.get('redirect')
        children = node.get('children', {})

        # whether my command is relevant enough to be rendered
        relevant = executable

        # build my argument string
        if type_ == 'root':
            args = ()
        elif type_ == 'literal':
            args = (key,)
        elif type_ == 'argument':
            parser = node['parser'].split(sep=':', maxsplit=1)[1]  # get the `string` from `brigadier:string`
            args = ('<{}: {}>'.format(key, parser),)
        else:
            args = ('{}*'.format(key),)

        # argument to provide for parents when collapsing
        argument = args[0] if args else None

        if redirect:
            # redirect is a list and there may be multiple
            args = (*args, '->', '|'.join(redirect))
            relevant = True

        # special case for `execute run`
        if not (executable or redirect or children):
            args = (*args, '...')
            relevant = True

        # build command
        my_command = ' '.join(arg for arg in (command or None, *args) if arg is not None)

        # build children, if any
        my_children = {k: self._build(k, v, my_command) for k, v in children.items()}

        # count population
        population = sum(child['population'] for child in my_children.values())
        if relevant:
            population += 1

        # build collapsed form
        collapsed = ' '.join((my_command, '|'.join((child['argument'] for child in my_children.values())), '...')) \
            if my_children else None

        # compile and return result
        result = {
            'relevant': relevant if relevant else None,
            'command': my_command if my_command else None,
            'children': my_children if my_children else None,
            'population': population,
            'argument': argument if argument else None,
            'collapsed': collapsed if collapsed else None
        }

        result = {k: v for k, v in result.items() if v is not None}

        return result

    def parse(self, raw):
        return self._build('root', raw, '')
