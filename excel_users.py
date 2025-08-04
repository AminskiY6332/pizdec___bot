import sqlite3
import pandas as pd
from logger import get_logger

# 1. Имя файла БД (при необходимости замените)
DB_FILE = 'users.db'
# 2. Подключение к базе данных SQLite
conn = sqlite3.connect(DB_FILE)

# 3. Чтение всех данных из таблицы users
df = pd.read_sql_query("SELECT * FROM users", conn)

# 4. Словарь соответствия английских колонок и русских названий
column_mapping = {
    'user_id': 'ID пользователя',
    'username': 'Имя пользователя',
    'generations_left': 'Осталось генераций',
    'avatar_left': 'Осталось аватаров',
    'has_trained_model': 'Есть обученная модель',
    'is_notified': 'Уведомлён',
    'first_purchase': 'Первая покупка',
    'email': 'Email',
    'active_avatar_id': 'ID активного аватара',
    'first_name': 'Имя',
    'referrer_id': 'ID пригласившего',
    'is_blocked': 'Заблокирован',
    'block_reason': 'Причина блокировки',
    'created_at': 'Дата создания',
    'updated_at': 'Дата обновления',
    'welcome_message_sent': 'Приветственное сообщение отправлено',
    'last_reminder_type': 'Тип последнего напоминания',
    'last_reminder_sent': 'Дата последнего напоминания',
    'utm_source': 'UTM источник'
}

df.rename(columns=column_mapping, inplace=True)

# 5. Сохранение в Excel
OUTPUT_FILE = 'users.xlsx'
df.to_excel(OUTPUT_FILE, index=False)

logger = get_logger('main')
logger.info(f"Экспорт завершён. Файл сохранён как '{OUTPUT_FILE}'.")
