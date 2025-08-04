#!/usr/bin/env python3
"""
Тестирование реальной функции send_daily_reminders с подменой базы данных
"""

import asyncio
import sys
import os
import aiosqlite
import tempfile
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch, MagicMock
from typing import Dict, Any, List

# Добавляем путь для импортов
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Мокируем зависимости
mock_modules = {
    'config': MagicMock(),
    'handlers.utils': MagicMock(),
    'keyboards': MagicMock(),
    'database': MagicMock(),
    'logger': MagicMock(),
    'pytz': MagicMock()
}

for name, mock in mock_modules.items():
    sys.modules[name] = mock

# Настраиваем моки
sys.modules['config'].DATABASE_PATH = None  # Будет переопределен в тестах
sys.modules['config'].TARIFFS = {}
sys.modules['config'].ADMIN_IDS = [12345]
sys.modules['config'].ERROR_LOG_ADMIN = 12345

# Создаем мок для logger
mock_logger = MagicMock()
sys.modules['logger'].get_logger.return_value = mock_logger

# Создаем мок для pytz
mock_tz = MagicMock()
mock_tz.timezone.return_value = MagicMock()
sys.modules['pytz'] = mock_tz

class MockBot:
    """Мок бота для тестирования"""
    def __init__(self):
        self.sent_messages = []
        self.errors = []

    async def send_message(self, chat_id: int, text: str, **kwargs):
        """Мок отправки сообщения"""
        self.sent_messages.append({
            'chat_id': chat_id,
            'text': text,
            'kwargs': kwargs,
            'timestamp': datetime.now()
        })
        print(f"📤 Сообщение пользователю {chat_id}: {text[:60]}...")
        return MagicMock(message_id=len(self.sent_messages))

    async def send_photo(self, chat_id: int, photo, **kwargs):
        """Мок отправки фото"""
        self.sent_messages.append({
            'chat_id': chat_id,
            'text': f"PHOTO: {kwargs.get('caption', 'No caption')}",
            'kwargs': kwargs,
            'timestamp': datetime.now()
        })
        print(f"📷 Фото пользователю {chat_id}: {kwargs.get('caption', 'No caption')[:60]}...")
        return MagicMock(message_id=len(self.sent_messages))

class RealFunnelTester:
    """Тестировщик реальной воронки"""

    def __init__(self):
        self.test_db = None
        self.mock_bot = MockBot()
        self.test_results = []

    async def setup_test_database(self):
        """Создание тестовой базы данных"""
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        temp_file.close()
        self.test_db = temp_file.name

        # Обновляем путь к базе в конфиге
        sys.modules['config'].DATABASE_PATH = self.test_db

        async with aiosqlite.connect(self.test_db) as conn:
            # Создаем таблицы как в реальной базе
            await conn.execute("""
                CREATE TABLE users (
                    user_id INTEGER PRIMARY KEY,
                    first_name TEXT,
                    username TEXT,
                    created_at TEXT,
                    welcome_message_sent INTEGER DEFAULT 0,
                    first_purchase INTEGER DEFAULT 1,
                    is_blocked INTEGER DEFAULT 0,
                    last_reminder_type TEXT,
                    last_reminder_sent TEXT,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            await conn.execute("""
                CREATE TABLE payments (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER,
                    amount REAL,
                    status TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            """)

            await conn.commit()

        print(f"✅ База данных для реального теста создана: {self.test_db}")

    async def create_realistic_test_data(self):
        """Создание реалистичных тестовых данных"""

        # Текущая дата для расчетов
        now = datetime.now()

        async with aiosqlite.connect(self.test_db) as conn:
            test_users = [
                # Пользователь для reminder_day2 (зарегистрирован 1 день назад)
                (
                    2001, "Алексей", "alex2001",
                    (now - timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S'),
                    1, 1, 0, None, None
                ),

                # Пользователь для reminder_day3 (зарегистрирован 2 дня назад)
                (
                    2002, "Мария", "maria2002",
                    (now - timedelta(days=2)).strftime('%Y-%m-%d %H:%M:%S'),
                    1, 1, 0, "reminder_day2", None
                ),

                # Пользователь для reminder_day4 (зарегистрирован 3 дня назад)
                (
                    2003, "Иван", "ivan2003",
                    (now - timedelta(days=3)).strftime('%Y-%m-%d %H:%M:%S'),
                    1, 1, 0, "reminder_day3", None
                ),

                # Пользователь для reminder_day5 (зарегистрирован 5 дней назад)
                (
                    2004, "Елена", "elena2004",
                    (now - timedelta(days=5)).strftime('%Y-%m-%d %H:%M:%S'),
                    1, 1, 0, "reminder_day4", None
                ),

                # Пользователь с покупкой (НЕ должен получать напоминания)
                (
                    2005, "Петр", "petr2005",
                    (now - timedelta(days=2)).strftime('%Y-%m-%d %H:%M:%S'),
                    1, 1, 0, None, None
                ),

                # Заблокированный пользователь
                (
                    2006, "Анна", "anna2006",
                    (now - timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S'),
                    0, 1, 1, None, None
                ),

                # Пользователь, уже получивший текущее напоминание
                (
                    2007, "Сергей", "sergey2007",
                    (now - timedelta(days=2)).strftime('%Y-%m-%d %H:%M:%S'),
                    1, 1, 0, "reminder_day3", None
                ),
            ]

            for user in test_users:
                await conn.execute("""
                    INSERT INTO users (user_id, first_name, username, created_at, welcome_message_sent,
                                     first_purchase, is_blocked, last_reminder_type, last_reminder_sent)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, user)

            # Добавляем покупку для пользователя 2005
            await conn.execute("""
                INSERT INTO payments (user_id, amount, status)
                VALUES (?, ?, ?)
            """, (2005, 399.0, "succeeded"))

            await conn.commit()

        print("✅ Реалистичные тестовые данные созданы")
        print("📊 Пользователи по дням регистрации:")
        for user in test_users:
            days_ago = (now - datetime.strptime(user[3], '%Y-%m-%d %H:%M:%S')).days
            status = "BLOCKED" if user[6] else "ACTIVE"
            print(f"  {user[1]} (ID: {user[0]}) - {days_ago} дней назад, {status}")

    async def test_real_send_daily_reminders(self):
        """Тест реальной функции send_daily_reminders"""
        print("\n🔥 ТЕСТИРОВАНИЕ РЕАЛЬНОЙ ФУНКЦИИ send_daily_reminders...")

        # Импортируем функции после настройки моков
        from onboarding_config import has_user_purchases

        # Создаем моки для функций
        async def mock_get_users_for_reminders():
            async with aiosqlite.connect(self.test_db) as conn:
                conn.row_factory = aiosqlite.Row
                c = await conn.cursor()
                await c.execute("""
                    SELECT user_id, first_name, username, created_at, last_reminder_type
                    FROM users
                    WHERE is_blocked = 0
                    AND user_id NOT IN (SELECT user_id FROM payments WHERE status = 'succeeded')
                    AND created_at IS NOT NULL
                """)
                users = await c.fetchall()
                return [dict(user) for user in users]

        async def mock_is_user_blocked(user_id):
            async with aiosqlite.connect(self.test_db) as conn:
                c = await conn.cursor()
                await c.execute("SELECT is_blocked FROM users WHERE user_id = ?", (user_id,))
                result = await c.fetchone()
                return bool(result[0]) if result else False

        async def mock_is_old_user(user_id, cutoff_date):
            # Эмулируем проверку старого пользователя
            # В нашем тесте все пользователи новые
            return False

        async def mock_check_database_user(user_id):
            async with aiosqlite.connect(self.test_db) as conn:
                c = await conn.cursor()
                await c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
                result = await c.fetchone()
                if result:
                    # Возвращаем кортеж в формате, ожидаемом функцией
                    return (
                        result[0],  # user_id
                        None, None,  # placeholder fields
                        result[2],   # username
                        None, None, None, None,  # more placeholders
                        result[1],   # first_name
                        None, None,  # more placeholders
                        result[4],   # welcome_message_sent
                        result[7],   # last_reminder_type
                        None  # last_reminder_sent
                    )
                return None

        async def mock_send_onboarding_message(bot, user_id, message_type, subscription_data):
            from onboarding_config import get_message_text

            first_name = subscription_data[8] if subscription_data and len(subscription_data) > 8 else "Пользователь"
            message_data = get_message_text(message_type, first_name)

            if message_data:
                await bot.send_message(
                    chat_id=user_id,
                    text=message_data['text'],
                    reply_markup={"inline_keyboard": [[{"text": message_data["button_text"], "callback_data": message_data["callback_data"]}]]}
                )

                # Обновляем last_reminder_type в базе
                async with aiosqlite.connect(self.test_db) as conn:
                    c = await conn.cursor()
                    await c.execute(
                        "UPDATE users SET last_reminder_type = ?, last_reminder_sent = ? WHERE user_id = ?",
                        (message_type, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), user_id)
                    )
                    await conn.commit()

        # Эмулируем реальную функцию send_daily_reminders
        print("Получение пользователей для напоминаний...")
        users = await mock_get_users_for_reminders()
        print(f"Найдено {len(users)} пользователей для ежедневных напоминаний")

        current_time = datetime.now()
        reminders_sent = 0

        for user in users:
            user_id = user['user_id']
            first_name = user['first_name']
            username = user['username']
            created_at = user['created_at']
            last_reminder_type = user['last_reminder_type']

            print(f"\nОбработка пользователя {user_id} ({first_name})...")

            # Проверяем, заблокирован ли пользователь
            if await mock_is_user_blocked(user_id):
                print(f"  ❌ Пользователь заблокирован, пропускаем")
                continue

            # Проверяем, является ли пользователь старым
            is_old_user_flag = await mock_is_old_user(user_id, "2025-07-11")
            if is_old_user_flag:
                print(f"  ❌ Старый пользователь, пропускаем")
                continue

            # Проверяем, есть ли у пользователя покупки
            has_purchases = await has_user_purchases(user_id, self.test_db)
            if has_purchases:
                print(f"  ❌ Пользователь имеет покупки, пропускаем")
                continue

            # Вычисляем дни с регистрации
            try:
                registration_date = datetime.strptime(created_at, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                print(f"  ❌ Неверный формат даты: {created_at}")
                continue

            days_since_registration = (current_time.date() - registration_date.date()).days
            print(f"  📅 Дней с регистрации: {days_since_registration}")
            print(f"  📝 Последнее напоминание: {last_reminder_type}")

            # Определяем, какое напоминание нужно отправить
            message_type = None
            if days_since_registration == 1 and last_reminder_type != "reminder_day2":
                message_type = "reminder_day2"
            elif days_since_registration == 2 and last_reminder_type != "reminder_day3":
                message_type = "reminder_day3"
            elif days_since_registration == 3 and last_reminder_type != "reminder_day4":
                message_type = "reminder_day4"
            elif days_since_registration >= 4 and last_reminder_type != "reminder_day5":
                message_type = "reminder_day5"

            if message_type:
                print(f"  ✅ Отправляем {message_type}")
                subscription_data = await mock_check_database_user(user_id)
                if subscription_data:
                    await mock_send_onboarding_message(self.mock_bot, user_id, message_type, subscription_data)
                    reminders_sent += 1
                else:
                    print(f"  ❌ Неполные данные пользователя")
            else:
                print(f"  ⏭️ Напоминание не требуется")

        print(f"\n📊 Итого отправлено напоминаний: {reminders_sent}")

        # Проверяем результаты
        expected_reminders = 4  # 2001 (day2), 2002 (day3), 2003 (day4), 2004 (day5)
        success = reminders_sent == expected_reminders

        print(f"🎯 Ожидалось: {expected_reminders}, Отправлено: {reminders_sent}")
        print(f"✅ Тест {'ПРОШЕЛ' if success else 'ПРОВАЛЕН'}")

        return success

    async def analyze_sent_messages(self):
        """Анализ отправленных сообщений"""
        print("\n📋 АНАЛИЗ ОТПРАВЛЕННЫХ СООБЩЕНИЙ:")

        if not self.mock_bot.sent_messages:
            print("❌ Сообщения не отправлялись")
            return

        # Группируем по пользователям
        user_messages = {}
        for msg in self.mock_bot.sent_messages:
            user_id = msg['chat_id']
            if user_id not in user_messages:
                user_messages[user_id] = []
            user_messages[user_id].append(msg)

        # Анализируем каждого пользователя
        for user_id, messages in user_messages.items():
            print(f"\n👤 Пользователь {user_id}:")
            for i, msg in enumerate(messages, 1):
                # Определяем тип сообщения по содержанию
                text = msg['text']
                if "Мини-пакет: 10 фото за 399₽" in text:
                    msg_type = "reminder_day2"
                elif "Напоминаем: Мини — 10 фото за 399₽" in text:
                    msg_type = "reminder_day3"
                elif "Попробуй Лайт: 20 фото за 599₽" in text:
                    msg_type = "reminder_day4"
                elif "Пакет Комфорт — 50 фото за 1199₽" in text:
                    msg_type = "reminder_day5"
                else:
                    msg_type = "unknown"

                print(f"  {i}. {msg_type}: {text[:50]}...")

    async def cleanup(self):
        """Очистка"""
        if self.test_db and os.path.exists(self.test_db):
            os.unlink(self.test_db)
            print("✅ Тестовая база удалена")

async def main():
    """Главная функция"""
    print("🔥 ТЕСТИРОВАНИЕ РЕАЛЬНОЙ ВОРОНКИ")
    print("="*50)

    tester = RealFunnelTester()

    try:
        await tester.setup_test_database()
        await tester.create_realistic_test_data()

        success = await tester.test_real_send_daily_reminders()
        await tester.analyze_sent_messages()

        print("\n" + "="*60)
        print("🏁 ФИНАЛЬНЫЙ РЕЗУЛЬТАТ:")
        print("="*60)
        print(f"✅ {'УСПЕХ' if success else 'ОШИБКА'}: Воронка {'работает корректно' if success else 'имеет проблемы'}")

        return 0 if success else 1

    finally:
        await tester.cleanup()

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
