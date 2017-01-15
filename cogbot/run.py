import argparse
import json
import logging

from cogbot.cog_bot import CogBot
from cogbot.cog_bot_config import CogBotConfig

log = logging.getLogger(__name__)

arg_parser = argparse.ArgumentParser()
arg_parser.add_argument('token')
arg_parser.add_argument('--log', help='log level', default='WARNING')
arg_parser.add_argument('--config', help='configuration file', default='config.json')
args = arg_parser.parse_args()

try:
    import loggy
    loggy.install(level=args.log)
except:
    logging.basicConfig(level=args.log)

try:
    with open(args.config) as fp:
        options = json.load(fp)
except FileNotFoundError:
    log.warning(f'configuration file not found: {args.config}')
    options = {}

config = CogBotConfig(**options)

bot = CogBot(config=config)

bot.run(args.token)
