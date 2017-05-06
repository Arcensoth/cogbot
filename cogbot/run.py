import argparse
import asyncio
import logging
import time

from cogbot.cog_bot import CogBot
from cogbot.cog_bot_state import CogBotState

log = logging.getLogger(__name__)


def run():
    state = CogBotState(args.state)

    loop = asyncio.get_event_loop()

    while True:
        log.info('Starting bot...')
        bot = CogBot(state=state, loop=loop)

        try:
            loop.run_until_complete(bot.start(args.token))

        except KeyboardInterrupt:
            log.info('Logging out bot...')
            loop.run_until_complete(bot.logout())

            log.info('Gathering leftover tasks...')
            pending = asyncio.Task.all_tasks(loop=loop)
            gathered = asyncio.gather(*pending, loop=loop)

            try:
                log.info('Cancelling leftover tasks...')
                gathered.cancel()
                loop.run_until_complete(gathered)
                gathered.exception()

            except:
                pass

            break

        except Exception as ex:
            log.critical('Encountered a fatal exception:')
            log.error(ex)
            log.warning(f'Restarting bot in {state.restart_delay} seconds...')
            time.sleep(state.restart_delay)

    log.info('Closing loop...')
    loop.close()

    log.info('Bot terminated')


arg_parser = argparse.ArgumentParser()
arg_parser.add_argument('token')
arg_parser.add_argument('--log', help='Log level', default='WARNING')
arg_parser.add_argument('--state', help='Bot state file', default='bot.json')
args = arg_parser.parse_args()

try:
    import loggy

    loggy.install(level=args.log)
except:
    logging.basicConfig(level=args.log)

log.info('Hello!')
run()
log.info('Goodbye!')
