import json
import logging
from datetime import datetime
import asyncio

import aiogram.exceptions

from src.config import config
from src.types.classes import LocalizationManager

from redis.asyncio import Redis

from src.db.sql import db_unmute_user, db_check_mute, db_get_created_filters

locales = LocalizationManager()
locales.load_from_csv(config.localization_path)

redis = Redis(host=config.redis_host,
              port=config.redis_port)


async def redis_get_lmt_from_users(main_bot):
    while True:
        cursor = b'0'
        current_time = datetime.now()

        # Перебираем все ключи в Redis
        while cursor:
            cursor, keys = await redis.scan(cursor=cursor, match=b'fsm:*:data')

            for key in keys:
                data = await redis.get(key)
                if data:
                    # Декодируем JSON из строки, получаемой из Redis
                    data_dict = json.loads(data)
                    user_id = data_dict.get('user_id')

                    # Проверяем состояние пользователя
                    state_key = f'fsm:{user_id}:{user_id}:state'
                    user_state = await redis.get(state_key)

                    if user_state != b'MenuStates:stop_state':
                        # Проверяем наличие ключа "lmt"
                        if 'lmt' in data_dict:
                            lmt = data_dict['lmt']
                            # Парсим дату из строки
                            lmt_time = datetime.strptime(lmt, '%Y-%m-%d %H:%M:%S')
                            # Сравниваем разницу во времени
                            time_difference = current_time - lmt_time
                            if user_id is not None:
                                if time_difference.total_seconds() > 600 and db_check_mute(user_id) and len(db_get_created_filters(user_id)) != 0:
                                    try:
                                        await main_bot.send_message(chat_id=user_id,
                                                                    text=locales.get_localized_string("Mg_you_unmuted",
                                                                                                      await redis_get_lang_from_users(
                                                                                                          user_id)))
                                    except aiogram.exceptions.TelegramForbiddenError:
                                        logging.warning(f"Can't send message to user {user_id} from redis")

                                    # удаление времени последнего сообщения и анмьют т.к. у него есть фильтры
                                    db_unmute_user(user_id)
                                    user_id = key.decode().split(':')[1]
                                    key = f'fsm:{user_id}:{user_id}:data'
                                    data_dict = json.loads(data)
                                    del data_dict['lmt']
                                    updated_data = json.dumps(data_dict)
                                    await redis.set(key, updated_data)
                                elif time_difference.total_seconds() > 600 and db_check_mute(user_id):
                                    try:
                                        await main_bot.send_message(chat_id=user_id,
                                                                    text=locales.get_localized_string("Mg_reminder_idle",
                                                                                                      await redis_get_lang_from_users(
                                                                                                          user_id)))
                                    except aiogram.exceptions.TelegramForbiddenError:
                                        logging.warning(f"Can't send message to user {user_id} from redis")

                                    # удаление времени последнего сообщения
                                    user_id = key.decode().split(':')[1]
                                    key = f'fsm:{user_id}:{user_id}:data'
                                    data_dict = json.loads(data)
                                    del data_dict['lmt']
                                    updated_data = json.dumps(data_dict)
                                    await redis.set(key, updated_data)
                            else:
                                logging.warning(f'Tried db_check_mute, but user_id is none. UserID: {user_id}, state_key: {state_key}, key: {key}, data: {data}, keys: {keys}')
            await redis.close()
            await asyncio.sleep(60)  # Пауза перед следующей итерацией - 5 минут (300 сек)


async def redis_get_lang_from_users(user_id):
    key = "fsm:{}:{}:data".format(user_id, user_id)
    # получение данных из Redis
    data = await redis.get(key)
    if data:
        # Распаковываем JSON и извлекаем язык
        user_data = json.loads(data)
        language = user_data.get('lang')
        return language


async def redis_delete_user(user_id):
    # Формируем шаблон ключей для удаления
    key_pattern = f"fsm:{user_id}:*"

    # Получаем все ключи, соответствующие шаблону
    keys_to_delete = await redis.keys(key_pattern)
    # Удаляем все найденные ключи
    for key in keys_to_delete:
        await redis.delete(key)
