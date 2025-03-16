from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.types.web_app_info import WebAppInfo


# главное меню
from src.config import config
from src.types.classes import LocalizationManager
from src.utils.other import get_language, get_premium

tutor_locales = LocalizationManager()
tutor_locales.load_from_csv(config.tutor_localization_path)

locales = LocalizationManager()
locales.load_from_csv(config.localization_path)


def get_start_menu_keyboard(state_data):
    button_create_filter = InlineKeyboardButton(text=locales.get_localized_string("Btn_create_filter", get_language(state_data)), callback_data="create_filter")
    button_edit_filter = InlineKeyboardButton(text=locales.get_localized_string("Btn_my_filters", get_language(state_data)), callback_data="delete_filter")
    button_reviews = InlineKeyboardButton(web_app=WebAppInfo(url=config.reviews_url), text=f'🆕 {locales.get_localized_string("Btn_reviews", get_language(state_data))} (BETA)')
    button_lang_en = InlineKeyboardButton(text='🇬🇧', callback_data='en')
    button_lang_ru = InlineKeyboardButton(text='🇷🇺', callback_data='ru')
    button_lang_hy = InlineKeyboardButton(text='🇦🇲', callback_data='hy')
    button_lang_hi = InlineKeyboardButton(text='🇮🇳', callback_data='hi')
    button_premium = InlineKeyboardButton(text=locales.get_localized_string("Btn_premium", get_language(state_data)), callback_data='premium')
    button_support = InlineKeyboardButton(text=f'{locales.get_localized_string("Btn_support", get_language(state_data))} 👨🏿‍💻', url=config.support_url)

    # если юзер проходит тутор, то убираем кнопку премиума и проходим тутор
    if state_data.get("tutor") == 1:
        button_tutor = InlineKeyboardButton(text=tutor_locales.get_localized_string("Tutor_btn_tutor", get_language(state_data)), callback_data='tutor_off')
        button_create_filter = InlineKeyboardButton(text=f'👉 {locales.get_localized_string("Btn_create_filter", get_language(state_data))} 👈 ', callback_data="create_filter")
        buttons = [[button_create_filter, button_edit_filter],
                   [button_tutor],
                   [button_reviews],
                   [button_lang_en, button_lang_ru, button_lang_hy, button_lang_hi],
                   [button_support]
                   ]
    else:
        buttons = [[button_create_filter, button_edit_filter],
                   [button_premium],

                   [button_lang_en, button_lang_ru, button_lang_hy, button_lang_hi],
                   [button_support],
                   ]
    start_menu_kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    return start_menu_kb


# кнопка "Начать!" после того, как юзер прекратил работу с ботом после вызова /stop
def get_stop_menu_keyboard(state_data):
    buttons = [[InlineKeyboardButton(text=locales.get_localized_string("Btn_continue", get_language(state_data)), callback_data="get")
                ]]
    comeback_kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    return comeback_kb


# выбираем для чего создаем фильтр
def get_select_type_keyboard(state_data):
    button_flat = InlineKeyboardButton(text=locales.get_localized_string("Btn_flat", get_language(state_data)), callback_data='selected_flat')
    if state_data.get("tutor") == 1:
        button_flat = InlineKeyboardButton(text=f'👉{locales.get_localized_string("Btn_flat", get_language(state_data))}👈 ',
                                           callback_data='selected_flat')

    button_house = InlineKeyboardButton(text=locales.get_localized_string("Btn_house", get_language(state_data)), callback_data='selected_house')
    button_back_to_main_start = InlineKeyboardButton(text=f'⬅ {locales.get_localized_string("Btn_back", get_language(state_data))}', callback_data='back_to_main_menu')

    buttons = [[button_flat, button_house],
               [button_back_to_main_start]
               ]
    select_type_kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    return select_type_kb


# выбираем тип фильтра для квартиры
def get_select_type_filter_keyboard(state_data):
    button_short = InlineKeyboardButton(text=locales.get_localized_string("Btn_short", get_language(state_data)), callback_data='type_short')
    button_full = InlineKeyboardButton(text=locales.get_localized_string("Btn_full", get_language(state_data)), callback_data='type_full')
    button_back_to_select_type = InlineKeyboardButton(text=f'⬅ {locales.get_localized_string("Btn_back", get_language(state_data))}', callback_data='back_to_select_type')

    buttons = [[button_short, button_full],
               [button_back_to_select_type]
               ]
    select_filter_type_kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    return select_filter_type_kb


'''здесь мы собираем клавиатуры для разного типа фильтров. Всего 4 клавиатуры: дом-короткий, квартира-короткий,
дом-полный и квартира-полный
'''


# клавиатура для коротких фильтров, и квартира и дом
def get_short_filter_keyboard(state_data):
    button_price_min = InlineKeyboardButton(text=locales.get_localized_string("Btn_price_min", get_language(state_data)), callback_data='price_min')
    button_price_max = InlineKeyboardButton(text=locales.get_localized_string("Btn_price_max", get_language(state_data)), callback_data='price_max')
    if state_data.get("selected_districts"):
        button_districts = InlineKeyboardButton(text=f'✅ {locales.get_localized_string("Btn_districts", get_language(state_data))}: {", ".join(locales.match_localized_districts(state_data))}',
                                                callback_data='districts')
    else:
        button_districts = InlineKeyboardButton(text=locales.get_localized_string("Btn_districts", get_language(state_data)), callback_data='districts')

    if state_data.get("selected_rooms"):
        rooms = state_data.get("selected_rooms")
        button_rooms = InlineKeyboardButton(text=f'✅ {locales.get_localized_string("Btn_rooms", get_language(state_data))}: {", ".join(rooms)}', callback_data='rooms')
    else:
        button_rooms = InlineKeyboardButton(text=locales.get_localized_string("Btn_rooms", get_language(state_data)), callback_data='rooms')

    button_save = InlineKeyboardButton(text=f'{locales.get_localized_string("Btn_save", get_language(state_data))} 💾', callback_data='save_filter')
    button_back_to_select_type_filter = InlineKeyboardButton(text=f'⬅ {locales.get_localized_string("Btn_back", get_language(state_data))}', callback_data='back_to_select_type_filter')
    if state_data:
        symbol = state_data.get("symbol")
        if symbol is not None:

            price_min = state_data.get("price_min")
            if price_min is not None:
                button_price_min = InlineKeyboardButton(text=f'✅ {locales.get_localized_string("Btn_price_min", get_language(state_data))} {price_min} {symbol}',
                                                        callback_data='price_min')

            price_max = state_data.get("price_max")
            if price_max is not None:
                button_price_max = InlineKeyboardButton(text=f'✅ {locales.get_localized_string("Btn_price_max", get_language(state_data))} {price_max} {symbol}',
                                                        callback_data='price_max')

    if state_data.get("selected_filter_type") == "flat_short" or state_data.get("selected_filter_type") == "house_short":
        if state_data.get("price_min") is None and state_data.get("price_max") is None:
            if (state_data.get("selected_districts") is None or len(state_data.get("selected_districts")) == 0) and (state_data.get("selected_rooms") is None or len(state_data.get("selected_rooms")) == 0):
                button_save = InlineKeyboardButton(text=locales.get_localized_string("Btn_cant_save", get_language(state_data)), callback_data='cant_save_filter')

    buttons = [[button_price_min, button_price_max],
               [button_districts],
               [button_rooms],
               [button_save],
               [button_back_to_select_type_filter]
               ]
    short_filter_kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    return short_filter_kb


def get_full_filter_flat_keyboard(state_data):
    button_price_min = InlineKeyboardButton(text=locales.get_localized_string("Btn_price_min", get_language(state_data)), callback_data='price_min')
    button_price_max = InlineKeyboardButton(text=locales.get_localized_string("Btn_price_max", get_language(state_data)), callback_data='price_max')
    button_floor_min = InlineKeyboardButton(text=locales.get_localized_string("Btn_floor_min", get_language(state_data)), callback_data='floor_min')
    button_floor_max = InlineKeyboardButton(text=locales.get_localized_string("Btn_floor_max", get_language(state_data)), callback_data='floor_max')
    button_square_min = InlineKeyboardButton(text=locales.get_localized_string("Btn_square_min", get_language(state_data)), callback_data='square_min')
    button_square_max = InlineKeyboardButton(text=locales.get_localized_string("Btn_square_max", get_language(state_data)), callback_data='square_max')
    button_ac = InlineKeyboardButton(text=locales.get_localized_string("Btn_ac", get_language(state_data)), callback_data='ac')
    button_owner = InlineKeyboardButton(text=locales.get_localized_string("Btn_owner", get_language(state_data)), callback_data='owner')
    button_save = InlineKeyboardButton(text=f'{locales.get_localized_string("Btn_save", get_language(state_data))} 💾', callback_data='save_filter')
    button_back_to_select_type_filter = InlineKeyboardButton(text=f'⬅ {locales.get_localized_string("Btn_back", get_language(state_data))}', callback_data='back_to_select_type_filter')

    if state_data.get("selected_districts"):
        button_districts = InlineKeyboardButton(text=f'✅ {locales.get_localized_string("Btn_districts", get_language(state_data))}: {", ".join(locales.match_localized_districts(state_data))}',
                                                callback_data='districts')
    else:
        button_districts = InlineKeyboardButton(text=locales.get_localized_string("Btn_districts", get_language(state_data)), callback_data='districts')

    if state_data.get("selected_rooms"):
        rooms = state_data.get("selected_rooms")
        button_rooms = InlineKeyboardButton(text=f'✅ {locales.get_localized_string("Btn_rooms", get_language(state_data))}: {", ".join(rooms)}', callback_data='rooms')
    else:
        button_rooms = InlineKeyboardButton(text=locales.get_localized_string("Btn_rooms", get_language(state_data)), callback_data='rooms')

    if state_data:
        symbol = state_data.get("symbol")
        if symbol is not None:

            price_min = state_data.get("price_min")
            if price_min is not None:
                button_price_min = InlineKeyboardButton(text=f'✅ {locales.get_localized_string("Btn_price_min", get_language(state_data))} {price_min} {symbol}', callback_data='price_min')

            price_max = state_data.get("price_max")
            if price_max is not None:
                button_price_max = InlineKeyboardButton(text=f'✅ {locales.get_localized_string("Btn_price_max", get_language(state_data))} {price_max} {symbol}', callback_data='price_max')

    if state_data.get("floor_min"):
        button_floor_min = InlineKeyboardButton(text=f'✅ {locales.get_localized_string("Btn_floor_min", get_language(state_data))} {state_data.get("floor_min")}', callback_data='floor_min')
    if state_data.get("floor_max"):
        button_floor_max = InlineKeyboardButton(text=f'✅ {locales.get_localized_string("Btn_floor_max", get_language(state_data))} {state_data.get("floor_max")}', callback_data='floor_max')

    if state_data.get("square_min"):
        button_square_min = InlineKeyboardButton(text=f'✅ {locales.get_localized_string("Btn_square_min", get_language(state_data))} {state_data.get("square_min")} {locales.get_localized_string("Btn_m", get_language(state_data))}', callback_data='square_min')
    if state_data.get("square_max"):
        button_square_max = InlineKeyboardButton(text=f'✅ {locales.get_localized_string("Btn_square_max", get_language(state_data))} {state_data.get("square_max")} {locales.get_localized_string("Btn_m", get_language(state_data))}', callback_data='square_max')

    # животные
    animals = state_data.get("selected_animals")
    if animals is None or not any(animals.values()):
        button_animals = InlineKeyboardButton(text=locales.get_localized_string("Btn_animals", get_language(state_data)), callback_data='animals')
    else:
        res = []
        if animals.get("yes_animals"):
            res.append(locales.get_localized_string("Txt_yes", get_language(state_data)))
        if animals.get("by_agreement"):
            res.append(locales.get_localized_string("Txt_by_agreement", get_language(state_data)))
        if animals.get("no_animals"):
            res.append(locales.get_localized_string("Txt_no", get_language(state_data)))
        button_animals = InlineKeyboardButton(text=f'✅ {locales.get_localized_string("Btn_animals", get_language(state_data))}: {", ".join(res)}', callback_data='animals')

    if state_data.get("selected_ac"):
        if state_data.get("selected_ac") == "yes":
            button_ac = InlineKeyboardButton(text=f'✅ {locales.get_localized_string("Btn_ac", get_language(state_data))}: {locales.get_localized_string("Txt_yes", get_language(state_data))}', callback_data='ac')
        if state_data.get("selected_ac") == "no":
            button_ac = InlineKeyboardButton(text=f'✅ {locales.get_localized_string("Btn_ac", get_language(state_data))}: {locales.get_localized_string("Txt_no", get_language(state_data))}', callback_data='ac')

    if state_data.get("selected_owner"):
        if state_data.get("selected_owner") == "yes":
            button_owner = InlineKeyboardButton(text=f'✅ {locales.get_localized_string("Btn_owner", get_language(state_data))}: {locales.get_localized_string("Txt_yes", get_language(state_data))}', callback_data='owner')
        if state_data.get("selected_owner") == "no":
            button_owner = InlineKeyboardButton(text=f'✅ {locales.get_localized_string("Btn_owner", get_language(state_data))}: {locales.get_localized_string("Txt_no", get_language(state_data))}', callback_data='owner')

    if state_data.get("selected_filter_type") == "flat_full":
        if state_data.get("price_min") is None and state_data.get("price_max") is None:
            if (state_data.get("selected_districts") is None or len(state_data.get("selected_districts")) == 0) and (state_data.get("selected_rooms") is None or len(state_data.get("selected_rooms")) == 0):
                if state_data.get("floor_min") is None and state_data.get("floor_max") is None:
                    if state_data.get("square_min") is None and state_data.get("square_max") is None:
                        if state_data.get("selected_animals") is None and state_data.get("selected_owner") is None and state_data.get("selected_ac") is None:
                            button_save = InlineKeyboardButton(text=locales.get_localized_string("Btn_cant_save", get_language(state_data)), callback_data='cant_save_filter')

    buttons = [[button_price_min, button_price_max],
               [button_districts, button_rooms],
               [button_floor_min, button_floor_max],
               [button_square_min, button_square_max],
               [button_animals],
               [button_ac, button_owner],
               [button_save],
               [button_back_to_select_type_filter]
               ]
    full_filter_flat_kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    return full_filter_flat_kb


def get_full_filter_house_keyboard(state_data=None):
    button_price_min = InlineKeyboardButton(text=locales.get_localized_string("Btn_price_min", get_language(state_data)), callback_data='price_min')
    button_price_max = InlineKeyboardButton(text=locales.get_localized_string("Btn_price_max", get_language(state_data)), callback_data='price_max')
    button_square_min = InlineKeyboardButton(text=locales.get_localized_string("Btn_square_min", get_language(state_data)), callback_data='square_min')
    button_square_max = InlineKeyboardButton(text=locales.get_localized_string("Btn_square_max", get_language(state_data)), callback_data='square_max')
    button_ac = InlineKeyboardButton(text=locales.get_localized_string("Btn_ac", get_language(state_data)), callback_data='ac')
    button_owner = InlineKeyboardButton(text=locales.get_localized_string("Btn_owner", get_language(state_data)), callback_data='owner')
    button_save = InlineKeyboardButton(text=f'{locales.get_localized_string("Btn_save", get_language(state_data))} 💾', callback_data='save_filter')
    button_back_to_select_type_filter = InlineKeyboardButton(text=f'⬅ {locales.get_localized_string("Btn_back", get_language(state_data))}',
                                                             callback_data='back_to_select_type_filter')

    if state_data.get("selected_districts"):
        button_districts = InlineKeyboardButton(
            text=f'✅ {locales.get_localized_string("Btn_districts", get_language(state_data))}: {", ".join(locales.match_localized_districts(state_data))}',
            callback_data='districts')
    else:
        button_districts = InlineKeyboardButton(
            text=locales.get_localized_string("Btn_districts", get_language(state_data)), callback_data='districts')

    if state_data.get("selected_rooms"):
        rooms = state_data.get("selected_rooms")
        button_rooms = InlineKeyboardButton(
            text=f'✅ {locales.get_localized_string("Btn_rooms", get_language(state_data))}: {", ".join(rooms)}',
            callback_data='rooms')
    else:
        button_rooms = InlineKeyboardButton(text=locales.get_localized_string("Btn_rooms", get_language(state_data)),
                                            callback_data='rooms')

    if state_data:
        symbol = state_data.get("symbol")
        if symbol is not None:

            price_min = state_data.get("price_min")
            if price_min is not None:
                button_price_min = InlineKeyboardButton(
                    text=f'✅ {locales.get_localized_string("Btn_price_min", get_language(state_data))} {price_min} {symbol}',
                    callback_data='price_min')

            price_max = state_data.get("price_max")
            if price_max is not None:
                button_price_max = InlineKeyboardButton(
                    text=f'✅ {locales.get_localized_string("Btn_price_max", get_language(state_data))} {price_max} {symbol}',
                    callback_data='price_max')

    if state_data.get("selected_floors"):
        floors = state_data.get("selected_floors")
        button_floors = InlineKeyboardButton(text=f'✅ {locales.get_localized_string("Btn_floors", get_language(state_data))}: {", ".join(floors)}', callback_data='floors')
    else:
        button_floors = InlineKeyboardButton(text=locales.get_localized_string("Btn_floors", get_language(state_data)), callback_data='floors')

    if state_data.get("square_min"):
        button_square_min = InlineKeyboardButton(
            text=f'✅ {locales.get_localized_string("Btn_square_min", get_language(state_data))} {state_data.get("square_min")} {locales.get_localized_string("Btn_m", get_language(state_data))}',
            callback_data='square_min')
    if state_data.get("square_max"):
        button_square_max = InlineKeyboardButton(
            text=f'✅ {locales.get_localized_string("Btn_square_max", get_language(state_data))} {state_data.get("square_max")} {locales.get_localized_string("Btn_m", get_language(state_data))}',
            callback_data='square_max')

    # животные
    animals = state_data.get("selected_animals")
    if animals is None or not any(animals.values()):
        button_animals = InlineKeyboardButton(text=locales.get_localized_string("Btn_animals", get_language(state_data)), callback_data='animals')
    else:
        res = []
        if animals.get("yes_animals"):
            res.append(locales.get_localized_string("Txt_yes", get_language(state_data)))
        if animals.get("by_agreement"):
            res.append(locales.get_localized_string("Txt_by_agreement", get_language(state_data)))
        if animals.get("no_animals"):
            res.append(locales.get_localized_string("Txt_no", get_language(state_data)))
        button_animals = InlineKeyboardButton(text=f'✅ {locales.get_localized_string("Btn_animals", get_language(state_data))}: {", ".join(res)}', callback_data='animals')

    if state_data.get("selected_ac"):
        if state_data.get("selected_ac") == "yes":
            button_ac = InlineKeyboardButton(text=f'✅ {locales.get_localized_string("Btn_ac", get_language(state_data))}: {locales.get_localized_string("Txt_yes", get_language(state_data))}', callback_data='ac')
        if state_data.get("selected_ac") == "no":
            button_ac = InlineKeyboardButton(text=f'✅ {locales.get_localized_string("Btn_ac", get_language(state_data))}: {locales.get_localized_string("Txt_no", get_language(state_data))}', callback_data='ac')

    if state_data.get("selected_owner"):
        if state_data.get("selected_owner") == "yes":
            button_owner = InlineKeyboardButton(text=f'✅ {locales.get_localized_string("Btn_owner", get_language(state_data))}: {locales.get_localized_string("Txt_yes", get_language(state_data))}', callback_data='owner')
        if state_data.get("selected_owner") == "no":
            button_owner = InlineKeyboardButton(text=f'✅ {locales.get_localized_string("Btn_owner", get_language(state_data))}: {locales.get_localized_string("Txt_no", get_language(state_data))}', callback_data='owner')

    if state_data.get("selected_filter_type") == "house_full":
        if state_data.get("price_min") is None and state_data.get("price_max") is None:
            if (state_data.get("selected_districts") is None or len(state_data.get("selected_districts")) == 0) and (state_data.get("selected_rooms") is None or len(state_data.get("selected_rooms")) == 0):
                if state_data.get("floors") is None:
                    if state_data.get("square_min") is None and state_data.get("square_max") is None:
                        if state_data.get("selected_animals") is None and state_data.get("selected_owner") is None and state_data.get("selected_ac") is None:
                            button_save = InlineKeyboardButton(text=locales.get_localized_string("Btn_cant_save", get_language(state_data)),
                                                               callback_data='cant_save_filter')

    buttons = [[button_price_min, button_price_max],
               [button_districts, button_rooms],
               [button_square_min, button_square_max],
               [button_animals, button_floors],
               [button_ac, button_owner],
               [button_save],
               [button_back_to_select_type_filter]
               ]
    full_filter_house_kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    return full_filter_house_kb


# функция для вызова клавиатуры из главного фильтра
def get_main_filter_keyboard(state_data):
    selected_type_filter = state_data.get("selected_filter_type")
    if selected_type_filter == "flat_short" or selected_type_filter == "house_short":
        return get_short_filter_keyboard(state_data)
    elif selected_type_filter == "flat_full":
        return get_full_filter_flat_keyboard(state_data)
    elif selected_type_filter == "house_full":
        return get_full_filter_house_keyboard(state_data)


# выбор валюты
def get_select_currency_keyboard(state_data):
    button_amd = InlineKeyboardButton(text='֏', callback_data='amd')
    button_usd = InlineKeyboardButton(text='$', callback_data='usd')
    button_rur = InlineKeyboardButton(text='₽', callback_data='rur')
    button_select_currency_back = InlineKeyboardButton(text=f'⬅ {locales.get_localized_string("Btn_back", get_language(state_data))}', callback_data='back_to_main_filter')

    buttons = [[button_amd, button_usd, button_rur],
               [button_select_currency_back]
               ]
    select_currency_kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    return select_currency_kb


# да нет клавиатура
def get_yes_no_keyboard(state_data):
    button_yes = InlineKeyboardButton(text=locales.get_localized_string("Txt_yes", get_language(state_data)), callback_data='yes')
    button_no = InlineKeyboardButton(text=locales.get_localized_string("Txt_no", get_language(state_data)), callback_data='no')
    buttons = [[button_yes, button_no]]
    yes_no_kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    return yes_no_kb


def get_yes_no_checkbox_keyboard(state_data):
    button_yes = InlineKeyboardButton(text=locales.get_localized_string("Txt_yes", get_language(state_data)), callback_data='yes')
    button_no = InlineKeyboardButton(text=locales.get_localized_string("Txt_no", get_language(state_data)), callback_data='no')
    button_save = InlineKeyboardButton(text=f'{locales.get_localized_string("Btn_save", get_language(state_data))} 💾', callback_data='save')
    previous_button = state_data.get("previous_button")
    if previous_button == "ac" or previous_button == "owner":
        if state_data.get(f'selected_{previous_button}'):
            match state_data.get(f'selected_{previous_button}'):
                case "yes":
                    button_yes = InlineKeyboardButton(text=f'{locales.get_localized_string("Txt_yes", get_language(state_data))} ✅', callback_data='yes')
                case "no":
                    button_no = InlineKeyboardButton(text=f'{locales.get_localized_string("Txt_no", get_language(state_data))} ✅', callback_data='no')
    buttons = [[button_yes, button_no],
               [button_save]]
    yes_no_kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    return yes_no_kb


# клавиатура с районами
def get_districts_keyboard(state_data):
    selected_districts = state_data.get("selected_districts")
    district_buttons = [
        [locales.get_localized_string("Txt_achapnyak", state_data.get("lang")), 'achapnyak'],
        [locales.get_localized_string("Txt_arabkir", state_data.get("lang")), 'arabkir'],
        [locales.get_localized_string("Txt_avan", state_data.get("lang")), 'avan'],
        [locales.get_localized_string("Txt_davtashen", state_data.get("lang")), 'davtashen'],
        [locales.get_localized_string("Txt_erebuni", state_data.get("lang")), 'erebuni'],
        [locales.get_localized_string("Txt_zeitun", state_data.get("lang")), 'zeitun'],
        [locales.get_localized_string("Txt_kentron", state_data.get("lang")), 'kentron'],
        [locales.get_localized_string("Txt_malatiya", state_data.get("lang")), 'malatiya'],
        [locales.get_localized_string("Txt_nor", state_data.get("lang")), 'nor'],
        [locales.get_localized_string("Txt_shengavit", state_data.get("lang")), 'shengavit'],
        [locales.get_localized_string("Txt_nork", state_data.get("lang")), 'nork'],
        [locales.get_localized_string("Txt_nubarashen", state_data.get("lang")), 'nubarashen']
    ]
    button_district_save = InlineKeyboardButton(text=f'{locales.get_localized_string("Btn_save", get_language(state_data))} 💾', callback_data='save_districts')

    buttons = []
    for i in range(0, len(district_buttons), 2):
        row = []
        for button_data in district_buttons[i:i+2]:
            if selected_districts is not None:
                if button_data[1] in selected_districts:
                    button_data[0] ="✅"+ button_data[0]
            button = InlineKeyboardButton(text=button_data[0], callback_data=button_data[1])
            row.append(button)
        buttons.append(row)
    buttons.append([button_district_save])
    districts_kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    return districts_kb


# выбор квартир
def get_rooms_keyboard(state_data):
    selected_rooms = state_data.get("selected_rooms")
    rooms_buttons = [
        ['1', '1'],
        ['2', '2'],
        ['3', '3'],
        ['4', '4'],
        ['5', '5'],
        ['6', '6'],
        ['7', '7'],
        ['8+', '8+']
        ]
    button_rooms_save = InlineKeyboardButton(text=f'{locales.get_localized_string("Btn_save", get_language(state_data))} 💾', callback_data='save_rooms')

    buttons = []
    for button_data in rooms_buttons:
        if selected_rooms is not None:
            if button_data[1] in selected_rooms:
                button_data[0] = button_data[0] + "✅"
        button = InlineKeyboardButton(text=button_data[0], callback_data=button_data[1])
        buttons.append([button])
    buttons.append([button_rooms_save])
    rooms_kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    return rooms_kb


def get_save_keyboard(state_data):
    button_yes = InlineKeyboardButton(text=locales.get_localized_string("Txt_yes", get_language(state_data)), callback_data="yes_sure")
    button_no = InlineKeyboardButton(text=locales.get_localized_string("Txt_no", get_language(state_data)), callback_data="no_sure")
    button_dontknow = InlineKeyboardButton(text=locales.get_localized_string("Btn_dontknow", get_language(state_data)), callback_data="dontknow")
    buttons = [[button_yes, button_no],
               [button_dontknow]]
    get_save_kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    return get_save_kb


def get_floor_keyboard(state_data):
    floors_buttons = [[str(i), str(i)] for i in range(1, 33)]
    button_floor_save = InlineKeyboardButton(text=f'{locales.get_localized_string("Btn_save", get_language(state_data))} 💾', callback_data='save_floor')

    buttons = []
    selected_floor = state_data.get(state_data.get("previous_button"))
    for i in range(0, len(floors_buttons), 4):
        row = []
        for button_data in floors_buttons[i:i+4]:
            # Проверяем, выбран ли этаж, чтобы добавить галочку
            if selected_floor is not None and button_data[1] == selected_floor:
                button_data[0] = button_data[0] + " ✅"
            # Создаем кнопку для этажа
            button = InlineKeyboardButton(text=button_data[0], callback_data=button_data[1])
            row.append(button)
        buttons.append(row)
    buttons.append([button_floor_save])
    floors_kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    return floors_kb


def get_animals_keyboard(state_data):
    selected_animals = state_data.get("selected_animals")
    button_yes = InlineKeyboardButton(text=f'{locales.get_localized_string("Txt_yes", get_language(state_data))}', callback_data="yes_animals")
    button_no = InlineKeyboardButton(text=f'{locales.get_localized_string("Txt_no", get_language(state_data))}', callback_data="no_animals")
    button_by_agreement = InlineKeyboardButton(text=locales.get_localized_string("Txt_by_agreement", get_language(state_data)), callback_data="by_agreement")
    if selected_animals:
        if "no_animals" in selected_animals and selected_animals["no_animals"]:
            button_no = InlineKeyboardButton(text=f'{locales.get_localized_string("Txt_no", get_language(state_data))} ✅', callback_data="no_animals")

        if "yes_animals" in selected_animals and selected_animals["yes_animals"]:
            button_yes = InlineKeyboardButton(text=f'{locales.get_localized_string("Txt_yes", get_language(state_data))} ✅', callback_data="yes_animals")

        if "by_agreement" in selected_animals and selected_animals["by_agreement"]:
            button_by_agreement = InlineKeyboardButton(text=f'{locales.get_localized_string("Txt_by_agreement", get_language(state_data))} ✅', callback_data="by_agreement")

    button_save = InlineKeyboardButton(text=f'{locales.get_localized_string("Btn_save", get_language(state_data))} 💾', callback_data='save_animals')

    buttons = [[button_yes, button_no],
               [button_by_agreement],
               [button_save]]
    get_animals_kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    return get_animals_kb


def get_floors_keyboard(state_data):
    selected_floors = state_data.get("selected_floors")
    floors_buttons = [
        ['1', '1'],
        ['2', '2'],
        ['3', '3'],
        ['4+', '4+']
        ]
    button_floors_save = InlineKeyboardButton(text=f'{locales.get_localized_string("Btn_save", get_language(state_data))} 💾', callback_data='save_floors')
    buttons = []
    for i in range(0, len(floors_buttons), 4):
        row_buttons = []
        for button_data in floors_buttons[i:i + 4]:
            if selected_floors is not None:
                if button_data[1] in selected_floors:
                    button_data[0] = button_data[0] + "✅"
            button = InlineKeyboardButton(text=button_data[0], callback_data=button_data[1])
            row_buttons.append(button)
        buttons.append(row_buttons)
    buttons.append([button_floors_save])
    floors_kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    return floors_kb


def get_select_type_subscribe(state_data, confirmation_tgstars_url_weekly, confirmation_tgstars_url_monthly):
    button_weekly_subcribe_tgstars = InlineKeyboardButton(text=f'{locales.get_localized_string("Btn_weekly_premium_tgstars", get_language(state_data))}', url=confirmation_tgstars_url_weekly)
    button_monthly_subscribe_tgstars = InlineKeyboardButton(text=f'{locales.get_localized_string("Btn_monthly_premium_tgstars", get_language(state_data))}', url=confirmation_tgstars_url_monthly)
    buttons = [[button_weekly_subcribe_tgstars, button_monthly_subscribe_tgstars]]
    payment_kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    return payment_kb
