from aiogram.types import BotCommand
from aiogram import Bot

# кнопка меню
async def set_bot_commands(bot: Bot):
    commands = [
        BotCommand(command="menu", description="Menu"),
        BotCommand(command="premium", description="Premium"),
        BotCommand(command="support", description="Support and collaboration"),
        BotCommand(command="stop", description="Stop"),
    ]
    await bot.set_my_commands(commands)
