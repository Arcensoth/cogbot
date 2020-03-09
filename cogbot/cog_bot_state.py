import json
import logging
import urllib.request

log = logging.getLogger(__name__)


# TODO persist state to file


class CogBotState:
    def __init__(self, state_file: str):
        log.info("Loading main bot state from: {}".format(state_file))

        raw_state = {}

        if state_file.startswith(("http://", "https://")):
            try:
                response = urllib.request.urlopen(state_file)
                content = response.read().decode("utf8")
                raw_state = json.loads(content)
                log.info('Successfully loaded main bot state from remote location')
            except Exception as error:
                log.error(f"Failed to load main bot state: {error}")
        else:
            try:
                with open(state_file, encoding='utf-8') as fp:
                    raw_state = json.load(fp)
                log.info('Successfully loaded main bot state from local file')
            except FileNotFoundError:
                log.error(f"Bot state file not found: {state_file}")

        # Optional
        self.servers = raw_state.get("servers", {})
        self.command_prefix = raw_state.get("command_prefix", ">")
        if not isinstance(self.command_prefix, list):
            self.command_prefix = [self.command_prefix]
        self.description = raw_state.get("description", "")
        self.managers = set(raw_state.get("managers", ()))
        self.staff_roles = set(raw_state.get("staff_roles", ()))
        self.recovery_delay = raw_state.get("recovery_delay", 10)
        self.notify_on_recovery = raw_state.get("notify_on_recovery", True)
        self.hide_help = raw_state.get("hide_help", False)
        self.react_to_command_cooldowns = raw_state.get(
            "react_to_command_cooldowns", False
        )
        self.react_to_check_failures = raw_state.get("react_to_check_failures", False)
        self.react_to_unknown_commands = raw_state.get(
            "react_to_unknown_commands", False
        )
        self.extensions = raw_state.get("extensions", [])
        self.extension_state = raw_state.get("extension_state", {})

        # Derived
        self.help_attrs = dict(name="_help", hidden=True) if self.hide_help else {}

    def get_extension_state(self, ext) -> dict:
        return self.extension_state.get(ext, {}).copy()
