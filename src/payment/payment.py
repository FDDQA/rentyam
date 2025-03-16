import asyncio

from src.config import config
from src.db.sql import db_payments_controller, db_get_user_lang, db_take_premium
from src.types.classes import LocalizationManager

locales = LocalizationManager()
locales.load_from_csv(config.localization_path)


# контролер истекшего премиума
async def payments_controller(main_bot):
    while True:
        user_ids_expired = await db_payments_controller()
        for item in user_ids_expired:
            await main_bot.send_message(chat_id=item['user_id'], text=locales.get_localized_string("Txt_premium_expired", db_get_user_lang(item['user_id'])))
            db_take_premium(item['user_id'])
        await asyncio.sleep(10)
