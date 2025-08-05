# Инструкция по настройке бота

## 1. Настройка Telegram Bot

1. Создайте бота через @BotFather в Telegram
2. Получите токен бота
3. Узнайте свой Telegram ID (можно через @userinfobot)

## 2. Настройка Google Sheets

1. Перейдите в [Google Cloud Console](https://console.cloud.google.com/)
2. Создайте новый проект или выберите существующий
3. Включите Google Sheets API и Google Drive API
4. Создайте Service Account:
   - Перейдите в "IAM & Admin" → "Service Accounts"
   - Нажмите "Create Service Account"
   - Заполните информацию и создайте
5. Создайте ключ для Service Account:
   - Выберите созданный аккаунт
   - Перейдите в "Keys" → "Add Key" → "Create New Key"
   - Выберите JSON формат
   - Скачайте файл и переименуйте в `credentials.json`
6. Создайте Google Spreadsheet:
   - Создайте новую таблицу в Google Sheets
   - Скопируйте ID из URL (длинная строка между `/d/` и `/edit`)
   - Дайте доступ на редактирование email-у из Service Account

## 3. Настройка переменных окружения

1. Переименуйте `.env` и заполните:
   ```
   BOT_TOKEN=ваш_токен_бота
   ADMIN_ID=ваш_telegram_id
   SPREADSHEET_ID=id_вашей_таблицы
   ```

2. Переименуйте `credentials.json.template` в `credentials.json` и заполните данными из Google Cloud

## 4. Установка зависимостей

```bash
pip install -r requirements.txt
```

## 5. Запуск бота

```bash
python bot.py
```

## Структура Google Sheets

Бот будет записывать данные в следующие колонки:
- A: Дата и время
- B: Username пользователя
- C: Размеры кухни
- D: Стиль
- E: Материал
- F: Идеи/пожелания