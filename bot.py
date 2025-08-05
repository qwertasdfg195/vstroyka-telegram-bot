import asyncio
import os
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.filters import Command, Text
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Load environment variables from .env file
load_dotenv()

# Load configuration from environment variables
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")

# Validate required environment variables
if not TOKEN:
    raise ValueError("BOT_TOKEN environment variable is required")
if not ADMIN_ID:
    raise ValueError("ADMIN_ID environment variable is required")
if not SPREADSHEET_ID:
    raise ValueError("SPREADSHEET_ID environment variable is required")

try:
    ADMIN_ID = int(ADMIN_ID)
except ValueError:
    raise ValueError("ADMIN_ID must be a valid integer")

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/spreadsheets"]

# Initialize Google Sheets with error handling
try:
    creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(SPREADSHEET_ID).sheet1
except FileNotFoundError:
    print("Error: credentials.json file not found. Please ensure the Google Service Account credentials file exists.")
    sheet = None
except Exception as e:
    print(f"Error initializing Google Sheets: {e}")
    sheet = None

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

class Form(StatesGroup):
    size = State()
    style = State()
    material = State()
    idea = State()

@dp.message(Command("start"))
async def start(message: types.Message):
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📸 Готовые кухни")],
            [KeyboardButton(text="🧩 Собрать свою кухню")]
        ],
        resize_keyboard=True
    )
    await message.answer("Привет! Я бот Встройка Мебель.\nВыберите действие:", reply_markup=keyboard)

@dp.message(Text("📸 Готовые кухни"))
async def send_catalog(message: types.Message):
    try:
        with open("catalog.pdf", "rb") as pdf_file:
            await message.answer_document(pdf_file, caption="📘 Наш каталог кухонь")
    except FileNotFoundError:
        await message.answer("Извините, каталог временно недоступен. Обратитесь к администратору.")
    except Exception as e:
        print(f"Error sending catalog: {e}")
        await message.answer("Произошла ошибка при отправке каталога. Попробуйте позже.")

@dp.message(Text("🧩 Собрать свою кухню"))
async def start_form(message: types.Message, state: FSMContext):
    await message.answer("Укажите размеры кухни (пример: 2.5м × 2.0м):")
    await state.set_state(Form.size)

@dp.message(Form.size)
async def get_size(message: types.Message, state: FSMContext):
    await state.update_data(size=message.text)
    await message.answer("Какой стиль вам нравится? (классика, модерн, минимализм и т.д.)")
    await state.set_state(Form.style)

@dp.message(Form.style)
async def get_style(message: types.Message, state: FSMContext):
    await state.update_data(style=message.text)
    await message.answer("Какой материал предпочтителен? (МДФ, ЛДСП, массив и т.д.)")
    await state.set_state(Form.material)

@dp.message(Form.material)
async def get_material(message: types.Message, state: FSMContext):
    await state.update_data(material=message.text)
    await message.answer("Есть ли у вас идея или пожелания по дизайну?")
    await state.set_state(Form.idea)

@dp.message(Form.idea)
async def finish_form(message: types.Message, state: FSMContext):
    await state.update_data(idea=message.text)
    data = await state.get_data()

    summary = (
        f"🧾 Новая заявка:\n\n"
        f"📐 Размеры: {data['size']}\n"
        f"🎨 Стиль: {data['style']}\n"
        f"🪵 Материал: {data['material']}\n"
        f"💡 Идея: {data['idea']}\n"
        f"\nОт: @{message.from_user.username or 'Без username'}"
    )

    # Send notification to admin with error handling
    try:
        await bot.send_message(chat_id=ADMIN_ID, text=summary)
    except Exception as e:
        print(f"Error sending message to admin: {e}")

    # Save to Google Sheets with error handling
    if sheet is not None:
        try:
            now = datetime.now().strftime("%Y-%m-%d %H:%M")
            row = [now, message.from_user.username or "Без username", data['size'], data['style'], data['material'], data['idea']]
            sheet.append_row(row)
        except Exception as e:
            print(f"Error saving to Google Sheets: {e}")
    else:
        print("Warning: Google Sheets not available, data not saved to spreadsheet")

    await message.answer("Спасибо! Ваша заявка отправлена.")
    await state.clear()

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())