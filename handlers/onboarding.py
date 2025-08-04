# handlers/onboarding.py

import asyncio
import logging
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import pytz
from aiogram import Bot, Router
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile, Message, CallbackQuery, InputMediaPhoto
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import aiosqlite
from config import DATABASE_PATH, TARIFFS, ADMIN_IDS, ERROR_LOG_ADMIN
from handlers.utils import safe_escape_markdown as escape_md, get_tariff_text
from database import check_database_user, get_user_payments, is_old_user, mark_welcome_message_sent, get_users_for_reminders, is_user_blocked, block_user_access
from keyboards import create_subscription_keyboard, create_main_menu_keyboard
from onboarding_config import get_day_config, get_message_text, has_user_purchases

from logger import get_logger
logger = get_logger('main')

onboarding_router = Router()

# Примеры изображений для приветственного сообщения
EXAMPLE_IMAGES = [
    "images/example1.jpg",
    "images/example2.jpg",
    "images/example3.jpg",
]

async def send_onboarding_message(bot: Bot, user_id: int, message_type: str, subscription_data: Optional[tuple] = None, first_purchase: bool = False) -> None:
    """Отправляет сообщения онбординга в зависимости от типа."""
    logger.debug(f"Отправка сообщения типа {message_type} для user_id={user_id}")

    try:
        username = subscription_data[3] if subscription_data and len(subscription_data) > 3 else "Пользователь"
        first_name = subscription_data[8] if subscription_data and len(subscription_data) > 8 else "Пользователь"

        # Проверяем, является ли пользователь старым
        is_old_user_flag = await is_old_user(user_id, cutoff_date="2025-07-11")
        logger.debug(f"Пользователь user_id={user_id} is_old_user={is_old_user_flag}")

        # Если пользователь старый, не отправляем напоминания
        if is_old_user_flag and message_type.startswith("reminder_"):
            logger.info(f"Напоминание {message_type} НЕ отправлено для user_id={user_id}: пользователь старый")
            return

        # Проверяем, есть ли у пользователя покупки
        has_purchases = await has_user_purchases(user_id, DATABASE_PATH)
        if has_purchases:
            logger.debug(f"Пользователь {user_id} уже имеет покупки, пропускаем воронку")
            return

        # Получаем данные о последнем отправленном напоминании
        async with aiosqlite.connect(DATABASE_PATH) as conn:
            conn.row_factory = aiosqlite.Row
            c = await conn.cursor()
            await c.execute("SELECT last_reminder_type, last_reminder_sent, welcome_message_sent FROM users WHERE user_id = ?", (user_id,))
            reminder_data = await c.fetchone()
            last_reminder_type = reminder_data['last_reminder_type'] if reminder_data else None
            last_reminder_sent = reminder_data['last_reminder_sent'] if reminder_data else None
            welcome_message_sent = reminder_data['welcome_message_sent'] if reminder_data else 0

        # Пропускаем отправку приветственного сообщения, если оно уже было отправлено
        if message_type == "welcome" and welcome_message_sent:
            logger.info(f"Приветственное сообщение уже отправлено для user_id={user_id}, пропускаем")
            return

        # Пропускаем отправку напоминания, если оно уже было отправлено
        if last_reminder_type == message_type:
            logger.info(f"Сообщение {message_type} уже отправлено для user_id={user_id}, пропускаем")
            return

        # Получаем текст сообщения из конфигурации
        message_data = get_message_text(message_type, first_name)
        if not message_data:
            logger.error(f"Неизвестный тип сообщения: {message_type} для user_id={user_id}")
            return

        # Создаем клавиатуру в зависимости от типа сообщения
        if message_type == "welcome":
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text=message_data["button_text"],
                    callback_data=message_data["callback_data"]
                )]
            ])
            with_images = True
        elif message_type == "reminder_day5":
            # Для последнего дня показываем все тарифы
            keyboard = await create_subscription_keyboard(hide_mini_tariff=False)
            with_images = False
        else:
            # Для остальных дней показываем кнопку оплаты конкретного тарифа
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text=message_data["button_text"],
                    callback_data=message_data["callback_data"]
                )]
            ])
            with_images = False

        try:
            if with_images:
                # Формируем медиагруппу для изображений
                media_group = []
                for img_path in EXAMPLE_IMAGES:
                    if os.path.exists(img_path):
                        media_group.append(InputMediaPhoto(media=FSInputFile(path=img_path)))
                    else:
                        logger.warning(f"Изображение не найдено: {img_path}")
                if media_group:
                    await bot.send_media_group(
                        chat_id=user_id,
                        media=media_group
                    )
                    logger.info(f"Медиагруппа с {len(media_group)} изображениями отправлена пользователю {user_id}")
                else:
                    logger.warning(f"Нет доступных изображений для медиагруппы для user_id={user_id}")

            await bot.send_message(
                chat_id=user_id,
                text=escape_md(message_data["text"], version=2),
                reply_markup=keyboard,
                parse_mode=ParseMode.MARKDOWN_V2
            )
            logger.info(f"Сообщение {message_type} отправлено пользователю {user_id}")

            # Обновление статуса отправки сообщения
            moscow_tz = pytz.timezone('Europe/Moscow')
            async with aiosqlite.connect(DATABASE_PATH) as conn:
                c = await conn.cursor()
                if message_type == "welcome":
                    await c.execute(
                        "UPDATE users SET welcome_message_sent = 1, last_reminder_type = ?, last_reminder_sent = ? WHERE user_id = ?",
                        (message_type, datetime.now(moscow_tz).strftime('%Y-%m-%d %H:%M:%S'), user_id)
                    )
                else:
                    await c.execute(
                        "UPDATE users SET last_reminder_type = ?, last_reminder_sent = ? WHERE user_id = ?",
                        (message_type, datetime.now(moscow_tz).strftime('%Y-%m-%d %H:%M:%S'), user_id)
                    )
                await conn.commit()
                logger.debug(f"Статус сообщения {message_type} обновлён для user_id={user_id}")

            # Уведомление админов об успешной отправке напоминания
            if message_type.startswith("reminder_"):
                admin_message = escape_md(
                    f"📬 Напоминание '{message_type}' успешно отправлено пользователю ID {user_id} (@{username})",
                    version=2
                )
                for admin_id in ADMIN_IDS:
                    try:
                        await bot.send_message(
                            chat_id=admin_id,
                            text=admin_message,
                            parse_mode=ParseMode.MARKDOWN_V2
                        )
                        logger.info(f"Уведомление о напоминании {message_type} отправлено админу {admin_id}")
                    except Exception as e:
                        logger.error(f"Ошибка отправки уведомления админу {admin_id} для user_id={user_id}: {e}")

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Ошибка отправки сообщения {message_type} для user_id={user_id}: {error_msg}")

            # Проверяем тип ошибки и обрабатываем соответственно
            if "chat not found" in error_msg.lower():
                logger.warning(f"Пользователь {user_id} заблокировал бота или удалил чат")
                # Блокируем пользователя с использованием централизованной функции
                block_reason = f"Чат не найден: {error_msg}"
                await block_user_access(user_id, block=True, block_reason=block_reason)
                return
            elif "bot can't initiate conversation" in error_msg.lower():
                logger.warning(f"Пользователь {user_id} не начал диалог с ботом")
                return
            elif any(phrase in error_msg.lower() for phrase in [
                "user_is_blocked", "user is blocked",
                "bot was blocked by the user", "forbidden: bot was blocked"
            ]):
                logger.warning(f"Пользователь {user_id} заблокировал бота: {error_msg}")
                # Используем централизованную обработку блокировки
                from handlers.utils import handle_user_blocked_bot
                await handle_user_blocked_bot(user_id, error_msg)
                return
            else:
                # Для других ошибок пытаемся отправить сообщение об ошибке
                try:
                    await bot.send_message(
                        chat_id=user_id,
                        text=escape_md("❌ Произошла ошибка. Попробуйте снова или обратитесь в поддержку: @AXIDI_Help", version=2),
                        reply_markup=await create_main_menu_keyboard(user_id),
                        parse_mode=ParseMode.MARKDOWN_V2
                    )
                except Exception as send_error:
                    logger.error(f"Не удалось отправить сообщение об ошибке пользователю {user_id}: {send_error}")

            # Уведомление админов об ошибке
            for admin_id in ADMIN_IDS:
                try:
                    await bot.send_message(
                        chat_id=admin_id,
                        text=escape_md(f"🚨 Ошибка отправки сообщения '{message_type}' для user_id={user_id}: {error_msg}", version=2),
                        parse_mode=ParseMode.MARKDOWN_V2
                    )
                    logger.info(f"Уведомление об ошибке отправки {message_type} отправлено админу {admin_id}")
                except Exception as e_admin:
                    logger.error(f"Ошибка отправки уведомления об ошибке админу {admin_id}: {e_admin}")

    except Exception as e:
        logger.error(f"Критическая ошибка в send_onboarding_message для user_id={user_id}, message_type={message_type}: {e}", exc_info=True)
        for admin_id in ERROR_LOG_ADMIN:
            try:
                await bot.send_message(
                    chat_id=admin_id,
                    text=escape_md(f"🚨 Критическая ошибка в send_onboarding_message для user_id={user_id}, message_type={message_type}: {str(e)}", version=2),
                    parse_mode=ParseMode.MARKDOWN_V2
                )
            except Exception as e_admin:
                logger.error(f"Ошибка отправки уведомления админу {admin_id}: {e_admin}")

async def schedule_welcome_message(bot: Bot, user_id: int) -> None:
    """Планирует отправку приветственного сообщения через 1 час после регистрации."""
    try:
        subscription_data = await check_database_user(user_id)
        if not subscription_data:
            logger.error(f"Неполные данные подписки для user_id={user_id}")
            return

        # Проверяем, есть ли у пользователя покупки
        has_purchases = await has_user_purchases(user_id, DATABASE_PATH)
        if has_purchases:
            logger.debug(f"Пользователь {user_id} уже имеет покупки, приветственное сообщение не планируется")
            return

        moscow_tz = pytz.timezone('Europe/Moscow')
        current_time = datetime.now(moscow_tz)

        # Проверяем валидность даты регистрации
        registration_date = current_time
        if subscription_data and len(subscription_data) > 10 and subscription_data[10]:
            try:
                registration_date = moscow_tz.localize(datetime.strptime(subscription_data[10], '%Y-%m-%d %H:%M:%S'))
            except ValueError as e:
                logger.warning(f"Невалидный формат даты в subscription_data[10] для user_id={user_id}: {subscription_data[10]}. Используется текущая дата. Ошибка: {e}")
                logger.debug(f"Содержимое subscription_data для user_id={user_id}: {subscription_data}")

        # Планируем отправку через 1 час
        schedule_time = registration_date + timedelta(hours=1)

        # Проверяем, было ли уже отправлено приветственное сообщение
        async with aiosqlite.connect(DATABASE_PATH) as conn:
            conn.row_factory = aiosqlite.Row
            c = await conn.cursor()
            await c.execute("SELECT welcome_message_sent FROM users WHERE user_id = ?", (user_id,))
            result = await c.fetchone()
            welcome_sent = result['welcome_message_sent'] if result else 0

        if welcome_sent:
            logger.debug(f"Приветственное сообщение уже отправлено для user_id={user_id}, пропускаем")
            return

        if schedule_time <= current_time:
            logger.warning(f"Попытка запланировать приветственное сообщение в прошлом для user_id={user_id}")
            await send_onboarding_message(bot, user_id, "welcome", subscription_data)
            return

        scheduler = AsyncIOScheduler(timezone=moscow_tz)
        job_id = f"welcome_{user_id}"

        logger.info(f"Планируем приветственное сообщение для user_id={user_id} на {schedule_time}")
        scheduler.add_job(
            send_onboarding_message,
            trigger='date',
            run_date=schedule_time,
            args=[bot, user_id, "welcome", subscription_data],
            id=job_id,
            misfire_grace_time=300
        )
        scheduler.start()
        logger.info(f"Приветственное сообщение запланировано для user_id={user_id}")

    except Exception as e:
        logger.error(f"Ошибка планирования приветственного сообщения для user_id={user_id}: {e}", exc_info=True)

async def schedule_daily_reminders(bot: Bot) -> None:
    """Планирует ежедневные напоминания в 11:15 по МСК."""
    try:
        logger.info("Ежедневные напоминания будут отправляться в 11:15 по МСК")
        # Задача теперь планируется в main.py через основной планировщик
    except Exception as e:
        logger.error(f"Ошибка планирования ежедневных напоминаний: {e}", exc_info=True)

async def send_daily_reminders(bot: Bot) -> None:
    """Отправляет ежедневные напоминания пользователям."""
    try:
        users = await get_users_for_reminders()
        logger.info(f"Найдено {len(users)} пользователей для ежедневных напоминаний")

        moscow_tz = pytz.timezone('Europe/Moscow')
        current_time = datetime.now(moscow_tz)

        for user in users:
            user_id = user['user_id']
            first_name = user['first_name']
            username = user['username']
            created_at = user['created_at']
            last_reminder_type = user['last_reminder_type']

            # Проверяем, заблокирован ли пользователь
            if await is_user_blocked(user_id):
                logger.info(f"Пользователь user_id={user_id} заблокирован, пропускаем напоминание")
                continue

            # Проверяем, является ли пользователь старым
            is_old_user_flag = await is_old_user(user_id, cutoff_date="2025-07-11")
            if is_old_user_flag:
                logger.info(f"Пользователь user_id={user_id} старый, пропускаем напоминание")
                continue

            # Проверяем, есть ли у пользователя покупки
            has_purchases = await has_user_purchases(user_id, DATABASE_PATH)
            if has_purchases:
                logger.info(f"Пользователь user_id={user_id} уже имеет покупки, пропускаем напоминание")
                continue

            try:
                registration_date = datetime.strptime(created_at, '%Y-%m-%d %H:%M:%S').replace(tzinfo=moscow_tz)
            except ValueError as e:
                logger.warning(f"Невалидный формат даты для user_id={user_id}: {created_at}. Пропускаем. Ошибка: {e}")
                continue

            days_since_registration = (current_time.date() - registration_date.date()).days

            # Определяем, какое напоминание нужно отправить
            if days_since_registration == 1 and last_reminder_type != "reminder_day2":
                message_type = "reminder_day2"
            elif days_since_registration == 2 and last_reminder_type != "reminder_day3":
                message_type = "reminder_day3"
            elif days_since_registration == 3 and last_reminder_type != "reminder_day4":
                message_type = "reminder_day4"
            elif days_since_registration >= 4 and last_reminder_type != "reminder_day5":
                message_type = "reminder_day5"
            else:
                continue

            subscription_data = await check_database_user(user_id)
            if not subscription_data or len(subscription_data) < 14:
                logger.error(f"Неполные данные подписки для user_id={user_id}, пропускаем")
                continue

            logger.info(f"Отправка напоминания {message_type} для user_id={user_id}")
            await send_onboarding_message(bot, user_id, message_type, subscription_data)

        logger.info("Ежедневные напоминания отправлены")

    except Exception as e:
        logger.error(f"Ошибка отправки ежедневных напоминаний: {e}", exc_info=True)

async def proceed_to_tariff_callback(callback_query: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    """Обрабатывает нажатие кнопки 'Начать' для перехода к тарифам."""
    user_id = callback_query.from_user.id
    subscription_data = await check_database_user(user_id)
    if not subscription_data or len(subscription_data) < 14:
        await callback_query.message.answer(
            escape_md("❌ Ошибка сервера! Попробуйте позже.", version=2),
            parse_mode=ParseMode.MARKDOWN_V2
        )
        await callback_query.answer()
        return

    # Проверяем, есть ли у пользователя покупки
    has_purchases = await has_user_purchases(user_id, DATABASE_PATH)
    first_purchase = bool(subscription_data[5]) if len(subscription_data) > 5 else True

    if has_purchases:
        # Для оплативших пользователей показываем все тарифы
        tariff_message_text = get_tariff_text(first_purchase=first_purchase, is_paying_user=True)
        subscription_kb = await create_subscription_keyboard(hide_mini_tariff=False)
        await callback_query.message.answer(
            tariff_message_text,
            reply_markup=subscription_kb,
            parse_mode=ParseMode.MARKDOWN_V2
        )
    else:
        # Для неоплативших пользователей показываем тариф "Комфорт"
        day_config = get_day_config(1)  # День 1 - тариф "Комфорт"
        tariff_key = day_config.get("tariff_key")
        price = day_config.get("price")
        description = day_config.get("description")

        if tariff_key and price:
            message_text = f"💎 Тариф '{tariff_key.title()}' за {price}₽\n{description}\n\nТы получаешь:\n✅ 70 фото высокого качества\n✅ 1 аватар в подарок при первой покупке\n✅ Генерация по описанию\n✅ Оживление фото\n✅ Идеи из канала: @pixelpie_idea"

            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=f"💳 Выбрать тариф за {price}₽", callback_data=f"pay_{price}")],
                [InlineKeyboardButton(text="🔙 Главное меню", callback_data="back_to_menu")]
            ])

            await callback_query.message.answer(
                escape_md(message_text, version=2),
                reply_markup=keyboard,
                parse_mode=ParseMode.MARKDOWN_V2
            )
        else:
            # Fallback на все тарифы
            tariff_message_text = get_tariff_text(first_purchase=first_purchase, is_paying_user=False)
            subscription_kb = await create_subscription_keyboard(hide_mini_tariff=False)
            await callback_query.message.answer(
                tariff_message_text,
                reply_markup=subscription_kb,
                parse_mode=ParseMode.MARKDOWN_V2
            )

    await callback_query.answer()

def setup_onboarding_handlers():
    """Регистрирует обработчики для онбординга."""
    @onboarding_router.callback_query(lambda c: c.data == "proceed_to_tariff")
    async def tariff_callback_handler(query: CallbackQuery, state: FSMContext) -> None:
        logger.debug(f"tariff_callback_handler: Callback_query получен: id={query.id}, data={query.data}, user_id={query.from_user.id}")
        await proceed_to_tariff_callback(query, state, query.bot)

    @onboarding_router.callback_query(lambda c: c.data == "show_all_tariffs")
    async def show_all_tariffs_handler(query: CallbackQuery, state: FSMContext) -> None:
        """Обрабатывает нажатие кнопки 'Выбрать тариф' для показа всех тарифов."""
        user_id = query.from_user.id
        subscription_data = await check_database_user(user_id)
        if not subscription_data or len(subscription_data) < 14:
            await query.message.answer(
                escape_md("❌ Ошибка сервера! Попробуйте позже.", version=2),
                parse_mode=ParseMode.MARKDOWN_V2
            )
            await query.answer()
            return

        first_purchase = bool(subscription_data[5]) if len(subscription_data) > 5 else True

        # Показываем все тарифы
        tariff_message_text = get_tariff_text(first_purchase=first_purchase, is_paying_user=False)
        subscription_kb = await create_subscription_keyboard(hide_mini_tariff=False)
        await query.message.answer(
            tariff_message_text,
            reply_markup=subscription_kb,
            parse_mode=ParseMode.MARKDOWN_V2
        )
        await query.answer()
