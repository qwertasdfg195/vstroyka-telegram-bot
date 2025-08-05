import asyncio
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, FSInputFile
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.filters import Command, Text
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv

# === Загрузка переменных окружения ===
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")

if not TOKEN or not ADMIN_ID or not SPREADSHEET_ID:
    raise ValueError("Не заданы переменные окружения: BOT_TOKEN, ADMIN_ID или SPREADSHEET_ID")

try:
    ADMIN_ID = int(ADMIN_ID)
except ValueError:
    raise ValueError("ADMIN_ID должен быть числом")

# === Google Sheets ===
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
try:
    creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(SPREADSHEET_ID).worksheet("Лист1")
except Exception as e:
    print(f"Ошибка подключения к Google Sheets: {e}")
    sheet = None

# === Инициализация бота ===
bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# === Состояния ===
class Form(StatesGroup):
    size = State()
    style = State()
    material = State()
    idea = State()

# === Стартовое меню ===
@dp.message(Command("start"))
async def start(message: types.Message):
    keyboard = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="🌟 Готовые кухни")],
        [KeyboardButton(text="🌱 Собрать свою кухню")]
    ], resize_keyboard=True)
    await message.answer("Привет! Я бот Встройка Мебель.\nВыберите действие:", reply_markup=keyboard)

# === Отправка PDF каталога ===
@dp.message(Text("🌟 Готовые кухни"))
async def send_catalog(message: types.Message):
    try:
        file = FSInputFile("catalog.pdf")
        await message.answer_document(file, caption="📘 Наш каталог кухонь")
    except FileNotFoundError:
        await message.answer("Файл каталога не найден.")
    except Exception as e:
        print(f"Ошибка отправки каталога: {e}")
        await message.answer("Произошла ошибка при отправке каталога. Попробуйте позже.")

# === Запуск формы заявки ===
@dp.message(Text("🌱 Собрать свою кухню"))
async def start_form(message: types.Message, state: FSMContext):
    await message.answer("Укажите размеры (в см, ширина × высота):")
    await state.set_state(Form.size)

@dp.message(Form.size)
async def process_size(message: types.Message, state: FSMContext):
    await state.update_data(size=message.text)
    keyboard = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="Современный")],
        [KeyboardButton(text="Классический")],
        [KeyboardButton(text="Минимализм")]
    ], resize_keyboard=True)
    await message.answer("Выберите стиль кухни:", reply_markup=keyboard)
    await state.set_state(Form.style)

@dp.message(Form.style)
async def process_style(message: types.Message, state: FSMContext):
    await state.update_data(style=message.text)
    keyboard = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="МДФ")],
        [KeyboardButton(text="ДСП")],
        [KeyboardButton(text="Шпон")]
    ], resize_keyboard=True)
    await message.answer("Выберите материал:", reply_markup=keyboard)
    await state.set_state(Form.material)

@dp.message(Form.material)
async def process_material(message: types.Message, state: FSMContext):
    await state.update_data(material=message.text)
    await message.answer("Есть ли у вас идеи, пожелания или референсы?")
    await state.set_state(Form.idea)

@dp.message(Form.idea)
async def finish_form(message: types.Message, state: FSMContext):
    await state.update_data(idea=message.text)
    data = await state.get_data()

    summary = (
        f"📥 Новая заявка:\n\n"
        f"📍 Размеры: {data['size']}\n"
        f"🎨 Стиль: {data['style']}\n"
        f"🧱 Материал: {data['material']}\n"
        f"💡 Идея: {data['idea']}\n"
        f"\nОт: @{message.from_user.username or 'Без username'}"
    )

    try:
        await bot.send_message(chat_id=ADMIN_ID, text=summary)
    except Exception as e:
        print(f"Ошибка отправки админу: {e}")

    if sheet:
        try:
            now = datetime.now().strftime("%Y-%m-%d %H:%M")
            row = [now, message.from_user.username or "Без username", data['size'], data['style'], data['material'], data['idea']]
            sheet.append_row(row)
        except Exception as e:
            print(f"Ошибка записи в Google Sheets: {e}")
    else:
        print("Google Sheets недоступен, данные не записаны")

    await message.answer("Спасибо! Ваша заявка отправлена.")
    await state.clear()

# === Запуск ===
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())