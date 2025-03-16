import json
import logging
import time
from typing import Any

import asyncio


from curl_cffi import requests
from curl_cffi.requests import RequestsError
from curl_cffi.requests import AsyncSession

# Стандартные значения заголовков
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Pragma": "no-cache",
    "Cache-Control": "no-cache"
}


def print_warning(text):
    pass
    #logging.info(text)


def key_exists(json_obj: list | dict, key):
    if isinstance(json_obj, dict):
        if key in json_obj:
            return True
        for k, v in json_obj.items():
            if isinstance(v, (dict, list)):
                if key_exists(v, key):
                    return True
    elif isinstance(json_obj, list):
        for item in json_obj:
            if isinstance(item, (dict, list)):
                if key_exists(item, key):
                    return True
    return False


def key_exists_by_path(json_obj, path_str, delimiter='.'):
    for key in path_str.split(delimiter):
        if not (isinstance(json_obj, dict) and key in json_obj):
            return False
        json_obj = json_obj[key]
    return True


def get_value_recursive_by_path(data, path_str, delimiter='.'):
    for key in path_str.split(delimiter):
        if not (isinstance(data, dict) and key in data):
            return None
        data = data[key]
    return data


def get_value_recursive(dictionary, key):
    if key in dictionary:
        return dictionary[key]

    for value in dictionary.values():
        if isinstance(value, dict):
            result = get_value_recursive(value, key)
            if result is not None:
                return result

    return None


def parse_cookies(cookie_str: str) -> dict:
    # Разбиваем строку по ";", чтобы получить список кук
    cookie_items = cookie_str.strip(";").split(";")

    # Преобразование списка кук в словарь
    cookies_dict = {}
    for item in cookie_items:

        # Если нет "="
        if "=" not in item:
            cookies_dict[item] = ""
            continue

        # Сделать сплит по первому "="
        name, value = item.split("=", 1)
        cookies_dict[name] = value

    return cookies_dict


class Response:
    def __init__(self, status_code: int, text: str, content: Any, headers: dict, cookies: dict, response):
        self.status_code = status_code
        self.text = text
        self.content = content
        self.headers = headers
        self.cookies = cookies

        self.response = response

    def json(self):
        return json.loads(self.response.text)



class RequestX:
    def __init__(self, proxy=None, cookies=None, headers=None,
                 impersonate="chrome99_android", **kwargs):

        self.proxy = proxy
        self.cookies = None if cookies is None else parse_cookies(cookies)
        self.headers = DEFAULT_HEADERS if headers is None else headers
        self.impersonate = impersonate

        # self.session = requests.Session()
        self.session = AsyncSession()

        # Ответ последнего запроса
        self.response = None

        self.applied_methods = []

        self.last_check_error = ""

        # Проверки
        # Проверка статуса кодов
        self.check_status_code_ = []

        # Текст для проверки на наличие в запросе
        self.check_contains_text_ = ''
        # Учитывать ли регистра при проверке на наличие текста
        self.check_contains_text_ignore_case_ = True

        # Ключ, который нужно проверить на существование
        self.check_existence_json_key_ = ''

        # Ключ, который нужно проверить на значение
        self.check_value_json_key_ = ''
        self.check_value_json_key_value_ = ''

    def set_proxy(self, proxy):
        self.proxy = {"https": f"http://{proxy}"}
        return self

    def check(self, res):
        # Если запрос прошёл успешно и нет других методов для проверки
        if res.status_code == 200 and len(self.applied_methods) == 0:
            return True
        elif res.status_code != 200 and len(self.applied_methods) == 0:
            print_warning(f"Проверка ответа кода не прошла, код: {res.status_code}")
            return False

        check = True

        if "check_status_code" in self.applied_methods:
            check = res.status_code in self.check_status_code_

        if not check:
            self.last_check_error = "check_status_code"
            print_warning(f"Проверка ответа кода не прошла, код: {res.status_code}")
            return False

        if "check_contains_text" in self.applied_methods:
            # Получение текста ответа
            res_text = self.get_text_or_content(res)

            if self.check_contains_text_ignore_case_:
                check = self.check_contains_text_.lower() in res_text.lower()
            else:
                check = self.check_contains_text_ in res_text

        if not check:
            self.last_check_error = "check_contains_text"
            print_warning(f"Проверка ответа на наличие текста не прошла, текст проверки: {self.check_contains_text_}")
            return False

        if "check_existence_json_key" in self.applied_methods:
            try:
                json_object = json.loads(res.text)
                # Если содержит точку, то проверяем как путь
                if "." in self.check_existence_json_key_:
                    check = key_exists_by_path(json_object, self.check_existence_json_key_)
                else:
                    check = key_exists(json_object, self.check_existence_json_key_)
            except:
                check = False

        if not check:
            self.last_check_error = "check_existence_json_key"
            print_warning(
                f"Проверка ответа на наличие ключа не прошла, ключ проверки: {self.check_existence_json_key_}")
            return False

        if "check_value_json_key" in self.applied_methods:
            try:
                json_object = json.loads(res.text)
                # Если содержит точку, то проверяем как путь
                if "." in self.check_value_json_key_:
                    check = key_exists_by_path(json_object, self.check_value_json_key_)
                else:
                    check = key_exists(json_object, self.check_value_json_key_)

                if check:
                    if "." in self.check_value_json_key_:
                        check = (str(get_value_recursive_by_path(json_object,
                                                                 self.check_value_json_key_)).rstrip().lower() ==
                                 str(self.check_value_json_key_value_).rstrip().lower())
                    else:
                        check = (str(get_value_recursive(json_object, self.check_value_json_key_)).rstrip().lower() ==
                                 str(self.check_value_json_key_value_).rstrip().lower())
            except:
                check = False

        if not check:
            self.last_check_error = "check_value_json_key"
            print_warning(
                f"Проверка ответа на значение ключа не прошла, ключ и значение проверки: {self.check_value_json_key_},"
                f" {self.check_value_json_key_value_} ")
            return False

        return check

    def check_status_code(self, status_code: int | list = 200):
        self.applied_methods.append('check_status_code')

        # Очистка от старых кодов
        self.check_status_code_.clear()

        # Запись новых кодов
        if isinstance(status_code, int):
            self.check_status_code_.append(status_code)
        elif isinstance(status_code, list):
            self.check_status_code_ = status_code.copy()

        return self

    def check_contains_text(self, text, ignore_case=True):
        self.applied_methods.append('check_contains_text')

        self.check_contains_text_ = text
        self.check_contains_text_ignore_case_ = ignore_case

        return self

    def check_existence_json_key(self, key):
        self.applied_methods.append("check_existence_json_key")

        self.check_existence_json_key_ = key
        return self

    def check_value_json_key(self, key, value):
        self.applied_methods.append("check_value_json_key")

        self.check_value_json_key_ = key
        self.check_value_json_key_value_ = value
        return self

    def default_request_processing(self, proxy, headers, cookies, attempts):
        if attempts < 1:
            raise ValueError("Количество попыток должно быть больше 0")

        if proxy is None:
            proxy = self.proxy

        if headers is None:
            headers = self.headers

        if cookies is None:
            cookies = self.cookies
        else:
            cookies = parse_cookies(cookies)

        # Первое значение - это res
        return None, proxy, headers, cookies

    @staticmethod
    def get_text_or_content(res):
        try:
            return res.text
        except:
            return str(res.content)

    # Функция получения всех кук
    def get_cookies(self, format="str"):
        if format == "cookie":
            return self.session.cookies

        elif format == "dict":
            cookie_dict = {}
            for cookie in self.session.cookies:
                try:
                    name = cookie
                    value = self.session.cookies.get(cookie)
                    cookie_dict[name] = value
                except:
                    # Ошибка мульти-куки
                    pass
            return cookie_dict

        elif format == "str":
            cookie_lst = []
            for cookie in self.session.cookies:
                try:
                    name = cookie
                    value = self.session.cookies.get(cookie)
                    cookie_lst.append(f"{name}={value}")
                except:
                    # Ошибка мульти-куки
                    pass
            return ";".join(cookie_lst)

    def to_json(self):
        return json.loads(self.response.text)

    def get(self, url, proxy=None, headers=None, cookies=None, attempts=1, delay=2, raise_on_error=True) -> Response:
        res, proxy, headers, cookies = self.default_request_processing(proxy, headers, cookies, attempts)

        success = False

        # Попытки запроса
        for i in range(attempts):
            try:
                res = self.session.get(url, impersonate=self.impersonate, proxies=proxy, headers=headers,
                                       cookies=cookies)
                # Проверяем успешность запроса
                success = self.check(res)
            # Отлови ошибки RequestsError
            except RequestsError:
                res = Response(0, "", "", {}, {}, None)
                success = False

            if success:
                break

            # Пауза
            time.sleep(delay)

        # Очистка от старых методов
        self.applied_methods.clear()

        if not success and raise_on_error:
            raise Exception(f"Не удалось выполнить запрос ({self.last_check_error})")

        self.response = res
        return res

    async def aget(self, url, proxy=None, headers=None, cookies=None, attempts=1, delay=2,
                   raise_on_error=True) -> Response:
        res, proxy, headers, cookies = self.default_request_processing(proxy, headers, cookies, attempts)

        success = False

        for i in range(attempts):
            try:
                res = await self.session.get(url, impersonate=self.impersonate, proxies=proxy, headers=headers,
                                             cookies=cookies)
                success = self.check(res)
            except Exception:
                res = Response(0, "", "", {}, {}, None)
                success = False

            if success:
                break

            await asyncio.sleep(delay)

        self.applied_methods.clear()

        if not success and raise_on_error:
            raise Exception(f"Не удалось выполнить запрос ({self.last_check_error})")

        self.response = res
        return res

    def post(self, url, proxy=None, headers=None, cookies=None, data=None, json=None, attempts=1,
             delay=2, raise_on_error=True) -> Response:
        res, proxy, headers, cookies = self.default_request_processing(proxy, headers, cookies, attempts)

        args = {}
        if data is not None:
            args["data"] = data

        # Если json не пустой
        if json is not None:
            args["json"] = json

        success = False

        # Попытки запроса
        for i in range(attempts):
            try:
                res = self.session.post(url, impersonate=self.impersonate, proxies=proxy, headers=headers,
                                        cookies=cookies, **args)
                # Проверяем успешность запроса
                success = self.check(res)
            # Отлови ошибки RequestsError
            except RequestsError:
                res = Response(0, "", "", {}, {}, None)
                success = False

            if success:
                break

            # Пауза
            time.sleep(delay)

        # Очистка от старых методов
        self.applied_methods.clear()

        if not success and raise_on_error:
            raise Exception(f"Не удалось выполнить запрос ({self.last_check_error})")

        self.response = res
        return res
