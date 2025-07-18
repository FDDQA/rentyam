# RentyAm — Telegram-бот для поиска квартир в Ереване

RentyAm — бот для аренды жилья в Ереване с интуитивным интерфейсом и премиум-функциями.

Стек: Python, Redis, MySQL, docker

## Основные команды
- `/menu` — главное меню
- `/premium` — покупка премиум-подписки
- `/support` — контакты поддержки
- `/stop` — отключение уведомлений

## Особенности
- Полноценный интерфейс через **интерактивные кнопки** (см. [keyboards.py](https://github.com/FDDQA/rentyam/blob/main/src/keyboards/keyboards.py))
- **Премиум** (оплата через Telegram Stars)
- **Админ-панель** с функциями:
  - Управление рекламой
  - Рефанды платежей
  - Рассылка уведомлений
  - Настройка показа рекламы (по времени/количеству просмотров)

## Техническая информация
- Платежная система: Telegram Stars (раньше была ЮKassa)
- Премиум доступен как разовая покупка на срок (без подписки). В конце будет нотиф.

## Установка
Лучше не надо.
