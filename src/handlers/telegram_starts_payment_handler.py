import datetime

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import PreCheckoutQuery, Message

from src.app.bot import main_bot
from src.config import config
from src.db.sql import db_get_end_time_subscription, db_add_payment
from src.types.classes import MenuStates, LocalizationManager
from src.utils.other import give_premium, get_language

router = Router()
locales = LocalizationManager()
locales.load_from_csv(config.localization_path)


@router.pre_checkout_query(lambda query: True)
async def pre_checkout_query_handler(pre_checkout_query: PreCheckoutQuery):
    await main_bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)
    # await state.set_state(MenuStates.start_menu)


@router.message(F.successful_payment)
async def successful_payment(message: Message, state: FSMContext):
    await state.set_state(MenuStates.start_menu)
    expired = db_get_end_time_subscription(message.from_user.id)
    if expired:
        if message.successful_payment.invoice_payload == "weeksub":
            expired = expired + datetime.timedelta(days=7)
        else:
            expired = expired + datetime.timedelta(days=30)
    else:
        if message.successful_payment.invoice_payload == "weeksub":
            expired = datetime.datetime.now() + datetime.timedelta(days=7)
        else:
            expired = datetime.datetime.now() + datetime.timedelta(days=30)

    db_add_payment(message.from_user.id,
                   message.successful_payment.telegram_payment_charge_id,
                   message.successful_payment.total_amount,
                   datetime.datetime.now(),
                   None,
                   expired
                   )
    await main_bot.send_message(chat_id=message.from_user.id, text=locales.get_localized_string("Txt_thx_for_buy_premium", get_language(await state.get_data())))
    give_premium(message.from_user.id)
    if config.refunding == 1:
        await main_bot.refund_star_payment(message.from_user.id, message.successful_payment.telegram_payment_charge_id)
