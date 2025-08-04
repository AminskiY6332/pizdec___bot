#!/usr/bin/env python3
"""
Тестирование воронки сообщений для пользователей без покупок
Этот скрипт тестирует логику отправки сообщений и правильность конфигурации
"""

import asyncio
import sys
import os
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, Any, List

# Добавляем текущую директорию в PATH для импортов
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Импортируем конфигурацию воронки
from onboarding_config import (
    get_day_config,
    get_message_text,
    ONBOARDING_FUNNEL,
    MESSAGE_TEXTS
)

class FunnelTester:
    """Класс для тестирования воронки"""

    def __init__(self):
        self.test_results = []
        self.errors = []

    def log_test(self, test_name: str, result: bool, message: str = ""):
        """Логирование результата теста"""
        status = "✅ PASS" if result else "❌ FAIL"
        self.test_results.append({
            'name': test_name,
            'result': result,
            'message': message
        })
        print(f"{status} {test_name}: {message}")

        if not result:
            self.errors.append(f"{test_name}: {message}")

    def test_funnel_configuration(self):
        """Тест конфигурации воронки"""
        print("\n🔧 Тестирование конфигурации воронки...")

        # Проверка структуры воронки
        expected_days = [1, 2, 3, 4, 5]
        for day in expected_days:
            config = get_day_config(day)
            has_required_fields = all(key in config for key in ['message_type', 'tariff_key', 'price', 'description'])
            self.log_test(
                f"День {day} - структура конфигурации",
                has_required_fields,
                f"Конфигурация: {config}" if has_required_fields else f"Отсутствуют поля в конфигурации: {config}"
            )

        # Проверка прогрессии цен
        day2_price = get_day_config(2)['price']
        day3_price = get_day_config(3)['price']
        day4_price = get_day_config(4)['price']
        day5_price = get_day_config(5)['price']

        price_progression_correct = (
            day2_price == 399 and
            day3_price == 399 and
            day4_price == 599 and
            day5_price == 1199
        )

        self.log_test(
            "Прогрессия цен",
            price_progression_correct,
            f"Цены: День2={day2_price}, День3={day3_price}, День4={day4_price}, День5={day5_price}"
        )

    def test_message_texts(self):
        """Тест текстов сообщений"""
        print("\n📝 Тестирование текстов сообщений...")

        test_user_name = "Тестовый Пользователь"

        # Проверка всех типов сообщений
        for message_type in MESSAGE_TEXTS.keys():
            message_data = get_message_text(message_type, test_user_name)

            has_required_fields = all(key in message_data for key in ['text', 'button_text', 'callback_data'])
            self.log_test(
                f"Сообщение {message_type} - структура",
                has_required_fields,
                f"Поля: {list(message_data.keys())}" if has_required_fields else f"Отсутствуют поля"
            )

            if has_required_fields:
                # Проверка содержания текста
                text_not_empty = len(message_data['text'].strip()) > 0
                button_not_empty = len(message_data['button_text'].strip()) > 0
                callback_not_empty = len(message_data['callback_data'].strip()) > 0

                self.log_test(
                    f"Сообщение {message_type} - содержание",
                    text_not_empty and button_not_empty and callback_not_empty,
                    f"Текст: {message_data['text'][:50]}..., Кнопка: {message_data['button_text']}, Действие: {message_data['callback_data']}"
                )

    def test_funnel_flow_logic(self):
        """Тест логики потока воронки"""
        print("\n🔄 Тестирование логики потока воронки...")

        # Проверка временных интервалов
        day1_config = get_day_config(1)
        has_time_offset = 'time_after_registration' in day1_config
        correct_offset = day1_config.get('time_after_registration') == timedelta(hours=1)

        self.log_test(
            "День 1 - временной офсет",
            has_time_offset and correct_offset,
            f"Офсет: {day1_config.get('time_after_registration')}"
        )

        # Проверка времени для дней 2-5
        for day in range(2, 6):
            config = get_day_config(day)
            correct_time = config.get('time') == '11:15'
            self.log_test(
                f"День {day} - время отправки",
                correct_time,
                f"Время: {config.get('time')}"
            )

    def test_callback_actions(self):
        """Тест действий кнопок"""
        print("\n🎯 Тестирование действий кнопок...")

        # Проверка действий для каждого дня
        expected_callbacks = {
            'welcome': 'proceed_to_tariff',
            'reminder_day2': 'pay_399',
            'reminder_day3': 'pay_399',
            'reminder_day4': 'pay_599',
            'reminder_day5': 'pay_1199'
        }

        for message_type, expected_callback in expected_callbacks.items():
            message_data = get_message_text(message_type, "Тест")
            actual_callback = message_data.get('callback_data')

            self.log_test(
                f"Действие {message_type}",
                actual_callback == expected_callback,
                f"Ожидалось: {expected_callback}, Получено: {actual_callback}"
            )

    def test_price_consistency(self):
        """Тест соответствия цен в конфигурации и текстах"""
        print("\n💰 Тестирование соответствия цен...")

        for day in range(2, 6):
            config = get_day_config(day)
            expected_price = config['price']
            message_type = config['message_type']

            message_data = get_message_text(message_type, "Тест")
            text = message_data['text']
            callback = message_data['callback_data']

            # Проверка цены в тексте
            price_in_text = f"{expected_price}₽" in text

            # Проверка цены в callback_data
            price_in_callback = f"pay_{expected_price}" in callback or message_type == "reminder_day5"

            self.log_test(
                f"День {day} - соответствие цен",
                price_in_text and (price_in_callback or message_type == "reminder_day5"),
                f"Цена {expected_price}₽ в тексте: {price_in_text}, в callback: {price_in_callback}"
            )

    def simulate_user_journey(self):
        """Симуляция пути пользователя через воронку"""
        print("\n🚀 Симуляция пути пользователя...")

        test_user = "Алексей"
        journey_log = []

        # День 1 - регистрация и приветственное сообщение
        day1_message = get_message_text("welcome", test_user)
        journey_log.append(f"День 1: {day1_message['text'][:100]}...")

        # Дни 2-5 - напоминания
        for day in range(2, 6):
            config = get_day_config(day)
            message_type = config['message_type']
            message_data = get_message_text(message_type, test_user)
            journey_log.append(f"День {day}: {message_data['text'][:100]}...")

        # Проверка, что путь пользователя логичен
        journey_complete = len(journey_log) == 5
        self.log_test(
            "Полный путь пользователя",
            journey_complete,
            f"Сообщений в воронке: {len(journey_log)}"
        )

        # Вывод пути пользователя
        print("\n📋 Путь пользователя через воронку:")
        for step in journey_log:
            print(f"  {step}")

    def generate_report(self):
        """Генерация отчета о тестировании"""
        print("\n" + "="*60)
        print("📊 ОТЧЕТ О ТЕСТИРОВАНИИ ВОРОНКИ")
        print("="*60)

        total_tests = len(self.test_results)
        passed_tests = sum(1 for test in self.test_results if test['result'])
        failed_tests = total_tests - passed_tests

        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0

        print(f"Всего тестов: {total_tests}")
        print(f"Прошли: {passed_tests}")
        print(f"Провалились: {failed_tests}")
        print(f"Успешность: {success_rate:.1f}%")

        if self.errors:
            print(f"\n❌ ОШИБКИ ({len(self.errors)}):")
            for error in self.errors:
                print(f"  • {error}")
        else:
            print(f"\n✅ ВСЕ ТЕСТЫ ПРОШЛИ УСПЕШНО!")

        return failed_tests == 0

def main():
    """Основная функция запуска тестов"""
    print("🔬 ТЕСТИРОВАНИЕ ВОРОНКИ СООБЩЕНИЙ")
    print("="*50)

    tester = FunnelTester()

    # Запуск всех тестов
    tester.test_funnel_configuration()
    tester.test_message_texts()
    tester.test_funnel_flow_logic()
    tester.test_callback_actions()
    tester.test_price_consistency()
    tester.simulate_user_journey()

    # Генерация отчета
    success = tester.generate_report()

    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
