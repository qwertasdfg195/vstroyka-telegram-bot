import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.filters import Command, Text
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# === НАСТРОЙКИ ===
TOKEN = "8327997405:AAE32BUJEImAtfYmPlyxmRAB8fcKRnC-Vh0" # ← твой токен
ADMIN_ID = 648338940 # ← твой Telegram ID
SPREADSHEET_ID = "1KiICzYA44y9Y-emnUiA53VOt2jW0h_8FrdOP-DLRR6Y"

# === Google Sheets ===
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/spreadsheets"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds)
sheet = client.open_by_key(SPREADSHEET_ID).sheet1

# === Telegram Bot ===
bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

class Form(StatesGroup):
    size = State()
    style = State()
    material = State()
    idea = State()

@dp.message(Command("start"))
async def start(message: types.Message):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("📸 Готовые кухни", "🧩 Собрать свою кухню")
    await message.answer("Привет! Я бот Встройка Мебель.\nВыберите действие:", reply_markup=keyboard)

@dp.message(Text("📸 Готовые кухни"))
async def send_catalog(message: types.Message):
    with open("catalog.pdf", "rb") as pdf_file:
        await message.answer_document(pdf_file, caption="📘 Наш каталог кухонь")

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

    # Отправка админу
    await bot.send_message(chat_id=ADMIN_ID, text=summary)

    # Сохранение в таблицу
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    row = [now, message.from_user.username or "Без username", data['size'], data['style'], data['material'], data['idea']]
    sheet.append_row(row)

    await message.answer("Спасибо! Ваша заявка отправлена.")
    await state.clear()

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
