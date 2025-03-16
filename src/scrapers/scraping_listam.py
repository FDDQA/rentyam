import random

import re
from datetime import datetime

from bs4 import BeautifulSoup
from aiogram import Bot

from src.types.classes import Flat, House

import logging
import asyncio

from requestx import RequestX


from src.db.sql import db_insert_house, db_insert_flat
from src.utils.other import send_house, send_flat, check_ad_in_db

log = logging.getLogger('scraping_listam')


class InfinityScrapingListam:
    pattern = re.compile(r'^/ru/item/\d+$')  # паттерн для поиска ссылок на квартиры и дома
    animals_mapping = {
        "Нет": 0,
        "Да": 1,
        "По договоренности": 2
    }
    houses_url = f"https://www.list.am/ru/category/63/1?&pfreq=1&n=1&sid=0&crc=-1&type=1"
    flat_url = f"https://www.list.am/ru/category/56/1?&pfreq=1&n=1&sid=0&crc=-1&type=1"
    cloudflare_stuff = [
                "https://www.list.am/ru/category/56/1?&pfreq=1&n=1&sid=0&crc=-1&type=1",
                "https://www.list.am/ru/category/63/1?&pfreq=1&n=1&sid=0&crc=-1&type=1"
            ]
    browser_args = [
        "--window-size=1,1",
        "--disable-dev-shm-usage",
        "--blink-settings=imagesEnabled=false",
        "--disable-blink-features=AutomationControlled",
        "--disable-gpu",
        "--disable-browser-side-navigation",
        "--disable-extensions"
    ]
    int_value_pattern = re.compile("[^0-9]")

    def __init__(self, bot: Bot):
        self.sleep_time_flat = 10
        self.sleep_time_house = 20
        self.bot = bot
        self.parser = None

    async def bypass_cloudflare(self, url):
        for i in range(0, 5):
            if i > 0:
                log.info(f'Try # {i}.Sleep 5 sec')
                await asyncio.sleep(5)
            response = await self.parser.aget(url,
                                              raise_on_error=False,
                                              )

            if response.status_code != 200:
                log.warning(f'BAD STATUS {response.status_code}')
                log.warning(f'CONTENT {response.text}')
                if 'Just a moment.' in response.text:
                    log.error('CLOUDFLARE')
            if url in self.cloudflare_stuff:
                # проверяем есть ли на странице 96 дивов
                divs = await self.get_gl_block(response.text)
                if divs is not None and len(divs) == 96:
                    return divs
                else:
                    log.warning(f'DID NOT FIND 96 DIVS {url}')
                    if 'Just a moment.' in response.text:
                        log.error('CLOUDFLARE')
                    continue
            else:
                return BeautifulSoup(response.text, "lxml")
        return None  # Если не удалось загрузить страницу после 10 попыток, возвращаем None


    async def get_gl_block(self, html):
        soup = BeautifulSoup(html, 'lxml')
        page = soup.findAll('div', class_="gl")
        # log.info(f'{len(page)} FOUNDED GL-BLOCKS')  # должно быть 3 блока при полной загрузке
        # возвращаем самый длинный gl-блок
        if len(page) > 1:
            biggest_gl_block = max(page, key=len)
            return biggest_gl_block
        if len(page) == 1:
            page = page[0]
            hrefs = 0
            for i in page:
                if 'href' in str(i):
                    hrefs += 1
                    if hrefs == 10:
                        # если нашли 1 блок и в нем больше 10 ссылок - значит не загрузился рекламный блок, возвращаем page
                        # log.info(f'Find 1 gl-block with 10+ hrefs')
                        return page

    async def infinity_scraping_flat(self, bot: Bot, semaphore):
        old_links_on_page = None
        first_pass = True
        while True:
            async with semaphore:
                divs = await self.bypass_cloudflare(self.flat_url)
                if divs is None:
                    continue
            new_links_on_page = divs.find_all('a', href=self.pattern)             # получаем список ссылок на квартиры
            if old_links_on_page and old_links_on_page == new_links_on_page:  # если прошлый результат равен текущему, то пропускаем и спим
                await asyncio.sleep(random.choice(range(self.sleep_time_flat-2, self.sleep_time_flat+2)))
                if self.sleep_time_flat < 60:
                    self.sleep_time_flat += 2
                continue
            else:
                self.sleep_time_flat = 10
            for i in new_links_on_page:
                if first_pass or i.get("href") not in str(old_links_on_page):
                    # если первых проход и объект есть в базе
                    if first_pass and await check_ad_in_db(i.get("href").split("/")[3], 'flats') is not None:
                        continue
                    url_card = "https://list.am" + i.get("href")
                    ad_id = i.get("href").split("/")[3]
                    district = i.find('div', class_="at").text.split(",")[0]
                    if district == 'Давидашен':
                        district = 'Давташен'
                    async with semaphore:
                        html_page = await self.bypass_cloudflare(url_card)
                    # если у нас этот фетч вернул none, то либо нет футера, либо нет цен, а значит скип
                    if html_page is None:
                        continue

                    try:
                        prices = html_page.find("span", class_="xprice").select('span')
                    except AttributeError:
                        # если наткнулить на объяву, в которой нет цены
                        continue
                    # если цена всё-таки есть, но определяем валюту и пишем в разные переменные

                    # тут лучше проработать момент отсутствия цены в каких-то единицах иначе скрипт споткнётся
                    for price in prices:
                        if "$" in price.text:
                            price_usd = int(re.sub(self.int_value_pattern, "", price.text))
                        elif "֏" in price.text:
                            price_amd = int(re.sub(self.int_value_pattern, "", price.text))
                        elif "₽" in price.text:
                            price_rur = int(re.sub(self.int_value_pattern, "", price.text))

                    # пробуем узнать площадь, если не указана, то пропускает
                    try:
                        square = re.sub(self.int_value_pattern, "",
                                        html_page.find('div', class_='t', string="Общая площадь").find_next().text)
                    except AttributeError:
                        log.info(f'Square not found {url_card}')
                        # УДАЛЯЕМ СУП И ВСЁ ЧТО В НЁМ. .clear() ОБЯЗАТЕЛЬНО из-за сложности объекта
                        html_page.clear()
                        del html_page
                        continue

                    # отладка
                    try:
                        rooms = html_page.find('div', class_='t',
                                               string="Количество комнат").find_next().text  # получаем кол-во комнат
                    except AttributeError:
                        log.info(f'Rooms not found {url_card}')
                    try:
                        floor = html_page.find('div', class_='t', string="Этаж").find_next().text  # узнаем какой этаж
                        floors = html_page.find('div', class_='t',
                                                string="Этажей в доме").find_next().text  # узнаем какой этаж
                    except AttributeError:
                        log.info(f'Floors or floor not found {url_card}')

                    # пробуем узнать можно ли с животными, если не указано, то присваиваем -1
                    try:
                        animals = html_page.find('div', class_='t', string="Можно с животными").find_next().text
                        animals = self.animals_mapping.get(animals, -1)
                    except AttributeError:
                        animals = -1

                    # из подвала берём даты создания и обновления
                    footer = html_page.find('div', class_="footer").findAll('span')

                    try:
                        date_str = footer[2].text.split(" ")[1] + " " + footer[2].text.split(" ")[2]
                        date = datetime.strptime(date_str, "%d.%m.%Y %H:%M").strftime("%Y-%m-%d %H:%M")
                    except IndexError:
                        date = datetime.now().strftime("%Y-%m-%d %H:%M")

                    # проверяем собственник или нет
                    try:
                        owner = html_page.find('span', class_="clabel").text
                        owner = False
                    except AttributeError:
                        owner = True
                    # смотрим наличие кондиционера
                    try:
                        ac = html_page.find('div', class_='t', string="Удобства").find_next().text.lower()
                        if "кондиционер" or "Кондиционер" in ac:
                            ac = True
                        else:
                            ac = False
                    except AttributeError:
                        ac = False

                    flat = Flat('listam', ad_id, url_card, district, price_amd, price_usd, price_rur, square, rooms,
                                floor, floors,
                                animals, ac, owner, date)
                    log.info(f'Flat: {flat.url_card}')
                    old_price = db_insert_flat(flat)
                    await send_flat(flat, bot, old_price)
            old_links_on_page = new_links_on_page
            first_pass = False

    async def infinity_scraping_house(self, bot: Bot, semaphore):
        old_links_on_page = None
        first_pass = True
        while True:
            async with semaphore:
                divs = await self.bypass_cloudflare(self.houses_url)
                if divs is None:
                    continue
            new_links_on_page = divs.find_all('a', href=self.pattern)  # получаем список ссылок на квартиры
            if old_links_on_page and old_links_on_page == new_links_on_page:  # если прошлый результат равен текущему, то пропускаем и спим
                await asyncio.sleep(random.choice(range(self.sleep_time_house - 2, self.sleep_time_house + 2)))
                if self.sleep_time_house < 60:
                    self.sleep_time_house += 2
                continue
            else:
                self.sleep_time_house = 20
            for i in new_links_on_page:
                if first_pass or i.get("href") not in str(old_links_on_page):
                    # если первых проход и объект есть в базе
                    if first_pass and await check_ad_in_db(i.get("href").split("/")[3], 'houses') is not None:
                        continue
                    url_card = "https://list.am" + i.get("href")
                    ad_id = i.get("href").split("/")[3]
                    district = i.find('div', class_="at").text.split(",")[0]
                    if district == 'Давидашен':
                        district = 'Давташен'
                    async with semaphore:
                        html_page = await self.bypass_cloudflare(url_card)
                    if html_page is None:
                        continue
                    try:
                        prices = html_page.find("span", class_="xprice").select('span')
                    except AttributeError:
                        continue
                    # если цена всё-таки есть, но определяем валюту и пишем в разные переменные
                    for price in prices:
                        if "$" in price.text:
                            price_usd = int(re.sub("[^0-9]", "", price.text))
                        elif "֏" in price.text:
                            price_amd = int(re.sub("[^0-9]", "", price.text))
                        elif "₽" in price.text:
                            price_rur = int(re.sub("[^0-9]", "", price.text))

                    # пробуем узнать площадь, если не указана, то пропускаем
                    try:
                        square = re.sub("[^0-9]", "",
                                        html_page.find('div', class_='t', string="Площадь дома").find_next().text)
                    except AttributeError:
                        log.info(f'Square not found {url_card}')

                        # УДАЛЯЕМ СУП И ВСЁ ЧТО В НЁМ. .clear() ОБЯЗАТЕЛЬНО из-за сложности объекта
                        html_page.clear()
                        del html_page
                        continue

                    # отладка
                    try:
                        rooms = html_page.find('div', class_='t',
                                               string="Количество комнат").find_next().text  # получаем кол-во комнат
                        floors = html_page.find('div', class_='t',
                                                string="Этажей в доме").find_next().text  # узнаем сколько этажей в доме
                    except AttributeError:
                        log.info(f'Rooms or floors not found{url_card}')

                    # пробуем узнать можно ли с животными, если не указано, то присваиваем -1
                    try:
                        animals = html_page.find('div', class_='t', string="Можно с животными").find_next().text
                        animals = self.animals_mapping.get(animals, -1)
                    except AttributeError:
                        animals = -1

                    # из подвала берём даты создания и обновления
                    # Отладка
                    footer = html_page.find('div', class_="footer").findAll('span')
                    try:
                        date_str = footer[2].text.split(" ")[1] + " " + footer[2].text.split(" ")[2]
                        date = datetime.strptime(date_str, "%d.%m.%Y %H:%M").strftime("%Y-%m-%d %H:%M")
                    except IndexError:
                        date = datetime.now().strftime("%Y-%m-%d %H:%M")

                    # проверяем собственник или нет
                    try:
                        owner = html_page.find('span', class_="clabel").text
                        owner = False
                    except AttributeError:
                        owner = True

                    # смотрим наличие кондиционера
                    try:
                        ac = html_page.find('div', class_='t', string="Удобства").find_next().text.lower()
                        if "кондиционер" or "Кондиционер" in ac:
                            ac = True
                        else:
                            ac = False
                    except AttributeError:
                        ac = False

                    house = House('listam', ad_id, url_card, district, price_amd, price_usd, price_rur, square,
                                  rooms, floors, animals, ac, owner, date)
                    log.info(f'House: {house.url_card}')
                    old_price = db_insert_house(house)
                    await send_house(house, bot, old_price)

            old_links_on_page = new_links_on_page
            first_pass = False

    async def main(self):
        log.info("Scraping listam started")
        self.parser = RequestX(impersonate="chrome110")
        semaphore = asyncio.Semaphore(1)
        log.info(
        await asyncio.gather(
            self.infinity_scraping_flat(self.bot, semaphore),
            self.infinity_scraping_house(self.bot, semaphore)
        ))
