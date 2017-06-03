# cogbot

[![Join the chat at https://gitter.im/arcensoth-cogbot/Lobby](https://badges.gitter.im/arcensoth-cogbot/Lobby.svg)](https://gitter.im/arcensoth-cogbot/Lobby?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge)
A collection of [discord.py](https://github.com/Rapptz/discord.py) wrappers and extensions.

You can [run a bot](#running-a-bot) without writing any code. All you need are the [dependencies](#dependencies) and, if you want to configure the bot up-front, some [configuration](#configuration) options.

## Dependencies

### Required
* [Python](https://www.python.org/) 3.6+
* [discord.py](https://github.com/Rapptz/discord.py) and [its dependencies](https://github.com/Rapptz/discord.py#requirements)

### Optional
* [loggy](https://github.com/Arcensoth/loggy) for pretty logs

## Running a bot
This is an example script that runs a bot using the state file `bot.json`. You can copy and run it, replacing arguments as necessary, but you will need to replace `token` with **your own bot token**.

```bash
python3.6 -m cogbot.run --log INFO --state bot.json "token"
```

### Configuration
These are the generic configuration options available for bots. They may be defined in the state file (specified by `--state`) or passed into the bot state object programmatically.

| Option            | Type  | Default   | Description
| ----------------- | ----- | --------- | -----------
| command_prefix    | str   | `'>'`     | The message prefix used by the bot to detect commands.
| description       | str   | `''`      | A description of the bot, displayed by the help command.
| managers          | list  | `[]`      | A list of user ids who are allowed to manage the bot.
| restart_delay     | float | `10`      | The number of seconds until the bot will restart after crashing.
| hide_help         | bool  | `False`   | Whether the built-in help command should be hidden.
| extensions        | list  | `[]`      | A list of [bot extensions](#extensions) to use.
| extension_state   | dict  | `{}`      | A mapping of extension name to [extension-specific state](#extension-configuration).

### Extensions
Extensions are specialized Python scripts that integrate with the bot to provide additional functionality. On startup, they are loaded in the same order as defined in the bot configuration `extensions` list.

There are several extensions already available in this repository, however none of them are loaded by default.

### Extension configuration
Some extensions may be provided with their own specific configuration, by defining an entry in the `extension_state` mapping, like so:

```json
{
  "extensions": [ "cogbot.extensions.about" ],
  "extension_state": {
    "cogbot.extensions.about": {
      "repos": ["https://github.com/Arcensoth/cogbot"]
    }
  }
}
```

See `examples/with_extension_state.json` for a complete example.
