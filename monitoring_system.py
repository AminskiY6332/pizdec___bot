#!/usr/bin/env python3
"""
Комплексная система мониторинга бота
Проверяет: обученные аватары, платежи, критические ошибки
"""

import asyncio
import aiosqlite
import logging
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import json
import pytz
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode

# Импорты из проекта
from config import ADMIN_IDS, ERROR_LOG_ADMIN, DATABASE_PATH
from database import check_database_user, get_user_trainedmodels, get_payments_by_date
from handlers.utils import send_message_with_fallback, safe_escape_markdown as escape_md
from logger import get_logger

logger = get_logger('monitoring')

class BotMonitoringSystem:
    """Система мониторинга бота"""

    def __init__(self, bot: Bot):
        self.bot = bot
        self.moscow_tz = pytz.timezone('Europe/Moscow')
        self.critical_errors = []
        self.warnings = []

    async def check_trained_avatars(self) -> Dict:
        """Проверка обученных аватаров и отправка уведомлений"""
        try:
            logger.info("🔍 Проверка обученных аватаров...")

            # Проверяем аватары за последние 6 часов (поскольку отчет запускается каждые 6 часов)
            six_hours_ago = datetime.now() - timedelta(hours=6)

            async with aiosqlite.connect(DATABASE_PATH) as conn:
                cursor = await conn.cursor()

                # Получаем аватары со статусом 'success' за последние 6 часов
                await cursor.execute("""
                    SELECT user_id, avatar_name, model_version, created_at, updated_at
                    FROM user_trainedmodels
                    WHERE status = 'success' AND updated_at > ?
                    ORDER BY updated_at DESC
                """, (six_hours_ago.strftime('%Y-%m-%d %H:%M:%S'),))

                successful_avatars = await cursor.fetchall()

                # Получаем аватары в процессе обучения (все текущие)
                await cursor.execute("""
                    SELECT user_id, avatar_name, status, created_at
                    FROM user_trainedmodels
                    WHERE status IN ('pending', 'starting', 'processing')
                    ORDER BY created_at DESC
                """)

                training_avatars = await cursor.fetchall()

                # Получаем неудачные аватары за последние 6 часов
                await cursor.execute("""
                    SELECT user_id, avatar_name, status, created_at
                    FROM user_trainedmodels
                    WHERE status IN ('failed', 'canceled')
                    AND created_at > ?
                    ORDER BY created_at DESC
                """, (six_hours_ago.strftime('%Y-%m-%d %H:%M:%S'),))

                failed_avatars = await cursor.fetchall()

            # Формируем отчет
            report = {
                'successful_count': len(successful_avatars),
                'training_count': len(training_avatars),
                'failed_count': len(failed_avatars),
                'successful_avatars': successful_avatars[:10],  # Топ 10
                'training_avatars': training_avatars,
                'failed_avatars': failed_avatars
            }

            # Отправляем уведомления админам
            await self._send_avatar_report(report)

            logger.info(f"✅ Проверка аватаров завершена: {report['successful_count']} успешных, {report['training_count']} в обучении, {report['failed_count']} неудачных")
            return report

        except Exception as e:
            error_msg = f"Ошибка проверки аватаров: {str(e)}"
            logger.error(error_msg, exc_info=True)
            await self._send_critical_error("Проверка аватаров", error_msg)
            return {'error': error_msg}

    async def check_payments(self) -> Dict:
        """Проверка платежей и отправка уведомлений"""
        try:
            logger.info("🔍 Проверка платежей...")

            # Получаем платежи за последние 24 часа
            yesterday = datetime.now() - timedelta(days=1)
            payments = await get_payments_by_date(
                start_date=yesterday.strftime('%Y-%m-%d'),
                end_date=datetime.now().strftime('%Y-%m-%d')
            )

            # Анализируем платежи
            successful_payments = [p for p in payments if p[3] == 'succeeded']
            failed_payments = [p for p in payments if p[3] != 'succeeded']

            total_amount = sum(p[2] for p in successful_payments)

            report = {
                'total_payments': len(payments),
                'successful_payments': len(successful_payments),
                'failed_payments': len(failed_payments),
                'total_amount': total_amount,
                'recent_payments': payments[:10]  # Последние 10 платежей
            }

            # Отправляем уведомления админам
            await self._send_payment_report(report)

            logger.info(f"✅ Проверка платежей завершена: {report['successful_payments']} успешных, {report['total_amount']:.2f}₽")
            return report

        except Exception as e:
            error_msg = f"Ошибка проверки платежей: {str(e)}"
            logger.error(error_msg, exc_info=True)
            await self._send_critical_error("Проверка платежей", error_msg)
            return {'error': error_msg}

    async def check_critical_errors(self) -> Dict:
        """Проверка критических ошибок в логах"""
        try:
            logger.info("🔍 Проверка критических ошибок...")

            # Проверяем последние логи на критические ошибки
            critical_keywords = [
                'CRITICAL', 'FATAL', 'Критическая ошибка', 'Critical error',
                'Database locked', 'Connection failed', 'Timeout',
                'MemoryError', 'OutOfMemory', 'Disk full'
            ]

            errors_found = []

            # Проверяем основные лог-файлы
            log_files = ['bot.log', 'logs/errors.log', 'logs/database.log']

            for log_file in log_files:
                if os.path.exists(log_file):
                    try:
                        with open(log_file, 'r', encoding='utf-8') as f:
                            lines = f.readlines()
                            # Проверяем последние 1000 строк
                            recent_lines = lines[-1000:] if len(lines) > 1000 else lines

                            for line in recent_lines:
                                for keyword in critical_keywords:
                                    if keyword.lower() in line.lower():
                                        errors_found.append({
                                            'file': log_file,
                                            'line': line.strip(),
                                            'keyword': keyword
                                        })
                                        break
                    except Exception as e:
                        logger.warning(f"Не удалось прочитать лог-файл {log_file}: {e}")

            report = {
                'errors_found': len(errors_found),
                'critical_errors': errors_found[:20]  # Топ 20 ошибок
            }

            # Если найдены критические ошибки, отправляем уведомление
            if errors_found:
                await self._send_critical_errors_report(report)

            logger.info(f"✅ Проверка критических ошибок завершена: найдено {len(errors_found)} ошибок")
            return report

        except Exception as e:
            error_msg = f"Ошибка проверки критических ошибок: {str(e)}"
            logger.error(error_msg, exc_info=True)
            await self._send_critical_error("Проверка критических ошибок", error_msg)
            return {'error': error_msg}

    async def check_system_health(self) -> Dict:
        """Проверка общего состояния системы"""
        try:
            logger.info("🔍 Проверка состояния системы...")

            # Проверяем размер базы данных
            db_size = os.path.getsize(DATABASE_PATH) if os.path.exists(DATABASE_PATH) else 0
            db_size_mb = db_size / (1024 * 1024)

            # Проверяем размер лог-файлов
            log_files = ['bot.log', 'logs/errors.log', 'logs/database.log']
            total_log_size = 0
            for log_file in log_files:
                if os.path.exists(log_file):
                    total_log_size += os.path.getsize(log_file)

            total_log_size_mb = total_log_size / (1024 * 1024)

            # Проверяем свободное место на диске
            disk_usage = os.statvfs('.')
            free_space_gb = (disk_usage.f_frsize * disk_usage.f_bavail) / (1024**3)

            # Проверяем количество пользователей
            async with aiosqlite.connect(DATABASE_PATH) as conn:
                cursor = await conn.cursor()
                await cursor.execute("SELECT COUNT(*) FROM users")
                total_users = (await cursor.fetchone())[0]

                await cursor.execute("SELECT COUNT(*) FROM users WHERE created_at > datetime('now', '-1 day')")
                new_users_today = (await cursor.fetchone())[0]

            report = {
                'db_size_mb': round(db_size_mb, 2),
                'log_size_mb': round(total_log_size_mb, 2),
                'free_space_gb': round(free_space_gb, 2),
                'total_users': total_users,
                'new_users_today': new_users_today,
                'warnings': []
            }

            # Проверяем предупреждения
            if db_size_mb > 100:
                report['warnings'].append("База данных больше 100MB")

            if total_log_size_mb > 500:
                report['warnings'].append("Лог-файлы больше 500MB")

            if free_space_gb < 1:
                report['warnings'].append("Мало места на диске (<1GB)")

            # Отправляем отчет о состоянии системы
            await self._send_system_health_report(report)

            logger.info(f"✅ Проверка состояния системы завершена")
            return report

        except Exception as e:
            error_msg = f"Ошибка проверки состояния системы: {str(e)}"
            logger.error(error_msg, exc_info=True)
            await self._send_critical_error("Проверка состояния системы", error_msg)
            return {'error': error_msg}

    async def _send_avatar_report(self, report: Dict):
        """Отправка отчета об аватарах"""
        try:
            timestamp = datetime.now(self.moscow_tz).strftime('%Y-%m-%d %H:%M:%S MSK')

            message_parts = [
                f"🎭 ОТЧЕТ ПО АВАТАРАМ ({timestamp})",
                f"✅ Успешных (6ч): {report['successful_count']}",
                f"⏳ В обучении: {report['training_count']}",
                f"❌ Неудачных (6ч): {report['failed_count']}"
            ]

            if report['training_avatars']:
                message_parts.append("\n🔄 В ОБУЧЕНИИ:")
                for avatar in report['training_avatars'][:5]:
                    user_id, avatar_name, status, created_at = avatar
                    created_time = datetime.fromisoformat(created_at.replace('Z', '+00:00')).astimezone(self.moscow_tz).strftime('%H:%M')
                    message_parts.append(f"• User {user_id}: {avatar_name} ({status}) - {created_time}")

            if report['failed_avatars']:
                message_parts.append("\n❌ НЕУДАЧНЫЕ (6ч):")
                for avatar in report['failed_avatars'][:5]:
                    user_id, avatar_name, status, created_at = avatar
                    created_time = datetime.fromisoformat(created_at.replace('Z', '+00:00')).astimezone(self.moscow_tz).strftime('%H:%M')
                    message_parts.append(f"• User {user_id}: {avatar_name} ({status}) - {created_time}")

            message = escape_md("\n".join(message_parts), version=2)

            # Отправляем всем админам (включая главного разработчика)
            for admin_id in ADMIN_IDS:
                try:
                    await send_message_with_fallback(
                        self.bot, admin_id, message,
                        parse_mode=ParseMode.MARKDOWN_V2
                    )
                except Exception as e:
                    logger.error(f"Ошибка отправки отчета об аватарах админу {admin_id}: {e}")

        except Exception as e:
            logger.error(f"Ошибка формирования отчета об аватарах: {e}")

    async def _send_payment_report(self, report: Dict):
        """Отправка отчета о платежах"""
        try:
            timestamp = datetime.now(self.moscow_tz).strftime('%Y-%m-%d %H:%M:%S MSK')

            message_parts = [
                f"💳 ОТЧЕТ ПО ПЛАТЕЖАМ ({timestamp})",
                f"📊 Всего платежей: {report['total_payments']}",
                f"✅ Успешных: {report['successful_payments']}",
                f"❌ Неудачных: {report['failed_payments']}",
                f"💰 Общая сумма: {report['total_amount']:.2f}₽"
            ]

            if report['recent_payments']:
                message_parts.append("\n💸 ПОСЛЕДНИЕ ПЛАТЕЖИ:")
                for payment in report['recent_payments'][:5]:
                    user_id, plan, amount, status, created_at, payment_id, username, first_name = payment
                    if isinstance(created_at, datetime):
                        created_time = created_at.strftime('%H:%M')
                    else:
                        created_time = "Unknown"
                    message_parts.append(f"• User {user_id}: {plan} - {amount}₽ ({status}) - {created_time}")

            message = escape_md("\n".join(message_parts), version=2)

            # Отправляем всем админам (включая главного разработчика)
            for admin_id in ADMIN_IDS:
                try:
                    await send_message_with_fallback(
                        self.bot, admin_id, message,
                        parse_mode=ParseMode.MARKDOWN_V2
                    )
                except Exception as e:
                    logger.error(f"Ошибка отправки отчета о платежах админу {admin_id}: {e}")

        except Exception as e:
            logger.error(f"Ошибка формирования отчета о платежах: {e}")

    async def _send_critical_errors_report(self, report: Dict):
        """Отправка отчета о критических ошибках"""
        try:
            timestamp = datetime.now(self.moscow_tz).strftime('%Y-%m-%d %H:%M:%S MSK')

            message_parts = [
                f"🚨 КРИТИЧЕСКИЕ ОШИБКИ ({timestamp})",
                f"❌ Найдено ошибок: {report['errors_found']}"
            ]

            if report['critical_errors']:
                message_parts.append("\n🔍 ПОСЛЕДНИЕ ОШИБКИ:")
                for error in report['critical_errors'][:5]:
                    file_name = os.path.basename(error['file'])
                    line_preview = error['line'][:100] + "..." if len(error['line']) > 100 else error['line']
                    message_parts.append(f"• {file_name}: {line_preview}")

            message = escape_md("\n".join(message_parts), version=2)

            # Отправляем главному разработчику (ERROR_LOG_ADMIN)
            for admin_id in ERROR_LOG_ADMIN:
                try:
                    await send_message_with_fallback(
                        self.bot, admin_id, message,
                        parse_mode=ParseMode.MARKDOWN_V2
                    )
                except Exception as e:
                    logger.error(f"Ошибка отправки отчета об ошибках главному разработчику {admin_id}: {e}")

        except Exception as e:
            logger.error(f"Ошибка формирования отчета об ошибках: {e}")

    async def _send_system_health_report(self, report: Dict):
        """Отправка отчета о состоянии системы"""
        try:
            timestamp = datetime.now(self.moscow_tz).strftime('%Y-%m-%d %H:%M:%S MSK')

            message_parts = [
                f"💻 СОСТОЯНИЕ СИСТЕМЫ ({timestamp})",
                f"📊 База данных: {report['db_size_mb']}MB",
                f"📝 Логи: {report['log_size_mb']}MB",
                f"💾 Свободное место: {report['free_space_gb']}GB",
                f"👥 Всего пользователей: {report['total_users']}",
                f"🆕 Новых сегодня: {report['new_users_today']}"
            ]

            if report['warnings']:
                message_parts.append("\n⚠️ ПРЕДУПРЕЖДЕНИЯ:")
                for warning in report['warnings']:
                    message_parts.append(f"• {warning}")

            message = escape_md("\n".join(message_parts), version=2)

            # Отправляем главному разработчику (ERROR_LOG_ADMIN)
            for admin_id in ERROR_LOG_ADMIN:
                try:
                    await send_message_with_fallback(
                        self.bot, admin_id, message,
                        parse_mode=ParseMode.MARKDOWN_V2
                    )
                except Exception as e:
                    logger.error(f"Ошибка отправки отчета о состоянии системы главному разработчику {admin_id}: {e}")

        except Exception as e:
            logger.error(f"Ошибка формирования отчета о состоянии системы: {e}")

    async def _send_critical_error(self, component: str, error: str):
        """Отправка уведомления о критической ошибке"""
        try:
            timestamp = datetime.now(self.moscow_tz).strftime('%Y-%m-%d %H:%M:%S MSK')

            message = escape_md(
                f"🚨 КРИТИЧЕСКАЯ ОШИБКА ({timestamp})\n"
                f"🔧 Компонент: {component}\n"
                f"❌ Ошибка: {error}",
                version=2
            )

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

    async def send_new_user_notification(self, user_id: int, username: str = None, first_name: str = None):
        """Отправка уведомления о новом пользователе"""
        try:
            timestamp = datetime.now(self.moscow_tz).strftime('%Y-%m-%d %H:%M:%S MSK')

            message_parts = [
                f"🆕 НОВЫЙ ПОЛЬЗОВАТЕЛЬ ({timestamp})",
                f"👤 User ID: {user_id}",
            ]

            if username:
                message_parts.append(f"🔗 Username: @{username}")

            if first_name:
                message_parts.append(f"📝 Имя: {first_name}")

            message = escape_md("\n".join(message_parts), version=2)

            # Отправляем всем админам (включая главного разработчика)
            for admin_id in ADMIN_IDS:
                try:
                    await send_message_with_fallback(
                        self.bot, admin_id, message,
                        parse_mode=ParseMode.MARKDOWN_V2
                    )
                except Exception as e:
                    logger.error(f"Ошибка отправки уведомления о новом пользователе админу {admin_id}: {e}")

        except Exception as e:
            logger.error(f"Ошибка отправки уведомления о новом пользователе: {e}")

    async def send_immediate_critical_notification(self, notification_type: str, data: Dict):
        """Отправка немедленных критических уведомлений"""
        try:
            timestamp = datetime.now(self.moscow_tz).strftime('%Y-%m-%d %H:%M:%S MSK')

            if notification_type == "critical_error":
                message_parts = [
                    f"🚨 КРИТИЧЕСКАЯ ОШИБКА ({timestamp})",
                    f"🔧 Компонент: {data.get('component', 'Неизвестно')}",
                    f"❌ Ошибка: {data.get('error', 'Неизвестная ошибка')}"
                ]

                if data.get('user_id'):
                    message_parts.append(f"👤 User ID: {data['user_id']}")

                if data.get('details'):
                    message_parts.append(f"📋 Детали: {data['details']}")

            elif notification_type == "payment_success":
                message_parts = [
                    f"💳 НОВЫЙ ПЛАТЕЖ ({timestamp})",
                    f"👤 User ID: {data.get('user_id', 'Неизвестно')}",
                    f"📦 Пакет: {data.get('plan', 'Неизвестно')}",
                    f"💰 Сумма: {data.get('amount', 0):.2f}₽",
                    f"✅ Статус: Успешно"
                ]

            elif notification_type == "avatar_trained":
                message_parts = [
                    f"🎭 АВАТАР ОБУЧЕН ({timestamp})",
                    f"👤 User ID: {data.get('user_id', 'Неизвестно')}",
                    f"🏷 Имя аватара: {data.get('avatar_name', 'Неизвестно')}",
                    f"🔑 Триггер: {data.get('trigger_word', 'Неизвестно')}"
                ]

            elif notification_type == "system_issue":
                message_parts = [
                    f"⚠️ ПРОБЛЕМА СИСТЕМЫ ({timestamp})",
                    f"🔧 Компонент: {data.get('component', 'Неизвестно')}",
                    f"❌ Проблема: {data.get('issue', 'Неизвестная проблема')}"
                ]

            message = escape_md("\n".join(message_parts), version=2)

            # Определяем получателей в зависимости от типа уведомления
            if notification_type == "payment_success":
                # Успешные платежи отправляем всем администраторам
                recipients = ADMIN_IDS
                logger.info(f"Отправка уведомления о платеже всем администраторам: {recipients}")
            else:
                # Остальные уведомления отправляем только главному разработчику
                recipients = ERROR_LOG_ADMIN
                logger.info(f"Отправка критического уведомления главному разработчику: {recipients}")

            # Отправляем уведомления
            for admin_id in recipients:
                try:
                    await send_message_with_fallback(
                        self.bot, admin_id, message,
                        parse_mode=ParseMode.MARKDOWN_V2
                    )
                except Exception as e:
                    logger.error(f"Ошибка отправки немедленного уведомления администратору {admin_id}: {e}")

        except Exception as e:
            logger.error(f"Ошибка отправки немедленного уведомления: {e}")

    async def send_hourly_summary(self):
        """Отправка ежечасной сводки"""
        try:
            timestamp = datetime.now(self.moscow_tz).strftime('%Y-%m-%d %H:%M:%S MSK')

            # Получаем статистику за последний час
            one_hour_ago = datetime.now(self.moscow_tz) - timedelta(hours=1)

            async with aiosqlite.connect(DATABASE_PATH) as conn:
                cursor = await conn.cursor()

                # Новые пользователи за час
                await cursor.execute("""
                    SELECT COUNT(*) FROM users
                    WHERE created_at > ?
                """, (one_hour_ago.strftime('%Y-%m-%d %H:%M:%S'),))
                new_users_count = (await cursor.fetchone())[0]

                # Платежи за час
                await cursor.execute("""
                    SELECT COUNT(*), SUM(amount) FROM payments
                    WHERE created_at > ? AND status = 'succeeded'
                """, (one_hour_ago.strftime('%Y-%m-%d %H:%M:%S'),))
                payments_result = await cursor.fetchone()
                payments_count = payments_result[0] if payments_result[0] else 0
                payments_amount = payments_result[1] if payments_result[1] else 0

                # Первые покупки за час
                await cursor.execute("""
                    SELECT COUNT(*) FROM users
                    WHERE first_purchase = 1 AND created_at > ?
                """, (one_hour_ago.strftime('%Y-%m-%d %H:%M:%S'),))
                first_purchases_count = (await cursor.fetchone())[0]

                # Обученные аватары за час
                await cursor.execute("""
                    SELECT COUNT(*) FROM user_trainedmodels
                    WHERE status = 'success' AND updated_at > ?
                """, (one_hour_ago.strftime('%Y-%m-%d %H:%M:%S'),))
                trained_avatars_count = (await cursor.fetchone())[0]

                # Статистика по пакетам
                await cursor.execute("""
                    SELECT plan, COUNT(*) FROM payments
                    WHERE created_at > ? AND status = 'succeeded'
                    GROUP BY plan
                """, (one_hour_ago.strftime('%Y-%m-%d %H:%M:%S'),))
                packages_stats = await cursor.fetchall()

            # Формируем сводку
            message_parts = [
                f"📊 ЕЖЕЧАСНАЯ СВОДКА ({timestamp})",
                f"👥 Новых пользователей: {new_users_count}",
                f"💳 Платежей: {payments_count}",
                f"💰 Сумма платежей: {payments_amount:.2f}₽",
                f"🎁 Первых покупок: {first_purchases_count}",
                f"🎭 Обученных аватаров: {trained_avatars_count}"
            ]

            if packages_stats:
                message_parts.append("\n📦 ПО ПАКЕТАМ:")
                for plan, count in packages_stats:
                    message_parts.append(f"• {plan}: {count}")

            message = escape_md("\n".join(message_parts), version=2)

            # Отправляем всем админам
            for admin_id in ADMIN_IDS:
                try:
                    await send_message_with_fallback(
                        self.bot, admin_id, message,
                        parse_mode=ParseMode.MARKDOWN_V2
                    )
                except Exception as e:
                    logger.error(f"Ошибка отправки ежечасной сводки админу {admin_id}: {e}")

        except Exception as e:
            logger.error(f"Ошибка формирования ежечасной сводки: {e}")

    async def send_daily_detailed_report(self):
        """Отправка детального ежедневного отчета"""
        try:
            timestamp = datetime.now(self.moscow_tz).strftime('%Y-%m-%d %H:%M:%S MSK')
            yesterday = datetime.now(self.moscow_tz) - timedelta(days=1)

            async with aiosqlite.connect(DATABASE_PATH) as conn:
                cursor = await conn.cursor()

                # Статистика за день
                await cursor.execute("""
                    SELECT COUNT(*) FROM users
                    WHERE DATE(created_at) = DATE(?)
                """, (yesterday.strftime('%Y-%m-%d'),))
                new_users_day = (await cursor.fetchone())[0]

                await cursor.execute("""
                    SELECT COUNT(*), SUM(amount) FROM payments
                    WHERE DATE(created_at) = DATE(?) AND status = 'succeeded'
                """, (yesterday.strftime('%Y-%m-%d'),))
                payments_result = await cursor.fetchone()
                payments_day = payments_result[0] if payments_result[0] else 0
                amount_day = payments_result[1] if payments_result[1] else 0

                await cursor.execute("""
                    SELECT COUNT(*) FROM user_trainedmodels
                    WHERE DATE(updated_at) = DATE(?) AND status = 'success'
                """, (yesterday.strftime('%Y-%m-%d'),))
                avatars_day = (await cursor.fetchone())[0]

                # Топ пользователей по активности
                await cursor.execute("""
                    SELECT user_id, COUNT(*) as activity_count
                    FROM user_actions
                    WHERE DATE(timestamp) = DATE(?)
                    GROUP BY user_id
                    ORDER BY activity_count DESC
                    LIMIT 5
                """, (yesterday.strftime('%Y-%m-%d'),))
                top_users = await cursor.fetchall()

            message_parts = [
                f"📈 ДЕТАЛЬНЫЙ ОТЧЕТ ЗА ДЕНЬ ({timestamp})",
                f"👥 Новых пользователей: {new_users_day}",
                f"💳 Платежей: {payments_day}",
                f"💰 Сумма: {amount_day:.2f}₽",
                f"🎭 Обученных аватаров: {avatars_day}"
            ]

            if top_users:
                message_parts.append("\n🔥 ТОП АКТИВНЫХ ПОЛЬЗОВАТЕЛЕЙ:")
                for user_id, activity_count in top_users:
                    message_parts.append(f"• User {user_id}: {activity_count} действий")

            message = escape_md("\n".join(message_parts), version=2)

            # Отправляем главному разработчику
            for admin_id in ERROR_LOG_ADMIN:
                try:
                    await send_message_with_fallback(
                        self.bot, admin_id, message,
                        parse_mode=ParseMode.MARKDOWN_V2
                    )
                except Exception as e:
                    logger.error(f"Ошибка отправки детального отчета главному разработчику {admin_id}: {e}")

        except Exception as e:
            logger.error(f"Ошибка формирования детального отчета: {e}")

    async def run_full_monitoring(self) -> Dict:
        """Запуск полного мониторинга"""
        logger.info("🚀 Запуск полного мониторинга системы...")

        results = {}

        # Запускаем все проверки
        checks = [
            ("avatars", self.check_trained_avatars),
            ("payments", self.check_payments),
            ("critical_errors", self.check_critical_errors),
            ("system_health", self.check_system_health)
        ]

        for name, check_func in checks:
            try:
                results[name] = await check_func()
            except Exception as e:
                error_msg = f"Ошибка в проверке {name}: {str(e)}"
                logger.error(error_msg, exc_info=True)
                results[name] = {'error': error_msg}

        # Сохраняем результаты
        def datetime_handler(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

        with open('monitoring_report.json', 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2, default=datetime_handler)

        logger.info("✅ Полный мониторинг завершен")
        return results

async def main():
    """Главная функция для тестирования"""
    # Для тестирования нужно создать экземпляр бота
    # В реальном использовании передается из main.py
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not bot_token:
        print("❌ TELEGRAM_BOT_TOKEN не установлен")
        return

    bot = Bot(token=bot_token)
    monitoring = BotMonitoringSystem(bot)

    try:
        results = await monitoring.run_full_monitoring()
        print("✅ Мониторинг завершен успешно")
        print(f"📄 Результаты сохранены в monitoring_report.json")
    except Exception as e:
        print(f"❌ Ошибка мониторинга: {e}")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
