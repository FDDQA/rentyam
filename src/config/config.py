import os
import random

token = os.getenv('BOT_TOKEN')

db_host = os.getenv('DB_HOST')
db_port = int(os.getenv('DB_PORT', 3306))
db_user = os.getenv('DB_USER', 'bot')
db_password = os.getenv('DB_PASSWORD')
db_name = os.getenv('DB_NAME',)

redis_port = int(os.getenv('REDIS_PORT', 6379))
redis_host = os.getenv('REDIS_HOST')

reviews_url = os.getenv('REVIEW_URL')

localization_path = os.path.join(os.getcwd(), 'src/localization', 'localization.csv')
tutor_localization_path = os.path.join(os.getcwd(), 'src/localization', 'tutor_localization.csv')

# каждые N объявления приходит реклама
ad_counter = 1

# лимит объявлений на бесплатном тарифе
free_ad_limit = 3


# если True, то возвращает старсы сразу после оплаты
refunding = False

# цена подписки в старсах, НЕ МЕНЯЕТ ЦЕНУ В КНОПКЕ
weekly_premium_price = 99
monthly_premium_price = 249



def sleep_time_listam():
    return random.choice(range(3, 5))


def sleep_time_tunmun():
    return random.choice(range(3, 5))

