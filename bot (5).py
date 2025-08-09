import asyncio
import os

from aiogram import Bot, Dispatcher, types, F
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, FSInputFile
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.filters import Command
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")

if not TOKEN or not ADMIN_ID or not SPREADSHEET_ID:
    raise ValueError(
        "BOT_TOKEN, ADMIN_ID and SPREADSHEET_ID must be provided in environment variables"
    )

ADMIN_ID = int(ADMIN_ID)

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]
try:
    credentials = ServiceAccountCredentials.from_json_keyfile_name(
        "credentials.json", scope
    )
    client = gspread.authorize(credentials)
    sheet = client.open_by_key(SPREADSHEET_ID).sheet1
except Exception as e:
    print(f"Failed to connect to Google Sheets: {e}")
    sheet = None

# ====== Кнопки ======
BACK_BTN = "🔙 В меню"

# Состояния формы (добавил shape)
class Form(StatesGroup):
    size = State()
    shape = State()      # NEW
    style = State()
    material = State()
    idea = State()

# Главное меню
@dp.message(Command("start"))
async def start_form(message: types.Message, state: FSMContext):
    await state.clear()
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(
        KeyboardButton(text="📸 Посмотреть каталог"),
        KeyboardButton(text="🧩 Собрать свою кухню")
    )
    await message.answer("Привет! Давайте подберем кухню.\nВыберите действие:", reply_markup=keyboard)

# Кнопка вернуться в меню
@dp.message(F.text == BACK_BTN)
async def back_to_menu(message: types.Message, state: FSMContext):
    await state.clear()
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(
        KeyboardButton(text="📸 Посмотреть каталог"),
        KeyboardButton(text="🧩 Собрать свою кухню")
    )
    await message.answer("Вы вернулись в главное меню. Что хотите сделать?", reply_markup=keyboard)

# Отправка каталога
@dp.message(F.text == "📸 Посмотреть каталог")
async def send_catalog(message: types.Message):
    try:
        file = FSInputFile("catalog.pdf")
        await message.answer_document(file, caption="📘 Вот наш каталог кухонь.")
    except FileNotFoundError:
        await message.answer("Файл каталога не найден.")
    except Exception as e:
        print(f"Ошибка при отправке PDF: {e}")
        await message.answer("⚠️ Произошла ошибка при отправке каталога.")

# Запуск формы
@dp.message(F.text == "🧩 Собрать свою кухню")
async def start_custom_kitchen(message: types.Message, state: FSMContext):
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=BACK_BTN)]],
        resize_keyboard=True
    )
    await message.answer("Укажите размеры кухни (в см, ширина × высота):", reply_markup=kb)
    await state.set_state(Form.size)

@dp.message(Form.size)
async def process_size(message: types.Message, state: FSMContext):
    if message.text == BACK_BTN:
        return await back_to_menu(message, state)

    await state.update_data(size=message.text)
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Прямая")],
            [KeyboardButton(text="Угловая")],
            [KeyboardButton(text="П-образная")],
            [KeyboardButton(text=BACK_BTN)]
        ],
        resize_keyboard=True
    )
    await message.answer("Выберите форму кухни:", reply_markup=kb)
    await state.set_state(Form.shape)

@dp.message(Form.shape)
async def process_shape(message: types.Message, state: FSMContext):
    if message.text == BACK_BTN:
        return await back_to_menu(message, state)

    await state.update_data(shape=message.text)
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Современный")],
            [KeyboardButton(text="Классический")],
            [KeyboardButton(text="Минимализм")],
            [KeyboardButton(text=BACK_BTN)]
        ],
        resize_keyboard=True
    )
    await message.answer("Выберите стиль кухни:", reply_markup=kb)
    await state.set_state(Form.style)

@dp.message(Form.style)
async def process_style(message: types.Message, state: FSMContext):
    if message.text == BACK_BTN:
        return await back_to_menu(message, state)

    await state.update_data(style=message.text)
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Дерево")],
            [KeyboardButton(text="Акрил")],
            [KeyboardButton(text="Пластик")],
            [KeyboardButton(text="Не знаю")],   # NEW
            [KeyboardButton(text=BACK_BTN)]
        ],
        resize_keyboard=True
    )
    await message.answer("Выберите материал:", reply_markup=kb)
    await state.set_state(Form.material)

@dp.message(Form.material)
async def process_material(message: types.Message, state: FSMContext):
    if message.text == BACK_BTN:
        return await back_to_menu(message, state)

    await state.update_data(material=message.text)
    kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text=BACK_BTN)]], resize_keyboard=True)
    await message.answer("Есть ли у вас идеи, пожелания или референсы?", reply_markup=kb)
    await state.set_state(Form.idea)

@dp.message(Form.idea)
async def finish_form(message: types.Message, state: FSMContext):
    if message.text == BACK_BTN:
        return await back_to_menu(message, state)

    await state.update_data(idea=message.text)
    data = await state.get_data()

    summary = (
        f"📥 Новая заявка:\n\n"
        f"📏 Размеры: {data.get('size')}\n"
        f"🧩 Форма: {data.get('shape')}\n"
        f"🎨 Стиль: {data.get('style')}\n"
        f"🧱 Материал: {data.get('material')}\n"
        f"💡 Идея: {data.get('idea')}\n"
        f"\nОт: @{message.from_user.username or 'Без username'}"
    )

    await bot.send_message(chat_id=ADMIN_ID, text=summary)

    now = datetime.now().strftime("%%Y-%m-%d %%H:%M")
    # добавил 'shape' в таблицу
    row = [
        now,
        message.from_user.username or "Без username",
        data.get("size"),
        data.get("shape"),
        data.get("style"),
        data.get("material"),
        data.get("idea"),
    ]

    if sheet:
        try:
            sheet.append_row(row)
        except Exception as e:
            print(f"Ошибка записи в Google Sheets: {e}")
    else:
        print("Google Sheets не настроен, пропуск записи заявки")

    await message.answer("Спасибо! Ваша заявка отправлена.")
    await state.clear()
    # возврат в меню после отправки
    await start_form(message, state)

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
