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
            my_arguments = ()
        elif type_ == 'literal':
            my_arguments = (key,)
        elif type_ == 'argument':
            parser = node['parser'].split(sep=':', maxsplit=1)[1]  # get the `string` from `brigadier:string`
            my_arguments = ('<{}: {}>'.format(key, parser),)
        else:
            my_arguments = ('{}*'.format(key),)

        if redirect:
            my_arguments = (*my_arguments, '->', '|'.join(redirect), '...')
            relevant = True

        # special case for `execute run`
        if not (executable or redirect or children):
            my_arguments = (*my_arguments, '->', '...')
            relevant = True

        # build command
        my_command = ' '.join(arg for arg in (command or None, *my_arguments) if arg is not None)

        # build children, if any
        my_children = {k: self._build(k, v, my_command) for k, v in children.items()}

        # count population
        # my_population = 1 + sum(child['population'] for child in my_children.values())
        my_population = sum(child['population'] for child in my_children.values())
        if relevant:
            my_population += 1

        # compile and return result
        result = {
            'relevant': relevant,
            'command': my_command if my_command else None,
            'children': my_children if my_children else None,
            'population': my_population
        }

        result = {k: v for k, v in result.items() if v is not None}

        return result

    def parse(self, raw):
        return self._build('root', raw, '')
