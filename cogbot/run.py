import argparse
import asyncio
import logging
import time

from cogbot.cog_bot import CogBot
from cogbot.cog_bot_state import CogBotState

log = logging.getLogger(__name__)


# TODO Consider switching to the library rewrite: https://github.com/Rapptz/discord.py/tree/rewrite
# The rewrite has auto-reconnect behaviour: https://github.com/Rapptz/discord.py/blob/rewrite/discord/client.py#L405
# This would make our hacky crash workarounds trivial.


def _attempt_logout(loop, bot):
    try:
        log.info('Logging out...')
        loop.run_until_complete(bot.logout())

        log.info('Gathering leftover tasks...')
        pending = asyncio.Task.all_tasks(loop=loop)
        gathered = asyncio.gather(*pending, loop=loop)

        log.info('Cancelling leftover tasks...')
        gathered.cancel()

        log.info('Allowing cancelled tasks to finish...')
        try:
            loop.run_until_complete(gathered)
        except:
            pass

    except Exception as ex:
        log.exception('Encountered an error while attempting to logout')
        log.critical('Forcibly terminating with system exit')
        exit()


def run():
    state = CogBotState(args.state)

    loop = asyncio.get_event_loop()

    last_death: type = None

    while True:
        log.info('Starting bot...')
        bot = CogBot(state=state, loop=loop)

        if last_death and state.managers:
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
            loop.run_until_complete(bot.start(args.token))

        except KeyboardInterrupt:
            log.info('Keyboard interrupt detected')
            _attempt_logout(loop, bot)
            break

        except Exception as ex:
            last_death = ex

            log.exception('Encountered a fatal exception')

            log.warning('Attempting clean logout...')
            _attempt_logout(loop, bot)

        log.info('Closing event loop...')
        loop.close()

        log.warning(f'Restarting bot in {state.restart_delay} seconds...')
        time.sleep(state.restart_delay)

        log.info('Opening a new event loop...')
        loop = asyncio.new_event_loop()

    log.info('Closing event loop for good...')
    loop.close()

    log.info('Bot terminated')


arg_parser = argparse.ArgumentParser()
arg_parser.add_argument('token')
arg_parser.add_argument('--log', help='Log level', default='WARNING')
arg_parser.add_argument('--state', help='Bot state file', default='bot.json')
args = arg_parser.parse_args()

logging.basicConfig(level=args.log)

log.info('Hello!')
run()
log.info('Goodbye!')
