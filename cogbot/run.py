import argparse
import logging.config

# parse args and setup logging before anything else

arg_parser = argparse.ArgumentParser()
arg_parser.add_argument('--token', help='Bot token')
arg_parser.add_argument('--tokenfile', help='Bot token file')
arg_parser.add_argument('--log', help='Log level', default='WARNING')
arg_parser.add_argument('--state', help='Bot state file', default='bot.json')
args = arg_parser.parse_args()

LOG_FMT = '%(asctime)s [%(name)s/%(levelname)s] %(message)s'

# attempt to use colorlog, if available
try:
    import colorlog
    import sys

    formatter = colorlog.ColoredFormatter(
        fmt='%(log_color)s' + LOG_FMT + '%(reset)s',
        log_colors={
            'DEBUG': 'blue',
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'white,bg_red',
        }
    )

    handler = colorlog.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    logging.root.addHandler(handler)
    logging.root.setLevel(args.log)

# otherwise just stick with basic logging
except:
    logging.basicConfig(
        level=args.log,
        format=LOG_FMT)

log = logging.getLogger(__name__)

import asyncio
import time

from cogbot.cog_bot import CogBot
from cogbot.cog_bot_state import CogBotState


# TODO Consider switching to the library rewrite: https://github.com/Rapptz/discord.py/tree/rewrite
# The rewrite has auto-reconnect behaviour: https://github.com/Rapptz/discord.py/blob/rewrite/discord/client.py#L405
# This would make our hacky crash workarounds trivial.


if args.token:
    TOKEN = args.token
elif args.tokenfile:
    with open(args.tokenfile) as fp:
        TOKEN = fp.read()
else:
    TOKEN = input('Enter bot token: ')


def _attempt_logout(loop, bot):
    try:
        log.warning('Attempting clean logout...')
        loop.run_until_complete(bot.logout())

        log.info('Gathering leftover tasks...')
        pending = asyncio.Task.all_tasks(loop=loop)
        gathered = asyncio.gather(*pending, loop=loop)

        log.warning(f'Cancelling {len(pending)} pending tasks:')
        for task in pending:
            log.warning(f"    {getattr(task, '_coro')}")
            
        gathered.cancel()

        log.info('Allowing cancelled tasks to finish...')
        try:
            # NOTE this is expected to raise a CancelledError if there were cancelled tasks
            loop.run_until_complete(gathered)
        except:
            pass

    except:
        log.exception('Encountered an error while attempting to logout')
        log.critical('Forcibly terminating with system exit')
        exit()


def run():
    loop = asyncio.get_event_loop()

    last_death: type = None

    while True:
        state = CogBotState(args.state)

        log.info('Starting bot...')
        
        bot = CogBot(state=state, loop=loop)

        if last_death and state.notify_on_recovery and state.managers:
            log.warning(f'Notifying {len(state.managers)} managers of crash recovery...')

            try:
                reason = last_death.__name__
            except:
                reason = None

            message = 'Hello! I\'ve just recovered from a fatal crash caused by'
            message += f': `{reason}`' if reason else ' an unknown error.'

            for manager in state.managers:
                bot.queue_message(bot.get_user_info, manager, message)

        try:
            loop.run_until_complete(bot.start(TOKEN))

        except KeyboardInterrupt:
            log.info('Keyboard interrupt detected')
            _attempt_logout(loop, bot)
            break

        except Exception as ex:
            last_death = ex
            log.exception('Encountered a fatal exception')

        except:
            last_death = None
            log.exception('Encountered an unknown error')

        _attempt_logout(loop, bot)

        log.info('Closing event loop...')
        loop.close()

        log.warning(f'Restarting bot in {state.recovery_delay} seconds...')
        time.sleep(state.recovery_delay)

        log.info('Opening a new event loop...')
        loop = asyncio.new_event_loop()

    log.info('Closing event loop for good...')
    loop.close()

    log.warning('Bot successfully terminated')


log.info('Hello!')
run()
log.info('Goodbye!')
