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
        self.command_prefix = raw_state.get('command_prefix', '>')
        self.description = raw_state.get('description', '')
        self.managers = set(raw_state.get('managers', ()))
        self.staff_roles = set(raw_state.get('staff_roles', ()))
        self.recovery_delay = raw_state.get('recovery_delay', 10)
        self.notify_on_recovery = raw_state.get('notify_on_recovery', True)
        self.hide_help = raw_state.get('hide_help', False)
        self.react_to_command_cooldowns = raw_state.get('react_to_command_cooldowns', False)
        self.react_to_unknown_commands = raw_state.get('react_to_unknown_commands', False)
        self.extensions = raw_state.get('extensions', [])
        self.extension_state = raw_state.get('extension_state', {})

        # Derived
        self.help_attrs = dict(name='_help', hidden=True) if self.hide_help else {}

    def get_extension_state(self, ext) -> dict:
        return self.extension_state.get(ext, {}).copy()
