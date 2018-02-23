# cogbot
A collection of [discord.py](https://github.com/Rapptz/discord.py) wrappers and extensions.

You can [run a bot](#running-a-bot) without writing any code. All you need are the [dependencies](#dependencies) and some [configuration](#configuration) options.

## Dependencies
* [Python](https://www.python.org/) 3.6+
* See [requirements.txt](./requirements.txt)

## Running a bot
See [examples/run.sh](./examples/run.sh) for an example script that runs a bot using one of the sample configuration files. You can copy and run it, replacing arguments as necessary. Note that you will need to provide **your own bot token**.

### Configuration
These are the generic configuration options available for bots. They may be defined in the state file (specified by `--state`) or passed into the bot state object programmatically.

| Option                        | Type  | Default   | Description
| ----------------------------- | ----- | --------- | -----------
| command_prefix                | str   | `'>'`     | The message prefix used by the bot to detect commands.
| description                   | str   | `''`      | A description of the bot, displayed by the help command.
| managers                      | list  | `[]`      | A list of user ids who are allowed to manage the bot.
| staff_roles                   | list  | `[]`      | A list of role ids that should be given elevated access (admins, moderators, etc).
| restart_delay                 | float | `10`      | The number of seconds until the bot will restart after crashing.
| hide_help                     | bool  | `False`   | Whether the built-in help command should be hidden.
| react_to_command_cooldowns    | bool  | `False`   | Whether to send a reaction to the user when they are being rate limited.
| react_to_unknown_commands     | bool  | `False`   | Whether to send a reaction to the user when they enter an unknown command.
| extensions                    | list  | `[]`      | A list of [bot extensions](#extensions) to use.
| extension_state               | dict  | `{}`      | A mapping of extension name to [extension-specific state](#extension-configuration).

### Extensions
Extensions are specialized Python scripts that integrate with the bot to provide additional functionality. On startup, they are loaded in the same order as defined in the bot configuration `extensions` list.

There are several extensions already available in this repository, however none of them are loaded by default.

### Extension configuration
Some extensions may be provided with their own specific configuration, by defining an entry in the `extension_state` mapping.

See [examples/with_extension_state.json](./examples/with_extension_state.json) for a complete example.
