#!/usr/bin/env python3
"""
Модуль для подсчета пользователей и обновления имени бота
"""

import asyncio
import logging
from typing import Optional
from aiogram import Bot, Router
from aiogram.types import BotCommand, BotCommandScopeDefault, Message
from database import get_total_users_count

# Создаем роутер для bot_counter
bot_counter_router = Router()

# Логгер
from logger import get_logger
logger = get_logger('bot_counter')


class BotCounter:
    """Класс для управления счетчиком пользователей в имени бота"""

    def __init__(self):
        self.bot: Optional[Bot] = None
        self.current_count = 0
        self.update_interval = 300  # 5 минут
        self.running = False

    async def start(self, bot: Bot):
        """Запуск счетчика пользователей (только для подсчета)"""
        self.bot = bot
        self.running = True
        logger.info("🔢 Счетчик пользователей запущен (без обновления имени)")

        # УДАЛЕНО: автоматическое обновление имени бота

    async def stop(self):
        """Остановка счетчика"""
        self.running = False
        logger.info("🔢 Счетчик пользователей остановлен")

    async def get_total_count(self) -> int:
        """Получить общее количество пользователей"""
        try:
            count = await get_total_users_count()
            self.current_count = count
            return count
        except Exception as e:
            logger.error(f"Ошибка получения количества пользователей: {e}")
            return self.current_count

    def format_number(self, number: int) -> str:
        """Форматирование числа для отображения"""
        if number >= 1000000:
            return f"{number / 1000000:.1f}М"
        elif number >= 1000:
            return f"{number / 1000:.1f}К"
        else:
            return str(number)

    # УДАЛЕНО: функции обновления имени бота
    # Функции update_bot_name() и _update_loop() удалены по запросу пользователя


# Создаем глобальный экземпляр
bot_counter = BotCounter()


# УДАЛЕНО: команда /botname
# Функция cmd_bot_name() удалена по запросу пользователя


async def update_bot_commands(bot: Bot):
    """Обновление команд бота"""
    try:
        commands = [
            BotCommand(command="start", description="🚀 Запустить бота"),
            BotCommand(command="menu", description="📋 Главное меню"),
            BotCommand(command="help", description="❓ Помощь"),
        ]

        await bot.set_my_commands(commands, scope=BotCommandScopeDefault())
        logger.info("✅ Команды бота обновлены")

    except Exception as e:
        logger.error(f"Ошибка обновления команд бота: {e}")
