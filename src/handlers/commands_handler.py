import asyncio
import binascii
import logging
from datetime import datetime

import aiogram
from aiogram import Router, exceptions
from aiogram.types import Message, FSInputFile
from aiogram.filters import CommandStart, Command, StateFilter, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.utils.payload import decode_payload

from src.config import config
from src.db.sql import db_get_users_data, db_get_end_time_subscription, db_find_payload, db_user_unblock_bot
from src.keyboards.admin_keyboards import get_admin_dash_kb
from src.keyboards.keyboards import get_start_menu_keyboard, get_stop_menu_keyboard, get_select_type_subscribe
from src.types.classes import MenuStates
from src.utils.other import insert_user, mute_user, unmute_user, get_language, take_premium, give_premium, \
    delete_user, get_premium
from src.app.bot import main_bot
from src.types.classes import LocalizationManager, AdminStates

locales = LocalizationManager()
locales.load_from_csv(config.localization_path)

tutor_locales = LocalizationManager()
tutor_locales.load_from_csv(config.tutor_localization_path)
router = Router()

log = logging.getLogger('commands_handler')


# TODO: вынести команды в глобальные переменные, типа command_menu = menu и использовать ее в хендлерах

# тестерские команды
@router.message(Command('debuggg'))
async def get_debug_data(message: Message, state: FSMContext):
    if message.from_user.id == 5372961337 or message.from_user.id == 664993249:
        state_data = await state.get_data()
        await main_bot.send_message(chat_id=message.from_user.id,
                                    text=f"STATE DATA:{state_data}")
        await main_bot.send_message(chat_id=message.from_user.id, text=str(await state.get_state()))
        db_get_users_data(message.from_user.id)
        await main_bot.send_message(chat_id=message.from_user.id,
                                    text=f"{db_get_users_data(message.from_user.id)}")


@router.message(Command('buyvip'))
async def buy_vip(message: Message):
    if message.from_user.id == 5372961337 or message.from_user.id == 664993249:
        give_premium(message.from_user.id)
        await main_bot.send_message(chat_id=message.from_user.id,
                                    text=f"Buy Premium")


@router.message(Command('sellvip'))
async def sell_vip(message: Message):
    if message.from_user.id == 5372961337 or message.from_user.id == 664993249:
        take_premium(message.from_user.id)
        await main_bot.send_message(chat_id=message.from_user.id,
                                    text=f"Sell Premium")


@router.message(Command('delete_me'))
async def delete_me(message: Message):
    if message.from_user.id == 5372961337 or message.from_user.id == 664993249:
        await delete_user(message.from_user.id)
        await main_bot.send_message(chat_id=message.from_user.id,
                                    text=f"User {message.from_user.username} deleted")


# команды админа
@router.message(Command('admin_dash'))
async def admin_dash(message: Message, state: FSMContext):
    if message.from_user.id == 5372961337 or message.from_user.id == 664993249:
        await main_bot.send_message(chat_id=message.from_user.id,
                                    text=f"Админ панель",
                                    reply_markup=get_admin_dash_kb())
        await state.set_state(AdminStates.admin_dash)


# первая отправка /start
@router.message(CommandStart(), StateFilter(None))
async def start_command(message: Message, state: FSMContext, command: CommandObject):
    args = command.args
    user_id = message.from_user.id
    username = message.from_user.username
    language = message.from_user.language_code
    if language not in ['ru', 'en', 'hy', 'hi']:
        language = 'en'
    last_name = message.from_user.last_name
    first_name = message.from_user.first_name
    await state.update_data(messages=[])
    await state.update_data(user_id=user_id)
    await state.update_data(lang=language)
    await state.update_data(tutor=1)
    if args:
        try:  # если кто-то в параметр старта попытался засунуть мусор, чтобы не развалиться на декоде
            payload = decode_payload(args)
        except UnicodeDecodeError:
            await message.answer('Пу-пу-пу')
            payload = None
        except binascii.Error:  # затык ошибки binascii.Error: Invalid base64-encoded string: number of data characters (13) cannot be 1 more than a multiple of 4
            await message.answer('Пу-пу-пу')
            payload = None

        if db_find_payload(payload):  # проверяем что в таблице marketing есть такой payload
            insert_user(user_id, username, first_name, last_name, language, payload)
        else:
            insert_user(user_id, username, first_name, last_name, language)
    else:
        insert_user(user_id, username, first_name, last_name, language)  # передаем нового юзера в базу
    welcome_message = await main_bot.send_message(chat_id=message.from_user.id,
                                                  text=locales.get_localized_string("Mg_welcome", language))

    await message.delete()
    await asyncio.sleep(5)
    last_message = await main_bot.send_message(chat_id=message.from_user.id,
                                               text=tutor_locales.get_localized_string("Tutor_kb_start_menu", language),
                                               reply_markup=get_start_menu_keyboard(await state.get_data()))
    await delete_extra_messages(state, last_message)
    await main_bot.delete_message(chat_id=user_id, message_id=welcome_message.message_id)
    await state.set_state(MenuStates.start_menu)
    # await get_state(state)


@router.message(StateFilter(MenuStates.stop_state))
async def message_when_stopped(message: Message, state: FSMContext):
    last_message = await main_bot.send_message(chat_id=message.from_user.id,
                                               text=locales.get_localized_string("Kb_stop",
                                                                                 get_language(await state.get_data())),
                                               reply_markup=get_stop_menu_keyboard(await state.get_data()))
    await delete_extra_messages(state, last_message)
    # await get_state(state)


# если юзер уже запустил бота и снова шлёт /start
@router.message(CommandStart())
async def already_started(message: Message, state: FSMContext):
    if await state.get_state() is not None:
        await message.delete()
        await main_bot.send_message(chat_id=message.from_user.id,
                                    text=locales.get_localized_string("Mg_already_started",
                                                                      get_language(await state.get_data())))
        await db_user_unblock_bot(message.from_user.id)

    # await get_state(state)


@router.message(Command('unmute'))
async def force_unmute(message: Message):
    unmute_user(message.from_user.id)
    await main_bot.send_message(chat_id=message.from_user.id,
                                text="Force unmute")


# юзер отправил /stop
@router.message(Command('stop'))
async def stop_command(message: Message, state: FSMContext):
    last_message = await main_bot.send_message(chat_id=message.from_user.id,
                                               text=locales.get_localized_string("Kb_silence",
                                                                                 get_language(await state.get_data())),
                                               reply_markup=get_stop_menu_keyboard(await state.get_data()))
    await delete_extra_messages(state, last_message)
    mute_user(message.from_user.id)
    await state.set_state(MenuStates.stop_state)
    await message.delete()
    #await get_state(state)


# юзер вызвал меню, показываем стартовое меню
@router.message(Command('menu'))
async def menu_command(message: Message, state: FSMContext):
    if await get_state_data(state, "tutor"):
        last_message = await main_bot.send_message(chat_id=message.from_user.id,
                                                   text=tutor_locales.get_localized_string("Tutor_kb_start_menu",
                                                                                           get_language(
                                                                                               await state.get_data())),
                                                   reply_markup=get_start_menu_keyboard(await state.get_data()))
    else:
        last_message = await main_bot.send_message(chat_id=message.from_user.id,
                                                   text=locales.get_localized_string("Kb_start_menu",
                                                                                     get_language(
                                                                                         await state.get_data())),
                                                   reply_markup=get_start_menu_keyboard(await state.get_data()))
    await delete_extra_messages(state, last_message)
    await state.set_state(MenuStates.start_menu)
    mute_user(message.from_user.id)
    await state.update_data(user_id=message.from_user.id)
    await state.update_data(previous_button=None)
    await state.update_data(lmt=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    #await get_state(state)


@router.message(Command('support'))
async def support_command(message: Message, state: FSMContext):
    await message.delete()
    await main_bot.send_message(chat_id=message.from_user.id,
                                text=locales.get_localized_string("Mg_support",
                                                                  get_language(await state.get_data())))


@router.message(Command('premium'))
async def premium_command(message: Message, state: FSMContext):
    await message.delete()
    await state.set_state(MenuStates.buy_premium)
    weekly_link = await main_bot.create_invoice_link(
        title='7 DAYS PREMIUM',
        description='Weekly Subscription RentyAm',
        payload='weeksub',
        currency='XTR',
        prices=[{'label': 'Price', 'amount': config.weekly_premium_price}],  # 99
    )
    monthly_link = await main_bot.create_invoice_link(
        title='30 DAYS PREMIUM',
        description='Monthly Subscription RentyAm',
        payload='monsub',
        currency='XTR',
        prices=[{'label': 'Price', 'amount': config.monthly_premium_price}],  # 249
    )
    # если премиума нет, то локаль с преимуществами
    text = locales.get_localized_string("Mg_premium", get_language(await state.get_data()))
    if get_premium(message.from_user.id) == 1 and db_get_end_time_subscription(message.from_user.id) is not None:
        expired_time = db_get_end_time_subscription(message.from_user.id)
        text += f'\n\n<b>{locales.get_localized_string("Txt_premium_active_to", get_language(await state.get_data()))} {str(expired_time.strftime("%d.%m.%Y %H:%M"))} UTC </b>'
    elif get_premium(message.from_user.id) == 1 and db_get_end_time_subscription(message.from_user.id) is None:
        text = "ERROR! Contact with support"
    # photo = FSInputFile(config.premium_photo)
    # last_message = await main_bot.send_photo(chat_id=message.from_user.id,
    #                                          photo=photo,
    #                                          caption=text,
    #                                          parse_mode='HTML',
    #                                          reply_markup=get_select_type_subscribe(
    #                                              state_data=await state.get_data(),
    #                                              confirmation_tgstars_url_weekly=weekly_link,
    #                                              confirmation_tgstars_url_monthly=monthly_link
    #                                          ))
    last_message = await main_bot.send_message(chat_id=message.from_user.id,
                                               text=text,
                                               parse_mode='HTML',
                                               reply_markup=get_select_type_subscribe(
                                                   state_data=await state.get_data(),
                                                   confirmation_tgstars_url_weekly=weekly_link,
                                                   confirmation_tgstars_url_monthly=monthly_link
                                               ))
    await delete_extra_messages(state, last_message)
    await state.update_data(lmt=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))


# вывод стейта для отладки
async def get_state(state: FSMContext):
    current_state = await state.get_state()
    current_data = await state.get_data()
    log.info(f"CURRENT STATE IS: {current_state} AND DATE IS {current_data}")


# получаем данные из state data
async def get_state_data(state: FSMContext, data):
    state_data = await state.get_data()
    return state_data.get(data)


async def delete_extra_messages(state: FSMContext, last_mg):
    state_data = await state.get_data()
    last_mg_id = last_mg.message_id
    messages = state_data.get("messages")
    if messages is None:
        messages = []
    messages.append(last_mg_id)
    user_id = state_data.get("user_id")
    if len(messages) > 1:
        for i in messages:
            try:
                await main_bot.delete_message(chat_id=user_id, message_id=i)
                messages.remove(i)
            except aiogram.exceptions.TelegramBadRequest:
                log.warning(f"Can't delete message with id {i} from commands handlers")
                messages.remove(i)
    await state.update_data(messages=messages)
