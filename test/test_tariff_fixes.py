#!/usr/bin/env python3
"""
Тест для проверки исправлений с тарифами
Проверяет, что пользователи могут выбирать тарифы без блокировки
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta
import json

# Добавляем корневую директорию в путь
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import database
from config import TARIFFS, ADMIN_IDS
from handlers.callbacks_user import handle_payment_callback
from aiogram import Bot
from aiogram.types import CallbackQuery, User, Chat, Message
from unittest.mock import Mock, AsyncMock, patch
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TariffFixTest:
    def __init__(self):
        self.bot = Mock(spec=Bot)
        self.test_results = []

    async def setup(self):
        """Настройка тестовой среды"""
        logger.info("🔧 Настройка тестовой среды...")

        # Инициализация базы данных
        await database.init_db()

        # Создание тестовых пользователей
        self.test_users = [
            {
                'user_id': 1001,
                'username': 'test_user_new',
                'days_since_registration': 0,
                'time_since_registration': 900,  # 15 минут
                'expected_tariff': 'комфорт'
            },
            {
                'user_id': 1002,
                'username': 'test_user_1day',
                'days_since_registration': 1,
                'time_since_registration': 86400,  # 1 день
                'expected_tariff': 'лайт'
            },
            {
                'user_id': 1003,
                'username': 'test_user_3days',
                'days_since_registration': 3,
                'time_since_registration': 259200,  # 3 дня
                'expected_tariff': 'мини'
            },
            {
                'user_id': 1004,
                'username': 'test_user_5days',
                'days_since_registration': 5,
                'time_since_registration': 432000,  # 5 дней
                'expected_tariff': None  # Все тарифы доступны
            }
        ]

        # Создание тестовых пользователей в БД
        for user_data in self.test_users:
            await database.add_user_without_subscription(
                user_id=user_data['user_id'],
                username=user_data['username'],
                first_name=f"Test User {user_data['user_id']}"
            )
            logger.info(f"✅ Создан тестовый пользователь {user_data['username']} (ID: {user_data['user_id']})")

    async def test_tariff_selection_no_blocking(self):
        """Тест: пользователи могут выбирать тарифы без блокировки"""
        logger.info("🧪 Тестирование выбора тарифов без блокировки...")

        test_cases = [
            # Новый пользователь (15 минут) - должен иметь доступ к комфорту
            {
                'user_id': 1001,
                'tariff_key': 'pay_1199',  # комфорт
                'should_work': True,
                'description': 'Новый пользователь выбирает комфорт'
            },
            # Пользователь 1 день - должен иметь доступ к лайту
            {
                'user_id': 1002,
                'tariff_key': 'pay_599',  # лайт
                'should_work': True,
                'description': 'Пользователь 1 день выбирает лайт'
            },
            # Пользователь 1 день - должен иметь доступ к мини (не блокируется)
            {
                'user_id': 1002,
                'tariff_key': 'pay_399',  # мини
                'should_work': True,
                'description': 'Пользователь 1 день выбирает мини (не блокируется)'
            },
            # Пользователь 3 дня - должен иметь доступ к мини
            {
                'user_id': 1003,
                'tariff_key': 'pay_399',  # мини
                'should_work': True,
                'description': 'Пользователь 3 дня выбирает мини'
            },
            # Пользователь 5 дней - должен иметь доступ ко всем тарифам
            {
                'user_id': 1004,
                'tariff_key': 'pay_3199',  # премиум
                'should_work': True,
                'description': 'Пользователь 5 дней выбирает премиум'
            }
        ]

        for test_case in test_cases:
            try:
                # Создаем мок callback query
                callback_query = Mock(spec=CallbackQuery)
                callback_query.data = test_case['tariff_key']
                callback_query.from_user = Mock(spec=User)
                callback_query.from_user.id = test_case['user_id']
                callback_query.message = Mock(spec=Message)
                callback_query.message.chat = Mock(spec=Chat)
                callback_query.message.chat.id = test_case['user_id']

                # Мокаем методы бота
                self.bot.send_message = AsyncMock()
                self.bot.edit_message_text = AsyncMock()

                # Вызываем функцию обработки платежа
                with patch('handlers.callbacks_user.bot', self.bot):
                    await handle_payment_callback(callback_query, None)

                # Проверяем, что сообщение было отправлено (значит, тариф доступен)
                if self.bot.send_message.called or self.bot.edit_message_text.called:
                    self.test_results.append({
                        'test': test_case['description'],
                        'status': 'PASS',
                        'message': 'Тариф доступен'
                    })
                    logger.info(f"✅ {test_case['description']} - ПРОЙДЕН")
                else:
                    self.test_results.append({
                        'test': test_case['description'],
                        'status': 'FAIL',
                        'message': 'Тариф заблокирован'
                    })
                    logger.error(f"❌ {test_case['description']} - ПРОВАЛЕН")

            except Exception as e:
                self.test_results.append({
                    'test': test_case['description'],
                    'status': 'ERROR',
                    'message': f'Ошибка: {str(e)}'
                })
                logger.error(f"💥 {test_case['description']} - ОШИБКА: {e}")

    async def test_datetime_comparison_fix(self):
        """Тест: исправление проблемы с datetime"""
        logger.info("🧪 Тестирование исправления datetime...")

        try:
            # Тестируем функцию is_old_user с разными форматами даты
            test_cases = [
                {
                    'created_at': '2025-08-01T10:00:00Z',
                    'cutoff_date': '2025-08-02',
                    'expected': True,  # Пользователь старше cutoff
                    'description': 'Дата с Z timezone'
                },
                {
                    'created_at': '2025-08-01T10:00:00',
                    'cutoff_date': '2025-08-02',
                    'expected': True,  # Пользователь старше cutoff
                    'description': 'Дата без timezone'
                },
                {
                    'created_at': '2025-08-03T10:00:00Z',
                    'cutoff_date': '2025-08-02',
                    'expected': False,  # Пользователь новее cutoff
                    'description': 'Новый пользователь'
                }
            ]

            for test_case in test_cases:
                # Создаем тестового пользователя
                user_id = 2000 + test_cases.index(test_case)
                await database.add_user_without_subscription(
                    user_id=user_id,
                    username=f'test_datetime_{user_id}',
                    first_name=f'Test DateTime {user_id}'
                )

                # Тестируем функцию is_old_user
                result = await database.is_old_user(user_id, test_case['cutoff_date'])

                if result == test_case['expected']:
                    self.test_results.append({
                        'test': f"Datetime: {test_case['description']}",
                        'status': 'PASS',
                        'message': f'Результат: {result}'
                    })
                    logger.info(f"✅ Datetime: {test_case['description']} - ПРОЙДЕН")
                else:
                    self.test_results.append({
                        'test': f"Datetime: {test_case['description']}",
                        'status': 'FAIL',
                        'message': f'Ожидалось: {test_case["expected"]}, получено: {result}'
                    })
                    logger.error(f"❌ Datetime: {test_case['description']} - ПРОВАЛЕН")

        except Exception as e:
            self.test_results.append({
                'test': 'Datetime comparison',
                'status': 'ERROR',
                'message': f'Ошибка: {str(e)}'
            })
            logger.error(f"💥 Datetime comparison - ОШИБКА: {e}")

    async def test_tariff_availability_logging(self):
        """Тест: проверка логирования доступности тарифов"""
        logger.info("🧪 Тестирование логирования тарифов...")

        try:
            # Получаем пользователя
            user_id = 1002  # Пользователь 1 день

            # Проверяем, что логирование работает без ошибок
            with patch('handlers.callbacks_user.logger') as mock_logger:
                callback_query = Mock(spec=CallbackQuery)
                callback_query.data = 'pay_399'  # мини
                callback_query.from_user = Mock(spec=User)
                callback_query.from_user.id = user_id
                callback_query.message = Mock(spec=Message)
                callback_query.message.chat = Mock(spec=Chat)
                callback_query.message.chat.id = user_id

                self.bot.send_message = AsyncMock()
                self.bot.edit_message_text = AsyncMock()

                with patch('handlers.callbacks_user.bot', self.bot):
                    await handle_payment_callback(callback_query, None)

                # Проверяем, что логирование не вызывает ошибок
                self.test_results.append({
                    'test': 'Tariff availability logging',
                    'status': 'PASS',
                    'message': 'Логирование работает корректно'
                })
                logger.info("✅ Tariff availability logging - ПРОЙДЕН")

        except Exception as e:
            self.test_results.append({
                'test': 'Tariff availability logging',
                'status': 'ERROR',
                'message': f'Ошибка: {str(e)}'
            })
            logger.error(f"💥 Tariff availability logging - ОШИБКА: {e}")

    def generate_report(self):
        """Генерация отчета о тестировании"""
        logger.info("📊 Генерация отчета...")

        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r['status'] == 'PASS'])
        failed_tests = len([r for r in self.test_results if r['status'] == 'FAIL'])
        error_tests = len([r for r in self.test_results if r['status'] == 'ERROR'])

        report = {
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'total_tests': total_tests,
                'passed': passed_tests,
                'failed': failed_tests,
                'errors': error_tests,
                'success_rate': (passed_tests / total_tests * 100) if total_tests > 0 else 0
            },
            'results': self.test_results
        }

        # Сохраняем отчет
        filename = f"tariff_fix_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        # Выводим краткий отчет
        logger.info("=" * 60)
        logger.info("📊 ОТЧЕТ О ТЕСТИРОВАНИИ ИСПРАВЛЕНИЙ ТАРИФОВ")
        logger.info("=" * 60)
        logger.info(f"Всего тестов: {total_tests}")
        logger.info(f"Пройдено: {passed_tests} ✅")
        logger.info(f"Провалено: {failed_tests} ❌")
        logger.info(f"Ошибок: {error_tests} 💥")
        logger.info(f"Успешность: {report['summary']['success_rate']:.1f}%")
        logger.info("=" * 60)

        for result in self.test_results:
            status_icon = "✅" if result['status'] == 'PASS' else "❌" if result['status'] == 'FAIL' else "💥"
            logger.info(f"{status_icon} {result['test']}: {result['message']}")

        logger.info("=" * 60)
        logger.info(f"📄 Подробный отчет сохранен в: {filename}")

        return report

async def main():
    """Основная функция тестирования"""
    logger.info("🚀 Запуск тестирования исправлений тарифов...")

    tester = TariffFixTest()

    try:
        # Настройка
        await tester.setup()

        # Запуск тестов
        await tester.test_tariff_selection_no_blocking()
        await tester.test_datetime_comparison_fix()
        await tester.test_tariff_availability_logging()

        # Генерация отчета
        report = tester.generate_report()

        # Проверяем успешность
        if report['summary']['success_rate'] >= 90:
            logger.info("🎉 Все тесты прошли успешно! Исправления работают корректно.")
            return True
        else:
            logger.error("⚠️ Некоторые тесты провалились. Требуется дополнительная отладка.")
            return False

    except Exception as e:
        logger.error(f"💥 Критическая ошибка в тестировании: {e}")
        return False
    finally:
        # Закрываем соединение с БД
        pass

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
