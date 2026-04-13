import asyncio
import os
import json
from datetime import datetime

ADMIN_ID = 8183757534

import gspread
from google.oauth2.service_account import Credentials

from aiogram import Bot, Dispatcher
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import CommandStart

TOKEN = "8592854204:AAEI939vRdiyYEQPzQqoOsxrugOSJU8vzD0"

scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

creds_json = os.getenv("GOOGLE_CREDENTIALS")

if not creds_json:
    raise Exception("GOOGLE_CREDENTIALS не найден")

creds_dict = json.loads(creds_json)

creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
client = gspread.authorize(creds)

sheet = client.open_by_key("1KUxWRxmHeCPB1xtTzs1AlwVTggfrqa6kyVm1pijy6mg").sheet1

bot = Bot(token=TOKEN)
dp = Dispatcher()

break_data = {}

keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Начать перерыв")],
        [KeyboardButton(text="Закончить перерыв")]
    ],
    resize_keyboard=True
)

@dp.message(CommandStart())
async def start(message: Message):
    await message.answer("Бот для учета перерывов", reply_markup=keyboard)

@dp.message()
async def handle(message: Message):
    user_id = message.from_user.id

    if message.text == "Начать перерыв":
        break_data[user_id] = datetime.now()
        
        await message.answer("Перерыв начат")

    await bot.send_message(
        ADMIN_ID,
        f"Начал перерыв:\n"
        f"{message.from_user.full_name}\n"
        f"@{message.from_user.username if message.from_user.username else 'без username'}"
    )

    elif message.text == "Закончить перерыв":

        if user_id not in break_data:
            await message.answer("Нет активного перерыва.")
            return

        now = datetime.now()
        start_time = break_data[user_id]
        duration = now - start_time
        minutes = int(duration.total_seconds() // 60)

        sheet.append_row([
            now.strftime("%d.%m.%Y"),
            message.from_user.full_name,
            message.from_user.username or "без username",
            start_time.strftime("%H:%M:%S"),
            now.strftime("%H:%M:%S"),
            minutes
        ])

await bot.send_message(
    ADMIN_ID,
    f"Закончил перерыв:\n"
    f"{message.from_user.full_name}\n"
    f"@{message.from_user.username if message.from_user.username else 'без username'}\n"
    f"Длительность: {minutes} мин"
)

        del break_data[user_id]

        await message.answer(
            f"Перерыв завершён\n"
            f"Длительность: {minutes} мин"
        )

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
