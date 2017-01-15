import logging


log = logging.getLogger(__name__)


class CogBotConfig:
    def __init__(self, **options):
        # optional
        self.command_prefix = options.pop('command_prefix', '>')
        self.description = options.pop('description', '')
        self.hide_help = options.pop('hide_help', False)
        self.extensions = options.pop('extensions', [])
        self.extension_options = options.pop('extension_options', {})

        # derived
        self.help_attrs = dict(name='_help', hidden=True) if self.hide_help else {}

    def get_extension_options(self, ext) -> dict:
        return self.extension_options.get(ext, {}).copy()
