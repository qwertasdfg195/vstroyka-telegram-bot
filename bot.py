import asyncio
import os
import logging
from typing import Optional
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, FSInputFile, ReplyKeyboardRemove
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.filters import Command, Text
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv

# === Настройка логирования ===
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

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
sheet: Optional[gspread.Worksheet] = None

def init_google_sheets():
    """Инициализация Google Sheets"""
    global sheet
    try:
        creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
        client = gspread.authorize(creds)
        sheet = client.open_by_key(SPREADSHEET_ID).worksheet("Лист1")
        logger.info("Google Sheets успешно подключены")
        
        # Проверяем и создаем заголовки если их нет
        try:
            headers = sheet.row_values(1)
            if not headers:
                sheet.append_row(["Дата", "Username", "Размеры", "Стиль", "Материал", "Идеи"])
                logger.info("Заголовки таблицы созданы")
        except Exception as e:
            logger.warning(f"Не удалось проверить заголовки: {e}")
            
    except FileNotFoundError:
        logger.error("Файл credentials.json не найден")
        sheet = None
    except Exception as e:
        logger.error(f"Ошибка подключения к Google Sheets: {e}")
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
    confirmation = State()

# === Клавиатуры ===
def get_main_keyboard():
    """Главная клавиатура"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🌟 Готовые кухни")],
            [KeyboardButton(text="🌱 Собрать свою кухню")],
            [KeyboardButton(text="📞 Контакты"), KeyboardButton(text="ℹ️ О нас")]
        ],
        resize_keyboard=True
    )

def get_style_keyboard():
    """Клавиатура выбора стиля"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Современный"), KeyboardButton(text="Классический")],
            [KeyboardButton(text="Минимализм"), KeyboardButton(text="Прованс")],
            [KeyboardButton(text="🔙 Назад"), KeyboardButton(text="🏠 Главное меню")]
        ],
        resize_keyboard=True
    )

def get_material_keyboard():
    """Клавиатура выбора материала"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="МДФ"), KeyboardButton(text="ДСП")],
            [KeyboardButton(text="Шпон"), KeyboardButton(text="Массив дерева")],
            [KeyboardButton(text="🔙 Назад"), KeyboardButton(text="🏠 Главное меню")]
        ],
        resize_keyboard=True
    )

def get_confirmation_keyboard():
    """Клавиатура подтверждения"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="✅ Отправить заявку")],
            [KeyboardButton(text="✏️ Изменить"), KeyboardButton(text="❌ Отменить")]
        ],
        resize_keyboard=True
    )

def get_back_keyboard():
    """Клавиатура с кнопкой назад"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔙 Назад"), KeyboardButton(text="🏠 Главное меню")]
        ],
        resize_keyboard=True
    )

# === Валидация данных ===
def validate_size(size_text: str) -> bool:
    """Проверка корректности размеров"""
    # Простая проверка на наличие цифр
    return any(char.isdigit() for char in size_text) and len(size_text.strip()) > 0

# === Обработчики команд ===
@dp.message(Command("start"))
async def start(message: types.Message, state: FSMContext):
    await state.clear()
    user_name = message.from_user.first_name or "друг"
    welcome_text = (
        f"Привет, {user_name}! 👋\n\n"
        f"Я бот компании «Встройка Мебель».\n"
        f"Помогу вам выбрать идеальную кухню!\n\n"
        f"Выберите действие:"
    )
    await message.answer(welcome_text, reply_markup=get_main_keyboard())
    logger.info(f"Пользователь {message.from_user.id} начал работу с ботом")

@dp.message(Command("help"))
async def help_command(message: types.Message):
    help_text = (
        "🤖 Команды бота:\n\n"
        "/start - Главное меню\n"
        "/help - Справка\n"
        "/cancel - Отменить текущее действие\n\n"
        "📋 Возможности:\n"
        "• Просмотр каталога готовых кухонь\n"
        "• Создание заявки на индивидуальную кухню\n"
        "• Получение контактной информации\n"
        "• Информация о компании"
    )
    await message.answer(help_text)

@dp.message(Command("cancel"))
async def cancel_handler(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is None:
        await message.answer("Нечего отменять.", reply_markup=get_main_keyboard())
        return
    
    await state.clear()
    await message.answer("Действие отменено.", reply_markup=get_main_keyboard())

# === Главное меню ===
@dp.message(Text("🏠 Главное меню"))
async def main_menu(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Главное меню:", reply_markup=get_main_keyboard())

@dp.message(Text("📞 Контакты"))
async def contacts(message: types.Message):
    contacts_text = (
        "📞 Наши контакты:\n\n"
        "🏢 ООО «Встройка Мебель»\n"
        "📱 Телефон: +7 (XXX) XXX-XX-XX\n"
        "📧 Email: info@vstroyka-mebel.ru\n"
        "🌐 Сайт: www.vstroyka-mebel.ru\n"
        "📍 Адрес: г. Москва, ул. Примерная, д. 1\n\n"
        "🕒 Режим работы:\n"
        "Пн-Пт: 9:00 - 18:00\n"
        "Сб: 10:00 - 16:00\n"
        "Вс: выходной"
    )
    await message.answer(contacts_text)

@dp.message(Text("ℹ️ О нас"))
async def about_us(message: types.Message):
    about_text = (
        "ℹ️ О компании «Встройка Мебель»:\n\n"
        "🏆 Более 10 лет на рынке кухонной мебели\n"
        "👥 Команда профессиональных дизайнеров\n"
        "🔧 Собственное производство\n"
        "✅ Гарантия качества 2 года\n"
        "🚚 Доставка и сборка по всей области\n"
        "💰 Рассрочка без переплат\n\n"
        "Мы создаем кухни вашей мечты! 🌟"
    )
    await message.answer(about_text)

# === Отправка PDF каталога ===
@dp.message(Text("🌟 Готовые кухни"))
async def send_catalog(message: types.Message):
    try:
        file = FSInputFile("catalog.pdf")
        await message.answer_document(
            file, 
            caption="📘 Наш каталог готовых кухонь\n\n"
                   "Здесь вы найдете популярные модели с фиксированными размерами и ценами.\n"
                   "Для заказа свяжитесь с нами по контактам из меню!"
        )
        logger.info(f"Каталог отправлен пользователю {message.from_user.id}")
    except FileNotFoundError:
        await message.answer(
            "📄 Каталог временно недоступен.\n"
            "Свяжитесь с нами для получения актуальной информации о готовых кухнях.",
            reply_markup=get_main_keyboard()
        )
        logger.error("Файл catalog.pdf не найден")
    except Exception as e:
        await message.answer(
            "Произошла ошибка при отправке каталога. Попробуйте позже.",
            reply_markup=get_main_keyboard()
        )
        logger.error(f"Ошибка отправки каталога: {e}")

# === Форма заявки ===
@dp.message(Text("🌱 Собрать свою кухню"))
async def start_form(message: types.Message, state: FSMContext):
    await message.answer(
        "🏗️ Создаем вашу идеальную кухню!\n\n"
        "📏 Укажите размеры кухни:\n"
        "(например: 3м × 2.5м или 300см × 250см)",
        reply_markup=get_back_keyboard()
    )
    await state.set_state(Form.size)

@dp.message(Form.size)
async def process_size(message: types.Message, state: FSMContext):
    if message.text in ["🔙 Назад", "🏠 Главное меню"]:
        await handle_navigation(message, state)
        return
    
    if not validate_size(message.text):
        await message.answer(
            "❌ Пожалуйста, укажите размеры корректно.\n"
            "Например: 3м × 2.5м или 300см × 250см",
            reply_markup=get_back_keyboard()
        )
        return
    
    await state.update_data(size=message.text)
    await message.answer(
        "🎨 Выберите стиль кухни:",
        reply_markup=get_style_keyboard()
    )
    await state.set_state(Form.style)

@dp.message(Form.style)
async def process_style(message: types.Message, state: FSMContext):
    if message.text in ["🔙 Назад", "🏠 Главное меню"]:
        await handle_navigation(message, state)
        return
    
    valid_styles = ["Современный", "Классический", "Минимализм", "Прованс"]
    if message.text not in valid_styles:
        await message.answer(
            "❌ Пожалуйста, выберите стиль из предложенных вариантов:",
            reply_markup=get_style_keyboard()
        )
        return
    
    await state.update_data(style=message.text)
    await message.answer(
        "🧱 Выберите материал фасадов:",
        reply_markup=get_material_keyboard()
    )
    await state.set_state(Form.material)

@dp.message(Form.material)
async def process_material(message: types.Message, state: FSMContext):
    if message.text in ["🔙 Назад", "🏠 Главное меню"]:
        await handle_navigation(message, state)
        return
    
    valid_materials = ["МДФ", "ДСП", "Шпон", "Массив дерева"]
    if message.text not in valid_materials:
        await message.answer(
            "❌ Пожалуйста, выберите материал из предложенных вариантов:",
            reply_markup=get_material_keyboard()
        )
        return
    
    await state.update_data(material=message.text)
    await message.answer(
        "💡 Расскажите о ваших пожеланиях:\n\n"
        "• Цветовые предпочтения\n"
        "• Особые требования\n"
        "• Бюджет\n"
        "• Сроки выполнения\n\n"
        "Или напишите \"нет\", если особых пожеланий нет.",
        reply_markup=get_back_keyboard()
    )
    await state.set_state(Form.idea)

@dp.message(Form.idea)
async def process_idea(message: types.Message, state: FSMContext):
    if message.text in ["🔙 Назад", "🏠 Главное меню"]:
        await handle_navigation(message, state)
        return
    
    await state.update_data(idea=message.text)
    data = await state.get_data()
    
    # Показываем сводку для подтверждения
    summary = (
        "📋 Проверьте вашу заявку:\n\n"
        f"📏 Размеры: {data['size']}\n"
        f"🎨 Стиль: {data['style']}\n"
        f"🧱 Материал: {data['material']}\n"
        f"💡 Пожелания: {data['idea']}\n\n"
        "Все верно?"
    )
    
    await message.answer(summary, reply_markup=get_confirmation_keyboard())
    await state.set_state(Form.confirmation)

@dp.message(Form.confirmation)
async def process_confirmation(message: types.Message, state: FSMContext):
    if message.text == "✅ Отправить заявку":
        await send_application(message, state)
    elif message.text == "✏️ Изменить":
        await message.answer(
            "Какой параметр хотите изменить?\n"
            "Начните заново с размеров:",
            reply_markup=get_back_keyboard()
        )
        await state.set_state(Form.size)
    elif message.text == "❌ Отменить":
        await state.clear()
        await message.answer(
            "Заявка отменена.",
            reply_markup=get_main_keyboard()
        )
    else:
        await message.answer(
            "Пожалуйста, выберите действие:",
            reply_markup=get_confirmation_keyboard()
        )

async def send_application(message: types.Message, state: FSMContext):
    """Отправка заявки администратору и запись в Google Sheets"""
    data = await state.get_data()
    user = message.from_user
    
    # Формируем сообщение для админа
    admin_summary = (
        f"📥 НОВАЯ ЗАЯВКА НА КУХНЮ\n\n"
        f"👤 Клиент: {user.first_name or ''} {user.last_name or ''}\n"
        f"📱 Username: @{user.username or 'не указан'}\n"
        f"🆔 ID: {user.id}\n\n"
        f"📏 Размеры: {data['size']}\n"
        f"🎨 Стиль: {data['style']}\n"
        f"🧱 Материал: {data['material']}\n"
        f"💡 Пожелания: {data['idea']}\n\n"
        f"🕒 Время: {datetime.now().strftime('%d.%m.%Y %H:%M')}"
    )

    # Отправляем админу
    try:
        await bot.send_message(chat_id=ADMIN_ID, text=admin_summary)
        logger.info(f"Заявка от пользователя {user.id} отправлена админу")
    except Exception as e:
        logger.error(f"Ошибка отправки админу: {e}")

    # Записываем в Google Sheets
    if sheet:
        try:
            now = datetime.now().strftime("%d.%m.%Y %H:%M")
            row = [
                now,
                f"{user.first_name or ''} {user.last_name or ''}".strip(),
                user.username or "не указан",
                str(user.id),
                data['size'],
                data['style'],
                data['material'],
                data['idea']
            ]
            sheet.append_row(row)
            logger.info(f"Заявка от пользователя {user.id} записана в Google Sheets")
        except Exception as e:
            logger.error(f"Ошибка записи в Google Sheets: {e}")
    else:
        logger.warning("Google Sheets недоступен, данные не записаны")

    # Отвечаем пользователю
    await message.answer(
        "✅ Спасибо! Ваша заявка принята.\n\n"
        "👨‍💼 Наш менеджер свяжется с вами в течение рабочего дня "
        "для уточнения деталей и расчета стоимости.\n\n"
        "📞 Если у вас срочный вопрос, звоните по телефону из раздела \"Контакты\".",
        reply_markup=get_main_keyboard()
    )
    
    await state.clear()

async def handle_navigation(message: types.Message, state: FSMContext):
    """Обработка навигационных кнопок"""
    if message.text == "🏠 Главное меню":
        await state.clear()
        await message.answer("Главное меню:", reply_markup=get_main_keyboard())
    elif message.text == "🔙 Назад":
        current_state = await state.get_state()
        if current_state == Form.size:
            await state.clear()
            await message.answer("Главное меню:", reply_markup=get_main_keyboard())
        elif current_state == Form.style:
            await message.answer(
                "📏 Укажите размеры кухни:",
                reply_markup=get_back_keyboard()
            )
            await state.set_state(Form.size)
        elif current_state == Form.material:
            await message.answer(
                "🎨 Выберите стиль кухни:",
                reply_markup=get_style_keyboard()
            )
            await state.set_state(Form.style)
        elif current_state == Form.idea:
            await message.answer(
                "🧱 Выберите материал фасадов:",
                reply_markup=get_material_keyboard()
            )
            await state.set_state(Form.material)

# === Обработчик неизвестных сообщений ===
@dp.message()
async def unknown_message(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state:
        await message.answer(
            "❌ Пожалуйста, используйте кнопки для навигации или введите корректные данные."
        )
    else:
        await message.answer(
            "❓ Не понимаю эту команду.\n"
            "Используйте меню или команду /help для справки.",
            reply_markup=get_main_keyboard()
        )

# === Запуск ===
async def main():
    logger.info("Запуск бота...")
    init_google_sheets()
    
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())