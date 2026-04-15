import asyncio
import os
import json
from datetime import datetime

from aiogram import Bot, Dispatcher
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import CommandStart

import gspread
from google.oauth2.service_account import Credentials

# НАСТРОЙКИ
ADMIN_ID = 8183757534
OWNER_ID = 1826030998
TEAM_NAME = "Radisson"
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
waiting_time = set()

keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Начать перерыв")],
        [KeyboardButton(text="Закончить перерыв")]
    ],
    resize_keyboard=True
)

@dp.message(CommandStart())
async def start(message: Message):
    await message.answer("Бот учета перерывов", reply_markup=keyboard)

# КОНТРОЛЬ ПЕРЕРЫВА
async def break_control(user_id: int, minutes: int, name: str, username: str | None):
    start_time = datetime.now()
    warned_5min = False
    last_overdue_sent = 0

    while user_id in break_data:
        now = datetime.now()
        elapsed = (now - start_time).total_seconds() / 60

        # За 5 минут до конца
        if not warned_5min and minutes > 5 and elapsed >= (minutes - 5):
            warned_5min = True
            await bot.send_message(user_id, "⏳ До конца перерыва осталось 5 минут")

        # Каждую минуту после окончания
        overdue = int(elapsed - minutes)

        if overdue > 0 and overdue != last_overdue_sent:
            last_overdue_sent = overdue

            text = (
                f"[{TEAM_NAME}]\n"
                f"🚨 ОПОЗДАНИЕ\n"
                f"{name}\n"
                f"@{username if username else 'без username'}\n"
                f"⏱ +{overdue} мин"
            )

            # Админу и тебе
            await bot.send_message(ADMIN_ID, text)
            await bot.send_message(OWNER_ID, text)

            # Переводчику
            await bot.send_message(
                user_id,
                f"🚨 Ты опаздываешь уже на {overdue} мин! Срочно возвращайся"
            )

        await asyncio.sleep(10)

@dp.message()
async def handle(message: Message):
    user_id = message.from_user.id

    if message.text == "Начать перерыв":
        waiting_time.add(user_id)
        await message.answer("Напиши длительность (максимум 30 минут)")

    elif user_id in waiting_time:
        if not message.text.isdigit():
            await message.answer("Введи число")
            return

        minutes = int(message.text)

        if minutes > 30:
            await message.answer("Максимум 30 минут")
            return

        if minutes <= 0:
            await message.answer("Некорректное значение")
            return

        waiting_time.remove(user_id)
        break_data[user_id] = datetime.now()

        await message.answer(f"Перерыв начат на {minutes} мин", reply_markup=keyboard)

        text = (
            f"[{TEAM_NAME}]\n"
            f"🟡 Начал перерыв ({minutes} мин)\n"
            f"{message.from_user.full_name}\n"
            f"@{message.from_user.username if message.from_user.username else 'без username'}"
        )

        await bot.send_message(ADMIN_ID, text)
        await bot.send_message(OWNER_ID, text)

        asyncio.create_task(
            break_control(
                user_id,
                minutes,
                message.from_user.full_name,
                message.from_user.username
            )
        )

    elif message.text == "Закончить перерыв":
        if user_id not in break_data:
            await message.answer("Нет активного перерыва")
            return

        start_time = break_data[user_id]
        now = datetime.now()
        minutes = int((now - start_time).total_seconds() // 60)

        sheet.append_row([
            now.strftime("%d.%m.%Y"),
            message.from_user.full_name,
            message.from_user.username or "без username",
            start_time.strftime("%H:%M:%S"),
            now.strftime("%H:%M:%S"),
            minutes
        ])

        text = (
            f"[{TEAM_NAME}]\n"
            f"🟢 Закончил перерыв\n"
            f"{message.from_user.full_name}\n"
            f"⏱ {minutes} мин"
        )

        await bot.send_message(ADMIN_ID, text)
        await bot.send_message(OWNER_ID, text)

        del break_data[user_id]

        await message.answer("Перерыв завершён", reply_markup=keyboard)

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
