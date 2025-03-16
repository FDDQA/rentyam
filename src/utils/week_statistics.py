import asyncio
import logging

import schedule

from src.config import config
from src.db.sql import db_get_weekly_statistics, db_get_premium_users, db_get_user_lang
from src.types.classes import LocalizationManager

locales = LocalizationManager()
locales.load_from_csv(config.localization_path)

async def send_market_trend(main_bot):
    premium_users = await db_get_premium_users()
    statistics_flats, statistics_houses = db_get_weekly_statistics()
    # получили статистику за прошлую неделю и позапрошлую неделю:
    # поля: old_count, actual_count, old_median_price, actual_median_price
    percentage_difference_trend_flats = ((statistics_flats['actual_median_price'] - statistics_flats['old_median_price'] ) / statistics_flats['old_median_price']) * 100
    percentage_difference_trend_houses = ((statistics_houses['actual_median_price'] - statistics_houses['old_median_price'] ) / statistics_houses['old_median_price']) * 100

    if premium_users:
        for premium_user in premium_users:
            user_id = premium_user['USER_ID']
            lang = db_get_user_lang(user_id)
            localized_message = locales.get_localized_string('Txt_main_week_statistics', lang)
            message = (localized_message
                       .replace("FLATS_COUNT", str(statistics_flats['actual_count']))
                       .replace("HOUSES_COUNT", str(statistics_houses['actual_count']))
                       .replace("MEDIAN_PRICE_FLATS", str(statistics_flats['actual_median_price']))
                       .replace("MEDIAN_PRICE_HOUSES", str(statistics_houses['actual_median_price'])))
            if percentage_difference_trend_flats != 0:
                message += f'\n{locales.get_localized_string('Txt_changed_trend_flats', lang)} {round(percentage_difference_trend_flats, 2)}%'
            if percentage_difference_trend_houses != 0:
                message += f'\n{locales.get_localized_string('Txt_changed_trend_houses', lang)} {round(percentage_difference_trend_houses, 2)}%'
            try:
                await main_bot.send_message(chat_id=user_id,
                                            text=message)
            except Exception as ex:
                logging.warning('Exception in send_market_trend: ' + str(ex))



async def schedule_task(main_bot):
    schedule.every().monday.at("08:00").do(lambda: asyncio.create_task(send_market_trend(main_bot)))

async def scheduler():
    while True:
        schedule.run_pending()
        await asyncio.sleep(1)

# Основная функция запуска
async def main(main_bot):
    await schedule_task(main_bot)
    await scheduler()
