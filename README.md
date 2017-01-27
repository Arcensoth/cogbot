# cogbot
A collection of [discord.py](https://github.com/Rapptz/discord.py) wrappers and extensions.

You can [run a bot](#running-a-bot) without writing any code. All you need are the [dependencies](#dependencies) and - if you want the bot to do something - a [configuration](#configuration) file.

## Dependencies

### Required
* [Python](https://www.python.org/) 3.6+
* [discord.py](https://github.com/Rapptz/discord.py) and [its dependencies](https://github.com/Rapptz/discord.py#requirements)

### Optional
* [loggy](https://github.com/Arcensoth/loggy) for pretty logs

## Running a bot
This is an example script that runs a bot using the configuration file `examples/basic.json`. You can copy and run it, replacing arguments as necessary, but you will need to replace `token` with **your own bot token**. Paths are relative to the root directory of the module.

```bash
python3 run.py --log INFO --config ../examples/config.json "token"
```

### Configuration
These are the generic configuration options available for bots. They may be defined in the configuration file (specified by `--config`) or passed into the bot config programmatically.

| Options           | Type | Default | Description
| ----------------- | ---- | ------- | -----------
| command_prefix    | str  | `'>'`   | The message prefix used by the bot to detect commands.
| description       | str  | `''`    | A description of the bot, displayed by the help command.
| managers          | list | `[]`    | A list of user ids who are allowed to manage the bot.
| hide_help         | bool | `False` | Whether the built-in help command should be hidden.
| extensions        | list | `[]`    | A list of [bot extensions](#extensions) to use.
| extension_options | dict | `{}`    | A mapping of [extension-specific configuration](#extension-options).

### Extensions
Extensions are specialized Python scripts that integrate with the bot to provide additional functionality. On startup, they are loaded in the same order as defined in the bot configuration `extensions` list.

There are several extensions already available in this repository, however none of them are loaded by default.

### Extension options
Some extensions may be provided with their own specific configuration. This can be accomplished by configuring an entry in the `extension_options` mapping, like so:

```json
{
  "extensions": [ "cogbot.extensions.about" ],
  "extension_options": {
    "cogbot.extensions.about": {
      "repos": ["https://github.com/Arcensoth/cogbot"]
    }
  }
}
```

See `examples/with_extension_options.json` for a complete example.
