import json
import logging

log = logging.getLogger(__name__)


# TODO persist state to file


class CogBotState:
    def __init__(self, state_file: str):
        with open(state_file) as fp:
            try:
                raw_state = json.load(fp)
            except FileNotFoundError:
                log.warning(f'Bot state file not found: {state_file}')
                raw_state = {}

        # Optional
        self.command_prefix = raw_state.pop('command_prefix', '>')
        self.description = raw_state.pop('description', '')
        self.manager_ids = raw_state.pop('manager_ids', set())
        self.staff_roles = raw_state.pop('staff_roles', set())
        self.restart_delay = raw_state.pop('restart_delay', 10)
        self.hide_help = raw_state.pop('hide_help', False)
        self.extensions = raw_state.pop('extensions', [])
        self.extension_state = raw_state.pop('extension_state', {})

        # Derived
        self.help_attrs = dict(name='_help', hidden=True) if self.hide_help else {}

    def get_extension_state(self, ext) -> dict:
        return self.extension_state.get(ext, {}).copy()
