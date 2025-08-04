#!/usr/bin/env python3
"""
Улучшенная система обработки ошибок
Автоматически уведомляет разработчиков о критических ошибках
"""

import asyncio
import logging
import traceback
import sys
from datetime import datetime
from typing import Dict, Any, Optional
from aiogram import Bot
from aiogram.types import Update
from aiogram.exceptions import TelegramAPIError, TelegramForbiddenError
import pytz
from aiogram.enums import ParseMode

from config import ADMIN_IDS, ERROR_LOG_ADMIN
from handlers.utils import send_message_with_fallback, safe_escape_markdown as escape_md
from logger import get_logger

logger = get_logger('errors')

class ErrorHandler:
    """Система обработки ошибок с уведомлениями"""

    def __init__(self, bot: Bot):
        self.bot = bot
        self.moscow_tz = pytz.timezone('Europe/Moscow')
        self.error_counts = {}  # Счетчик ошибок для предотвращения спама
        self.critical_errors = set()  # Множество критических ошибок

    async def handle_error(self, update: Update, exception: Exception) -> bool:
        """
        Обрабатывает ошибки и отправляет уведомления разработчикам

        Args:
            update: Объект обновления Telegram
            exception: Исключение

        Returns:
            bool: True если ошибка обработана, False если нужно продолжить обработку
        """
        try:
            # Получаем информацию об ошибке
            error_info = self._extract_error_info(update, exception)

            # Логируем ошибку
            logger.error(f"Ошибка в обработке: {error_info['message']}", exc_info=True)

            # Проверяем, является ли ошибка критической
            if self._is_critical_error(exception):
                await self._send_critical_error_notification(error_info)

            # Проверяем, нужно ли уведомить разработчиков
            if self._should_notify_developers(error_info):
                await self._send_developer_notification(error_info)

            # Обрабатываем специальные случаи
            if isinstance(exception, TelegramForbiddenError):
                return await self._handle_forbidden_error(update, exception)

            return True

        except Exception as e:
            logger.error(f"Ошибка в обработчике ошибок: {e}", exc_info=True)
            return False

    def _extract_error_info(self, update: Update, exception: Exception) -> Dict[str, Any]:
        """Извлекает информацию об ошибке"""
        error_info = {
            'timestamp': datetime.now(self.moscow_tz).strftime('%Y-%m-%d %H:%M:%S MSK'),
            'exception_type': type(exception).__name__,
            'message': str(exception),
            'traceback': traceback.format_exc(),
            'update_type': update.__class__.__name__,
            'user_id': None,
            'chat_id': None,
            'update_data': {}
        }

        # Извлекаем информацию о пользователе
        if update.message:
            error_info['user_id'] = update.message.from_user.id if update.message.from_user else None
            error_info['chat_id'] = update.message.chat.id
            error_info['update_data'] = {
                'text': update.message.text[:100] if update.message.text else None,
                'content_type': update.message.content_type
            }
        elif update.callback_query:
            error_info['user_id'] = update.callback_query.from_user.id if update.callback_query.from_user else None
            error_info['chat_id'] = update.callback_query.message.chat.id if update.callback_query.message else None
            error_info['update_data'] = {
                'callback_data': update.callback_query.data
            }

        return error_info

    def _is_critical_error(self, exception: Exception) -> bool:
        """Проверяет, является ли ошибка критической"""
        critical_patterns = [
            'Database locked',
            'Connection failed',
            'Timeout',
            'MemoryError',
            'OutOfMemory',
            'Disk full',
            'Permission denied',
            'File not found',
            'ImportError',
            'ModuleNotFoundError'
        ]

        error_message = str(exception).lower()
        return any(pattern.lower() in error_message for pattern in critical_patterns)

    def _should_notify_developers(self, error_info: Dict[str, Any]) -> bool:
        """Проверяет, нужно ли уведомить разработчиков"""
        # Создаем ключ для подсчета ошибок
        error_key = f"{error_info['exception_type']}:{error_info['message'][:50]}"

        # Увеличиваем счетчик
        self.error_counts[error_key] = self.error_counts.get(error_key, 0) + 1

        # Уведомляем если:
        # 1. Это критическая ошибка
        # 2. Ошибка повторяется более 3 раз
        # 3. Это новая ошибка (не в множестве критических)

        if self._is_critical_error(Exception(error_info['message'])):
            if error_key not in self.critical_errors:
                self.critical_errors.add(error_key)
                return True

        if self.error_counts[error_key] >= 3:
            return True

        return False

    async def _send_critical_error_notification(self, error_info: Dict[str, Any]):
        """Отправляет уведомление о критической ошибке"""
        try:
            message_parts = [
                f"🚨 КРИТИЧЕСКАЯ ОШИБКА ({error_info['timestamp']})",
                f"❌ Тип: {error_info['exception_type']}",
                f"💬 Сообщение: {error_info['message']}",
            ]

            if error_info['user_id']:
                message_parts.append(f"👤 User ID: {error_info['user_id']}")

            if error_info['chat_id']:
                message_parts.append(f"💬 Chat ID: {error_info['chat_id']}")

            message_parts.append(f"📋 Update: {error_info['update_type']}")

            # Добавляем первые строки трейсбека
            traceback_lines = error_info['traceback'].split('\n')[:5]
            message_parts.append(f"🔍 Traceback:\n{chr(10).join(traceback_lines)}")

            message = escape_md("\n".join(message_parts), version=2)

            # Отправляем главному разработчику (ERROR_LOG_ADMIN)
            for admin_id in ERROR_LOG_ADMIN:
                try:
                    await send_message_with_fallback(
                        self.bot, admin_id, message,
                        parse_mode=ParseMode.MARKDOWN_V2
                    )
                except Exception as e:
                    logger.error(f"Ошибка отправки уведомления о критической ошибке главному разработчику {admin_id}: {e}")

        except Exception as e:
            logger.error(f"Ошибка отправки уведомления о критической ошибке: {e}")

    async def _send_developer_notification(self, error_info: Dict[str, Any]):
        """Отправляет уведомление разработчикам"""
        try:
            message_parts = [
                f"⚠️ ОШИБКА БОТА ({error_info['timestamp']})",
                f"❌ Тип: {error_info['exception_type']}",
                f"💬 Сообщение: {error_info['message']}",
            ]

            if error_info['user_id']:
                message_parts.append(f"👤 User ID: {error_info['user_id']}")

            if error_info['update_data']:
                message_parts.append(f"📋 Данные: {str(error_info['update_data'])[:100]}...")

            message = escape_md("\n".join(message_parts), version=2)

            # Отправляем главному разработчику (ERROR_LOG_ADMIN)
            for admin_id in ERROR_LOG_ADMIN:
                try:
                    await send_message_with_fallback(
                        self.bot, admin_id, message,
                        parse_mode=ParseMode.MARKDOWN_V2
                    )
                except Exception as e:
                    logger.error(f"Ошибка отправки уведомления главному разработчику {admin_id}: {e}")

        except Exception as e:
            logger.error(f"Ошибка отправки уведомления разработчику: {e}")

    async def _handle_forbidden_error(self, update: Update, exception: TelegramForbiddenError) -> bool:
        """Обрабатывает ошибки запрета доступа"""
        try:
            # Проверяем, заблокировал ли пользователь бота
            error_message = str(exception)
            if "bot was blocked by the user" in error_message.lower():
                # Импортируем функцию обработки блокировки
                from handlers.utils import handle_user_blocked_bot

                user_id = None
                if update.message:
                    user_id = update.message.from_user.id
                elif update.callback_query:
                    user_id = update.callback_query.from_user.id

                if user_id:
                    await handle_user_blocked_bot(user_id, error_message)
                    logger.info(f"Пользователь {user_id} заблокировал бота, данные удалены")

                return True

            return False

        except Exception as e:
            logger.error(f"Ошибка обработки forbidden error: {e}")
            return False

    async def send_error_summary(self):
        """Отправляет сводку ошибок за день"""
        try:
            if not self.error_counts:
                return

            timestamp = datetime.now(self.moscow_tz).strftime('%Y-%m-%d %H:%M:%S MSK')

            message_parts = [
                f"📊 СВОДКА ОШИБОК ({timestamp})",
                f"❌ Всего ошибок: {sum(self.error_counts.values())}",
                f"🔍 Уникальных ошибок: {len(self.error_counts)}"
            ]

            # Топ-5 ошибок
            top_errors = sorted(self.error_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            if top_errors:
                message_parts.append("\n🔥 ТОП ОШИБОК:")
                for error_key, count in top_errors:
                    error_type = error_key.split(':')[0]
                    message_parts.append(f"• {error_type}: {count} раз")

            message = escape_md("\n".join(message_parts), version=2)

            # Отправляем главному разработчику (ERROR_LOG_ADMIN)
            for admin_id in ERROR_LOG_ADMIN:
                try:
                    await send_message_with_fallback(
                        self.bot, admin_id, message,
                        parse_mode=ParseMode.MARKDOWN_V2
                    )
                except Exception as e:
                    logger.error(f"Ошибка отправки сводки ошибок главному разработчику {admin_id}: {e}")

        except Exception as e:
            logger.error(f"Ошибка отправки сводки ошибок: {e}")

    def reset_error_counts(self):
        """Сбрасывает счетчики ошибок"""
        self.error_counts.clear()
        self.critical_errors.clear()

# Глобальный экземпляр обработчика ошибок
error_handler_instance = None

def get_error_handler(bot: Bot) -> ErrorHandler:
    """Получает или создает экземпляр обработчика ошибок"""
    global error_handler_instance
    if error_handler_instance is None:
        error_handler_instance = ErrorHandler(bot)
    return error_handler_instance

async def error_handler(update: Update, exception: Exception) -> bool:
    """Глобальный обработчик ошибок"""
    if error_handler_instance:
        return await error_handler_instance.handle_error(update, exception)
    else:
        logger.error(f"Ошибка в обработке: {exception}", exc_info=True)
        return True
