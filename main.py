import asyncio
import json
import os
from datetime import datetime, time, timedelta, timezone
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

# Ваш токен бота
TOKEN = "8919020879:AAGx2RUGnlAZCH8iXARp3iibNu8jXOfNA8M"
DB_FILE = "user_dates.json"

# Начальная дата по умолчанию
DEFAULT_DATE_STR = "24.06.2026"

# Часовой пояс МСК+3 (UTC+6)
TARGET_TZ = timezone(timedelta(hours=6))

# Время отправки: 00:00 по местному времени (МСК+3)
NOTIFICATION_TIME = time(0, 0)

bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- Работа с хранилищем (JSON) ---

def load_data() -> dict:
    if not os.path.exists(DB_FILE):
        return {}
    with open(DB_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}

def save_user_date(user_id: int, date_str: str):
    data = load_data()
    data[str(user_id)] = date_str
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def get_user_date(user_id: int) -> str:
    data = load_data()
    return data.get(str(user_id), DEFAULT_DATE_STR)

def get_days_word(n: int) -> str:
    n = abs(n)
    if n % 10 == 1 and n % 100 != 11:
        return "день"
    elif 2 <= n % 10 <= 4 and (n % 100 < 10 or n % 100 >= 20):
        return "дня"
    else:
        return "дней"

def calculate_message(saved_date_str: str) -> str:
    """Расчет дней с учетом местного часового пояса"""
    start_date = datetime.strptime(saved_date_str, "%d.%m.%Y")
    
    # Получаем текущую дату по часовому поясу МСК+3
    today = datetime.now(TARGET_TZ).replace(tzinfo=None)
    
    delta_days = (today - start_date).days
    days_word = get_days_word(delta_days)

    return f"привет, киса, сегодня нам {delta_days} {days_word}"

# --- Фоновая рассылка в 00:00 по МСК+3 ---

async def daily_scheduler():
    while True:
        # Текущее время в поясе МСК+3
        now_tz = datetime.now(TARGET_TZ)
        
        # Ближайшие 00:00 по местному времени
        target_time = datetime.combine(now_tz.date(), NOTIFICATION_TIME, tzinfo=TARGET_TZ)
        
        if now_tz >= target_time:
            target_time += timedelta(days=1)

        # Считаем задержку в секундах до полуночи по местному времени
        sleep_seconds = (target_time - now_tz).total_seconds()
        await asyncio.sleep(sleep_seconds)

        data = load_data()
        for user_id_str, saved_date_str in data.items():
            try:
                user_id = int(user_id_str)
                msg_text = calculate_message(saved_date_str)
                await bot.send_message(chat_id=user_id, text=msg_text)
                await asyncio.sleep(0.05)
            except Exception as e:
                print(f"Ошибка отправки пользователю {user_id_str}: {e}")

# --- Обработчики команд ---

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    
    data = load_data()
    if str(user_id) not in data:
        save_user_date(user_id, DEFAULT_DATE_STR)

    await message.answer(
        f"Привет Кошечка❤️! Я решил сделать такую мелочь специально для тебя) Дата отсчета установлена на **{DEFAULT_DATE_STR}**.\n\n"
        f"• Отправь команду /date, чтобы получить наше с тобой число💕.\n"
        f"• Каждую полночь в **00:00 по нашему времени.** я буду присылать его автоматически.\n"
        f"• Если нужно поменять дату, просто напиши новую (например: `24.06.2026`).",
        parse_mode="Markdown"
    )

@dp.message(Command("date", "days"))
async def cmd_date(message: types.Message):
    user_date_str = get_user_date(message.from_user.id)
    text = calculate_message(user_date_str)
    await message.answer(text)

@dp.message()
async def process_date_input(message: types.Message):
    text = message.text.strip()
    try:
        parsed_date = datetime.strptime(text, "%d.%m.%Y")
        formatted_date = parsed_date.strftime("%d.%m.%Y")

        save_user_date(message.from_user.id, formatted_date)

        await message.answer(
            f"✅ Новая дата **{formatted_date}** сохранена!\n"
            f"Теперь по команде /date и в 00:00 (МСК+3) будет считаться отсчет от неё.",
            parse_mode="Markdown"
        )
    except ValueError:
        await message.answer(
            "❌ Неверный формат даты.\n"
            "Отправь дату в формате `ДД.ММ.ГГГГ` (например: `24.06.2026`).",
            parse_mode="Markdown"
        )

# --- Запуск ---

async def main():
    print("Бот успешно запущен и работает по часовому поясу МСК+3...")
    asyncio.create_task(daily_scheduler())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
