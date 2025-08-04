#!/usr/bin/env python3
"""
Простой тест для проверки исправлений с тарифами
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta
import json

# Добавляем корневую директорию в путь
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import database
from config import TARIFFS
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_datetime_fix():
    """Тест исправления проблемы с datetime"""
    logger.info("🧪 Тестирование исправления datetime...")

    try:
        # Создаем тестового пользователя
        user_id = 9999
        await database.add_user_without_subscription(
            user_id=user_id,
            username='test_datetime_user',
            first_name='Test DateTime User'
        )

        # Тестируем функцию is_old_user с разными форматами даты
        test_cases = [
            {
                'cutoff_date': '2025-08-01',
                'expected': False,  # Пользователь новее cutoff
                'description': 'Новый пользователь'
            }
        ]

        for test_case in test_cases:
            result = await database.is_old_user(user_id, test_case['cutoff_date'])

            if result == test_case['expected']:
                logger.info(f"✅ Datetime: {test_case['description']} - ПРОЙДЕН")
                return True
            else:
                logger.error(f"❌ Datetime: {test_case['description']} - ПРОВАЛЕН")
                return False

    except Exception as e:
        logger.error(f"💥 Datetime comparison - ОШИБКА: {e}")
        return False

async def test_tariff_config():
    """Тест конфигурации тарифов"""
    logger.info("🧪 Тестирование конфигурации тарифов...")

    try:
        # Проверяем, что все тарифы доступны
        required_tariffs = ['pay_399', 'pay_599', 'pay_1199', 'pay_3199']

        for tariff_key in required_tariffs:
            # Ищем тариф по callback значению
            found = False
            for tariff_name, tariff_data in TARIFFS.items():
                if tariff_data.get('callback') == tariff_key:
                    logger.info(f"✅ Тариф {tariff_key} ({tariff_data['name']}) доступен")
                    found = True
                    break

            if not found:
                logger.error(f"❌ Тариф {tariff_key} отсутствует")
                return False

        logger.info("✅ Все тарифы доступны")
        return True

    except Exception as e:
        logger.error(f"💥 Tariff config - ОШИБКА: {e}")
        return False

async def test_user_creation():
    """Тест создания пользователей"""
    logger.info("🧪 Тестирование создания пользователей...")

    try:
        # Создаем тестового пользователя
        user_id = 8888
        await database.add_user_without_subscription(
            user_id=user_id,
            username='test_user_creation',
            first_name='Test User Creation'
        )

        # Проверяем, что пользователь создан
        user_info = await database.get_user_info(user_id)

        if user_info:
            logger.info(f"✅ Пользователь {user_id} создан успешно")
            return True
        else:
            logger.error(f"❌ Пользователь {user_id} не найден")
            return False

    except Exception as e:
        logger.error(f"💥 User creation - ОШИБКА: {e}")
        return False

async def main():
    """Основная функция тестирования"""
    logger.info("🚀 Запуск простого тестирования исправлений тарифов...")

    # Инициализация базы данных
    await database.init_db()

    results = []

    # Запуск тестов
    tests = [
        ("Datetime fix", test_datetime_fix),
        ("Tariff config", test_tariff_config),
        ("User creation", test_user_creation)
    ]

    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append({
                'test': test_name,
                'status': 'PASS' if result else 'FAIL',
                'message': 'Тест пройден' if result else 'Тест провален'
            })
        except Exception as e:
            results.append({
                'test': test_name,
                'status': 'ERROR',
                'message': f'Ошибка: {str(e)}'
            })

    # Генерация отчета
    total_tests = len(results)
    passed_tests = len([r for r in results if r['status'] == 'PASS'])
    failed_tests = len([r for r in results if r['status'] == 'FAIL'])
    error_tests = len([r for r in results if r['status'] == 'ERROR'])

    logger.info("=" * 60)
    logger.info("📊 ОТЧЕТ О ПРОСТОМ ТЕСТИРОВАНИИ ИСПРАВЛЕНИЙ ТАРИФОВ")
    logger.info("=" * 60)
    logger.info(f"Всего тестов: {total_tests}")
    logger.info(f"Пройдено: {passed_tests} ✅")
    logger.info(f"Провалено: {failed_tests} ❌")
    logger.info(f"Ошибок: {error_tests} 💥")
    logger.info(f"Успешность: {(passed_tests / total_tests * 100) if total_tests > 0 else 0:.1f}%")
    logger.info("=" * 60)

    for result in results:
        status_icon = "✅" if result['status'] == 'PASS' else "❌" if result['status'] == 'FAIL' else "💥"
        logger.info(f"{status_icon} {result['test']}: {result['message']}")

    logger.info("=" * 60)

    # Сохраняем отчет
    report = {
        'timestamp': datetime.now().isoformat(),
        'summary': {
            'total_tests': total_tests,
            'passed': passed_tests,
            'failed': failed_tests,
            'errors': error_tests,
            'success_rate': (passed_tests / total_tests * 100) if total_tests > 0 else 0
        },
        'results': results
    }

    filename = f"simple_tariff_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    logger.info(f"📄 Подробный отчет сохранен в: {filename}")

    # Проверяем успешность
    if passed_tests == total_tests:
        logger.info("🎉 Все тесты прошли успешно! Исправления работают корректно.")
        return True
    else:
        logger.error("⚠️ Некоторые тесты провалились. Требуется дополнительная отладка.")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
