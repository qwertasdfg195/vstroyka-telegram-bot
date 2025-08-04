import logging
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text, Command
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils import executor
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# === НАСТРОЙКИ ===
TOKEN = "8327997405:AAE32BUJEImAtfYmPlyxmRAB8fcKRnC-Vh0"
ADMIN_ID = 648338940
SPREADSHEET_ID = "1KiICzYA44y9Y-emnUiA53VOt2jW0h_8FrdOP-DLRR6Y"

# === Google Sheets ===
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/spreadsheets"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds)
sheet = client.open_by_key(SPREADSHEET_ID).sheet1

# === Telegram Bot ===
bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)
logging.basicConfig(level=logging.INFO)

class Form(StatesGroup):
    size = State()
    style = State()
    material = State()
    idea = State()

@dp.message_handler(Command("start"))
async def start(message: types.Message):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("📸 Готовые кухни", "🧩 Собрать свою кухню")
    await message.answer("Привет! Я бот Встройка Мебель.\nВыберите действие:", reply_markup=keyboard)

@dp.message_handler(Text(equals="📸 Готовые кухни"))
async def send_catalog(message: types.Message):
    with open("catalog.pdf", "rb") as pdf_file:
        await message.answer_document(pdf_file, caption="📘 Наш каталог кухонь")

@dp.message_handler(Text(equals="🧩 Собрать свою кухню"))
async def start_form(message: types.Message):
    await Form.size.set()
    await message.answer("Укажите размеры кухни (пример: 2.5м × 2.0м):")

@dp.message_handler(state=Form.size)
async def get_size(message: types.Message, state: FSMContext):
    await state.update_data(size=message.text)
    await Form.style.set()
    await message.answer("Какой стиль вам нравится? (классика, модерн, минимализм и т.д.)")

@dp.message_handler(state=Form.style)
async def get_style(message: types.Message, state: FSMContext):
    await state.update_data(style=message.text)
    await Form.material.set()
    await message.answer("Какой материал предпочтителен? (МДФ, ЛДСП, массив и т.д.)")

@dp.message_handler(state=Form.material)
async def get_material(message: types.Message, state: FSMContext):
    await state.update_data(material=message.text)
    await Form.idea.set()
    await message.answer("Есть ли у вас идея или пожелания по дизайну?")

@dp.message_handler(state=Form.idea)
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

    await bot.send_message(chat_id=ADMIN_ID, text=summary)

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    row = [now, message.from_user.username or "Без username", data['size'], data['style'], data['material'], data['idea']]
    sheet.append_row(row)

    await message.answer("Спасибо! Ваша заявка отправлена.")
    await state.finish()

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
