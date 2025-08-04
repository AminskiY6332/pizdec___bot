import asyncio
import pytest
import pytest_asyncio
import aiosqlite
import tempfile
import os
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any

# Mock the imports to avoid circular dependencies
import sys
from unittest.mock import MagicMock

# Create mock modules
sys.modules['config'] = MagicMock()
sys.modules['handlers.utils'] = MagicMock()
sys.modules['handlers.commands'] = MagicMock()
sys.modules['handlers.onboarding'] = MagicMock()

# Now import our modules
from onboarding_config import (
    get_day_config,
    get_message_text,
    has_user_purchases,
    ONBOARDING_FUNNEL,
    MESSAGE_TEXTS
)


class TestOnboardingConfig:
    """Тесты для функций конфигурации онбординга"""

    def test_get_day_config(self):
        """Тест получения конфигурации для дня"""
        # Тест для дня 1 - должен показывать все тарифы
        day1_config = get_day_config(1)
        assert day1_config["message_type"] == "welcome"
        assert day1_config["tariff_key"] is None  # Все тарифы
        assert day1_config["price"] is None

        # Тест для дня 2 - мини тариф
        day2_config = get_day_config(2)
        assert day2_config["message_type"] == "reminder_day2"
        assert day2_config["tariff_key"] == "мини"
        assert day2_config["price"] == 399

        # Тест для дня 3 - мини тариф
        day3_config = get_day_config(3)
        assert day3_config["message_type"] == "reminder_day3"
        assert day3_config["tariff_key"] == "мини"
        assert day3_config["price"] == 399

        # Тест для дня 4 - лайт тариф
        day4_config = get_day_config(4)
        assert day4_config["message_type"] == "reminder_day4"
        assert day4_config["tariff_key"] == "лайт"
        assert day4_config["price"] == 599

        # Тест для дня 5 - комфорт тариф
        day5_config = get_day_config(5)
        assert day5_config["message_type"] == "reminder_day5"
        assert day5_config["tariff_key"] == "комфорт"
        assert day5_config["price"] == 1199

        # Тест для несуществующего дня
        invalid_config = get_day_config(999)
        assert invalid_config == {}

    def test_get_message_text(self):
        """Тест получения текста сообщения"""
        # Тест для welcome сообщения
        welcome_text = get_message_text("welcome", "Иван")
        assert "PixelPie" in welcome_text["text"]
        assert welcome_text["button_text"] == "Загрузить фото"
        assert welcome_text["callback_data"] == "proceed_to_tariff"

        # Тест для reminder_day2
        reminder_text = get_message_text("reminder_day2", "Мария")
        assert "399₽" in reminder_text["text"]
        assert reminder_text["button_text"] == "Купить Лайт-Мини"
        assert reminder_text["callback_data"] == "pay_399"

        # Тест для reminder_day3
        reminder3_text = get_message_text("reminder_day3", "Алексей")
        assert "399₽" in reminder3_text["text"]
        assert reminder3_text["button_text"] == "Выбрать Мини"
        assert reminder3_text["callback_data"] == "pay_399"

        # Тест для reminder_day4
        reminder4_text = get_message_text("reminder_day4", "Анна")
        assert "599₽" in reminder4_text["text"]
        assert reminder4_text["button_text"] == "Выбрать Лайт"
        assert reminder4_text["callback_data"] == "pay_599"

        # Тест для reminder_day5
        reminder5_text = get_message_text("reminder_day5", "Петр")
        assert "1199₽" in reminder5_text["text"]
        assert reminder5_text["button_text"] == "Выбрать Комфорт"
        assert reminder5_text["callback_data"] == "pay_1199"

        # Тест для несуществующего типа сообщения
        invalid_text = get_message_text("nonexistent", "Тест")
        assert invalid_text == {}


class TestDatabaseFunctions:
    """Тесты для функций работы с базой данных"""

    @pytest_asyncio.fixture
    async def temp_db(self):
        """Создание временной базы данных для тестов"""
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        temp_file.close()

        # Создаем таблицы
        async with aiosqlite.connect(temp_file.name) as conn:
            await conn.execute("""
                CREATE TABLE users (
                    user_id INTEGER PRIMARY KEY,
                    first_name TEXT,
                    username TEXT,
                    created_at TEXT,
                    welcome_message_sent INTEGER DEFAULT 0,
                    first_purchase INTEGER DEFAULT 1,
                    is_blocked INTEGER DEFAULT 0,
                    last_reminder_type TEXT
                )
            """)

            await conn.execute("""
                CREATE TABLE payments (
                    user_id INTEGER,
                    status TEXT,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            """)

            await conn.commit()

        yield temp_file.name

        # Удаляем временный файл
        os.unlink(temp_file.name)

    @pytest.mark.asyncio
    async def test_has_user_purchases_with_purchases(self, temp_db):
        """Тест проверки покупок пользователя - есть покупки"""
        # Добавляем пользователя с покупкой
        async with aiosqlite.connect(temp_db) as conn:
            await conn.execute(
                "INSERT INTO users (user_id, first_name) VALUES (?, ?)",
                (123, "Тест")
            )
            await conn.execute(
                "INSERT INTO payments (user_id, status) VALUES (?, ?)",
                (123, "succeeded")
            )
            await conn.commit()

        # Проверяем функцию
        has_purchases = await has_user_purchases(123, temp_db)
        assert has_purchases is True

    @pytest.mark.asyncio
    async def test_has_user_purchases_without_purchases(self, temp_db):
        """Тест проверки покупок пользователя - нет покупок"""
        # Добавляем пользователя без покупок
        async with aiosqlite.connect(temp_db) as conn:
            await conn.execute(
                "INSERT INTO users (user_id, first_name) VALUES (?, ?)",
                (456, "Тест2")
            )
            await conn.commit()

        # Проверяем функцию
        has_purchases = await has_user_purchases(456, temp_db)
        assert has_purchases is False

    @pytest.mark.asyncio
    async def test_has_user_purchases_nonexistent_user(self, temp_db):
        """Тест проверки покупок несуществующего пользователя"""
        has_purchases = await has_user_purchases(999, temp_db)
        assert has_purchases is False


class TestOnboardingFunnelLogic:
    """Тесты логики воронки онбординга"""

    def test_onboarding_funnel_structure(self):
        """Тест структуры воронки онбординга"""
        # Проверяем, что все дни имеют правильную структуру
        for day, config in ONBOARDING_FUNNEL.items():
            assert "message_type" in config
            assert "tariff_key" in config
            assert "price" in config
            assert "description" in config

            if day == 1:
                assert "time_after_registration" in config
                assert config["time_after_registration"] == timedelta(hours=1)
                assert config["tariff_key"] is None  # Все тарифы
                assert config["price"] is None
            else:
                assert "time" in config
                assert config["time"] == "11:15"

    def test_message_texts_structure(self):
        """Тест структуры текстов сообщений"""
        # Проверяем, что все типы сообщений имеют необходимые поля
        for message_type, text_data in MESSAGE_TEXTS.items():
            assert "text" in text_data
            assert "button_text" in text_data
            assert "callback_data" in text_data

    def test_funnel_progression(self):
        """Тест прогрессии воронки"""
        # День 1 - welcome (все тарифы)
        day1 = get_day_config(1)
        assert day1["message_type"] == "welcome"
        assert day1["tariff_key"] is None
        assert day1["price"] is None

        # День 2 - reminder_day2 (мини)
        day2 = get_day_config(2)
        assert day2["message_type"] == "reminder_day2"
        assert day2["tariff_key"] == "мини"
        assert day2["price"] == 399

        # День 3 - reminder_day3 (мини)
        day3 = get_day_config(3)
        assert day3["message_type"] == "reminder_day3"
        assert day3["tariff_key"] == "мини"
        assert day3["price"] == 399

        # День 4 - reminder_day4 (лайт)
        day4 = get_day_config(4)
        assert day4["message_type"] == "reminder_day4"
        assert day4["tariff_key"] == "лайт"
        assert day4["price"] == 599

        # День 5 - reminder_day5 (комфорт)
        day5 = get_day_config(5)
        assert day5["message_type"] == "reminder_day5"
        assert day5["tariff_key"] == "комфорт"
        assert day5["price"] == 1199


class TestButtonCreation:
    """Тесты создания кнопок"""

    def test_welcome_button_creation(self):
        """Тест создания кнопки для welcome сообщения"""
        message_data = get_message_text("welcome", "Тест")

        # Проверяем, что кнопка создается правильно
        assert message_data["button_text"] == "Загрузить фото"
        assert message_data["callback_data"] == "proceed_to_tariff"

        # Проверяем, что текст содержит правильную информацию
        assert "PixelPie" in message_data["text"]
        assert "фотосессия" in message_data["text"]

    def test_payment_button_creation(self):
        """Тест создания кнопок для оплаты"""
        # Тест для дня 2
        day2_data = get_message_text("reminder_day2", "Тест")
        assert day2_data["button_text"] == "Купить Лайт-Мини"
        assert day2_data["callback_data"] == "pay_399"
        assert "399₽" in day2_data["text"]

        # Тест для дня 3
        day3_data = get_message_text("reminder_day3", "Тест")
        assert day3_data["button_text"] == "Выбрать Мини"
        assert day3_data["callback_data"] == "pay_399"
        assert "399₽" in day3_data["text"]

        # Тест для дня 4
        day4_data = get_message_text("reminder_day4", "Тест")
        assert day4_data["button_text"] == "Выбрать Лайт"
        assert day4_data["callback_data"] == "pay_599"
        assert "599₽" in day4_data["text"]

        # Тест для дня 5
        day5_data = get_message_text("reminder_day5", "Тест")
        assert day5_data["button_text"] == "Выбрать Комфорт"
        assert day5_data["callback_data"] == "pay_1199"
        assert "1199₽" in day5_data["text"]


class TestPriceValidation:
    """Тесты валидации цен"""

    def test_price_consistency(self):
        """Тест соответствия цен в конфигурации и текстах"""
        # Проверяем, что цены в конфигурации соответствуют ценам в текстах
        for day in range(2, 6):
            config = get_day_config(day)
            message_type = config["message_type"]
            expected_price = config["price"]

            message_data = get_message_text(message_type, "Тест")
            callback_data = message_data["callback_data"]

            # Проверяем, что callback_data содержит правильную цену
            assert f"pay_{expected_price}" in callback_data

            # Проверяем, что текст содержит правильную цену
            assert f"{expected_price}₽" in message_data["text"]

    def test_welcome_no_price(self):
        """Тест, что welcome сообщение не содержит конкретную цену"""
        day1_config = get_day_config(1)
        assert day1_config["price"] is None
        assert day1_config["tariff_key"] is None

        message_data = get_message_text("welcome", "Тест")
        assert "pay_" not in message_data["callback_data"]
        assert message_data["callback_data"] == "proceed_to_tariff"


class TestIntegration:
    """Интеграционные тесты"""

    @pytest_asyncio.fixture
    async def temp_db_with_data(self):
        """Создание временной БД с тестовыми данными"""
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        temp_file.close()

        # Создаем таблицы и добавляем тестовые данные
        async with aiosqlite.connect(temp_file.name) as conn:
            await conn.execute("""
                CREATE TABLE users (
                    user_id INTEGER PRIMARY KEY,
                    first_name TEXT,
                    username TEXT,
                    created_at TEXT,
                    welcome_message_sent INTEGER DEFAULT 0,
                    first_purchase INTEGER DEFAULT 1,
                    is_blocked INTEGER DEFAULT 0,
                    last_reminder_type TEXT
                )
            """)

            await conn.execute("""
                CREATE TABLE payments (
                    user_id INTEGER,
                    status TEXT,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            """)

            # Добавляем тестовых пользователей
            await conn.execute("""
                INSERT INTO users (user_id, first_name, username, created_at, welcome_message_sent, first_purchase, is_blocked)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (111, "Тест1", "test1", "2024-01-01 10:00:00", 0, 1, 0))

            await conn.execute("""
                INSERT INTO users (user_id, first_name, username, created_at, welcome_message_sent, first_purchase, is_blocked)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (222, "Тест2", "test2", "2024-01-01 10:00:00", 0, 1, 0))

            await conn.commit()

        yield temp_file.name
        os.unlink(temp_file.name)

    @pytest.mark.asyncio
    async def test_full_onboarding_flow(self, temp_db_with_data):
        """Тест полного потока онбординга"""
        # Проверяем функцию проверки покупок
        has_purchases_111 = await has_user_purchases(111, temp_db_with_data)
        assert has_purchases_111 is False

        # Добавляем покупку для одного пользователя
        async with aiosqlite.connect(temp_db_with_data) as conn:
            await conn.execute(
                "INSERT INTO payments (user_id, status) VALUES (?, ?)",
                (111, "succeeded")
            )
            await conn.commit()

        # Проверяем, что пользователь с покупкой больше не попадает в выборку
        has_purchases_111_after = await has_user_purchases(111, temp_db_with_data)
        assert has_purchases_111_after is True


# Запуск тестов
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
