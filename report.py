import asyncio
import os
import tempfile
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import pandas as pd
from aiogram import Bot
from aiogram.types import FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton
import sqlite3
import logging

from logger import get_logger
logger = get_logger('main')

class ReportGenerator:
    def __init__(self, db_path: str = "users.db"):
        self.db_path = db_path

    def get_db_connection(self):
        """Создает соединение с базой данных"""
        return sqlite3.connect(self.db_path)

    async def create_users_report(self) -> str:
        """Создает отчет по пользователям"""
        try:
            conn = self.get_db_connection()
            query = """
            SELECT
                user_id,
                username,
                first_name,
                generations_left,
                avatar_left,
                has_trained_model,
                is_notified,
                first_purchase,
                email,
                active_avatar_id,
                referrer_id,
                is_blocked,
                block_reason,
                welcome_message_sent,
                last_reminder_type,
                last_reminder_sent,
                utm_source,
                created_at,
                updated_at
            FROM users
            ORDER BY created_at DESC
            """

            df = pd.read_sql_query(query, conn)
            conn.close()

            # Переименовываем колонки на русский
            column_mapping = {
                'user_id': 'ID пользователя',
                'username': 'Имя пользователя',
                'first_name': 'Имя',
                'generations_left': 'Осталось генераций',
                'avatar_left': 'Осталось аватаров',
                'has_trained_model': 'Есть обученная модель',
                'is_notified': 'Уведомления включены',
                'first_purchase': 'Первая покупка',
                'email': 'Email',
                'active_avatar_id': 'ID активного аватара',
                'referrer_id': 'ID пригласившего',
                'is_blocked': 'Заблокирован',
                'block_reason': 'Причина блокировки',
                'welcome_message_sent': 'Приветствие отправлено',
                'last_reminder_type': 'Тип последнего напоминания',
                'last_reminder_sent': 'Последнее напоминание',
                'utm_source': 'UTM источник',
                'created_at': 'Дата регистрации',
                'updated_at': 'Последнее обновление',
            }

            df = df.rename(columns=column_mapping)

            # Преобразуем булевы значения (с проверкой наличия колонок)
            boolean_columns = {
                'Есть обученная модель': 'Есть обученная модель',
                'Уведомления включены': 'Уведомления включены',
                'Первая покупка': 'Первая покупка',
                'Заблокирован': 'Заблокирован',
                'Приветствие отправлено': 'Приветствие отправлено'
            }

            for col_name, col_key in boolean_columns.items():
                if col_key in df.columns:
                    df[col_name] = df[col_name].map({1: 'Да', 0: 'Нет'})
                else:
                    logger.warning(f"Колонка {col_key} отсутствует в отчете пользователей")

            # Сохраняем в Excel
            filename = f"users_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            filepath = os.path.join(tempfile.gettempdir(), filename)

            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Пользователи', index=False)

                # Автоматически подгоняем ширину колонок
                worksheet = writer.sheets['Пользователи']
                for column in worksheet.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    adjusted_width = min(max_length + 2, 50)
                    worksheet.column_dimensions[column_letter].width = adjusted_width

            return filepath

        except Exception as e:
            logger.error(f"Ошибка создания отчета пользователей: {e}", exc_info=True)
            raise

    async def create_activity_report(self) -> str:
        """Создает отчет по активности пользователей"""
        try:
            conn = self.get_db_connection()

            # Получаем данные о генерациях
            generation_query = """
            SELECT
                gl.user_id,
                u.username,
                u.first_name,
                gl.generation_type,
                gl.replicate_model_id,
                gl.units_generated,
                gl.cost_per_unit,
                gl.total_cost,
                gl.style,
                gl.ratio,
                gl.created_at
            FROM generation_log gl
            LEFT JOIN users u ON gl.user_id = u.user_id
            ORDER BY gl.created_at DESC
            """

            df_generations = pd.read_sql_query(generation_query, conn)

            # Получаем данные о действиях пользователей
            actions_query = """
            SELECT
                ua.user_id,
                u.username,
                u.first_name,
                ua.action,
                ua.details,
                ua.style,
                ua.ratio,
                ua.created_at
            FROM user_actions ua
            LEFT JOIN users u ON ua.user_id = u.user_id
            ORDER BY ua.created_at DESC
            """

            df_actions = pd.read_sql_query(actions_query, conn)

            # Получаем статистику по дням
            daily_stats_query = """
            SELECT
                DATE(gl.created_at) as date,
                COUNT(DISTINCT gl.user_id) as active_users,
                COUNT(*) as total_generations,
                SUM(gl.units_generated) as total_units
            FROM generation_log gl
            WHERE gl.created_at >= date('now', '-30 days')
            GROUP BY DATE(gl.created_at)
            ORDER BY date DESC
            """

            df_daily_stats = pd.read_sql_query(daily_stats_query, conn)
            conn.close()

            # Переименовываем колонки
            df_generations = df_generations.rename(columns={
                'user_id': 'ID пользователя',
                'username': 'Имя пользователя',
                'first_name': 'Имя',
                'generation_type': 'Тип генерации',
                'replicate_model_id': 'Модель',
                'units_generated': 'Количество единиц',
                'cost_per_unit': 'Стоимость за единицу',
                'total_cost': 'Общая стоимость',
                'style': 'Стиль',
                'ratio': 'Соотношение',
                'created_at': 'Дата генерации'
            })

            df_actions = df_actions.rename(columns={
                'user_id': 'ID пользователя',
                'username': 'Имя пользователя',
                'first_name': 'Имя',
                'action': 'Действие',
                'details': 'Детали',
                'style': 'Стиль',
                'ratio': 'Соотношение',
                'created_at': 'Дата действия'
            })

            df_daily_stats = df_daily_stats.rename(columns={
                'date': 'Дата',
                'active_users': 'Активных пользователей',
                'total_generations': 'Всего генераций',
                'total_units': 'Всего единиц'
            })

            # Сохраняем в Excel
            filename = f"activity_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            filepath = os.path.join(tempfile.gettempdir(), filename)

            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                df_generations.to_excel(writer, sheet_name='Генерации', index=False)
                df_actions.to_excel(writer, sheet_name='Действия', index=False)
                df_daily_stats.to_excel(writer, sheet_name='Статистика по дням', index=False)

                # Автоматически подгоняем ширину колонок для всех листов
                for sheet_name in writer.sheets:
                    worksheet = writer.sheets[sheet_name]
                    for column in worksheet.columns:
                        max_length = 0
                        column_letter = column[0].column_letter
                        for cell in column:
                            try:
                                if len(str(cell.value)) > max_length:
                                    max_length = len(str(cell.value))
                            except:
                                pass
                        adjusted_width = min(max_length + 2, 50)
                        worksheet.column_dimensions[column_letter].width = adjusted_width

            return filepath

        except Exception as e:
            logger.error(f"Ошибка создания отчета активности: {e}", exc_info=True)
            raise

    async def create_payments_report(self) -> str:
        """Создает отчет по платежам"""
        try:
            conn = self.get_db_connection()

                        # Получаем данные о платежах
            payments_query = """
            SELECT
                p.payment_id,
                p.user_id,
                u.username,
                u.first_name,
                p.plan,
                p.amount,
                p.status,
                p.created_at
            FROM payments p
            LEFT JOIN users u ON p.user_id = u.user_id
            ORDER BY p.created_at DESC
            """

            df_payments = pd.read_sql_query(payments_query, conn)

            # Получаем статистику платежей
            payment_stats_query = """
            SELECT
                user_id,
                COUNT(*) as total_payments,
                SUM(amount) as total_amount,
                MIN(created_at) as first_payment_date,
                MAX(created_at) as last_payment_date
            FROM payments
            WHERE status = 'completed'
            GROUP BY user_id
            ORDER BY total_amount DESC
            """

            df_payment_stats = pd.read_sql_query(payment_stats_query, conn)

            # Получаем детальные логи платежей
            payment_logs_query = """
            SELECT
                pl.payment_id,
                pl.payment_info,
                pl.amount,
                pl.created_at
            FROM payment_logs pl
            ORDER BY pl.created_at DESC
            """

            df_payment_logs = pd.read_sql_query(payment_logs_query, conn)
            conn.close()

            # Переименовываем колонки
            df_payments = df_payments.rename(columns={
                'payment_id': 'ID платежа',
                'user_id': 'ID пользователя',
                'username': 'Имя пользователя',
                'first_name': 'Имя',
                'plan': 'План',
                'amount': 'Сумма',
                'status': 'Статус',
                'created_at': 'Дата создания'
            })

            df_payment_stats = df_payment_stats.rename(columns={
                'user_id': 'ID пользователя',
                'total_payments': 'Всего платежей',
                'total_amount': 'Общая сумма',
                'first_payment_date': 'Дата первого платежа',
                'last_payment_date': 'Дата последнего платежа'
            })

            df_payment_logs = df_payment_logs.rename(columns={
                'payment_id': 'ID платежа',
                'payment_info': 'Информация о платеже',
                'amount': 'Сумма',
                'created_at': 'Дата создания'
            })

            # Преобразуем статусы
            df_payments['Статус'] = df_payments['Статус'].map({
                'pending': 'В ожидании',
                'completed': 'Завершен',
                'failed': 'Ошибка'
            })

            # Сохраняем в Excel
            filename = f"payments_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            filepath = os.path.join(tempfile.gettempdir(), filename)

            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                df_payments.to_excel(writer, sheet_name='Платежи', index=False)
                df_payment_stats.to_excel(writer, sheet_name='Статистика платежей', index=False)
                df_payment_logs.to_excel(writer, sheet_name='Логи платежей', index=False)

                # Автоматически подгоняем ширину колонок
                for sheet_name in writer.sheets:
                    worksheet = writer.sheets[sheet_name]
                    for column in worksheet.columns:
                        max_length = 0
                        column_letter = column[0].column_letter
                        for cell in column:
                            try:
                                if len(str(cell.value)) > max_length:
                                    max_length = len(str(cell.value))
                            except:
                                pass
                        adjusted_width = min(max_length + 2, 50)
                        worksheet.column_dimensions[column_letter].width = adjusted_width

            return filepath

        except Exception as e:
            logger.error(f"Ошибка создания отчета платежей: {e}", exc_info=True)
            raise

    async def create_referrals_report(self) -> str:
        """Создает отчет по рефералам"""
        try:
            conn = self.get_db_connection()

            # Получаем данные о рефералах
            referrals_query = """
            SELECT
                r.referrer_id,
                CASE
                    WHEN u1.username IS NOT NULL THEN u1.username
                    ELSE 'ID: ' || r.referrer_id
                END as referrer_display,
                r.referred_id,
                CASE
                    WHEN u2.username IS NOT NULL THEN u2.username
                    ELSE 'ID: ' || r.referred_id
                END as referred_display,
                r.created_at,
                r.completed_at,
                r.status
            FROM referrals r
            LEFT JOIN users u1 ON r.referrer_id = u1.user_id
            LEFT JOIN users u2 ON r.referred_id = u2.user_id
            ORDER BY r.created_at DESC
            """

            df_referrals = pd.read_sql_query(referrals_query, conn)

            # Получаем награды за рефералов
            rewards_query = """
            SELECT
                rr.referrer_id,
                CASE
                    WHEN u.username IS NOT NULL THEN u.username
                    ELSE 'ID: ' || rr.referrer_id
                END as referrer_display,
                rr.referred_user_id,
                CASE
                    WHEN u2.username IS NOT NULL THEN u2.username
                    ELSE 'ID: ' || rr.referred_user_id
                END as referred_display,
                rr.created_at,
                rr.reward_photos
            FROM referral_rewards rr
            LEFT JOIN users u ON rr.referrer_id = u.user_id
            LEFT JOIN users u2 ON rr.referred_user_id = u2.user_id
            ORDER BY rr.created_at DESC
            """

            df_rewards = pd.read_sql_query(rewards_query, conn)

            # Получаем статистику рефералов
            stats_query = """
            SELECT
                rs.user_id,
                CASE
                    WHEN u.username IS NOT NULL THEN u.username
                    ELSE 'ID: ' || rs.user_id
                END as user_display,
                rs.total_referrals,
                rs.total_reward_photos,
                rs.updated_at
            FROM referral_stats rs
            LEFT JOIN users u ON rs.user_id = u.user_id
            ORDER BY rs.total_referrals DESC
            """

            df_stats = pd.read_sql_query(stats_query, conn)
            conn.close()

            # Переименовываем колонки
            df_referrals = df_referrals.rename(columns={
                'referrer_id': 'ID пригласившего',
                'referrer_display': 'Пригласивший',
                'referred_id': 'ID приглашенного',
                'referred_display': 'Приглашенный',
                'created_at': 'Дата создания',
                'completed_at': 'Дата завершения',
                'status': 'Статус'
            })

            df_rewards = df_rewards.rename(columns={
                'referrer_id': 'ID пригласившего',
                'referrer_display': 'Получатель награды',
                'referred_user_id': 'ID приглашенного',
                'referred_display': 'За кого награда',
                'created_at': 'Дата награды',
                'reward_photos': 'Награда (фото)'
            })

            df_stats = df_stats.rename(columns={
                'user_id': 'ID пользователя',
                'user_display': 'Пользователь',
                'total_referrals': 'Всего рефералов',
                'total_reward_photos': 'Всего наград (фото)',
                'updated_at': 'Последнее обновление'
            })

            # Преобразуем статусы
            df_referrals['Статус'] = df_referrals['Статус'].map({
                'pending': 'В ожидании',
                'completed': 'Завершен'
            })

            # Сохраняем в Excel
            filename = f"referrals_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            filepath = os.path.join(tempfile.gettempdir(), filename)

            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                df_referrals.to_excel(writer, sheet_name='Рефералы', index=False)
                df_rewards.to_excel(writer, sheet_name='Награды', index=False)
                df_stats.to_excel(writer, sheet_name='Статистика', index=False)

                # Автоматически подгоняем ширину колонок
                for sheet_name in writer.sheets:
                    worksheet = writer.sheets[sheet_name]
                    for column in worksheet.columns:
                        max_length = 0
                        column_letter = column[0].column_letter
                        for cell in column:
                            try:
                                if len(str(cell.value)) > max_length:
                                    max_length = len(str(cell.value))
                            except:
                                pass
                        adjusted_width = min(max_length + 2, 50)
                        worksheet.column_dimensions[column_letter].width = adjusted_width

            return filepath

        except Exception as e:
            logger.error(f"Ошибка создания отчета рефералов: {e}", exc_info=True)
            raise

async def send_report_to_admin(bot: Bot, admin_id: int, filepath: str, report_type: str):
    """Отправляет отчет администратору"""
    try:
        if not os.path.exists(filepath):
            await bot.send_message(
                admin_id,
                f"❌ Ошибка: файл отчета не найден"
            )
            return

        # Создаем клавиатуру с кнопкой удаления
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🗑 Удалить файл", callback_data=f"delete_report_{os.path.basename(filepath)}")]
        ])

        # Отправляем файл
        document = FSInputFile(filepath)
        await bot.send_document(
            chat_id=admin_id,
            document=document,
            caption=f"📊 Отчет: {report_type}\n📅 Создан: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}",
            reply_markup=keyboard
        )

        logger.info(f"Отчет {report_type} отправлен администратору {admin_id}")

    except Exception as e:
        logger.error(f"Ошибка отправки отчета: {e}")
        await bot.send_message(
            admin_id,
            f"❌ Ошибка отправки отчета: {str(e)}"
        )

async def delete_report_file(filepath: str):
    """Удаляет файл отчета"""
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
            logger.info(f"Файл отчета удален: {filepath}")
    except Exception as e:
        logger.error(f"Ошибка удаления файла отчета: {e}")

# Создаем экземпляр генератора отчетов
report_generator = ReportGenerator()
