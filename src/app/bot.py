import logging
import asyncio

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage
from redis.asyncio import Redis

from src.config import config
from commands import set_bot_commands
from src.db.sql import db_create_tables
from src.payment.payment import payments_controller
from src.scrapers.scraping_listam import InfinityScrapingListam
from src.scrapers.scraping_tunmun import InfinityScrapingTunmun
from src.types.classes import LoggingMiddleware
from src.utils.other import get_last_message_time_from_users
import src.handlers
import src.utils.week_statistics as week_statistics


main_bot = Bot(config.token)
app_log = logging.getLogger('app')
scraping_listam_log = logging.getLogger('scraping_listam')
scraping_tunmun_log = logging.getLogger('scraping_tunmun')

inf_scr_listam = InfinityScrapingListam(main_bot)
inf_scr_tunmun = InfinityScrapingTunmun(main_bot)


def setup_logging():
    # Настройка логгирования для 'app'
    app_handler = logging.FileHandler("app.log")
    app_handler.setLevel(logging.INFO)
    app_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    app_handler.setFormatter(app_formatter)
    app_log.addHandler(app_handler)

    # Настройка логгирования для 'scraping_listam'
    scraping_listam_handler = logging.FileHandler("scraping_listam.log")
    scraping_listam_handler.setLevel(logging.INFO)
    scraping_listam_handler.setFormatter(app_formatter)
    scraping_listam_log.addHandler(scraping_listam_handler)

    # Настройка логгирования для 'scraping_tunmun'
    scraping_tunmun_handler = logging.FileHandler("scraping_tunmun.log")
    scraping_tunmun_handler.setLevel(logging.INFO)
    scraping_tunmun_handler.setFormatter(app_formatter)
    scraping_tunmun_log.addHandler(scraping_tunmun_handler)

    # Настройка общего логгера
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler()
        ]
    )


async def main():
    setup_logging()
    redis = Redis(host=config.redis_host, port=config.redis_port)
    storage = RedisStorage(redis=redis)
    dp = Dispatcher(storage=storage)
    # db_create_tables()
    dp.include_router(src.handlers.commands_handler.router)
    dp.include_router(src.handlers.menu.router)
    dp.include_router(src.handlers.admin_handler.router)
    dp.include_router(src.handlers.telegram_starts_payment_handler.router)
    await set_bot_commands(main_bot)
    dp.update.middleware(LoggingMiddleware())
    app_log.info(await dp.start_polling(main_bot, skip_updates=True, on_startup=set_bot_commands, storage=storage))


async def launch():
    await asyncio.gather(main(),
                         inf_scr_listam.main(),
                         inf_scr_tunmun.main(),
                         get_last_message_time_from_users(main_bot),
                         payments_controller(main_bot),
                         week_statistics.main(main_bot)
                         )


if __name__ == '__main__':
    asyncio.run(launch())
