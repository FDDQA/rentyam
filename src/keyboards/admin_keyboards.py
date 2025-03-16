from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def get_admin_dash_kb():
    buttons = [
        [InlineKeyboardButton(text='Добавить рекламу', callback_data="add_ad")],
        [InlineKeyboardButton(text='Удалить рекламу', callback_data="delete_ad")],
        [InlineKeyboardButton(text='Отправить уведомление всем', callback_data="send_notification")],
        [InlineKeyboardButton(text='Сгенерировать ссылку', callback_data="generate_link")],
        [InlineKeyboardButton(text='Рефанд', callback_data="refund")]
    ]
    admin_dash_kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    return admin_dash_kb
