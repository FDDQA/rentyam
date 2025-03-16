import asyncio
from datetime import datetime
import logging

import psutil
from aiogram.exceptions import TelegramForbiddenError  # эксепшен, когда попробовали отправить тому юзеру, который заблокировал бота
from aiogram.fsm.context import FSMContext

from src.config import config
from src.config.config import ad_counter
from src.types.classes import LocalizationManager
from src.db.redis_methods import redis_get_lmt_from_users, redis_get_lang_from_users, redis_delete_user
from src.db.sql import db_change_language, db_get_created_filters, db_delete_filter, db_delete_filters, \
    db_get_filters_id, \
    db_insert_user, db_mute_user, db_unmute_user, db_get_user_ids_matching_flats, db_get_user_ids_matching_houses, \
    db_add_filter, db_get_premium, db_increment_sent_ads, db_check_mute, db_give_premium, db_take_premium, \
    db_delete_user, db_get_actual_ads, increment_sent_ad, \
    db_get_filter_currency, db_get_median_price_by_currency_flat, db_get_user_lang, \
    db_get_median_price_by_currency_house, \
    db_check_ad_in_db, db_get_last_created_filter, db_get_number_suitable_flats, db_get_number_suitable_houses

locales = LocalizationManager()
locales.load_from_csv(config.localization_path)

log = logging.getLogger('other')


# проверка времени последнего сообщения. Если давно ничего не нажимал
async def get_last_message_time_from_users(main_bot):
    await redis_get_lmt_from_users(main_bot)


async def check_ad_in_db(ad_id, table):
    return db_check_ad_in_db(ad_id, table)


async def change_language(language, user_id):
    db_change_language(language, user_id)


async def get_memory_info():
    process = psutil.Process()
    await asyncio.sleep(5)
    while True:
        log.info(f"RAM used: {process.memory_info().rss / 1024 / 1024} MB ")
        await asyncio.sleep(120)


def get_premium(user_id):
    return db_get_premium(user_id)


def get_language(state_data):
    return state_data.get("lang")


def get_language_from_db(user_id):
    return db_get_user_lang(user_id)


async def get_created_filters(user_id, state_data):
    filters = db_get_created_filters(user_id)
    if len(filters) < 1:
        return False
    message = f"{locales.get_localized_string('Txt_yours_filters', state_data.get('lang'))}\n"
    for i, filt in enumerate(filters, start=1):
        if filt["type"] == "flat":
            type_object = locales.get_localized_string("Txt_type_object_flat", state_data.get('lang'))
        else:
            type_object = locales.get_localized_string("Txt_type_object_house", state_data.get('lang'))
        message += f"{i}. {locales.get_localized_string('Txt_object', state_data.get('lang'))} {type_object}\n"
        if filt["filter_id"]:
            message += f"{locales.get_localized_string('Txt_id_filter', state_data.get('lang'))} {filt['filter_id']}\n"
        if filt["districts"]:
            message += f"{locales.get_localized_string('Txt_districts', state_data.get('lang'))}: {', '.join(locales.match_localized_districts(state_data, filt['districts'].split(', ')))}\n"
        if filt["price_amd_min"]:
            message += f"{locales.get_localized_string('Txt_price_amd_min', state_data.get('lang'))} {filt['price_amd_min']}\n"
        if filt["price_amd_max"]:
            message += f"{locales.get_localized_string('Txt_price_amd_max', state_data.get('lang'))} {filt['price_amd_max']}\n"
        if filt["price_usd_min"]:
            message += f"{locales.get_localized_string('Txt_price_usd_min', state_data.get('lang'))} {filt['price_usd_min']}\n"
        if filt["price_usd_max"]:
            message += f"{locales.get_localized_string('Txt_price_usd_max', state_data.get('lang'))} {filt['price_usd_max']}\n"
        if filt["price_rur_min"]:
            message += f"{locales.get_localized_string('Txt_price_rur_min', state_data.get('lang'))} {filt['price_rur_min']}\n"
        if filt["price_rur_max"]:
            message += f"{locales.get_localized_string('Txt_price_rur_max', state_data.get('lang'))} {filt['price_rur_max']}\n"
        if filt["rooms"]:
            message += f"{locales.get_localized_string('Txt_rooms', state_data.get('lang'))} {filt['rooms']}\n"
        if filt["square_min"]:
            message += f"{locales.get_localized_string('Txt_square_min', state_data.get('lang'))} {filt['square_min']}\n"
        if filt["square_max"]:
            message += f"{locales.get_localized_string('Txt_square_max', state_data.get('lang'))} {filt['square_max']}\n"

        # если квартира, то этажи от и до и нет сдвига по полям, если дом, то только кол-во этажей и есть сдвиг т.к. меньше полей
        if filt["type"] == "flat":
            if filt["floor_min"]:
                message += f"{locales.get_localized_string('Txt_floor_min', state_data.get('lang'))} {filt['floor_min']}\n"
            if filt["floor_max"]:
                message += f"{locales.get_localized_string('Txt_floor_max', state_data.get('lang'))} {filt['floor_max']}\n"
            if filt["animals"]:
                animal_status = []
                if "1" in filt["animals"]:
                    animal_status.append(locales.get_localized_string("Txt_yes", state_data.get("lang")))
                if "2" in filt["animals"]:
                    animal_status.append(locales.get_localized_string("Txt_by_agreement", state_data.get("lang")))
                if "0" in filt["animals"]:
                    animal_status = locales.get_localized_string("Txt_no", state_data.get("lang"))
                message += f"{locales.get_localized_string('Txt_animals', state_data.get('lang'))} {', '.join(animal_status)}\n"
            if filt["ac"]:
                message += f"{locales.get_localized_string('Txt_ac', state_data.get('lang'))} {locales.get_localized_string('Txt_yes', state_data.get('lang')) if filt['ac'] else locales.get_localized_string('Txt_no', state_data.get('lang'))}\n"
            if filt["owner"]:
                message += f"{locales.get_localized_string('Txt_owner', state_data.get('lang'))} {locales.get_localized_string('Txt_yes', state_data.get('lang')) if filt['owner'] else locales.get_localized_string('Txt_no', state_data.get('lang'))}\n"
        else:
            if filt["floors"]:
                message += f"{locales.get_localized_string('Txt_floors', state_data.get('lang'))} {filt['floors']}\n"
            if filt["animals"]:
                animal_status = []
                if "1" in filt["animals"]:
                    animal_status.append(locales.get_localized_string("Txt_yes", state_data.get("lang")))
                if "2" in filt["animals"]:
                    animal_status.append(locales.get_localized_string("Txt_by_agreement", state_data.get("lang")))
                if "0" in filt["animals"]:
                    animal_status = locales.get_localized_string("Txt_no", state_data.get("lang"))
                message += f"{locales.get_localized_string('Txt_animals', state_data.get('lang'))} {', '.join(animal_status)}\n"
            if filt["ac"]:
                message += f"{locales.get_localized_string('Txt_ac', state_data.get('lang'))} {locales.get_localized_string('Txt_yes', state_data.get('lang')) if filt['ac'] else locales.get_localized_string('Txt_no', state_data.get('lang'))}\n"
            if filt["owner"]:
                message += f"{locales.get_localized_string('Txt_owner', state_data.get('lang'))} {locales.get_localized_string('Txt_yes', state_data.get('lang')) if filt['owner'] else locales.get_localized_string('Txt_no', state_data.get('lang'))}\n"
        message += "\n"

    return message


async def remove_filter(user_id, filter_number):
    # удаление всех фильтров, если юзер писал 0
    if filter_number == 0:
        db_delete_filters(user_id)
        return
    filters = db_get_filters_id(user_id)
    if 0 < filter_number <= len(filters):
        filter_id = filters[filter_number - 1]
        filter_id = filter_id.get('filter_id')
        db_delete_filter(filter_id)
        return True
    return False


# вывод стейта для отладки
async def get_state(state: FSMContext):
    current_state = await state.get_state()
    current_data = await state.get_data()
    print(f"CURRENT STATE IS: {current_state} AND DATE IS {current_data}")


# получаем данные из state data
async def get_state_data(state: FSMContext, data):
    state_data = await state.get_data()
    return state_data.get(data)


# добавляем юзера в базу
def insert_user(user_id, username, first_name, last_name, language, payload=None):
    db_insert_user(user_id, username, first_name, last_name, language, payload)
    return


def give_premium(user_id):
    db_give_premium(user_id)


def take_premium(user_id):
    db_take_premium(user_id)


async def delete_user(user_id):
    db_delete_user(user_id)
    await redis_delete_user(user_id)


def check_mute(user_id):
    return db_check_mute(user_id)


def mute_user(user_id):
    db_mute_user(user_id)


def unmute_user(user_id):
    db_unmute_user(user_id)


# добавление фильтра в базу с фильтрами
async def add_filter_to_base(state_data):
    db_add_filter(state_data)


async def get_lang_from_users(user_id):
    await redis_get_lang_from_users(user_id)


async def send_flat(flat, main_bot, old_price):
    users_ads_premium_filter = db_get_user_ids_matching_flats(flat.ad_id)
    for item in users_ads_premium_filter:
        user_id = item['user_id']
        sent_ads = item['sent_ads']
        premium = item['PREMIUM']
        filter_id = item['filter_id']
        lang = item['LANG']

        # если у юезра нет премиума и кол-во объяв до N лимита и объявление с listam ли премиум 1
        if (premium == 0 and sent_ads < config.free_ad_limit and flat.site == 'listam') or premium == 1:
            # логика отправки рекламы
            # если нет премиума и кол-во объяв делится на N без остатка (каждое N объявление)
            if premium == 0 and sent_ads != 0 and sent_ads % ad_counter == 0:
                actual_ads = db_get_actual_ads()
                current_datetime = datetime.now()
                for ad in actual_ads:
                    if ad['end_datetime'] is not None:
                        if ad['end_datetime'] > current_datetime:
                            try:
                                await main_bot.copy_message(chat_id=user_id,
                                                            from_chat_id=5372961337,
                                                            message_id=ad['message_id'])
                                increment_sent_ad(ad['id'])
                            except TelegramForbiddenError:
                                mute_user(user_id)
                                log.info('Tried send $ ad, but user blocked. Set mute 1.')
                            break
                    elif ad['max_sends_count'] is not None:
                        if ad['advertising_sends_count'] < ad['max_sends_count']:
                            try:
                                await main_bot.copy_message(chat_id=user_id,
                                                            from_chat_id=5372961337,
                                                            message_id=ad['message_id'])
                                increment_sent_ad(ad['id'])
                                break
                            # если юзер заблокировал бота, а мы попробовали отправить сообщение
                            except TelegramForbiddenError:
                                mute_user(user_id)
                                log.info('Tried send $ ad, but user blocked. Set mute 1.')

            # логика отправки самого объявления
            try:
                if lang == 'hy':
                    url = flat.url_card.replace('/ru', '')
                elif lang == 'ru':
                    url = flat.url_card
                else:
                    url = flat.url_card.replace('/ru', '/en')
                # узнаем символ валюты на основании того, для какой валюты выставлен фильтр. Если нет, то в USD
                currency = db_get_filter_currency(filter_id)
                if currency == '֏':
                    db_currency = 'PRICE_AMD'
                    price = flat.price_amd
                elif currency == '₽':
                    db_currency = 'PRICE_RUR'
                    price = flat.price_rur
                else:
                    db_currency = 'PRICE_USD'
                    price = flat.price_usd
                message_text = (f'{locales.get_localized_string('Txt_found_flat', lang)}\n'
                                f'{url}\n'
                                f'<b>{locales.get_localized_string("Txt_price", lang)} {price} {currency}</b>\n')
                # добавление информации при наличии премиума
                if premium == 1:
                    message_text += '<blockquote>'
                    # получаем медиану из таблицы flats по таким же параметрам, как новая найденная квартира
                    median_price, min_range_price, max_range_price  = db_get_median_price_by_currency_flat(flat, 'flats', db_currency)
                    if median_price:
                        message_text += f"{locales.get_localized_string('Txt_avg_price', lang)} {median_price} {currency}\n"  # локаль про среднюю цену, но по факту медиана
                        message_text += f"{locales.get_localized_string('Txt_price_range', lang)} {min_range_price} - {max_range_price} {currency}\n"
                        price_difference_percentage = ((int(price) - median_price) / median_price) * 100
                        if abs(price_difference_percentage) <= 5:
                            message_text += f"↕️ {locales.get_localized_string('Txt_avg_market', lang)}\n"
                        elif price_difference_percentage > 5:
                            message_text += f"⬆️ {locales.get_localized_string('Txt_above_market', lang)}\n"
                        else:
                            message_text += f"⬇️ {locales.get_localized_string('Txt_below_market', lang)}\n"

                    if old_price:
                        # если у нас есть старая цена, то смотрит разницу между новой и старой. Если разница больше 4%, то движение цены и повод для торгов
                        delta_prices = ((flat.price_amd - old_price) / old_price) * 100
                        if delta_prices < -4:
                            localized_text = locales.get_localized_string('Txt_price_changed', lang)
                            message_text += f'{localized_text.replace('@', str(old_price)).replace('&', str(flat.price_amd))}\n'
                    message_text += '</blockquote>'
                await main_bot.send_message(chat_id=user_id,
                                            parse_mode='HTML',
                                            text=message_text)
                db_increment_sent_ads(user_id)
            # если юзер заблокировал бота, а мы попробовали отправить сообщение
            except TelegramForbiddenError:
                mute_user(user_id)
                log.info('Tried send ad, but user blocked. Set mute 1.')

        # на сегодня у юзера закончились объявления, уведомляем
        if premium == 0 and sent_ads == config.free_ad_limit:
            try:
                await main_bot.send_message(chat_id=user_id,
                                            text=locales.get_localized_string('Mg_limit_ads',
                                                                              db_get_user_lang(user_id)))
                db_increment_sent_ads(user_id)
            except TelegramForbiddenError:
                mute_user(user_id)
                log.info('Tried send ad, but premium user blocked. Set mute 1.')


async def send_house(house, main_bot, old_price):
    users_ads_premium_filter = db_get_user_ids_matching_houses(house.ad_id)
    for item in users_ads_premium_filter:
        user_id = item['user_id']
        sent_ads = item['sent_ads']
        premium = item['PREMIUM']
        filter_id = item['filter_id']
        lang = item['LANG']
        # если у юезра нет премиума и кол-во объяв до 10 и объявление с listam ли премиум 1
        if (premium == 0 and sent_ads < config.free_ad_limit and house.site == 'listam') or premium == 1:
            # логика отправки рекламы
            # если нет премиума и кол-во объяв делится на 2 без остатка (каждое 2 объявление)
            if premium == 0 and sent_ads != 0 and sent_ads % ad_counter == 0:
                actual_ads = db_get_actual_ads()
                current_datetime = datetime.now()
                for ad in actual_ads:
                    if ad['end_datetime'] is not None:
                        if ad['end_datetime'] > current_datetime:
                            try:
                                await main_bot.copy_message(chat_id=user_id, from_chat_id=5372961337,
                                                            message_id=ad['message_id'])
                                increment_sent_ad(ad['id'])
                            except TelegramForbiddenError:
                                mute_user(user_id)
                                log.info('Tried send $ ad, but user blocked. Set mute 1.')
                            break
                    elif ad['max_sends_count'] is not None:
                        if ad['advertising_sends_count'] < ad['max_sends_count']:
                            try:
                                await main_bot.copy_message(chat_id=user_id, from_chat_id=5372961337,
                                                            message_id=ad['message_id'])
                                increment_sent_ad(ad['id'])
                                break
                            # если юзер заблокировал бота, а мы попробовали отправить сообщение
                            except TelegramForbiddenError:
                                mute_user(user_id)
                                log.info('Tried send $ ad, but user blocked. Set mute 1.')

            # логика отправки самого объявления
            try:
                if lang == 'hy':
                    url = house.url_card.replace('/ru', '')
                elif lang == 'ru':
                    url = house.url_card
                else:
                    url = house.url_card.replace('/ru', '/en')
                # узнаем символ валюты на основании того, для какой валюты выставлен фильтр. Если нет, то в USD
                currency = db_get_filter_currency(filter_id)
                if currency == '֏':
                    db_currency = 'PRICE_AMD'
                    price = house.price_amd
                elif currency == '₽':
                    db_currency = 'PRICE_RUR'
                    price = house.price_rur
                else:
                    db_currency = 'PRICE_USD'
                    price = house.price_usd

                message_text = (f'{locales.get_localized_string('Txt_found_house', lang)}\n'
                                f'{url}\n'
                                f'<b>{locales.get_localized_string('Txt_price', lang)} {price} {currency}</b>\n')
                # добавление информации при наличии премиума
                if premium == 1:
                    message_text += '<blockquote>'
                    # получаем медиану из таблицы flats по таким же параметрам, как новая найденная квартира
                    median_price, min_range_price, max_range_price = db_get_median_price_by_currency_house(house, 'houses', db_currency)
                    if median_price:
                        message_text += f"{locales.get_localized_string('Txt_avg_price', lang)} {median_price}{currency}\n"  # локаль про среднюю цену, но по факту медиана
                        message_text += f"{locales.get_localized_string('Txt_price_range', lang)} {min_range_price} - {max_range_price} {currency}\n"

                        price_difference_percentage = ((int(price) - median_price) / median_price) * 100
                        if abs(price_difference_percentage) <= 5:
                            message_text += f"↕️ {locales.get_localized_string('Txt_avg_price', lang)}\n"
                        elif price_difference_percentage > 5:
                            message_text += f"⬆️ {locales.get_localized_string('Txt_above_market', lang)}\n"
                        else:
                            message_text += f"{locales.get_localized_string('Txt_below_market', lang)}\n"
                    if old_price:
                        # если у нас есть старая цена, то смотрит разницу между новой и старой. Если разница больше 4%, то движение цены и повод для торгов
                        delta_prices = ((house.price_amd - old_price) / old_price) * 100
                        if delta_prices < -4:
                            localized_text = locales.get_localized_string('Txt_price_changed', lang)
                            message_text += f'{localized_text.replace('@', str(old_price)).replace('&', str(house.price_amd))}\n'
                    message_text += '</blockquote>'
                await main_bot.send_message(chat_id=user_id,
                                            parse_mode='HTML',
                                            text=message_text)
                db_increment_sent_ads(user_id)
            # если юзер заблокировал бота, а мы попробовали отправить сообщение
            except TelegramForbiddenError:
                mute_user(user_id)
                log.info('Tried send ad, but user blocked. Set mute 1.')

        # на сегодня у юзера закончились объявления, уведомляем
        if premium == 0 and sent_ads == config.free_ad_limit:
            try:
                await main_bot.send_message(chat_id=user_id,
                                            text=locales.get_localized_string('Mg_limit_ads',
                                                                              db_get_user_lang(user_id)))
                db_increment_sent_ads(user_id)
            except TelegramForbiddenError:
                mute_user(user_id)
                log.info('Tried send ad, but premium user blocked. Set mute 1.')

# возвращает кол-во подходящих квартир
async def get_number_suitable_flats(last_filter):
    return db_get_number_suitable_flats(last_filter)

# возвращает кол-во подходящих домов
async def get_number_suitable_houses(last_filter):
    return db_get_number_suitable_houses(last_filter)


async def get_number_suitable_housing(user_id):
    last_filter = db_get_last_created_filter(user_id)  # получаем последний созданный фильтр
    if last_filter['type'] == 'flat':
        return await get_number_suitable_flats(last_filter['filter_id'])
    elif last_filter['type'] == 'house':
        return await get_number_suitable_houses(last_filter['filter_id'])


