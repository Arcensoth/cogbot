from cogbot.extensions.mcc.parsers.minecraft_commands_parser import MinecraftCommandsParser


class V1MinecraftCommandsParser(MinecraftCommandsParser):
    def _build(self, key: str, node: dict, command: str, command_t: str):
        type_ = node['type']
        executable = node.get('executable')
        redirect = node.get('redirect')
        children = node.get('children', {})

        # whether my command is relevant enough to be rendered
        relevant = executable

        # build my argument string
        if type_ == 'root':
            args = args_t = ()
        elif type_ == 'literal':
            args = args_t = (key,)
        elif type_ == 'argument':
            parser = node['parser'].split(sep=':', maxsplit=1)[1]  # get the `string` from `brigadier:string`
            args = ('<{}>'.format(key),)
            args_t = ('<{}: {}>'.format(key, parser),)
        else:
            args = args_t = ('{}*'.format(key),)

        # argument to provide for parents when collapsing
        argument = args[0] if args else None
        argument_t = args_t[0] if args_t else None

        if redirect:
            # redirect is a list and there may be multiple
            args += ('->', '|'.join(redirect))
            relevant = True

        # special case for `execute run`
        if not (executable or redirect or children):
            args += ('...',)
            relevant = True

        # build command
        my_command = ' '.join(arg for arg in ((command or None,) + args) if arg is not None)
        my_command_t = ' '.join(arg_t for arg_t in ((command_t or None,) + args_t) if arg_t is not None)

        # build children, if any
        my_children = {k: self._build(k, v, my_command, my_command_t) for k, v in children.items()}

        # count population
        population = sum(child['population'] for child in my_children.values())
        if relevant:
            population += 1

        # build collapsed form
        collapsed = collapsed_t = None
        if my_children:
            collapsed = ' '.join((my_command, '|'.join((child['argument'] for child in my_children.values()))))
            collapsed_t = ' '.join((my_command_t, '|'.join((child['argument_t'] for child in my_children.values()))))
            # look for at least one grandchild before appending `...`
            if next((True for child in my_children.values() if child.get('children')), False):
                collapsed += ' ...'
                collapsed_t += ' ...'

        # compile and return result
        result = {
            'children': my_children if my_children else None,
            'population': population,
            'relevant': relevant if relevant else None,
            'command': my_command if my_command else None,
            'command_t': my_command_t if my_command_t else None,
            'argument': argument if argument else None,
            'argument_t': argument_t if argument_t else None,
            'collapsed': collapsed if collapsed else None,
            'collapsed_t': collapsed_t if collapsed_t else None
        }

        result = {k: v for k, v in result.items() if v is not None}

        return result

    def parse(self, raw):
        return self._build('root', raw, '', '')
