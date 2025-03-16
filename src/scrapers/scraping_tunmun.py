import random
import re
from datetime import datetime
import logging
import json

from aiogram import Bot
from bs4 import BeautifulSoup
import asyncio

from requestx import RequestX
from src.db.sql import db_insert_flat, db_insert_house
from src.types.classes import Flat, House
from src.utils.other import send_flat, send_house, check_ad_in_db

log = logging.getLogger('scraping_tunmun')


class InfinityScrapingTunmun:
    def __init__(self, bot: Bot):
        self.bot = bot
        self.parser = None
        self.FLAT_URL = 'http://tunmun.am/ru/rent/flat/?RealtySearch%5Bsearch%5D=%7B%22label%22:%22%D0%95%D1%80%D0%B5%D0%B2%D0%B0%D0%BD%22,%22region_id%22:2%7D'
        self.HOUSE_URL = f"http://tunmun.am/ru/rent/house/?RealtySearch%5Bsearch%5D=%7B%22label%22%3A%22%D0%95%D1%80%D0%B5%D0%B2%D0%B0%D0%BD%22%2C%22region_id%22%3A2%7D"
        self.ADMIN_DISTRICT = 'административный район'
        self.ZEITUN_KANAKER = 'Зейтун Канакер'
        self.sleep_time_flat = 20
        self.sleep_time_house = 30

    async def fetch(self, url):
        response = await self.parser.aget(url, raise_on_error=False, attempts=10)
        if response.status_code >= 400:
            log.warning(f'BAD STATUS {response.status_code}')
        return BeautifulSoup(response.text, "lxml")

    async def infinity_scraping_flat(self, bot: Bot, semaphore):
        old_links_on_page = None
        first_pass = True
        while True:
            async with semaphore:
                soup = await self.fetch(self.FLAT_URL)
            links = [link.get("href") for link in soup.find_all('a', class_='images-line-box')]
            soup.clear(decompose=True)
            if old_links_on_page and old_links_on_page == links:  # если прошлый результат равен текущему, то пропускаем и спим
                await asyncio.sleep(random.choice(range(self.sleep_time_flat - 2, self.sleep_time_flat + 2)))
                if self.sleep_time_flat < 60:
                    self.sleep_time_flat += 2
                continue
            else:
                self.sleep_time_flat = 20
            for link in links:
                if first_pass or link not in str(old_links_on_page):
                    # если первых проход и объект есть в базе
                    if first_pass and await check_ad_in_db(link.split("/")[-2], 'flats') is not None:
                        continue
                    ad_id = link.split("/")[-2]
                    soup = await self.fetch(link)
                    try:
                        district = soup.find('div', class_="item-floor mt-3").get_text()
                        if self.ADMIN_DISTRICT in district:
                            district = district.split(' ')[2].replace('-', ' ')
                            if 'Канакер' in district:
                                district = self.ZEITUN_KANAKER
                            if district == 'Давидашен':
                                district = 'Давташен'
                        else:
                            district = None
                    except AttributeError:
                        district = None

                    default_price = soup.find("div", class_="item-price")
                    default_price = int(default_price.get("data-amd-price"))
                    script_price = soup.find("script", string=lambda text: text and "var currencies=JSON.parse" in text)
                    # Извлекаем значение валюты из скрипта с помощью регулярного выражения
                    match = re.search(r"var currency_value='(\S+)'", script_price.string)
                    default_currency = match.group(1)

                    all_currencies = re.search(r"var currencies=JSON\.parse\('([^']+)", script_price.string)
                    json_currencies = all_currencies.group(1)
                    dict_exchange_currency = json.loads(json_currencies)
                    amd_usd_rate = dict_exchange_currency['usd']['rate']
                    amd_rur_rate = dict_exchange_currency['rub']['rate']
                    match default_currency:
                        case 'amd':
                            price_amd = default_price
                            price_rur = int(round(price_amd / amd_rur_rate))
                            price_usd = int(round(price_amd / amd_usd_rate))
                        case 'usd':
                            price_usd = default_price
                            price_amd = int(round(price_usd * amd_usd_rate))
                            price_rur = int(round(price_amd / amd_rur_rate))
                        case 'rub':
                            price_rur = default_price
                            price_amd = int(round(price_rur * amd_rur_rate))
                            price_usd = int(round(price_amd / amd_usd_rate))

                    square = re.sub("[^0-9]", "",
                                    soup.find('span', class_='col-auto',
                                              string="Общая площадь").find_next().text).replace(
                        " ", "")  # общая площадь
                    try:
                        rooms = re.sub(r"\s+", "",
                                       soup.find('span', class_='col-auto', string="Комнат").find_next().text.replace(
                                           " ",
                                           ""))  # получаем кол-во комнат
                    except AttributeError:
                        rooms = None

                    try:
                        floor = re.sub(r"\s+", "",
                                       soup.find('span', class_='col-auto', string="Этаж").find_next().text.replace(" ",
                                                                                                                    ""))  # узнаем какой этаж
                    except AttributeError:
                        floor = None

                    try:
                        floors = re.sub(r"\s+", "", soup.find('span', class_='col-auto',
                                                              string="Количество этажей").find_next().text.replace(" ",
                                                                                                                   ""))  # узнаем какой этаж
                    except AttributeError:
                        floors = None

                    # пробуем узнать можно ли с животными, если не указано, то присваиваем -1, иначе 1
                    try:
                        animals = re.sub(r"\s+", "", soup.find('div', class_='col-auto col-lg-4 mb-4',
                                                               string="Можно с животными").find_next().text)
                        if animals:
                            animals = 1
                    except AttributeError:
                        animals = -1
                    # берём дату
                    date = datetime.now().strftime("%Y-%m-%d %H:%M")
                    # проверяем собственник или нет
                    try:
                        owner = soup.find('div', class_="mb-3", string='Собственник')
                        if owner:
                            owner = True
                        else:
                            owner = False
                    except AttributeError:
                        owner = None
                    # смотрим наличие кондиционера
                    try:
                        ac = soup.find('div', class_='col-auto col-lg-4 mb-4', string='Кондиционер')
                        if ac:
                            ac = True
                        else:
                            ac = False
                    except AttributeError:
                        ac = False
                    flat = Flat('tunmun', ad_id, link, district, price_amd, price_usd, price_rur, square, rooms, floor,
                                floors, animals, ac, owner, date)
                    log.info(f'House: {flat.url_card}')
                    # методы для отправки в базу и юзерам в тг, для воспроизведения не нужны
                    old_price = db_insert_flat(flat)
                    await send_flat(flat, bot, old_price)
                soup.clear(decompose=True)
                # TODO: логика парсинга и логика отправки в базу должны быть разбиты на разные методы. После этой строки должен быть отдельный метод
            old_links_on_page = links
            del links
            first_pass = False

    async def infinity_scraping_house(self, bot: Bot, semaphore):
        old_links_on_page = None
        first_pass = True
        while True:
            async with semaphore:
                soup = await self.fetch(self.HOUSE_URL)
            links = [link.get("href") for link in soup.find_all('a', class_='images-line-box')]
            soup.clear(decompose=True)
            if old_links_on_page and old_links_on_page == links:  # если прошлый результат равен текущему, то пропускаем и спим
                await asyncio.sleep(random.choice(range(self.sleep_time_house - 2, self.sleep_time_house + 2)))
                if self.sleep_time_house < 60:
                    self.sleep_time_house += 2
                continue
            else:
                self.sleep_time_house = 30
            for link in links:
                if first_pass or link not in str(old_links_on_page):
                    # если первых проход и объект есть в базе
                    if first_pass and await check_ad_in_db(link.split("/")[-2], 'houses') is not None:
                        continue
                    ad_id = link.split("/")[-2]
                    soup = await self.fetch(link)
                    try:
                        district = soup.find('div', class_="item-floor mt-3").get_text()
                        if self.ADMIN_DISTRICT in district:
                            district = district.split(' ')[2].replace('-', ' ')
                            if 'Канакер' in district:
                                district = self.ZEITUN_KANAKER
                            if district == 'Давидашен':
                                district = 'Давташен'
                        else:
                            district = None
                    except AttributeError:
                        district = None

                    default_price = soup.find("div", class_="item-price")
                    default_price = int(default_price.get("data-amd-price"))
                    script_price = soup.find("script", string=lambda text: text and "var currencies=JSON.parse" in text)
                    # Извлекаем значение валюты из скрипта с помощью регулярного выражения
                    match = re.search(r"var currency_value='(\S+)'", script_price.string)
                    default_currency = match.group(1)

                    all_currencies = re.search(r"var currencies=JSON\.parse\('([^']+)", script_price.string)
                    json_currencies = all_currencies.group(1)
                    dict_exchange_currency = json.loads(json_currencies)
                    amd_usd_rate = dict_exchange_currency['usd']['rate']
                    amd_rur_rate = dict_exchange_currency['rub']['rate']
                    match default_currency:
                        case 'amd':
                            price_amd = default_price
                            price_rur = int(round(price_amd / amd_rur_rate))
                            price_usd = int(round(price_amd / amd_usd_rate))
                        case 'usd':
                            price_usd = default_price
                            price_amd = int(round(price_usd * amd_usd_rate))
                            price_rur = int(round(price_amd / amd_rur_rate))
                        case 'rub':
                            price_rur = default_price
                            price_amd = int(round(price_rur * amd_rur_rate))
                            price_usd = int(round(price_amd / amd_usd_rate))

                    dict_exchange_currency.clear()
                    del dict_exchange_currency

                    square = re.sub("[^0-9]", "",
                                    soup.find('span', class_='col-auto', string="Площадь").find_next().text).replace(
                        " ", "")  # общая площадь

                    rooms = None  # для домов не указывается количество комнат
                    try:
                        floors = re.sub(r"\s+", "", soup.find('span', class_='col-auto',
                                                              string="Количество этажей").find_next().text.replace(" ",
                                                                                                                   ""))  # узнаем какой этаж
                    except AttributeError:
                        floors = None

                    # пробуем узнать можно ли с животными, если не указано, то присваиваем -1, иначе 1
                    try:
                        animals = re.sub(r"\s+", "", soup.find('div', class_='col-auto col-lg-4 mb-4',
                                                               string="Можно с животными").find_next().text)
                        if animals:
                            animals = 1
                    except AttributeError:
                        animals = -1
                    # берём дату
                    date = datetime.now().strftime("%Y-%m-%d %H:%M")
                    # проверяем собственник или нет
                    try:
                        owner = soup.find('div', class_="mb-3", string='Собственник')
                        if owner:
                            owner = True
                        else:
                            owner = False
                    except AttributeError:
                        owner = None
                    # смотрим наличие кондиционера
                    try:
                        ac = soup.find('div', class_='col-auto col-lg-4 mb-4', string='Кондиционер')
                        if ac:
                            ac = True
                        else:
                            ac = False
                    except AttributeError:
                        ac = False
                    house = House('tunmun', ad_id, link, district, price_amd, price_usd, price_rur, square, rooms,
                                  floors, animals, ac, owner, date)
                    log.info(f'House: {house.url_card}')
                    # методы для отправки в базу и юзерам в тг, для воспроизведения не нужны
                    old_price = db_insert_house(house)
                    await send_house(house, bot, old_price)
                    # УДАЛЯЕМ СУП И ВСЁ ЧТО В НЁМ. .clear() ОБЯЗАТЕЛЬНО из-за сложности объекта
                    # TODO: логика парсинга и логика отправки в базу должны быть разбиты на разные методы. После этой строки должен быть отдельный метод
            old_links_on_page = links
            del links
            first_pass = False

    async def main(self):
        log.info("Scrapping tunmun started")
        self.parser = RequestX(impersonate="chrome110")
        semaphore = asyncio.Semaphore(1)
        await asyncio.gather(
            self.infinity_scraping_flat(self.bot, semaphore),
            self.infinity_scraping_house(self.bot, semaphore)
        )

