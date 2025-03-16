import logging
from datetime import datetime

import aiogram.exceptions
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from src.config import config
from src.db.sql import db_get_end_time_subscription
from src.types.classes import MenuStates, LocalizationManager
from src.keyboards.keyboards import get_start_menu_keyboard, get_select_type_keyboard, get_select_type_filter_keyboard, \
    get_short_filter_keyboard, \
    get_full_filter_flat_keyboard, get_full_filter_house_keyboard, get_select_currency_keyboard, get_yes_no_keyboard, \
    get_main_filter_keyboard, get_districts_keyboard, get_rooms_keyboard, get_save_keyboard, get_floor_keyboard, \
    get_animals_keyboard, get_yes_no_checkbox_keyboard, get_floors_keyboard, get_select_type_subscribe
from src.utils.other import get_state_data, add_filter_to_base, unmute_user, \
    get_created_filters, remove_filter, change_language, get_language, get_state, get_premium, \
    get_number_suitable_housing
from src.app.bot import main_bot

tutor_locales = LocalizationManager()
tutor_locales.load_from_csv(config.tutor_localization_path)

locales = LocalizationManager()
locales.load_from_csv(config.localization_path)
router = Router()


# юзер нажал "начать снова" после паузы
@router.callback_query(MenuStates.stop_state, F.data == "get")
async def comebacked_user(message: Message, state: FSMContext):
    last_message = await main_bot.send_message(chat_id=message.from_user.id,
                                               text=locales.get_localized_string("Kb_start_menu",
                                                                                 get_language(await state.get_data())),
                                               reply_markup=get_start_menu_keyboard(await state.get_data()))
    await state.set_state(MenuStates.start_menu)
    unmute_user(message.from_user.id)
    await state.update_data(lmt=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    # await get_state(state)
    await delete_extra_messages(state, last_message)


@router.callback_query(MenuStates.start_menu, F.data == "tutor_off")
async def tutor_off(c: CallbackQuery, state: FSMContext):
    await state.update_data(tutor=0)
    last_message = await main_bot.send_message(chat_id=c.from_user.id,
                                               text=locales.get_localized_string("Kb_start_menu",
                                                                                 get_language(await state.get_data())),
                                               reply_markup=get_start_menu_keyboard(await state.get_data()))

    await main_bot.answer_callback_query(c.id, locales.get_localized_string("Mg_tutor_off",
                                                                            get_language(await state.get_data())),
                                         show_alert=True)
    await state.update_data(lmt=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    # await get_state(state)
    await delete_extra_messages(state, last_message)


# платеж
@router.callback_query(MenuStates.start_menu, F.data == "premium")
async def premium(c: CallbackQuery, state: FSMContext):
    await state.set_state(MenuStates.buy_premium)
    # если у юзера нет премиум, то выводим кнопки покупки премиума
    weekly_link = await main_bot.create_invoice_link(
        title='7 DAYS PREMIUM',
        description='Weekly Subscription RentyAm',
        payload='weeksub',
        currency='XTR',
        prices=[{'label': 'Price', 'amount': config.weekly_premium_price}],  # 100
    )
    monthly_link = await main_bot.create_invoice_link(
        title='30 DAYS PREMIUM',
        description='Monthly Subscription RentyAm',
        payload='monsub',
        currency='XTR',
        prices=[{'label': 'Price', 'amount': config.monthly_premium_price}],  # 250
    )
    # если премиума нет, то локаль с преимуществами
    text = locales.get_localized_string("Mg_premium", get_language(await state.get_data()))
    if get_premium(c.from_user.id) == 1 and db_get_end_time_subscription(c.from_user.id) is not None:
        expired_time = db_get_end_time_subscription(c.from_user.id)
        text += f'\n\n<b>{locales.get_localized_string("Txt_premium_active_to", get_language(await state.get_data()))} {str(expired_time.strftime("%d.%m.%Y %H:%M"))} UTC </b>'
    elif get_premium(c.from_user.id) == 1 and db_get_end_time_subscription(c.from_user.id) is None:
        text = "ERROR! Contact with support"
    last_message = await main_bot.send_message(chat_id=c.from_user.id,
                                               text=text,
                                               parse_mode='HTML',
                                               reply_markup=get_select_type_subscribe(
                                                   state_data=await state.get_data(),
                                                   confirmation_tgstars_url_weekly=weekly_link,
                                                   confirmation_tgstars_url_monthly=monthly_link
                                               ))

    await delete_extra_messages(state, last_message)
    await main_bot.answer_callback_query(c.id)
    await state.update_data(lmt=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))


@router.callback_query(MenuStates.buy_premium, F.data == "unsubscribe")
async def unsubscribe(c: CallbackQuery, state: FSMContext):
    await main_bot.send_message(chat_id=c.from_user.id,
                                text=locales.get_localized_string("Mg_unsubscribed_manually",
                                                                  get_language(await state.get_data())))
    last_message = await main_bot.send_message(chat_id=c.from_user.id,
                                               text=locales.get_localized_string("Kb_start_menu",
                                                                                 get_language(await state.get_data())),
                                               reply_markup=get_start_menu_keyboard(await state.get_data()))
    await delete_extra_messages(state, last_message)
    await main_bot.answer_callback_query(c.id)
    await state.set_state(MenuStates.start_menu)
    await state.update_data(lmt=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))


@router.message(MenuStates.start_menu, lambda message: message.text.isdigit())
async def input_filter_number(message: Message, state: FSMContext):
    if await get_state_data(state, "previous_button") == "delete_filter":
        filter_number = int(message.text)
        user_id = message.from_user.id
        # если ввели 0, то удаляем все фильтры
        if filter_number == 0:
            await remove_filter(user_id, 0)
            await message.answer(
                locales.get_localized_string("Mg_all_filters_deleted", get_language(await state.get_data())))
            if await get_created_filters(user_id, await state.get_data()):
                last_message = await main_bot.send_message(chat_id=message.from_user.id,
                                                           text=locales.get_localized_string("Kb_more_filters",
                                                                                             get_language(
                                                                                                 await state.get_data())),
                                                           reply_markup=get_yes_no_keyboard(await state.get_data()))
            # если фильтров больше нет, то говорим, что фильтров больше нет и призываем создать
            else:
                last_message = await main_bot.send_message(chat_id=message.from_user.id,
                                                           text=locales.get_localized_string("Kb_no_filters",
                                                                                             get_language(
                                                                                                 await state.get_data())),
                                                           reply_markup=get_start_menu_keyboard(await state.get_data()))
            await delete_extra_messages(state, last_message)
        # если ввели номер существующего фильтра
        elif await remove_filter(user_id, filter_number):
            get_localized_string = locales.get_localized_string("Mg_filter_deleted", get_language(await state.get_data()))
            localized_string = get_localized_string.replace("@", str(filter_number))
            await message.answer(localized_string)
            # если еще есть фильтры, то спрашиваем хочет ли еще удалить
            if await get_created_filters(user_id, await state.get_data()):
                last_message = await main_bot.send_message(chat_id=message.from_user.id,
                                                           text=locales.get_localized_string("Kb_more_filters",
                                                                                             get_language(
                                                                                                 await state.get_data())),
                                                           reply_markup=get_yes_no_keyboard(await state.get_data()))
            # если фильтров больше нет, то говорим, что фильтров больше нет и призываем создать
            else:
                last_message = await main_bot.send_message(chat_id=message.from_user.id,
                                                           text=locales.get_localized_string("Kb_no_filters",
                                                                                             get_language(
                                                                                                 await state.get_data())),
                                                           reply_markup=get_start_menu_keyboard(await state.get_data()))
            await delete_extra_messages(state, last_message)
        # если ввели неправильный номер фильтра
        else:
            await message.answer(locales.get_localized_string("Mg_incorrect_number", get_language(await state.get_data())))

        await state.update_data(lmt=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))


# нажатие на смену языка
@router.callback_query(MenuStates.start_menu, lambda c: c.data in ['en', 'ru', 'hy', 'hi'])
async def select_language(c: CallbackQuery, state: FSMContext):
    language = c.data
    user = c.from_user.id
    await state.update_data(lang=c.data)
    await change_language(user, language)
    if await get_state_data(state, "tutor"):
        last_message = await main_bot.send_message(chat_id=c.from_user.id,
                                                   text=tutor_locales.get_localized_string("Tutor_kb_start_menu",
                                                                                           language),
                                                   reply_markup=get_start_menu_keyboard(await state.get_data()))
    else:
        last_message = await main_bot.send_message(chat_id=c.from_user.id,
                                                   text=locales.get_localized_string("Kb_start_menu", language),
                                                   reply_markup=get_start_menu_keyboard(await state.get_data()))
    await delete_extra_messages(state, last_message)
    await main_bot.answer_callback_query(c.id)
    await state.update_data(lmt=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    #await get_state(state)


@router.callback_query(MenuStates.start_menu, F.data == "delete_filter")
async def delete_filter(c: CallbackQuery, state: FSMContext):
    await state.update_data(previous_button="delete_filter")
    created_filters = await get_created_filters(c.from_user.id, await state.get_data())
    if created_filters:
        last_message = await main_bot.send_message(chat_id=c.from_user.id,
                                    text=f'{created_filters}{locales.get_localized_string("Mg_select_delete_filter", get_language(await state.get_data()))}')
        await main_bot.answer_callback_query(c.id)
        await delete_extra_messages(state, last_message)
    else:
        await main_bot.answer_callback_query(c.id,
                                             locales.get_localized_string("Mg_cant_delete",
                                                                          get_language(
                                                                              await state.get_data())),
                                             show_alert=True)
    await state.update_data(lmt=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))


@router.callback_query(MenuStates.start_menu, lambda c: c.data == "yes" or c.data == "no")
async def delete_more_filter(c: CallbackQuery, state: FSMContext):
    created_filters = await get_created_filters(c.from_user.id, await state.get_data())
    if c.data == "yes" and created_filters:
        await main_bot.send_message(chat_id=c.from_user.id,
                                    text=f'{created_filters}{locales.get_localized_string("Mg_select_delete_filter", get_language(await state.get_data()))}')
    else:
        await main_bot.send_message(chat_id=c.from_user.id,
                                    text=locales.get_localized_string("Mg_no_filters_1",
                                                                      get_language(
                                                                          await state.get_data())))
        last_message = await main_bot.send_message(chat_id=c.from_user.id,
                                                   text=locales.get_localized_string("Kb_start_menu",
                                                                                     get_language(
                                                                                         await state.get_data())),
                                                   reply_markup=get_start_menu_keyboard(await state.get_data()))
        await delete_extra_messages(state, last_message)
        await state.set_state(MenuStates.start_menu)
    await main_bot.answer_callback_query(c.id)
    await state.update_data(lmt=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))


# в стартовом меню юзер выбираем любое объявление
@router.callback_query(MenuStates.start_menu, F.data != "create_filter")
async def get_any_ads(call: CallbackQuery, state: FSMContext):
    if call.data == "get_any_flats":  # если нажали на квартиры
        data = await get_state_data(state, call.data)  # получаем значение по ключу, равному колбэк дате
        if data is None:  # если данных нет
            await state.update_data(get_any_flats=True)  # значит юзер первый раз нажал на кнопку и устанвливаем True
        if data is not None:  # если у нас есть данные по выбору
            data = not data  # инвертируем текущее значение
            await state.update_data(get_any_flats=data)  # записываем новое значение в state.data юзера

    # аналогично, только в домами
    elif call.data == "get_any_houses":
        data = await get_state_data(state, call.data)
        if data is None:
            await state.update_data(get_any_houses=True)
        if data is not None:
            data = not data
            await state.update_data(get_any_houses=data)

    # возвращаем клавиатуру методом, которой принимает state.data
    await main_bot.edit_message_reply_markup(call.message.chat.id,
                                             call.message.message_id,
                                             reply_markup=get_start_menu_keyboard(await state.get_data())
                                             )
    await state.update_data(lmt=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    # await get_state(state)
    await main_bot.answer_callback_query(call.id)


# юзер нажал на создание фильтра
@router.callback_query(MenuStates.start_menu, F.data == "create_filter")
async def create_filter(c: CallbackQuery, state: FSMContext):
    state_data = await state.get_data()
    if state_data.get("tutor"):
        await main_bot.edit_message_text(chat_id=c.message.chat.id,
                                         message_id=c.message.message_id,
                                         text=tutor_locales.get_localized_string("Tutor_kb_select_type",
                                                                                 get_language(await state.get_data())))

    else:
        await main_bot.edit_message_text(chat_id=c.message.chat.id,
                                         message_id=c.message.message_id,
                                         text=locales.get_localized_string("Kb_select_type",
                                                                           get_language(await state.get_data())))
    # выводим клавиатуру с выбором типа (дом/квартира)
    await main_bot.edit_message_reply_markup(c.message.chat.id,
                                             c.message.message_id,
                                             reply_markup=get_select_type_keyboard(await state.get_data()))
    await state.set_state(MenuStates.select_type)
    # await get_state(state)
    await main_bot.answer_callback_query(c.id)
    await state.update_data(previous_button="create_filter")
    await state.update_data(lmt=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))


# смотрим какой тип (дом/квартира) выбрал юзер
@router.callback_query(MenuStates.select_type, F.data != "back_to_main_menu")
async def select_type(c: CallbackQuery, state: FSMContext):
    await main_bot.edit_message_text(chat_id=c.message.chat.id,
                                     message_id=c.message.message_id,
                                     text=locales.get_localized_string("Kb_select_type",
                                                                       get_language(await state.get_data())))
    # если выбрана квартира
    if c.data == "selected_flat":
        # записываем в стейт, что тип теперь квартира
        await state.update_data(selected_type=c.data)
    elif c.data == "selected_house":
        await state.update_data(selected_type=c.data)

    # выводим клавиатуру с выбором короткий/длинный
    await main_bot.edit_message_text(chat_id=c.message.chat.id, message_id=c.message.message_id,
                                     text=locales.get_localized_string("Kb_select_type_filter",
                                                                       get_language(await state.get_data())))
    await main_bot.edit_message_reply_markup(c.message.chat.id, c.message.message_id,
                                             reply_markup=get_select_type_filter_keyboard(await state.get_data()))
    await state.set_state(MenuStates.select_type_filter)
    await state.update_data(lmt=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    # await get_state(state)
    await main_bot.answer_callback_query(c.id)


# смотрим какой тип (короткий/длинный) выбрал юзер
@router.callback_query(MenuStates.select_type_filter, F.data != "back_to_select_type")
async def select_type_filter(c: CallbackQuery, state: FSMContext):
    current_state_data = await state.get_data()
    await main_bot.edit_message_text(chat_id=c.message.chat.id, message_id=c.message.message_id,
                                     text=locales.get_localized_string("Kb_main_filter",
                                                                       get_language(await state.get_data())))
    # выбираем по условию - короткий фильтр или полный
    if c.data == "type_short":  # если выбрал короткий
        if current_state_data.get("selected_type") == "selected_flat":  # если до этого уже выбрал квартиру
            await state.update_data(selected_filter_type="flat_short")
        else:
            await state.update_data(selected_filter_type="house_short")
        await main_bot.edit_message_reply_markup(c.message.chat.id, c.message.message_id,
                                                 reply_markup=get_short_filter_keyboard(await state.get_data()))

    elif c.data == "type_full":  # если выбрал длинный
        if current_state_data.get("selected_type") == "selected_flat":  # если до этого уже выбрал квартиру
            await state.update_data(selected_filter_type="flat_full")
            await main_bot.edit_message_reply_markup(c.message.chat.id, c.message.message_id,
                                                     reply_markup=get_full_filter_flat_keyboard(await state.get_data()))
        else:  # если до этого уже выбрал дома
            await state.update_data(selected_filter_type="house_full")
            await main_bot.edit_message_reply_markup(c.message.chat.id, c.message.message_id,
                                                     reply_markup=get_full_filter_house_keyboard(
                                                         await state.get_data()))

    await main_bot.answer_callback_query(c.id)
    await state.set_state(MenuStates.main_filter)
    await state.update_data(lmt=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    # await get_state(state)


# кнопки назад
@router.callback_query(MenuStates.select_type, F.data == "back_to_main_menu")
async def back_button_handler_st(c: CallbackQuery, state: FSMContext):
    await main_bot.answer_callback_query(c.id)
    await state.set_state(MenuStates.start_menu)
    if await get_state_data(state, "tutor"):
        await main_bot.edit_message_text(chat_id=c.message.chat.id,
                                         message_id=c.message.message_id,
                                         text=tutor_locales.get_localized_string("Tutor_kb_start_menu",
                                                                                 get_language(await state.get_data())))
    else:
        await main_bot.edit_message_text(chat_id=c.message.chat.id,
                                         message_id=c.message.message_id,
                                         text=locales.get_localized_string("Kb_start_menu",
                                                                           get_language(await state.get_data())))
    await main_bot.edit_message_reply_markup(c.message.chat.id, c.message.message_id,
                                             reply_markup=get_start_menu_keyboard(await state.get_data()))
    # await get_state(state)
    await state.update_data(lmt=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))


@router.callback_query(MenuStates.select_type_filter, F.data == "back_to_select_type")
async def back_button_handler_stf(c: CallbackQuery, state: FSMContext):
    await main_bot.edit_message_text(chat_id=c.message.chat.id, message_id=c.message.message_id,
                                     text=locales.get_localized_string("Kb_select_type",
                                                                       get_language(await state.get_data())))
    await main_bot.answer_callback_query(c.id)
    await main_bot.edit_message_reply_markup(c.message.chat.id, c.message.message_id,
                                             reply_markup=get_select_type_keyboard(await state.get_data()))
    await state.set_state(MenuStates.select_type)
    await state.update_data(lmt=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    # await get_state(state)


@router.callback_query(MenuStates.main_filter, F.data == "back_to_select_type_filter")
async def back_button_handler_mf(c: CallbackQuery, state: FSMContext):
    await main_bot.edit_message_text(chat_id=c.message.chat.id,
                                     message_id=c.message.message_id,
                                     text=locales.get_localized_string("Kb_select_type_filter",
                                                                       get_language(await state.get_data())))
    await main_bot.edit_message_reply_markup(c.message.chat.id,
                                             c.message.message_id,
                                             reply_markup=get_select_type_filter_keyboard(await state.get_data()))
    await main_bot.answer_callback_query(c.id)
    await state.set_state(MenuStates.select_type_filter)
    await state.update_data(lmt=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    # await get_state(state)


@router.callback_query(MenuStates.select_option, F.data == "back_to_main_filter")
async def back_button_handler_so(c: CallbackQuery, state: FSMContext):
    current_state_data = await state.get_data()
    await main_bot.edit_message_text(chat_id=c.message.chat.id,
                                     message_id=c.message.message_id,
                                     text=locales.get_localized_string("Kb_main_filter",
                                                                       get_language(await state.get_data())))
    if current_state_data.get("selected_filter_type") == "flat_short" or current_state_data.get(
            "selected_filter_type") == "house_short":
        await main_bot.edit_message_reply_markup(c.message.chat.id,
                                                 c.message.message_id,
                                                 reply_markup=get_short_filter_keyboard(await state.get_data()))
    elif current_state_data.get("selected_filter_type") == "flat_full":
        await main_bot.edit_message_reply_markup(c.message.chat.id,
                                                 c.message.message_id,
                                                 reply_markup=get_full_filter_flat_keyboard(await state.get_data()))
    elif current_state_data.get("selected_filter_type") == "house_full":
        await main_bot.edit_message_reply_markup(c.message.chat.id,
                                                 c.message.message_id,
                                                 reply_markup=get_full_filter_house_keyboard(await state.get_data()))

    await main_bot.answer_callback_query(c.id)
    await state.set_state(MenuStates.main_filter)
    await state.update_data(lmt=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    # await get_state(state)


# кнопки назад закончились


# юзер выбирает менять валюту или не менять после того, как он ее уже выбрал однажды
@router.callback_query(MenuStates.main_filter,
                       lambda c: c.data == "yes" or c.data == "no")  # здесь используем lamda, а не F.data, потому что с ней почему-то не работает...
async def yes_no_keyboard(c: CallbackQuery, state: FSMContext):
    if c.data == "yes":
        await main_bot.edit_message_text(chat_id=c.message.chat.id,
                                         message_id=c.message.message_id,
                                         text=locales.get_localized_string("Mg_select_currency",
                                                                           get_language(await state.get_data())))
        await main_bot.edit_message_reply_markup(c.message.chat.id, c.message.message_id,
                                                 reply_markup=get_select_currency_keyboard(await state.get_data()))
    else:
        last_message = await main_bot.send_message(c.message.chat.id,
                                                   locales.get_localized_string("Mg_input_price",
                                                                                get_language(await state.get_data())))
        await delete_extra_messages(state, last_message)

    await main_bot.answer_callback_query(c.id)
    await state.set_state(MenuStates.select_option)
    await state.update_data(lmt=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))


@router.callback_query(MenuStates.main_filter, F.data == "cant_save_filter")
async def cant_save_filter(c: CallbackQuery, state: FSMContext):
    await main_bot.answer_callback_query(c.id,
                                         locales.get_localized_string("Mg_cant_save_filter",
                                                                      get_language(
                                                                          await state.get_data())),
                                         show_alert=True)


# юзер нажал сохранить финальный фильтр
@router.callback_query(MenuStates.main_filter, F.data == "save_filter")
async def save_filter(c: CallbackQuery, state: FSMContext):
    await main_bot.edit_message_text(chat_id=c.message.chat.id, message_id=c.message.message_id,
                                     text=locales.get_localized_string("Kb_approve_create",
                                                                       get_language(await state.get_data())))
    await main_bot.edit_message_reply_markup(c.message.chat.id, c.message.message_id,
                                             reply_markup=get_save_keyboard(await state.get_data()))
    await state.update_data(previous_button=c.data)
    await state.set_state(MenuStates.save_filter)
    await main_bot.answer_callback_query(c.id)
    await state.update_data(lmt=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    # await get_state(state)


# юзер подтверждает создание фильтра
@router.callback_query(MenuStates.save_filter,
                       lambda c: c.data == "yes_sure" or c.data == "no_sure" or c.data == "dontknow")
async def sure_save_filter(c: CallbackQuery, state: FSMContext):
    if c.data == "yes_sure":
        # сохраняем предыдущее состояние кнопок получения всех квартир или домов
        state_data = await state.get_data()
        language = state_data.get("lang")
        user_id = state_data.get("user_id")
        await state.update_data(previous_button=c.data)
        await state.update_data(user_id=c.from_user.id)  # Добавляем в стейт дату ID юзера
        await add_filter_to_base(await state.get_data())  # добавляем фильтр в базу фильтров
        await state.clear()  # чистим стейт дату

        await state.update_data(lang=language)
        await state.update_data(user_id=user_id)


        localized_text = locales.get_localized_string("Kb_filter_added",
                                                                           get_language(await state.get_data())).replace('@', str(await get_number_suitable_housing(c.from_user.id)))
        last_message = await main_bot.edit_message_text(chat_id=c.message.chat.id,
                                         message_id=c.message.message_id,
                                         text=f'{localized_text}')
        await main_bot.edit_message_reply_markup(c.message.chat.id, c.message.message_id,
                                                 reply_markup=get_yes_no_keyboard(await state.get_data()))
        await main_bot.answer_callback_query(c.id)
        await state.set_state(MenuStates.save_filter)
        await delete_extra_messages(state, last_message)
        # await get_state(state)
    elif c.data == "no_sure":
        await main_bot.edit_message_text(chat_id=c.message.chat.id, message_id=c.message.message_id,
                                         text=locales.get_localized_string("Kb_return_edit_filter",
                                                                           get_language(await state.get_data())))
        await main_bot.edit_message_reply_markup(c.message.chat.id, c.message.message_id,
                                                 reply_markup=get_main_filter_keyboard(await state.get_data()))
        await main_bot.answer_callback_query(c.id)
        await state.set_state(MenuStates.main_filter)

    elif c.data == "dontknow":
        last_message = await main_bot.send_message(c.message.chat.id,
                                    locales.get_localized_string("Mg_ill_wait",
                                                                 get_language(await state.get_data())))
        await main_bot.answer_callback_query(c.id)
        await delete_extra_messages(state, last_message)
    await main_bot.answer_callback_query(c.id)
    await state.update_data(lmt=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    # await get_state(state)


# юзер хочет еще фильтр или нет
@router.callback_query(MenuStates.save_filter, lambda c: c.data == "yes" or c.data == "no")
async def more_filter(c: CallbackQuery, state: FSMContext):
    if c.data == "yes":
        await state.set_state(MenuStates.main_filter)
        await main_bot.edit_message_text(chat_id=c.message.chat.id,
                                         message_id=c.message.message_id,
                                         text=locales.get_localized_string("Kb_select_type",
                                                                           get_language(await state.get_data())))

        await main_bot.edit_message_reply_markup(c.message.chat.id,
                                                 c.message.message_id,
                                                 reply_markup=get_select_type_keyboard(await state.get_data())
                                                 )
        await state.set_state(MenuStates.select_type)
    if c.data == "no":
        last_message = await main_bot.send_message(c.message.chat.id,
                                    locales.get_localized_string("Kb_no_more_filters",
                                                                 get_language(await state.get_data())))
        await delete_extra_messages(state, last_message)
        unmute_user(c.from_user.id)
    await main_bot.answer_callback_query(c.id)
    await state.update_data(lmt=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    # await get_state(state)


# смотрим что нажмет юзер в главной настройке фильтра
@router.callback_query(MenuStates.main_filter, F.data != "back_to_select_type_filter")
async def main_filter(c: CallbackQuery, state: FSMContext):
    # если юзер нажал по выбору цены
    if c.data == "price_min" or c.data == "price_max":
        await state.update_data(previous_button=c.data)
        current_currency = await get_state_data(state, "selected_currency")
        # если у юзера отсутствует информация о выбранной валюте, то выводим выбор валюты
        if current_currency is None:
            await main_bot.edit_message_text(chat_id=c.message.chat.id,
                                             message_id=c.message.message_id,
                                             text=locales.get_localized_string("Mg_select_currency",
                                                                               get_language(await state.get_data())))
            await main_bot.edit_message_reply_markup(c.message.chat.id, c.message.message_id,
                                                                    reply_markup=get_select_currency_keyboard(
                                                                        await state.get_data()))
            await main_bot.answer_callback_query(c.id)
            await state.set_state(MenuStates.select_option)
            # await get_state(state)
        # если у юзера уже выбрана валюта
        elif current_currency is not None:
            if c.data == "price_min" and await get_state_data(state,
                                                              "price_min") is not None:  # если юзер нажал мин цену и он уже вводил цену
                await main_bot.edit_message_text(chat_id=c.message.chat.id,
                                                 message_id=c.message.message_id,
                                                 text=locales.get_localized_string("Kb_change_currency", get_language(
                                                     await state.get_data())),
                                                 reply_markup=get_yes_no_keyboard(await state.get_data()))
            elif c.data == "price_max" and await get_state_data(state,
                                                                "price_max") is not None:  # если юзер нажал макс цену и он уже вводил цену
                await main_bot.edit_message_text(chat_id=c.message.chat.id,
                                                 message_id=c.message.message_id,
                                                 text=locales.get_localized_string("Kb_change_currency", get_language(
                                                     await state.get_data())),
                                                 reply_markup=get_yes_no_keyboard(await state.get_data()))
            else:  # если юзер выбрал валюту, но у него не записана цена
                last_message = await main_bot.send_message(c.message.chat.id,
                                                           locales.get_localized_string("Mg_input_price",
                                                                                        get_language(
                                                                                            await state.get_data())))
                await state.set_state(MenuStates.select_option)
                await delete_extra_messages(state, last_message)

    # выбор района
    if c.data == "districts":
        await main_bot.edit_message_text(chat_id=c.message.chat.id,
                                         message_id=c.message.message_id,
                                         text=locales.get_localized_string("Kb_districts",
                                                                           get_language(await state.get_data())))
        await main_bot.edit_message_reply_markup(c.message.chat.id, c.message.message_id,
                                                 reply_markup=get_districts_keyboard(await state.get_data()))
        await state.update_data(previous_button=c.data)
        await state.set_state(MenuStates.checkbox_kb)
        # await get_state(state)

    # выбор комнат
    if c.data == "rooms":
        await state.update_data(previous_button=c.data)
        await main_bot.edit_message_text(chat_id=c.message.chat.id,
                                         message_id=c.message.message_id,
                                         text=locales.get_localized_string("Kb_rooms",
                                                                           get_language(await state.get_data())))
        await main_bot.edit_message_reply_markup(c.message.chat.id, c.message.message_id,
                                                 reply_markup=get_rooms_keyboard(await state.get_data()))
        await state.set_state(MenuStates.checkbox_kb)
        # await get_state(state)

    # выбор этажей (только для полного фильтра квартиры)
    if c.data == "floor_min" or c.data == "floor_max":
        await state.update_data(previous_button=c.data)
        if c.data == "floor_min":
            await main_bot.edit_message_text(chat_id=c.message.chat.id,
                                             message_id=c.message.message_id,
                                             text=locales.get_localized_string("Kb_floor_min",
                                                                               get_language(await state.get_data())))
            await main_bot.edit_message_reply_markup(c.message.chat.id, c.message.message_id,
                                                     reply_markup=get_floor_keyboard(await state.get_data()))
        else:
            await main_bot.edit_message_text(chat_id=c.message.chat.id,
                                             message_id=c.message.message_id,
                                             text=locales.get_localized_string("Kb_floor_max",
                                                                               get_language(await state.get_data())))
            await main_bot.edit_message_reply_markup(c.message.chat.id, c.message.message_id,
                                                     reply_markup=get_floor_keyboard(await state.get_data()))
        await state.set_state(MenuStates.checkbox_kb)
        # await get_state(state)

    # выбор этажей (только для полного фильтра дома)
    if c.data == "floors":
        await main_bot.edit_message_text(chat_id=c.message.chat.id,
                                         message_id=c.message.message_id,
                                         text=locales.get_localized_string("Kb_select_floors",
                                                                           get_language(await state.get_data())))
        await main_bot.edit_message_reply_markup(c.message.chat.id,
                                                 c.message.message_id,
                                                 reply_markup=get_floors_keyboard(await state.get_data()))
        await state.update_data(previous_button=c.data)
        await state.set_state(MenuStates.checkbox_kb)
        # await get_state(state)

    # выбор площади
    if c.data == "square_min" or c.data == "square_max":
        await state.update_data(previous_button=c.data)
        last_message = await main_bot.send_message(c.message.chat.id,
                                                   locales.get_localized_string("Mg_input_square",
                                                                                get_language(await state.get_data())))
        await state.set_state(MenuStates.select_option)
        await delete_extra_messages(state, last_message)
        # await get_state(state)

    # выбор животных
    if c.data == "animals":
        await state.update_data(previous_button=c.data)
        await main_bot.edit_message_text(chat_id=c.message.chat.id,
                                         message_id=c.message.message_id,
                                         text=locales.get_localized_string("Kb_animals",
                                                                           get_language(await state.get_data())))
        await main_bot.edit_message_reply_markup(c.message.chat.id,
                                                 c.message.message_id,
                                                 reply_markup=get_animals_keyboard(await state.get_data()))
        await state.set_state(MenuStates.checkbox_kb)
        # await get_state(state)

    # выбор кондиционера
    if c.data == "ac":
        await state.update_data(previous_button=c.data)
        await main_bot.edit_message_text(chat_id=c.message.chat.id,
                                         message_id=c.message.message_id,
                                         text=locales.get_localized_string("Kb_ac",
                                                                           get_language(await state.get_data())))
        await main_bot.edit_message_reply_markup(c.message.chat.id,
                                                 c.message.message_id,
                                                 reply_markup=get_yes_no_checkbox_keyboard(await state.get_data()))
        await state.set_state(MenuStates.checkbox_kb)
        # await get_state(state)

    # выбор владелец/агент
    if c.data == "owner":
        await state.update_data(previous_button=c.data)
        await main_bot.edit_message_text(chat_id=c.message.chat.id,
                                         message_id=c.message.message_id,
                                         text=locales.get_localized_string("Kb_owner",
                                                                           get_language(await state.get_data())))
        await main_bot.edit_message_reply_markup(c.message.chat.id,
                                                 c.message.message_id,
                                                 reply_markup=get_yes_no_checkbox_keyboard(await state.get_data()))
        await state.set_state(MenuStates.checkbox_kb)
        # await get_state(state)

    # если юзер ответил да/нет на вопрос о создании еще одного фильтра
    if c.data == "yes_more" or c.data == "no_enough":
        if c.data == "yes_more":
            await main_bot.edit_message_reply_markup(c.from_user.id,
                                                     c.message.message_id,
                                                     reply_markup=get_start_menu_keyboard(await state.get_data()))
        else:
            await main_bot.edit_message_text(chat_id=c.message.chat.id, message_id=c.message.message_id,
                                             text=locales.get_localized_string("Mg_no_enough_filters",
                                                                               get_language(await state.get_data())))
    await main_bot.answer_callback_query(c.id)
    await state.update_data(lmt=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))


# хендлер для цен
@router.callback_query(MenuStates.select_option, F.data != "back_to_main_filter")
async def select_option(c: CallbackQuery, state: FSMContext):
    # часть, отвечающая за цены
    if c.data in ["amd", "usd", "rur"]:  # если юзер выбрал валюту, то записываем ее и просим ввести цену
        await state.update_data(selected_currency=c.data)
        await main_bot.answer_callback_query(c.id)
        last_message = await main_bot.send_message(c.message.chat.id,
                                                   locales.get_localized_string("Mg_input_price",
                                                                                get_language(await state.get_data())))
        await delete_extra_messages(state, last_message)
    # await get_state(state)
    await main_bot.answer_callback_query(c.id)


# хендлер для обработки меню, где выбор чекбоксами: районы, комнаты
@router.callback_query(MenuStates.checkbox_kb)
async def checkbox_keyboard_handler(c: CallbackQuery, state: FSMContext):
    previous_button = await get_state_data(state, "previous_button")
    # логика по районам
    if previous_button == "districts":
        if await get_state_data(state, "selected_districts") is None:
            selected_districts = []
            await state.update_data(selected_districts=selected_districts)

        if previous_button == "districts":
            if c.data == "save_districts":
                if len(await get_state_data(state, "selected_districts")) < 1:
                    await state.update_data(selected_districts=None)
                await state.set_state(MenuStates.main_filter)
                await main_bot.edit_message_text(chat_id=c.message.chat.id,
                                                 message_id=c.message.message_id,
                                                 text=locales.get_localized_string("Kb_main_filter",
                                                                                   get_language(
                                                                                       await state.get_data())))
                await main_bot.edit_message_reply_markup(c.message.chat.id,
                                                         c.message.message_id,
                                                         reply_markup=get_main_filter_keyboard(await state.get_data())
                                                         )  # вызываем функцию, чтобы понять какое у него было меню
            else:
                selected_districts = await get_state_data(state, "selected_districts")
                if c.data not in await get_state_data(state, "selected_districts"):
                    selected_districts.append(c.data)
                elif c.data in await get_state_data(state, "selected_districts"):
                    selected_districts.remove(c.data)
                await state.update_data(selected_districts=selected_districts)
                await main_bot.edit_message_reply_markup(c.message.chat.id, c.message.message_id,
                                                         reply_markup=get_districts_keyboard(await state.get_data()))

    # логика по комнатам
    if previous_button == "rooms":
        if c.data == "save_rooms":
            await state.set_state(MenuStates.main_filter)
            await main_bot.edit_message_text(chat_id=c.message.chat.id,
                                             message_id=c.message.message_id,
                                             text=locales.get_localized_string("Kb_main_filter",
                                                                               get_language(
                                                                                   await state.get_data())))
            await main_bot.edit_message_reply_markup(c.message.chat.id,
                                                     c.message.message_id,
                                                     reply_markup=get_main_filter_keyboard(await state.get_data())
                                                     )  # вызываем функцию, чтобы понять какое у него было меню
        else:
            if await get_state_data(state, "selected_rooms") is None:
                selected_rooms = []
            else:
                selected_rooms = await get_state_data(state, "selected_rooms")
            if c.data not in selected_rooms:
                selected_rooms.append(c.data)
            elif c.data in selected_rooms:
                selected_rooms.remove(c.data)
            selected_rooms = sorted(selected_rooms, key=lambda x: int(x.rstrip('+')))
            if not selected_rooms:
                selected_rooms = None
            await state.update_data(selected_rooms=selected_rooms)
            await main_bot.edit_message_reply_markup(c.message.chat.id, c.message.message_id,
                                                     reply_markup=get_rooms_keyboard(await state.get_data()))

    # логика по кнопкам этажей
    # если была нажата кнопка floor_min или floor_max
    if previous_button == "floor_min" or previous_button == "floor_max":
        # если нажали сохранить
        if c.data == "save_floor":
            await state.set_state(MenuStates.main_filter)
            await main_bot.edit_message_text(chat_id=c.message.chat.id,
                                             message_id=c.message.message_id,
                                             text=locales.get_localized_string("Kb_main_filter",
                                                                               get_language(
                                                                                   await state.get_data())))
            await main_bot.edit_message_reply_markup(c.message.chat.id,
                                                     c.message.message_id,
                                                     reply_markup=get_main_filter_keyboard(await state.get_data())
                                                     )  # вызываем функцию, чтобы понять какое у него было меню
        else:
            # получаем стейт дату по кнопке. Например, какой этаж был выбран при floor_min. Второе условие проверяет, что там не та же дата, что и была
            if await get_state_data(state, previous_button) is None or c.data not in await get_state_data(state,
                                                                                                          previous_button):
                await state.update_data(**{previous_button: c.data})
                # доппроверка, чтоыб не было макс меньше мин
                await main_bot.edit_message_reply_markup(c.message.chat.id,
                                                         c.message.message_id,
                                                         reply_markup=get_floor_keyboard(await state.get_data()))
            # если юзер нажал тот же этаж, что и раньше
            elif c.data == await get_state_data(state, previous_button):
                await state.update_data(**{previous_button: None})
                await main_bot.edit_message_reply_markup(c.message.chat.id,
                                                         c.message.message_id,
                                                         reply_markup=get_floor_keyboard(await state.get_data()))
            # проверка, что максимум больше минимума и наоборот
            floor_min = await get_state_data(state, "floor_min")
            floor_max = await get_state_data(state, "floor_max")

            if floor_min is not None and floor_max is not None:
                if int(floor_min) > int(floor_max):
                    await main_bot.send_message(chat_id=c.message.chat.id,
                                                text=locales.get_localized_string("Mg_wrong_min_floor",
                                                                                  get_language(
                                                                                      await state.get_data())))
                    await state.update_data(**{previous_button: None})
                    await main_bot.edit_message_reply_markup(c.message.chat.id, c.message.message_id,
                                                             reply_markup=get_floor_keyboard(await state.get_data()))

    if previous_button == "floors":
        if c.data == "save_floors":
            await state.set_state(MenuStates.main_filter)
            await main_bot.edit_message_text(chat_id=c.message.chat.id,
                                             message_id=c.message.message_id,
                                             text=locales.get_localized_string("Kb_main_filter",
                                                                               get_language(
                                                                                   await state.get_data())))
            await main_bot.edit_message_reply_markup(c.message.chat.id,
                                                     c.message.message_id,
                                                     reply_markup=get_main_filter_keyboard(
                                                         await state.get_data())
                                                     )  # вызываем функцию, чтобы понять какое у него было меню
        else:
            if await get_state_data(state, "selected_floors") is None:
                selected_floors = []
            else:
                selected_floors = await get_state_data(state, "selected_floors")
            if c.data not in selected_floors:
                selected_floors.append(c.data)
            elif c.data in selected_floors:
                selected_floors.remove(c.data)
            selected_floors = sorted(selected_floors, key=lambda x: int(x.rstrip('+')))
            if not selected_floors:
                selected_floors = None
            await state.update_data(selected_floors=selected_floors)
            await main_bot.edit_message_reply_markup(c.message.chat.id, c.message.message_id,
                                                     reply_markup=get_floors_keyboard(await state.get_data()))

    if previous_button == "animals":
        if c.data == "save_animals":
            await state.set_state(MenuStates.main_filter)
            await main_bot.edit_message_text(chat_id=c.message.chat.id,
                                             message_id=c.message.message_id,
                                             text=locales.get_localized_string("Kb_main_filter",
                                                                               get_language(
                                                                                   await state.get_data())))
            await main_bot.edit_message_reply_markup(c.message.chat.id,
                                                     c.message.message_id,
                                                     reply_markup=get_main_filter_keyboard(await state.get_data())
                                                     )  # вызываем функцию, чтобы понять какое у него было меню
        else:
            animals = await get_state_data(state, "selected_animals")
            if animals is None:
                animals = {}

            new_state = not animals.get(c.data)
            if c.data == "no_animals":
                animals.clear()
            else:
                animals["no_animals"] = False

            animals[c.data] = new_state

            if all(value is False for value in animals.values()):
                animals = None
            await state.update_data(selected_animals=animals)
            await main_bot.edit_message_reply_markup(c.message.chat.id,
                                                     c.message.message_id,
                                                     reply_markup=get_animals_keyboard(await state.get_data()))

    if previous_button == "ac":
        ac = await get_state_data(state, "selected_ac")
        if c.data == "save":
            await state.set_state(MenuStates.main_filter)
            await main_bot.edit_message_text(chat_id=c.message.chat.id,
                                             message_id=c.message.message_id,
                                             text=locales.get_localized_string("Kb_main_filter",
                                                                               get_language(
                                                                                   await state.get_data())))
            await main_bot.edit_message_reply_markup(c.message.chat.id,
                                                     c.message.message_id,
                                                     reply_markup=get_main_filter_keyboard(
                                                         await state.get_data()))  # вызываем функцию, чтобы понять какое у него было меню
        else:
            if c.data is None:  # если там пусто как на старте
                await state.update_data(selected_ac=c.data)
            elif c.data == ac:  # если кнопка равна той, которая нажата
                await state.update_data(selected_ac=None)
            else:  # если кнопка не равна той, которая нажат и в данных не пусто
                await state.update_data(selected_ac=c.data)

            await main_bot.edit_message_reply_markup(c.message.chat.id,
                                                     c.message.message_id,
                                                     reply_markup=get_yes_no_checkbox_keyboard(await state.get_data()))

    if previous_button == "owner":
        owner = await get_state_data(state, "selected_owner")
        if c.data == "save":
            await state.set_state(MenuStates.main_filter)
            await main_bot.edit_message_text(chat_id=c.message.chat.id,
                                             message_id=c.message.message_id,
                                             text=locales.get_localized_string("Kb_main_filter",
                                                                               get_language(
                                                                                   await state.get_data())))
            await main_bot.edit_message_reply_markup(c.message.chat.id,
                                                     c.message.message_id,
                                                     reply_markup=get_main_filter_keyboard(
                                                         await state.get_data()))  # вызываем функцию, чтобы понять какое у него было меню
        else:
            if c.data is None:  # если там пусто как на старте
                await state.update_data(selected_owner=c.data)
            elif c.data == owner:  # если кнопка равна той, которая нажата
                await state.update_data(selected_owner=None)
            else:  # если кнопка не равна той, которая нажат и в данных не пусто
                await state.update_data(selected_owner=c.data)

            await main_bot.edit_message_reply_markup(c.message.chat.id,
                                                     c.message.message_id,
                                                     reply_markup=get_yes_no_checkbox_keyboard(await state.get_data()))

    await main_bot.answer_callback_query(c.id)
    await state.update_data(lmt=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    #await get_state(state)


@router.message(MenuStates.select_option, lambda message: message.text.isdigit())
async def input_data(message: Message, state: FSMContext):
    previous_button = await get_state_data(state, "previous_button")
    if previous_button == "price_min" or previous_button == "price_max":
        if message.text.isdigit():  # если ввели цифры
            current_currency = await get_state_data(state, "selected_currency")
            if current_currency is None:  # обработка кейса, когда ввели цифры до выбора валюты и запроса на ввод
                await main_bot.send_message(chat_id=message.chat.id,
                                            text=locales.get_localized_string("Mg_currency_not_selected",
                                                                              get_language(
                                                                                  await state.get_data())))
                return
            elif current_currency == "amd":
                await state.update_data(symbol="֏")
            elif current_currency == "usd":
                await state.update_data(symbol="$")
            elif current_currency == "rur":
                await state.update_data(symbol="₽")
            entered_price = int(message.text)
            price_min = await get_state_data(state, "price_min")
            price_max = await get_state_data(state, "price_max")
            if previous_button == "price_min":
                if price_max is not None and price_max < entered_price:  # обработка кейса, когда ввели минимальную цену больше, чем максимальную
                    await main_bot.send_message(chat_id=message.chat.id,
                                                text=locales.get_localized_string("Mg_wrong_min_price",
                                                                                  get_language(
                                                                                      await state.get_data())))
                else:
                    await state.update_data(price_min=int(message.text))  # Сохраняем введенное число в состояние
                    last_message = await main_bot.send_message(message.chat.id,
                                                               text=locales.get_localized_string("Kb_main_filter",
                                                                                                 get_language(
                                                                                                     await state.get_data())),
                                                               reply_markup=get_main_filter_keyboard(
                                                                   await state.get_data()))
                    await delete_extra_messages(state, last_message)
                    await state.set_state(MenuStates.main_filter)  # Возвращаем пользователя в состояние фильтра

            elif previous_button == "price_max":
                if price_min is not None and price_min > entered_price:
                    await main_bot.send_message(chat_id=message.chat.id,
                                                text=locales.get_localized_string("Mg_wrong_max_price",
                                                                                  get_language(
                                                                                      await state.get_data())))
                else:
                    await state.update_data(price_max=int(message.text))  # Сохраняем введенное число в состояние
                    last_message = await main_bot.send_message(message.chat.id,
                                                               text=locales.get_localized_string("Kb_main_filter",
                                                                                                 get_language(
                                                                                                     await state.get_data())),
                                                               reply_markup=get_main_filter_keyboard(
                                                                   await state.get_data()))
                    await delete_extra_messages(state, last_message)
                    await state.set_state(MenuStates.main_filter)  # Возвращаем пользователя в состояние фильтра

        else:  # Если введено не число, просим ввести число еще раз
            await message.answer(
                locales.get_localized_string("Mg_incorrect_input", get_language(await state.get_data())))
        # await get_state(state)

    # ввод площади
    if previous_button == "square_min" or previous_button == "square_max":
        if message.text.isdigit():  # если ввели цифры
            previous_button = await get_state_data(state, "previous_button")
            entered_square = int(message.text)
            square_min = await get_state_data(state, "square_min")
            square_max = await get_state_data(state, "square_max")
            if previous_button == "square_min":
                if square_max is not None and square_max < entered_square:  # обработка кейса, когда ввели минимальную цену больше, чем максимальную
                    await main_bot.send_message(chat_id=message.chat.id,
                                                text=locales.get_localized_string("Mg_wrong_min_square",
                                                                                  get_language(
                                                                                      await state.get_data())))
                else:
                    await state.update_data(square_min=int(message.text))  # Сохраняем введенное число в состояние
                    last_message = await main_bot.send_message(message.chat.id,
                                                               text=locales.get_localized_string("Kb_main_filter",
                                                                                                 get_language(
                                                                                                     await state.get_data())),
                                                               reply_markup=get_main_filter_keyboard(
                                                                   await state.get_data()))
                    await state.set_state(MenuStates.main_filter)  # Возвращаем пользователя в состояние фильтра
                    await delete_extra_messages(state, last_message)

            elif previous_button == "square_max":
                if square_min is not None and square_min > entered_square:
                    await main_bot.send_message(chat_id=message.chat.id,
                                                text=locales.get_localized_string("Mg_wrong_max_square",
                                                                                  get_language(
                                                                                      await state.get_data())))
                else:
                    await state.update_data(square_max=int(message.text))  # Сохраняем введенное число в состояние
                    last_message = await main_bot.send_message(message.chat.id,
                                                               text=locales.get_localized_string("Kb_main_filter",
                                                                                                 get_language(
                                                                                                     await state.get_data())),
                                                               reply_markup=get_main_filter_keyboard(
                                                                   await state.get_data()))
                    await state.set_state(MenuStates.main_filter)  # Возвращаем пользователя в состояние фильтра
                    await delete_extra_messages(state, last_message)

        else:  # Если введено не число, просим ввести число еще раз
            await message.answer(
                locales.get_localized_string("Mg_incorrect_input", get_language(await state.get_data())))
        await state.update_data(lmt=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        # await get_state(state)


@router.message(MenuStates.select_option, lambda message: not message.text.isdigit())
async def input_wrong_data(message: Message, state: FSMContext):
    state_data = await state.get_data()
    if not state_data.get("selected_currency") and (
            state_data.get('previous_button') == "price_min" or state_data.get('previous_button') == "price_max"):
        await main_bot.send_message(chat_id=message.chat.id,
                                    text=locales.get_localized_string("Mg_currency_not_selected",
                                                                      get_language(
                                                                          await state.get_data())))

    else:
        await message.answer(
            locales.get_localized_string("Mg_incorrect_input", get_language(await state.get_data())))
        await state.update_data(lmt=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))


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
                logging.warning(f"Can't delete message with id {i} from menu handler")
                messages.remove(i)
    await state.update_data(messages=messages)
