import logging
from datetime import datetime

from aiogram import Router
from aiogram.filters import command
from aiogram.types import CallbackQuery, Message

from aiogram.fsm.context import FSMContext
from aiogram.utils.deep_linking import create_start_link

from src.types.classes import AdminStates
from src.app.bot import main_bot
from src.db.sql import db_get_all_users, db_add_ad, db_add_start_link, db_user_block_bot
from src.keyboards.admin_keyboards import get_admin_dash_kb

router = Router()


@router.callback_query(AdminStates.admin_dash)
async def add_ad(c: CallbackQuery, state: FSMContext):
    if c.data == 'add_ad':
        await main_bot.send_message(chat_id=c.from_user.id,
                                    text='Ожидаю рекламное сообщение')
        await state.set_state(AdminStates.input_ad)
        await main_bot.answer_callback_query(c.id)
    if c.data == 'delete_ad':
        await main_bot.send_message(chat_id=c.from_user.id,
                                    text='Какое объявление удаляем?')
        await state.set_state(AdminStates.delete_ad)
        await main_bot.answer_callback_query(c.id)
    if c.data == 'send_notification':
        await main_bot.send_message(chat_id=c.from_user.id,
                                    text='Введите уведомление')
        await state.set_state(AdminStates.send_notification)
        await main_bot.answer_callback_query(c.id)
    if c.data == 'generate_link':
        await main_bot.send_message(chat_id=c.from_user.id,
                                    text='Введите строку на английском для генерации ссылки')
        await state.set_state(AdminStates.generate_link)
        await main_bot.answer_callback_query(c.id)

    if c.data == 'refund':
        await main_bot.send_message(chat_id=c.from_user.id,
                                    text='Введите user_id и id платежа для рефанда, разделив их пробелом')
        await state.set_state(AdminStates.refund)
        await main_bot.answer_callback_query(c.id)

    if c.data == 'add_admin':
        await main_bot.send_message(chat_id=c.from_user.id,
                                    text='Введите id пользователя для добавления админа')
        await state.set_state(AdminStates.add_admin)
        await main_bot.answer_callback_query(c.id)


@router.message(AdminStates.input_ad)
async def input_ad(message: Message, state: FSMContext):
    await state.update_data(ad_message_id=message.message_id)
    await state.set_state(AdminStates.input_start_datetime)
    await main_bot.send_message(chat_id=message.from_user.id,
                                text='Сохранил рекламу. Введите дату старта')


@router.message(AdminStates.generate_link)
async def generate_link(message: Message, state: FSMContext):
    link = await create_start_link(main_bot, message.text, encode=True)
    await message.answer(link)
    db_add_start_link(message.text, link)
    await main_bot.send_message(chat_id=message.from_user.id,
                                text='Ссылка готова')
    await state.set_state(AdminStates.admin_dash)


@router.message(AdminStates.input_start_datetime)
async def input_start_datetime(message: Message, state: FSMContext):
    date_str = message.text
    date_obj = datetime.strptime(date_str, "%d.%m.%Y")
    formatted_date_start_str = date_obj.strftime("%Y-%m-%d %H:%M:%S")
    await state.update_data(formatted_date_start_str=formatted_date_start_str)
    await state.set_state(AdminStates.input_end_datetime)
    await main_bot.send_message(chat_id=message.from_user.id,
                                text='Сохранил дату старта. Введите дату окончания или 1, если будем смотреть на кол-во отправок')


@router.message(AdminStates.input_end_datetime)
async def input_end_datetime(message: Message, state: FSMContext):
    date_str = message.text
    if date_str != '1':
        date_obj = datetime.strptime(date_str, "%d.%m.%Y")
        formatted_date_end_str = date_obj.strftime("%Y-%m-%d %H:%M:%S")
        await state.update_data(formatted_date_end_str=formatted_date_end_str)
    else:
        await state.update_data(formatted_date_end_str=None)
    await state.set_state(AdminStates.input_max_count)
    await main_bot.send_message(chat_id=message.from_user.id,
                                text='Сохранил дату окончания. Введите максимум отправок объяв или 1, если безлимитно и смотрим на дату окончания')


@router.message(AdminStates.input_max_count)
async def input_end_datetime(message: Message, state: FSMContext):
    state_data = await state.get_data()
    max_sends_count = int(message.text)
    if max_sends_count == 1:
        max_sends_count = None
    db_add_ad(message_id=state_data.get('ad_message_id'),
              start_datetime=state_data.get('formatted_date_start_str'),
              end_datetime=state_data.get('formatted_date_end_str'),
              max_sends_count=max_sends_count)
    await main_bot.send_message(chat_id=message.from_user.id,
                                text='Сохранил рекламу в базу')
    await state.clear()
    if message.from_user.id == 5372961337 or message.from_user.id == 664993249:
        await main_bot.send_message(chat_id=message.from_user.id,
                                    text=f"Админ панель",
                                    reply_markup=get_admin_dash_kb())
        await state.set_state(AdminStates.admin_dash)
        await state.update_data(user_id=message.from_user.id)


@router.message(AdminStates.send_notification)
async def send_notification(message: Message, state: FSMContext):
    if message.text == '0':
        await state.set_state()
        await main_bot.send_message(chat_id=message.from_user.id, text='Отменил рассылку')
        return
    user_ids = db_get_all_users()
    for i in user_ids:
        user_id = i['user_id']
        try:
            await main_bot.copy_message(chat_id=user_id, from_chat_id=message.from_user.id, message_id=message.message_id)

        except Exception as ex:
            logging.warning(f'Error send notification {user_id} - {ex}')
            if 'Forbidden: bot was blocked by the user' in str(ex):
                await db_user_block_bot(user_id)
    await main_bot.send_message(chat_id=message.from_user.id,
                                text='Уведомления отправлены, сменил стейт на админдэш')
    await state.set_state(AdminStates.admin_dash)


@router.message(AdminStates.refund)
async def admin_dash(message: Message, state: FSMContext):
    user_id = int(message.text.split()[0])
    telegram_payment_id = message.text.split()[1]
    try:
        await main_bot.refund_star_payment(user_id, telegram_payment_id)
    except Exception as ex:
        await main_bot.send_message(chat_id=message.from_user.id,
                                    text=f'Ошибка рефанда {ex}')
    if message.from_user.id == 5372961337 or message.from_user.id == 664993249:
        await main_bot.send_message(chat_id=message.from_user.id,
                                    text=f"Админ панель",
                                    reply_markup=get_admin_dash_kb())
        await state.set_state(AdminStates.admin_dash)
