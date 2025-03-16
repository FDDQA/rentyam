import logging

import pymysql

from src.config import config
from src.types.classes import LocalizationManager

locales = LocalizationManager()
locales.load_from_csv(config.localization_path)
log = logging.getLogger('sql')

# подключение к базе


def db_connect():
    cursor = None
    connection = None
    try:
        connection = pymysql.connect(
            host=config.db_host,
            port=config.db_port,
            user=config.db_user,
            password=config.db_password,
            database=config.db_name,
            cursorclass=pymysql.cursors.DictCursor
        )
        log.info('Successfully connected to SQL')
        cursor = connection.cursor()
    except Exception as ex:
        log.error('Connection to SQL refused')
        log.error(ex)
    return connection, cursor


connection, cursor = db_connect()


# закрытие соединения
def db_connect_close():
    connection.close()
    log.warning("Connection to SQL closed")


def db_create_tables():
    # обнуляем кол-во отправленных объявлений каждый день
    cursor.execute('''
                    CREATE EVENT IF NOT EXISTS reset_sent_ads_count_daily
                    ON SCHEDULE EVERY 1 DAY
                    STARTS CURRENT_TIMESTAMP
                    DO
                    BEGIN
                        UPDATE users
                        SET SENT_ADS = 0
                        WHERE SENT_ADS > 0;
                    END
    ''')
    cursor.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                    USER_ID BIGINT,
                    PREMIUM BOOLEAN DEFAULT FALSE,
                    LANG VARCHAR(10),
                    USERNAME VARCHAR (255),
                    FIRST_NAME VARCHAR (255),
                    LAST_NAME VARCHAR (255),
                    MUTED BOOLEAN,
                    DATE_REG DATETIME,
                    SENT_ADS INT DEFAULT 0,
                    PAYLOAD VARCHAR(255),
                    PRIMARY KEY (USER_ID),
                    UNIQUE (USER_ID));
    ''')

    cursor.execute('''
                    CREATE TABLE IF NOT EXISTS filters (
                    filter_id INT AUTO_INCREMENT,
                    user_id BIGINT,
                    type VARCHAR(255),
                    creation_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                    districts VARCHAR(255),
                    price_amd_min INT,
                    price_amd_max INT,
                    price_usd_min INT,
                    price_usd_max INT,
                    price_rur_min INT,
                    price_rur_max INT,
                    rooms VARCHAR(255),
                    square_min INT,
                    square_max INT,
                    floor_min INT,
                    floor_max INT,
                    floors VARCHAR(255),
                    animals VARCHAR(255),
                    ac boolean,
                    owner boolean,
                    PRIMARY KEY (filter_id)
                );
    ''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS flats (
                    ID INT NOT NULL AUTO_INCREMENT,
                    SITE VARCHAR(50),
                    AD_ID INT,
                    URL_CARD VARCHAR(255),
                    DISTRICT VARCHAR(50),
                    PRICE_AMD INT,
                    PRICE_USD INT,
                    PRICE_RUR INT,
                    SQUARE INT,
                    ROOMS VARCHAR(2),
                    FLOOR VARCHAR(2),
                    FLOORS VARCHAR(2),
                    ANIMALS INT,
                    AC BOOLEAN,
                    OWNER BOOLEAN,
                    DATE DATETIME,
                    PRIMARY KEY (ID),
                    UNIQUE (AD_ID)
                );
    ''')

    cursor.execute('''
                    CREATE TABLE IF NOT EXISTS houses (
                    ID INT NOT NULL AUTO_INCREMENT,
                    SITE VARCHAR(50),
                    AD_ID INT,
                    URL_CARD VARCHAR(255),
                    DISTRICT VARCHAR(50),
                    PRICE_AMD INT,
                    PRICE_USD INT,
                    PRICE_RUR INT,
                    SQUARE INT,
                    ROOMS VARCHAR(2),
                    FLOORS VARCHAR(2),
                    ANIMALS INT,
                    AC BOOLEAN,
                    OWNER BOOLEAN,
                    DATE DATETIME,
                    PRIMARY KEY (ID),
                    UNIQUE (AD_ID)
                );
    ''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS ads (
    id INT AUTO_INCREMENT PRIMARY KEY,
    added_datetime DATETIME,
    start_datetime DATETIME,
    end_datetime DATETIME,
    message_id INT,
    advertising_sends_count INT DEFAULT 0,
    max_sends_count INT
);''')

    cursor.execute('''
    create table IF NOT EXISTS payments
    (
        id           int auto_increment
            primary key,
        user_id      bigint         null,
        payment_id   varchar(255)   null,
        amount_value decimal(10, 2) null,
        created_at   datetime       null,
        description  text           null,
        expires_at   datetime       null,
        UNIQUE (user_id)
    );
    ''')

    cursor.execute('''
    create table IF NOT EXISTS marketing  (
    id int not null AUTO_INCREMENT,
    payload VARCHAR(255) not null,
    link VARCHAR(255) not null,
    PRIMARY KEY (id)
);
    ''')


def db_get_users_data(user_id):
    cursor.execute(f"SELECT * FROM users WHERE USER_ID = {user_id} ")
    user_data = cursor.fetchall()
    connection.commit()
    return user_data


def db_get_all_users():
    cursor.execute(f'SELECT user_id FROM users')
    user_ids = cursor.fetchall()
    return user_ids


def db_increment_sent_ads(user_id):
    cursor.execute(f"UPDATE users SET SENT_ADS = SENT_ADS + 1 WHERE user_id = {user_id}")
    connection.commit()


# смена языка в базе
def db_change_language(user_id, language):
    cursor.execute("UPDATE users SET LANG = %s WHERE USER_ID = %s", (language, user_id))
    connection.commit()


def db_get_user_lang(user_id):
    cursor.execute(f"SELECT LANG FROM users WHERE USER_ID = {user_id}")
    lang = cursor.fetchone()
    return lang['LANG']


# получение всех фильтров по user_id из таблицы filters
def db_get_created_filters(user_id):
    cursor.execute(f"SELECT * FROM filters WHERE user_id = {user_id}")
    filters = cursor.fetchall()
    return filters


# удаление одного фильтра в таблице filters по user_id
def db_delete_filter(filter_id):
    cursor.execute(f"DELETE FROM filters WHERE filter_id = {filter_id}")
    connection.commit()


# удаление всех фильтров в таблице filters по user_id
def db_delete_filters(user_id):
    cursor.execute(f"DELETE FROM filters WHERE user_id = {user_id}")
    connection.commit()


# получение всех filter_id
def db_get_filters_id(user_id):
    cursor.execute(f"SELECT filter_id FROM filters WHERE user_id = {user_id}")
    filters = cursor.fetchall()
    connection.commit()
    return filters


# добавление пользователя в базу
def db_insert_user(user_id, username, first_name, last_name, language, payload=None):
    query = "INSERT IGNORE INTO users (USER_ID, MUTED, USERNAME, FIRST_NAME, LAST_NAME, DATE_REG, LANG, PAYLOAD) " \
            "VALUES (%s, FALSE, %s, %s, %s, NOW(), %s, %s)"
    values = (user_id, username, first_name, last_name, language, payload)
    cursor.execute(query, values)
    connection.commit()


def db_add_ad(message_id, start_datetime=None, end_datetime=None, max_sends_count=None):
    sql = "INSERT INTO ads (message_id, added_datetime, start_datetime, end_datetime, max_sends_count) VALUES (%s, NOW(), %s, %s, %s)"
    val = (message_id, start_datetime, end_datetime, max_sends_count)
    cursor.execute(sql, val)
    connection.commit()


def db_get_actual_ads():
    cursor.execute(f'SELECT * FROM ads')
    actual_ads = cursor.fetchall()
    return actual_ads


# увеличваем на 1 кол-во отправок рекламного сообщения
def increment_sent_ad(ad_id):
    cursor.execute(f"UPDATE ads SET advertising_sends_count = advertising_sends_count + 1 WHERE id = {ad_id}")
    connection.commit()


def db_check_mute(user_id):
    cursor.execute(f"SELECT MUTED FROM users WHERE user_id = {user_id}")
    muted = cursor.fetchall()
    if muted:
        return muted[0].get('MUTED')


# заблокировать отправку сообщений юзеру
def db_mute_user(user_id):
    cursor.execute(f"UPDATE users SET MUTED = TRUE WHERE USER_ID = %s", user_id)
    connection.commit()


# разблокировать отправку сообщений юзеру
def db_unmute_user(user_id):
    cursor.execute(f"UPDATE users SET MUTED = FALSE WHERE USER_ID = %s", user_id)
    connection.commit()


# добавление квартиры в базу
def db_insert_flat(flat):

    cursor.execute(f"SELECT PRICE_AMD FROM flats WHERE AD_ID = {flat.ad_id}")
    old_price = cursor.fetchone()
    if old_price:
        old_price = old_price['PRICE_AMD']
        # Удаляем существующую запись, если такой AD_ID есть в базе
        cursor.execute(f"DELETE FROM flats WHERE AD_ID = {flat.ad_id}")
        connection.commit()
    # Вставляем новую запись
    insert_query = """
        INSERT INTO flats (
            SITE, AD_ID, URL_CARD, DISTRICT, PRICE_AMD, PRICE_USD, PRICE_RUR, SQUARE, ROOMS, FLOOR, FLOORS, ANIMALS, AC, OWNER, DATE
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
    """
    cursor.execute(insert_query, (
        flat.site, flat.ad_id, flat.url_card, flat.district, flat.price_amd, flat.price_usd, flat.price_rur,
        flat.square,
        flat.rooms, flat.floor, flat.floors, flat.animals, flat.ac, flat.owner,
        flat.date
    ))
    connection.commit()
    return old_price


# добавление дома в базу
def db_insert_house(house):
    # Проверяем наличие записи с таким AD_ID
    cursor.execute(f"SELECT PRICE_AMD FROM houses WHERE AD_ID = {house.ad_id}")
    old_price = cursor.fetchone()

    if old_price:
        old_price = old_price['PRICE_AMD']
        # Удаляем существующую запись
        cursor.execute(f"DELETE FROM houses WHERE AD_ID = {house.ad_id}")
        connection.commit()

    # Вставляем новую запись
    query = """
        INSERT INTO houses (
            SITE, AD_ID, URL_CARD, DISTRICT, PRICE_AMD, PRICE_USD, PRICE_RUR, SQUARE, ROOMS, FLOORS, ANIMALS, AC, OWNER, DATE
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
    """
    cursor.execute(query, (
        house.site, house.ad_id, house.url_card, house.district, house.price_amd, house.price_usd, house.price_rur,
        house.square, house.rooms, house.floors, house.animals, house.ac, house.owner, house.date
    ))
    connection.commit()
    return old_price


# получение списка user_id при появлении новой квартиры и в случае, если она подходит по фильтру
def db_get_user_ids_matching_flats(ad_id):
    query = f"""
        SELECT 
            ff.user_id, 
            MIN(ff.filter_id) AS filter_id,
            u.SENT_ADS AS sent_ads,
            u.PREMIUM,
            u.LANG
        FROM filters ff
        JOIN 
            flats f ON (ff.districts IS NULL OR FIND_IN_SET(f.DISTRICT, REPLACE(ff.districts, ', ', ',')) > 0)
        JOIN 
            users u ON ff.user_id = u.user_id
        WHERE
            ff.type = 'flat'
            AND (
                (ff.price_amd_min IS NULL OR f.PRICE_AMD >= ff.price_amd_min)
                AND (ff.price_amd_max IS NULL OR f.PRICE_AMD <= ff.price_amd_max)
            )
            AND (
                (ff.price_usd_min IS NULL OR f.PRICE_USD >= ff.price_usd_min)
                AND (ff.price_usd_max IS NULL OR f.PRICE_USD <= ff.price_usd_max)
            )
            AND (
                (ff.price_rur_min IS NULL OR f.PRICE_RUR >= ff.price_rur_min)
                AND (ff.price_rur_max IS NULL OR f.PRICE_RUR <= ff.price_rur_max)
            )
            AND (f.SQUARE >= ff.square_min OR ff.square_min IS NULL)
            AND (f.SQUARE <= ff.square_max OR ff.square_max IS NULL)
            AND (
                (ff.rooms IS NULL AND f.ROOMS IS NOT NULL)
                OR (f.ROOMS IN (1, 2, 3, 4, 5, 6, 7, 8) AND FIND_IN_SET(f.ROOMS, REPLACE(ff.rooms, ' ', '')))
            )
            AND (f.FLOOR >= ff.floor_min OR ff.floor_min IS NULL)
            AND (f.FLOOR <= ff.floor_max OR ff.floor_max IS NULL)
            AND (
                (ff.animals IS NULL AND f.ANIMALS IS NOT NULL)
                OR (f.ANIMALS IN (1, 2, 3) AND FIND_IN_SET(f.ANIMALS, REPLACE(ff.animals, ' ', '')))
            )
            AND (f.AC = ff.ac OR ff.ac IS NULL)
            AND (f.OWNER = ff.owner OR ff.owner IS NULL)
            AND u.muted = 0
            AND f.AD_ID = {ad_id}
        GROUP BY ff.user_id;
    """

    cursor.execute(query)
    user_info = cursor.fetchall()
    return user_info


# получение списка user_id при появлении нового дома и в случае, если он подходит по фильтру
def db_get_user_ids_matching_houses(ad_id):
    query = f"""
        SELECT 
            ff.user_id, 
            MIN(ff.filter_id) AS filter_id,
            u.SENT_ADS AS sent_ads,
            u.PREMIUM,
            u.LANG
        FROM 
            filters ff
        JOIN 
            houses f ON (ff.districts IS NULL OR FIND_IN_SET(f.DISTRICT, REPLACE(ff.districts, ', ', ',')) > 0)
        JOIN 
            users u ON ff.user_id = u.user_id
        WHERE
            ff.type = 'house' -- Условие для поля type, чтобы были только фильтры для домов
            AND (
                (ff.price_amd_min IS NULL OR f.PRICE_AMD >= ff.price_amd_min)
                AND (ff.price_amd_max IS NULL OR f.PRICE_AMD <= ff.price_amd_max)
            )
            AND (
                (ff.price_usd_min IS NULL OR f.PRICE_USD >= ff.price_usd_min)
                AND (ff.price_usd_max IS NULL OR f.PRICE_USD <= ff.price_usd_max)
            )
            AND (
                (ff.price_rur_min IS NULL OR f.PRICE_RUR >= ff.price_rur_min)
                AND (ff.price_rur_max IS NULL OR f.PRICE_RUR <= ff.price_rur_max)
            )
            AND (f.SQUARE >= ff.square_min OR ff.square_min IS NULL)
            AND (f.SQUARE <= ff.square_max OR ff.square_max IS NULL)
            AND (
                (ff.floors IS NULL AND f.FLOORS IS NOT NULL)  
                OR (f.FLOORS IN (1, 2, 3, 4) AND FIND_IN_SET(f.FLOORS, REPLACE(ff.rooms, ' ', '')))
            )
            AND (
                (ff.rooms IS NULL AND f.ROOMS IS NOT NULL)
                OR (f.ROOMS IN (1, 2, 3, 4, 5, 6, 7, 8) AND FIND_IN_SET(f.ROOMS, REPLACE(ff.rooms, ' ', '')))
            )
            AND (
                (ff.animals IS NULL AND f.ANIMALS IS NOT NULL)
                OR (f.ANIMALS IN (1, 2, 3) AND FIND_IN_SET(f.ANIMALS, REPLACE(ff.animals, ' ', '')))
            )            AND (f.AC = ff.ac OR ff.ac IS NULL)
            AND (f.OWNER = ff.owner OR ff.owner IS NULL)
            AND u.muted = 0
            AND f.AD_ID = {ad_id}
        GROUP BY 
            ff.user_id;

    """

    cursor.execute(query)
    user_info = cursor.fetchall()
    return user_info


# добавление фильтра юзера в базу
def db_add_filter(state_data):
    # если выбраны районы, то перевеодим их в читаемый вид
    if state_data.get("selected_districts"):
        state_data["selected_districts"] = ', '.join(
            locales.match_localized_districts(state_data))

    # если выбраны комнаты, собираем их
    rooms = state_data.get("selected_rooms")
    if rooms:
        rooms = ', '.join(state_data.get("selected_rooms"))
    else:
        rooms = None

    floors = state_data.get("selected_floors")
    if floors:
        floors = ', '.join(state_data.get("selected_floors"))
    else:
        floors = None

    # условие для того, чтобы заполнить нужную цену в базе
    if state_data.get("selected_currency") == "amd":
        price_min_field = "price_amd_min"
        price_max_field = "price_amd_max"
    elif state_data.get("selected_currency") == "usd":
        price_min_field = "price_usd_min"
        price_max_field = "price_usd_max"
    else:  # Валюта - RUR
        price_min_field = "price_rur_min"
        price_max_field = "price_rur_max"

    selected_animals = []
    if state_data.get("selected_animals"):
        if state_data.get("selected_animals", {}).get("no_animals", False):
            selected_animals.append("-1")
        if state_data.get("selected_animals", {}).get("by_agreement", False):
            selected_animals.append("2")
        if state_data.get("selected_animals", {}).get("yes_animals", False):
            selected_animals.append("1")
        selected_animals = ', '.join(selected_animals)
    else:
        selected_animals = None

    ac = None
    if state_data.get("selected_ac"):
        ac = state_data.get("selected_ac") == "yes"

    owner = None
    if state_data.get("selected_owner"):
        owner = state_data.get("selected_owner") == "yes"

    # определяем какой тип фильтра сохраняет -
    if state_data.get("selected_type") == "selected_flat":  # если юзер сохранил фильтр по квартире
        if state_data.get('selected_filter_type') == 'flat_short':
            query = f"INSERT IGNORE INTO filters (user_id, type, districts, {price_min_field}, {price_max_field}," \
                    "rooms) " \
                    "VALUES (%s, %s, %s, %s, %s, %s)"
            values = (
                state_data.get("user_id"), "flat", state_data.get("selected_districts"),
                state_data.get("price_min"), state_data.get("price_max"), rooms
            )
        else:
            query = f"INSERT IGNORE INTO filters (user_id, type, districts, {price_min_field}, {price_max_field}," \
                    "rooms, square_min, square_max, floor_min, floor_max, animals, ac, owner) " \
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
            values = (
                state_data.get("user_id"), "flat", state_data.get("selected_districts"),
                state_data.get("price_min"), state_data.get("price_max"),
                rooms, state_data.get("square_min"),
                state_data.get("square_max"), state_data.get("floor_min"), state_data.get("floor_max"),
                selected_animals, ac, owner  # 13 параметров
            )
    else:  # если юзер сохранил фильтр по дому
        if state_data.get('selected_filter_type') == 'house_short':
            query = f"INSERT IGNORE INTO filters (user_id, type, districts, {price_min_field}, {price_max_field}," \
                    "rooms) " \
                    "VALUES (%s, %s, %s, %s, %s, %s)"
            values = (
                state_data.get("user_id"), "house", state_data.get("selected_districts"),
                state_data.get("price_min"), state_data.get("price_max"), rooms
            )
        else:
            query = f"INSERT IGNORE INTO filters (user_id, type, districts, {price_min_field}, {price_max_field}," \
                    "rooms, square_min, square_max, floors, animals, ac, owner) " \
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
            values = (
                state_data.get("user_id"), "house", state_data.get("selected_districts"),
                state_data.get("price_min"), state_data.get("price_max"),
                rooms, state_data.get("square_min"),
                state_data.get("square_max"), floors,
                selected_animals, ac, owner
            )

    cursor.execute(query, values)
    connection.commit()


def db_get_filter_currency(filter_id):
    query = f"""
            SELECT 
                CASE
                    WHEN price_amd_min IS NOT NULL OR price_amd_max IS NOT NULL THEN '֏'
                    WHEN price_usd_min IS NOT NULL OR price_usd_max IS NOT NULL THEN '$'
                    WHEN price_rur_min IS NOT NULL OR price_rur_max IS NOT NULL THEN '₽'
                    ELSE '$'  -- В USD по умолчанию, если ничего не указано
                END AS currency
            FROM filters
            WHERE filter_id = {filter_id};
        """
    cursor.execute(query)
    currency = cursor.fetchone()['currency']
    return currency


def db_get_median_price_by_currency_flat(flat, table_name, currency):
    # диапазон площади для поиска +- 20% и +- 2 этажа
    if flat.floor == '32+':
        floor = flat.floor
    else:
        floor = int(flat.floor)
    square_min = int(flat.square) - 0.2 * int(flat.square)
    square_max = int(flat.square) + 0.2 * int(flat.square)
    floor_min = floor - 3
    floor_max = floor + 3
    # запрос на поиск похожих квартир по параметрам
    query_for_median = f"""
    SELECT AVG(dd.val) as median_price
    FROM (
        SELECT d.{currency} AS val, @rownum:=@rownum+1 as `row_number`, @total_rows:=@rownum
        FROM (
            SELECT d.{currency}
            FROM {table_name} d
            WHERE d.{currency} IS NOT NULL
                AND DISTRICT = '{flat.district}'
                AND SQUARE >= {square_min}
                AND SQUARE <= {square_max}
                AND FLOOR >= {floor_min}
                AND FLOOR <= {floor_max}
                AND ROOMS = '{flat.rooms}'
                AND AC = '{flat.ac}'
            ORDER BY d.{currency}
        ) d, (SELECT @rownum:=0) r
    ) as dd
    WHERE dd.row_number IN (FLOOR((@total_rows+1)/2), FLOOR((@total_rows+2)/2))
    AND @total_rows >= 5;
            """
    # можно еще добавить AND FLOOR = '{flat.floor}' для соответствия по этажу
    # AND (FLOORS = '32+' OR CAST(FLOORS AS UNSIGNED) >= {floors_min} AND CAST(FLOORS AS UNSIGNED) <= {floors_max})
    # если у нас 32+ этаж, то по этажу ищем 32+, иначе по этажу ищем +- 2 этажа
    cursor.execute(query_for_median)
    median_price = cursor.fetchone()

    if median_price['median_price']:
        query_for_range_price = f"""
                SELECT
                    MIN(d.PRICE_AMD) as min_price,
                    MAX(d.PRICE_AMD) as max_price
                FROM {table_name} d
                WHERE d.{currency} IS NOT NULL
                    AND DISTRICT = '{flat.district}'
                    AND SQUARE >= {square_min}
                    AND SQUARE <= {square_max}
                    AND FLOOR >= {floor_min}
                    AND FLOOR <= {floor_max}
                    AND ROOMS = '{flat.rooms}'
                    AND AC = '{flat.ac}'
                ORDER BY d.{currency}
                """
        cursor.execute(query_for_range_price)
        min_price, max_price = cursor.fetchall()[0].values() # тут ошибка, но на самом деле ее нет. values() корретно распаковывает значения
        return int(median_price['median_price']), int(min_price), int(max_price)
    return None, None, None


def db_get_median_price_by_currency_house(house, table_name, currency):
    # диапазон площади для поиска +- 20% и +- 2 этажа
    square_min = int(house.square) - 0.2 * int(house.square)
    square_max = int(house.square) + 0.2 * int(house.square)
    # запрос на поиск похожих квартир по параметрам

    query_for_median = f"""
        SELECT AVG(dd.val) as median_price
        FROM (
            SELECT d.{currency} AS val, @rownum:=@rownum+1 as `row_number`, @total_rows:=@rownum
            FROM (
                SELECT d.{currency}
                FROM {table_name} d
                WHERE d.{currency} IS NOT NULL
                    AND DISTRICT = '{house.district}'
                    AND SQUARE >= {square_min}
                    AND SQUARE <= {square_max}
                    AND ROOMS = '{house.rooms}'
                    AND AC = '{house.ac}'
                ORDER BY d.{currency}
            ) d, (SELECT @rownum:=0) r
        ) as dd
        WHERE dd.row_number IN (FLOOR((@total_rows+1)/2), FLOOR((@total_rows+2)/2))
        AND @total_rows >= 5;

            """
    cursor.execute(query_for_median)
    median_price = cursor.fetchone()
    if median_price['median_price']:
        query_for_range_price = f"""
                    SELECT
                        MIN(d.PRICE_AMD) as min_price,
                        MAX(d.PRICE_AMD) as max_price
                    FROM {table_name} d
                    WHERE d.{currency} IS NOT NULL
                        AND DISTRICT = '{house.district}'
                        AND SQUARE >= {square_min}
                        AND SQUARE <= {square_max}
                        AND ROOMS = '{house.rooms}'
                        AND AC = '{house.ac}'
                    ORDER BY d.{currency}
                    """
        cursor.execute(query_for_range_price)
        cursor.execute(query_for_range_price)
        min_price, max_price = cursor.fetchall()[0].values() # тут ошибка, но на самом деле ее нет. values() корретно распаковывает значения
        return int(median_price['median_price']), int(min_price), int(max_price)
    return None, None, None


def db_get_premium(user_id):
    cursor.execute(f"SELECT PREMIUM FROM users WHERE user_id = {user_id}")
    premium = cursor.fetchall()[0]
    premium_status = premium.get("PREMIUM")  # тут ошибка, но на самом деле ее нет. fetchall возвращает словарь, а не кортеж
    connection.commit()
    return premium_status


def db_give_premium(user_id):
    cursor.execute(f"UPDATE users SET PREMIUM = 1 WHERE user_id = {user_id}")


def db_take_premium(user_id):
    cursor.execute(f"UPDATE users SET PREMIUM = 0 WHERE user_id = {user_id}")


def db_delete_user(user_id):
    # Удаление всех записей по user_id из таблицы filters
    cursor.execute(f"DELETE FROM filters WHERE user_id = {user_id}")

    # Удаление всех записей по user_id из таблицы users
    cursor.execute(f"DELETE FROM users WHERE user_id = {user_id}")


def db_add_payment(user_id, payment_id, amount, created_at, description, expired_at):
    query = """
    INSERT INTO payments (user_id, payment_id, amount_value, created_at, description, expires_at)
    VALUES (%s, %s, %s, %s, %s, %s)
    ON DUPLICATE KEY UPDATE
        payment_id = VALUES(payment_id),
        amount_value = VALUES(amount_value),
        created_at = VALUES(created_at),
        description = VALUES(description),
        expires_at = VALUES(expires_at);
    """
    cursor.execute(query, (user_id, payment_id, amount, created_at, description, expired_at))
    connection.commit()


async def db_payments_controller(payment_id=None, income_value=None, income_currency=None):
    cursor.execute("""SELECT p.user_id, u.PREMIUM
                        FROM payments p
                        JOIN users u ON p.user_id = u.user_id
                        WHERE p.expires_at < NOW() AND u.PREMIUM = True;
    """)
    user_ids = cursor.fetchall()
    return user_ids


def db_get_end_time_subscription(user_id):
    cursor.execute(f'''
    SELECT expires_at
    FROM payments
    WHERE user_id = {user_id}
    AND expires_at > NOW();
    ''')
    expired_time = cursor.fetchone()
    if expired_time:
        return expired_time['expires_at']


def db_add_start_link(payload, link):
    cursor.execute("INSERT INTO marketing (payload, link) VALUES (%s, %s)", (payload, link))
    connection.commit()


def db_find_payload(payload):
    cursor.execute("SELECT * FROM marketing WHERE payload = %s", payload)
    result = cursor.fetchone()
    if result:
        return True


def db_check_ad_in_db(ad_id, table):
    cursor.execute(f"SELECT * FROM {table} WHERE AD_ID = {ad_id}")
    ad = cursor.fetchone()
    return ad


def db_get_weekly_statistics():
    statistics_flats = {}
    statistics_houses = {}

    # Количество объявлений за позапрошлую неделю (с понедельника по воскресенье)
    cursor.execute(f'''
        SELECT COUNT(*) as 'count'
        FROM flats
        WHERE DATE >= DATE(DATE_SUB(NOW(), INTERVAL 14 DAY)) + INTERVAL 4 HOUR 
        AND DATE < DATE(DATE_SUB(NOW(), INTERVAL 7 DAY)) + INTERVAL 4 HOUR;
    ''')
    statistics_flats['old_count'] = cursor.fetchone()['count']

    # Количество объявлений за прошлую неделю (с понедельника по воскресенье)
    cursor.execute(f'''
        SELECT COUNT(*) as 'count'
        FROM flats
        WHERE DATE >= DATE(DATE_SUB(NOW(), INTERVAL 7 DAY)) + INTERVAL 4 HOUR
        AND DATE < CURDATE() + INTERVAL 4 HOUR;
    ''')
    statistics_flats['actual_count'] = cursor.fetchone()['count']

    # Медианная цена за позапрошлую неделю
    cursor.execute(f'''
        SELECT AVG(dd.val) AS median_price
        FROM (
            SELECT d.PRICE_AMD AS val, @rownum:=@rownum+1 AS 'row_number', @total_rows:=@rownum
            FROM (
                SELECT d.PRICE_AMD
                FROM flats d
                WHERE d.DATE >= DATE(DATE_SUB(NOW(), INTERVAL 14 DAY)) + INTERVAL 4 HOUR
                    AND d.DATE < DATE(DATE_SUB(NOW(), INTERVAL 7 DAY)) + INTERVAL 4 HOUR
                    AND d.PRICE_AMD IS NOT NULL
                ORDER BY d.PRICE_AMD
            ) d, (SELECT @rownum:=0) r
        ) AS dd
        WHERE dd.row_number IN (FLOOR((@total_rows+1)/2), FLOOR((@total_rows+2)/2));
    ''')
    statistics_flats['old_median_price'] = int(cursor.fetchone()['median_price'])

    # Медианная цена за прошлую неделю
    cursor.execute(f'''
        SELECT AVG(dd.val) AS median_price
        FROM (
            SELECT d.PRICE_AMD AS val, @rownum:=@rownum+1 AS 'row_number', @total_rows:=@rownum
            FROM (
                SELECT d.PRICE_AMD
                FROM flats d
                WHERE d.DATE >= DATE(DATE_SUB(NOW(), INTERVAL 7 DAY)) + INTERVAL 4 HOUR
                    AND d.DATE < CURDATE() + INTERVAL 4 HOUR
                    AND d.PRICE_AMD IS NOT NULL
                ORDER BY d.PRICE_AMD
            ) d, (SELECT @rownum:=0) r
        ) AS dd
        WHERE dd.row_number IN (FLOOR((@total_rows+1)/2), FLOOR((@total_rows+2)/2));
    ''')
    statistics_flats['actual_median_price'] = int(cursor.fetchone()['median_price'])

    # все то же самое, только по домам
    # получаем кол-во объявлений за прошлую неделю
    # Количество объявлений за позапрошлую неделю
    cursor.execute(f'''
        SELECT COUNT(*) as 'count'
        FROM houses
        WHERE DATE >= DATE(DATE_SUB(NOW(), INTERVAL 14 DAY)) + INTERVAL 4 HOUR 
        AND DATE < DATE(DATE_SUB(NOW(), INTERVAL 7 DAY)) + INTERVAL 4 HOUR;
    ''')
    statistics_houses['old_count'] = cursor.fetchone()['count']

    # Количество объявлений за прошлую неделю
    cursor.execute(f'''
        SELECT COUNT(*) as 'count'
        FROM houses
        WHERE DATE >= DATE(DATE_SUB(NOW(), INTERVAL 7 DAY)) + INTERVAL 4 HOUR
        AND DATE < CURDATE() + INTERVAL 4 HOUR;
    ''')
    statistics_houses['actual_count'] = cursor.fetchone()['count']

    # Медианная цена за позапрошлую неделю
    cursor.execute(f'''
        SELECT AVG(dd.val) AS median_price
        FROM (
            SELECT d.PRICE_AMD AS val, @rownum:=@rownum+1 AS 'row_number', @total_rows:=@rownum
            FROM (
                SELECT d.PRICE_AMD
                FROM houses d
                WHERE d.DATE >= DATE(DATE_SUB(NOW(), INTERVAL 14 DAY)) + INTERVAL 4 HOUR
                    AND d.DATE < DATE(DATE_SUB(NOW(), INTERVAL 7 DAY)) + INTERVAL 4 HOUR
                    AND d.PRICE_AMD IS NOT NULL
                ORDER BY d.PRICE_AMD
            ) d, (SELECT @rownum:=0) r
        ) AS dd
        WHERE dd.row_number IN (FLOOR((@total_rows+1)/2), FLOOR((@total_rows+2)/2));
    ''')
    statistics_houses['old_median_price'] = int(cursor.fetchone()['median_price'])

    # Медианная цена за прошлую неделю
    cursor.execute(f'''
        SELECT AVG(dd.val) AS median_price
        FROM (
            SELECT d.PRICE_AMD AS val, @rownum:=@rownum+1 AS 'row_number', @total_rows:=@rownum
            FROM (
                SELECT d.PRICE_AMD
                FROM houses d
                WHERE d.DATE >= DATE(DATE_SUB(NOW(), INTERVAL 7 DAY)) + INTERVAL 4 HOUR
                    AND d.DATE < CURDATE() + INTERVAL 4 HOUR
                    AND d.PRICE_AMD IS NOT NULL
                ORDER BY d.PRICE_AMD
            ) d, (SELECT @rownum:=0) r
        ) AS dd
        WHERE dd.row_number IN (FLOOR((@total_rows+1)/2), FLOOR((@total_rows+2)/2));
    ''')
    statistics_houses['actual_median_price'] = int(cursor.fetchone()['median_price'])

    return statistics_flats, statistics_houses

async def db_get_premium_users():
    cursor.execute('SELECT USER_ID FROM users WHERE PREMIUM = 1;')
    return cursor.fetchall()

async def db_user_block_bot(user_id):
    cursor.execute(f'UPDATE users SET BLOCKED = 1 WHERE USER_ID = {user_id};')
    connection.commit()

async def db_user_unblock_bot(user_id):
    cursor.execute(f'UPDATE users SET BLOCKED = 0 WHERE USER_ID = {user_id};')
    connection.commit()


def db_get_last_created_filter(user_id):
    query = f"""
        SELECT filter_id, type
            FROM filters
            WHERE user_id = {user_id}
            ORDER BY filter_id DESC
            LIMIT 1;
        """
    cursor.execute(query)
    return cursor.fetchone()

def db_get_number_suitable_flats(filter_id):

    # Базовая часть SQL-запроса
    query = f"""
    SELECT 
    COUNT(*) AS matching_flats_count
FROM 
    flats f
JOIN 
    filters ff ON (ff.districts IS NULL OR FIND_IN_SET(f.DISTRICT, REPLACE(ff.districts, ', ', ',')) > 0)
JOIN 
    users u ON ff.user_id = u.user_id
WHERE
    filter_id = {filter_id}
    AND (
        (ff.price_amd_min IS NULL OR f.PRICE_AMD >= ff.price_amd_min)
        AND (ff.price_amd_max IS NULL OR f.PRICE_AMD <= ff.price_amd_max)
    )
    AND (
        (ff.price_usd_min IS NULL OR f.PRICE_USD >= ff.price_usd_min)
        AND (ff.price_usd_max IS NULL OR f.PRICE_USD <= ff.price_usd_max)
    )
    AND (
        (ff.price_rur_min IS NULL OR f.PRICE_RUR >= ff.price_rur_min)
        AND (ff.price_rur_max IS NULL OR f.PRICE_RUR <= ff.price_rur_max)
    )
    AND (f.SQUARE >= ff.square_min OR ff.square_min IS NULL)
    AND (f.SQUARE <= ff.square_max OR ff.square_max IS NULL)
    AND (
        (ff.rooms IS NULL AND f.ROOMS IS NOT NULL)
        OR (f.ROOMS IN (1, 2, 3, 4, 5, 6, 7, 8) AND FIND_IN_SET(f.ROOMS, REPLACE(ff.rooms, ' ', '')))
    )
    AND (f.FLOOR >= ff.floor_min OR ff.floor_min IS NULL)
    AND (f.FLOOR <= ff.floor_max OR ff.floor_max IS NULL)
    AND (
        (ff.animals IS NULL AND f.ANIMALS IS NOT NULL)
        OR (f.ANIMALS IN (1, 2, 3) AND FIND_IN_SET(f.ANIMALS, REPLACE(ff.animals, ' ', '')))
    )
    AND (f.AC = ff.ac OR ff.ac IS NULL)
    AND (f.OWNER = ff.owner OR ff.owner IS NULL)
    AND f.DATE >= NOW() - INTERVAL 1 WEEK;
    """

    cursor.execute(query)
    return cursor.fetchone()['matching_flats_count']

def db_get_number_suitable_houses(filter_id):
    # Базовая часть SQL-запроса
    query = f"""
    SELECT 
    COUNT(*) AS matching_houses_count
FROM 
    houses f
JOIN 
    filters ff ON (ff.districts IS NULL OR FIND_IN_SET(f.DISTRICT, REPLACE(ff.districts, ', ', ',')) > 0)
JOIN 
    users u ON ff.user_id = u.user_id
WHERE
    filter_id = {filter_id}
    AND (
        (ff.price_amd_min IS NULL OR f.PRICE_AMD >= ff.price_amd_min)
        AND (ff.price_amd_max IS NULL OR f.PRICE_AMD <= ff.price_amd_max)
    )
    AND (
        (ff.price_usd_min IS NULL OR f.PRICE_USD >= ff.price_usd_min)
        AND (ff.price_usd_max IS NULL OR f.PRICE_USD <= ff.price_usd_max)
    )
    AND (
        (ff.price_rur_min IS NULL OR f.PRICE_RUR >= ff.price_rur_min)
        AND (ff.price_rur_max IS NULL OR f.PRICE_RUR <= ff.price_rur_max)
    )
    AND (f.SQUARE >= ff.square_min OR ff.square_min IS NULL)
    AND (f.SQUARE <= ff.square_max OR ff.square_max IS NULL)
    AND (
        (ff.floors IS NULL AND f.FLOORS IS NOT NULL)
        OR (f.FLOORS IN (1, 2, 3, 4) AND FIND_IN_SET(f.FLOORS, REPLACE(ff.floors, ' ', '')))
    )
    AND (
        (ff.rooms IS NULL AND f.ROOMS IS NOT NULL)
        OR (f.ROOMS IN (1, 2, 3, 4, 5, 6, 7, 8) AND FIND_IN_SET(f.ROOMS, REPLACE(ff.rooms, ' ', '')))
    )
    AND (
        (ff.animals IS NULL AND f.ANIMALS IS NOT NULL)
        OR (f.ANIMALS IN (1, 2, 3) AND FIND_IN_SET(f.ANIMALS, REPLACE(ff.animals, ' ', '')))
    )
    AND (f.AC = ff.ac OR ff.ac IS NULL)
    AND (f.OWNER = ff.owner OR ff.owner IS NULL)
    AND f.DATE >= NOW() - INTERVAL 1 WEEK;
    """

    cursor.execute(query)
    return cursor.fetchone()['matching_houses_count']