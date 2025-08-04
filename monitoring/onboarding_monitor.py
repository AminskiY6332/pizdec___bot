#!/usr/bin/env python3
"""
Мониторинг воронки онбординга
Отслеживает отправку сообщений и создает отдельный лог-файл
"""

import asyncio
import logging
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Добавляем путь к проекту
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import TELEGRAM_BOT_TOKEN as TOKEN, ADMIN_IDS
from handlers.onboarding import send_onboarding_message, send_daily_reminders
from database import check_database_user, get_users_for_welcome_message, get_users_for_reminders
from onboarding_config import has_user_purchases

# Создаем директорию для логов мониторинга
MONITORING_LOG_DIR = Path("logs/monitoring")
MONITORING_LOG_DIR.mkdir(parents=True, exist_ok=True)

# Настройка логирования для мониторинга
def setup_monitoring_logger():
    """Настраивает логгер для мониторинга воронки"""
    logger = logging.getLogger('onboarding_monitor')
    logger.setLevel(logging.INFO)

    # Создаем форматтер
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Хендлер для файла
    log_file = MONITORING_LOG_DIR / f"onboarding_monitor_{datetime.now().strftime('%Y%m%d')}.log"
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)

    # Хендлер для консоли
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    # Добавляем хендлеры к логгеру
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger

# Инициализируем логгер
monitor_logger = setup_monitoring_logger()

class OnboardingMonitor:
    """Класс для мониторинга воронки онбординга"""

    def __init__(self):
        self.logger = monitor_logger
        self.stats = {
            'welcome_sent': 0,
            'welcome_failed': 0,
            'reminders_sent': 0,
            'reminders_failed': 0,
            'users_blocked': 0,
            'users_skipped': 0,
            'start_time': datetime.now()
        }

    async def monitor_welcome_messages(self):
        """Мониторинг отправки приветственных сообщений"""
        self.logger.info("=== МОНИТОРИНГ ПРИВЕТСТВЕННЫХ СООБЩЕНИЙ ===")

        try:
            from aiogram import Bot
            bot = Bot(token=TOKEN)

            # Получаем пользователей для приветственного сообщения
            users = await get_users_for_welcome_message()
            self.logger.info(f"Найдено {len(users)} пользователей для приветственного сообщения")

            if not users:
                self.logger.info("Нет пользователей для отправки приветственного сообщения")
                return

            for user in users:
                user_id = user['user_id']
                self.logger.info(f"Обрабатываем пользователя {user_id}")

                try:
                    # Получаем данные пользователя
                    subscription_data = await check_database_user(user_id)
                    if not subscription_data:
                        self.logger.warning(f"Не удалось получить данные пользователя {user_id}")
                        self.stats['welcome_failed'] += 1
                        continue

                    # Отправляем приветственное сообщение
                    await send_onboarding_message(bot, user_id, "welcome", subscription_data)
                    self.logger.info(f"✅ Приветственное сообщение отправлено для user_id={user_id}")
                    self.stats['welcome_sent'] += 1

                except Exception as e:
                    error_msg = str(e)
                    self.logger.error(f"❌ Ошибка отправки приветственного сообщения для user_id={user_id}: {error_msg}")
                    self.stats['welcome_failed'] += 1

                    if "chat not found" in error_msg.lower():
                        self.stats['users_blocked'] += 1
                        self.logger.warning(f"Пользователь {user_id} заблокировал бота")
                    elif "bot can't initiate conversation" in error_msg.lower():
                        self.stats['users_skipped'] += 1
                        self.logger.warning(f"Пользователь {user_id} не начал диалог с ботом")

            await bot.session.close()

        except Exception as e:
            self.logger.error(f"Ошибка мониторинга приветственных сообщений: {e}", exc_info=True)

    async def monitor_daily_reminders(self):
        """Мониторинг отправки ежедневных напоминаний"""
        self.logger.info("=== МОНИТОРИНГ ЕЖЕДНЕВНЫХ НАПОМИНАНИЙ ===")

        try:
            from aiogram import Bot
            bot = Bot(token=TOKEN)

            # Получаем пользователей для напоминаний
            users = await get_users_for_reminders()
            self.logger.info(f"Найдено {len(users)} пользователей для ежедневных напоминаний")

            if not users:
                self.logger.info("Нет пользователей для отправки ежедневных напоминаний")
                return

            for user in users:
                user_id = user['user_id']
                self.logger.info(f"Обрабатываем пользователя {user_id}")

                try:
                    # Получаем данные пользователя
                    subscription_data = await check_database_user(user_id)
                    if not subscription_data:
                        self.logger.warning(f"Не удалось получить данные пользователя {user_id}")
                        self.stats['reminders_failed'] += 1
                        continue

                    # Определяем тип напоминания
                    last_reminder = subscription_data[12] if len(subscription_data) > 12 else None
                    reminder_type = self._get_next_reminder_type(last_reminder)

                    if reminder_type:
                        # Отправляем напоминание
                        await send_onboarding_message(bot, user_id, reminder_type, subscription_data)
                        self.logger.info(f"✅ Напоминание {reminder_type} отправлено для user_id={user_id}")
                        self.stats['reminders_sent'] += 1
                    else:
                        self.logger.info(f"Пропускаем пользователя {user_id} - нет подходящего напоминания")
                        self.stats['users_skipped'] += 1

                except Exception as e:
                    error_msg = str(e)
                    self.logger.error(f"❌ Ошибка отправки напоминания для user_id={user_id}: {error_msg}")
                    self.stats['reminders_failed'] += 1

                    if "chat not found" in error_msg.lower():
                        self.stats['users_blocked'] += 1
                        self.logger.warning(f"Пользователь {user_id} заблокировал бота")
                    elif "bot can't initiate conversation" in error_msg.lower():
                        self.stats['users_skipped'] += 1
                        self.logger.warning(f"Пользователь {user_id} не начал диалог с ботом")

            await bot.session.close()

        except Exception as e:
            self.logger.error(f"Ошибка мониторинга ежедневных напоминаний: {e}", exc_info=True)

    def _get_next_reminder_type(self, last_reminder):
        """Определяет следующий тип напоминания"""
        if not last_reminder:
            return "reminder_day2"

        reminder_map = {
            "reminder_day2": "reminder_day3",
            "reminder_day3": "reminder_day4",
            "reminder_day4": "reminder_day5",
            "reminder_day5": None  # Конец воронки
        }

        return reminder_map.get(last_reminder)

    def print_statistics(self):
        """Выводит статистику мониторинга"""
        duration = datetime.now() - self.stats['start_time']

        self.logger.info("=== СТАТИСТИКА МОНИТОРИНГА ===")
        self.logger.info(f"Время выполнения: {duration}")
        self.logger.info(f"Приветственных сообщений отправлено: {self.stats['welcome_sent']}")
        self.logger.info(f"Приветственных сообщений не отправлено: {self.stats['welcome_failed']}")
        self.logger.info(f"Напоминаний отправлено: {self.stats['reminders_sent']}")
        self.logger.info(f"Напоминаний не отправлено: {self.stats['reminders_failed']}")
        self.logger.info(f"Пользователей заблокировали бота: {self.stats['users_blocked']}")
        self.logger.info(f"Пользователей пропущено: {self.stats['users_skipped']}")

        total_processed = (self.stats['welcome_sent'] + self.stats['welcome_failed'] +
                         self.stats['reminders_sent'] + self.stats['reminders_failed'])

        if total_processed > 0:
            success_rate = ((self.stats['welcome_sent'] + self.stats['reminders_sent']) / total_processed) * 100
            self.logger.info(f"Процент успешных отправок: {success_rate:.1f}%")

        self.logger.info("=== КОНЕЦ СТАТИСТИКИ ===")

async def run_monitoring():
    """Запускает мониторинг воронки"""
    monitor = OnboardingMonitor()

    try:
        # Мониторинг приветственных сообщений
        await monitor.monitor_welcome_messages()

        # Мониторинг ежедневных напоминаний
        await monitor.monitor_daily_reminders()

        # Выводим статистику
        monitor.print_statistics()

    except Exception as e:
        monitor.logger.error(f"Ошибка выполнения мониторинга: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(run_monitoring())
