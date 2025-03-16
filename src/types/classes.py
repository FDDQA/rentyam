import logging

from aiogram.fsm.state import StatesGroup, State
from aiogram import BaseMiddleware
from aiogram.types import Update

import csv


class LoggingMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: Update, data: dict):
        app_log = logging.getLogger('app')
        user_id = None
        username = None

        if event.message:
            user_id = event.message.from_user.id
            username = event.message.from_user.username
            message = event.message.text
            app_log.info(f"Message from {username} (ID: {user_id}): {message}")
        elif event.callback_query:
            user_id = event.callback_query.from_user.id
            username = event.callback_query.from_user.username
            callback_data = event.callback_query.data
            app_log.info(f"Callback from {username} (ID: {user_id}): {callback_data}")

        return await handler(event, data)


class MenuStates (StatesGroup):
    start_menu = State()  # находимся в стартовом меню
    select_type = State()  # юзер выбирает для чего создает фильтр - квартира или дом
    select_type_filter = State()  # юзер выбирает тип фильтра - краткий или полный
    main_filter = State()   # юзер выбирает параметр в меню (может быть короткое меню или полное)
    select_option = State()  # юзер настраивает параметр - валюту и т.п.
    checkbox_kb = State()  # юзер находится в клавиатуре с множественным выбором с помощью чекбоксов
    save_filter = State()  # юзер вводит данные, типа цены
    buy_premium = State()  # юзер выбирает покупку премиум
    stop_state = State()  # юзер находится в состоянии после отправки /stop


class AdminStates (StatesGroup):
    admin_dash = State()
    input_ad = State()
    input_start_datetime = State()
    input_end_datetime = State()
    input_max_count = State()
    delete_ad = State()
    send_notification = State()
    generate_link = State()
    refund = State()
    add_admin = State()


class Flat:
    def __init__(self, site, ad_id, url_card, district, price_amd, price_usd, price_rur, square, rooms, floor, floors,
                 animals, ac, owner, date):
        self.site = site
        self.owner = owner
        self.ad_id = ad_id
        self.url_card = url_card
        self.district = district
        self.price_amd = price_amd
        self.price_usd = price_usd
        self.price_rur = price_rur
        self.square = square
        self.rooms = rooms
        self.floor = floor
        self.floors = floors
        self.animals = animals
        self.ac = ac
        self.date = date
# 17 параметров квартиры


class House:
    def __init__(self, site, ad_id, url_card, district, price_amd, price_usd, price_rur, square, rooms, floors,
                 animals, ac, owner, date):
        self.site = site
        self.ad_id = ad_id
        self.url_card = url_card
        self.district = district
        self.price_amd = price_amd
        self.price_usd = price_usd
        self.price_rur = price_rur
        self.square = square
        self.rooms = rooms
        self.floors = floors
        self.animals = animals
        self.ac = ac
        self.owner = owner
        self.date = date


class LocalizationManager:
    def __init__(self):
        self.localizedStringByKey = {}
        self.LanguageCodes = []

    def load_from_csv(self, filename):
        self.localizedStringByKey = {}
        self.LanguageCodes = []

        with open(filename, newline='', encoding='utf-8') as file:
            reader = csv.reader(file)
            record = next(reader, None)
            if record is None:
                return

            self.LanguageCodes.extend(record[1:])

            for record in reader:
                key = record[0]
                self.localizedStringByKey[key] = {}

                for i, translation in enumerate(record[1:]):
                    self.localizedStringByKey[key][self.LanguageCodes[i]] = translation

    def get_localized_string(self, key, language):
        if key in self.localizedStringByKey:
            langmap = self.localizedStringByKey[key]
            if language in langmap:
                return langmap[language]
            return self.get_localized_string(key, "en")

        return "---"

    def match_localized_districts(self, state_data, districts_from_sql=None):
        districts = state_data.get("selected_districts")
        previous_button = state_data.get("previous_button")
        if previous_button == 'delete_filter':
            if districts_from_sql:
                match_dict = {
                    'Ачапняк': self.get_localized_string("Txt_achapnyak", state_data.get("lang")),
                    'Арабкир': self.get_localized_string("Txt_arabkir", state_data.get("lang")),
                    'Аван': self.get_localized_string("Txt_avan", state_data.get("lang")),
                    'Давташен': self.get_localized_string("Txt_davtashen", state_data.get("lang")),
                    'Эребуни': self.get_localized_string("Txt_erebuni", state_data.get("lang")),
                    'Зейтун Канакер': self.get_localized_string("Txt_zeitun", state_data.get("lang")),
                    'Кентрон': self.get_localized_string("Txt_kentron", state_data.get("lang")),
                    'Малатия Себастия': self.get_localized_string("Txt_malatiya", state_data.get("lang")),
                    'Нор Норк': self.get_localized_string("Txt_nor", state_data.get("lang")),
                    'Шенгавит': self.get_localized_string("Txt_shengavit", state_data.get("lang")),
                    'Норк Мараш': self.get_localized_string("Txt_nork", state_data.get("lang")),
                    'Нубарашен': self.get_localized_string("Txt_nubarashen", state_data.get("lang"))
                }
                matched_districts = []
                for district in districts_from_sql:
                    matched_districts.append(match_dict.get(district))
                return matched_districts
        elif previous_button == 'yes_sure':  # при сохранении фильтра в базу сохраняем названия районов на русском
            match_dict = {
                'achapnyak': 'Ачапняк',
                'arabkir': 'Арабкир',
                'avan': 'Аван',
                'davtashen': 'Давташен',
                'erebuni': 'Эребуни',
                'zeitun': 'Зейтун Канакер',
                'kentron': 'Кентрон',
                'malatiya': 'Малатия Себастия',
                'nor': 'Нор Норк',
                'shengavit': 'Шенгавит',
                'nork': 'Норк Мараш',
                'nubarashen': 'Нубарашен'
            }

            matched_districts = []
            for district in districts:
                matched_districts.append(match_dict.get(district))
            return matched_districts

        else:
            if districts:
                match_dict = {
                    'achapnyak': self.get_localized_string("Txt_achapnyak", state_data.get("lang")),
                    'arabkir': self.get_localized_string("Txt_arabkir", state_data.get("lang")),
                    'avan': self.get_localized_string("Txt_avan", state_data.get("lang")),
                    'davtashen': self.get_localized_string("Txt_davtashen", state_data.get("lang")),
                    'erebuni': self.get_localized_string("Txt_erebuni", state_data.get("lang")),
                    'zeitun': self.get_localized_string("Txt_zeitun", state_data.get("lang")),
                    'kentron': self.get_localized_string("Txt_kentron", state_data.get("lang")),
                    'malatiya': self.get_localized_string("Txt_malatiya", state_data.get("lang")),
                    'nor': self.get_localized_string("Txt_nor", state_data.get("lang")),
                    'shengavit': self.get_localized_string("Txt_shengavit", state_data.get("lang")),
                    'nork': self.get_localized_string("Txt_nork", state_data.get("lang")),
                    'nubarashen': self.get_localized_string("Txt_nubarashen", state_data.get("lang"))
                }
                matched_districts = []
                for district in districts:
                    matched_districts.append(match_dict.get(district))
                return matched_districts
        return None
