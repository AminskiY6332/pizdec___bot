# handlers/admin/payments.py

import asyncio
import logging
import os
import uuid
import pytz
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Dict
from aiogram import Router, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.enums import ParseMode
from aiogram.filters import Command
from database import get_payments_by_date, get_generation_cost_log, get_registrations_by_date
from config import ADMIN_IDS, DATABASE_PATH
from generation_config import IMAGE_GENERATION_MODELS
from excel_utils import create_payments_excel, create_registrations_excel
from keyboards import create_admin_keyboard
from handlers.utils import safe_escape_markdown as escape_md, send_message_with_fallback, anti_spam
from states import BotStates

from logger import get_logger
logger = get_logger('payments')

# Создание роутера для платежей
payments_router = Router()

# Функция для экранирования символов в Markdown V2
def escape_md_v2(text: str) -> str:
    """Экранирует специальные символы для ParseMode.MARKDOWN_V2."""
    characters_to_escape = r'_[]()*~`#+-=|{}!.>'
    for char in characters_to_escape:
        text = text.replace(char, f'\\{char}')
    return text

async def show_payments_menu(query: CallbackQuery, state: FSMContext) -> None:
    """Показывает меню выбора периода для статистики платежей и регистраций."""
    user_id = query.from_user.id
    if user_id not in ADMIN_IDS:
        await send_message_with_fallback(
            query.bot, user_id, escape_md_v2("❌ У вас нет прав для доступа к этой функции\\."),
            reply_markup=await create_admin_keyboard(user_id),
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    try:
        msk_tz = pytz.timezone('Europe/Moscow')
        today = datetime.now(msk_tz).strftime('%Y-%m-%d')
        yesterday = (datetime.now(msk_tz) - timedelta(days=1)).strftime('%Y-%m-%d')
        last_7_days_start = (datetime.now(msk_tz) - timedelta(days=7)).strftime('%Y-%m-%d')
        last_30_days_start = (datetime.now(msk_tz) - timedelta(days=30)).strftime('%Y-%m-%d')

        # Проверка корректности формата дат
        for date_str in [today, yesterday, last_7_days_start, last_30_days_start]:
            datetime.strptime(date_str, '%Y-%m-%d')

        # Изменение: Формат дат не экранируем, так как он внутри ` ` и безопасен
        text = (
            escape_md("📈 Статистика платежей и регистраций\n\n"
                         "Выберите период для получения статистики или введите даты вручную в формате:\n") +
            "`YYYY-MM-DD` (для одного дня)\nили\n`YYYY-MM-DD YYYY-MM-DD` (для диапазона)\\.\n\n" +
            escape_md_v2("Пример:\n") +
            f"`{today}` или `{last_30_days_start} {today}`"
        )

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Сегодня", callback_data=f"payments_date_{today}_{today}")],
            [InlineKeyboardButton(text="Вчера", callback_data=f"payments_date_{yesterday}_{yesterday}")],
            [InlineKeyboardButton(text="Последние 7 дней", callback_data=f"payments_date_{last_7_days_start}_{today}")],
            [InlineKeyboardButton(text="Последние 30 дней", callback_data=f"payments_date_{last_30_days_start}_{today}")],
            [InlineKeyboardButton(text="Ввести даты вручную", callback_data="payments_manual_date")],
            [InlineKeyboardButton(text="🔙 Назад в админ-панель", callback_data="admin_panel")]
        ])

        await send_message_with_fallback(
            query.bot, user_id, text,
            reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN_V2
        )
    except Exception as e:
        logger.error(f"Ошибка в show_payments_menu для user_id={user_id}: {e}", exc_info=True)
        await send_message_with_fallback(
            query.bot, user_id, escape_md_v2("❌ Ошибка при отображении меню\\. Попробуйте снова\\."),
            reply_markup=await create_admin_keyboard(user_id),
            parse_mode=ParseMode.MARKDOWN_V2
        )

async def handle_payments_date(query: CallbackQuery, state: FSMContext, start_date: str, end_date: str) -> None:
    """Обрабатывает запрос статистики платежей и регистраций за указанный период."""
    user_id = query.from_user.id
    if user_id not in ADMIN_IDS:
        await send_message_with_fallback(
            query.bot, user_id, escape_md_v2("❌ У вас нет прав для доступа к этой функции\\."),
            reply_markup=await create_admin_keyboard(user_id),
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    try:
        # Получаем данные о платежах
        payments_data = await get_payments_by_date(start_date, end_date)
        
        # Получаем данные о регистрациях
        registrations_data = await get_registrations_by_date(start_date, end_date)
        
        # Получаем данные о стоимости генераций
        generation_costs = await get_generation_cost_log(start_date, end_date)
        
        # Подсчитываем статистику
        total_payments = len(payments_data) if payments_data else 0
        total_amount = sum(payment[2] for payment in payments_data) if payments_data else 0
        total_registrations = len(registrations_data) if registrations_data else 0
        total_generation_cost = sum(cost[2] for cost in generation_costs) if generation_costs else 0
        
        # Формируем текст отчета
        text_parts = [
            escape_md_v2("📊 Статистика за период ") + f"`{start_date}` - `{end_date}`\n\n",
            escape_md_v2("💰 Платежи:\n") +
            f"  • Количество: `{total_payments}`\n" +
            f"  • Общая сумма: `{total_amount}` руб\\.\n\n",
            escape_md_v2("👥 Регистрации:\n") +
            f"  • Новых пользователей: `{total_registrations}`\n\n",
            escape_md_v2("🎨 Генерации:\n") +
            f"  • Общая стоимость: `{total_generation_cost}` руб\\.\n\n"
        ]
        
        # Добавляем детали по моделям генерации
        if generation_costs:
            model_costs = {}
            for cost in generation_costs:
                model_name = cost[1]
                model_costs[model_name] = model_costs.get(model_name, 0) + cost[2]
            
            text_parts.append(escape_md_v2("📈 Детали по моделям:\n"))
            for model, cost in model_costs.items():
                text_parts.append(f"  • {model}: `{cost}` руб\\.\n")
        
        text = "".join(text_parts)
        
        # Создаем клавиатуру с опциями экспорта
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📊 Экспорт платежей", callback_data=f"export_payments_{start_date}_{end_date}")],
            [InlineKeyboardButton(text="📊 Экспорт регистраций", callback_data=f"export_registrations_{start_date}_{end_date}")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_payments")]
        ])
        
        await send_message_with_fallback(
            query.bot, user_id, text,
            reply_markup=keyboard,
            parse_mode=ParseMode.MARKDOWN_V2
        )
        
    except Exception as e:
        logger.error(f"Ошибка в handle_payments_date для user_id={user_id}: {e}", exc_info=True)
        await send_message_with_fallback(
            query.bot, user_id, escape_md_v2("❌ Ошибка при получении статистики\\. Попробуйте снова\\."),
            reply_markup=await create_admin_keyboard(user_id),
            parse_mode=ParseMode.MARKDOWN_V2
        )

async def handle_manual_date_input(query: CallbackQuery, state: FSMContext) -> None:
    """Обрабатывает запрос на ввод дат вручную."""
    user_id = query.from_user.id
    if user_id not in ADMIN_IDS:
        await send_message_with_fallback(
            query.bot, user_id, escape_md_v2("❌ У вас нет прав для доступа к этой функции\\."),
            reply_markup=await create_admin_keyboard(user_id),
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    text = (
        escape_md_v2("📅 Введите даты в формате:\n\n") +
        "`YYYY-MM-DD` (для одного дня)\nили\n`YYYY-MM-DD YYYY-MM-DD` (для диапазона)\n\n" +
        escape_md_v2("Примеры:\n") +
        "`2024-01-15` или `2024-01-01 2024-01-31`"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Отмена", callback_data="admin_payments")]
    ])

    await send_message_with_fallback(
        query.bot, user_id, text,
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN_V2
    )
    await state.set_state(BotStates.AWAITING_PAYMENTS_DATE)

async def handle_payments_date_input(message: Message, state: FSMContext) -> None:
    """Обрабатывает ввод дат для статистики платежей."""
    user_id = message.from_user.id
    if user_id not in ADMIN_IDS:
        return

    date_input = message.text.strip()
    
    try:
        if ' ' in date_input:
            # Диапазон дат
            start_date, end_date = date_input.split(' ', 1)
            start_date = start_date.strip()
            end_date = end_date.strip()
            
            # Проверяем формат дат
            datetime.strptime(start_date, '%Y-%m-%d')
            datetime.strptime(end_date, '%Y-%m-%d')
        else:
            # Одна дата
            start_date = date_input.strip()
            end_date = start_date
            
            # Проверяем формат даты
            datetime.strptime(start_date, '%Y-%m-%d')
        
        # Вызываем обработчик статистики
        fake_query = type('FakeQuery', (), {
            'from_user': message.from_user,
            'bot': message.bot,
            'data': f"payments_date_{start_date}_{end_date}"
        })()
        
        await handle_payments_date(fake_query, state, start_date, end_date)
        
    except ValueError:
        text = escape_md_v2("❌ Неверный формат даты\\. Используйте формат `YYYY-MM-DD`\\.")
        await send_message_with_fallback(
            message.bot, user_id, text,
            parse_mode=ParseMode.MARKDOWN_V2
        )
    except Exception as e:
        logger.error(f"Ошибка в handle_payments_date_input для user_id={user_id}: {e}", exc_info=True)
        text = escape_md_v2("❌ Ошибка при обработке дат\\. Попробуйте снова\\.")
        await send_message_with_fallback(
            message.bot, user_id, text,
            parse_mode=ParseMode.MARKDOWN_V2
        )

async def show_replicate_costs(query: CallbackQuery, state: FSMContext) -> None:
    """Показывает статистику затрат на генерации."""
    user_id = query.from_user.id
    if user_id not in ADMIN_IDS:
        await send_message_with_fallback(
            query.bot, user_id, escape_md_v2("❌ У вас нет прав для доступа к этой функции\\."),
            reply_markup=await create_admin_keyboard(user_id),
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    try:
        # Получаем данные о стоимости генераций за последние 30 дней
        msk_tz = pytz.timezone('Europe/Moscow')
        end_date = datetime.now(msk_tz).strftime('%Y-%m-%d')
        start_date = (datetime.now(msk_tz) - timedelta(days=30)).strftime('%Y-%m-%d')
        
        generation_costs = await get_generation_cost_log(start_date, end_date)
        
        if not generation_costs:
            text = escape_md_v2("❌ Нет данных о затратах на генерации за последние 30 дней\\.")
            await send_message_with_fallback(
                query.bot, user_id, text,
                reply_markup=await create_admin_keyboard(user_id),
                parse_mode=ParseMode.MARKDOWN_V2
            )
            return
        
        # Группируем по моделям
        model_costs = {}
        total_cost = 0
        
        for cost in generation_costs:
            model_name = cost[1]
            cost_amount = cost[2]
            model_costs[model_name] = model_costs.get(model_name, 0) + cost_amount
            total_cost += cost_amount
        
        # Формируем текст отчета
        text_parts = [
            escape_md_v2("🎨 Затраты на генерации за последние 30 дней\n\n") +
            f"Общая сумма: `{total_cost}` руб\\.\n\n"
        ]
        
        for model, cost in model_costs.items():
            percentage = (cost / total_cost * 100) if total_cost > 0 else 0
            text_parts.append(f"• {model}: `{cost}` руб\\. \\({percentage:.1f}%\\)\n")
        
        text = "".join(text_parts)
        
        await send_message_with_fallback(
            query.bot, user_id, text,
            reply_markup=await create_admin_keyboard(user_id),
            parse_mode=ParseMode.MARKDOWN_V2
        )
        
    except Exception as e:
        logger.error(f"Ошибка в show_replicate_costs для user_id={user_id}: {e}", exc_info=True)
        await send_message_with_fallback(
            query.bot, user_id, escape_md_v2("❌ Ошибка при получении статистики затрат\\."),
            reply_markup=await create_admin_keyboard(user_id),
            parse_mode=ParseMode.MARKDOWN_V2
        )

async def cancel_payments(message: Message, state: FSMContext) -> None:
    """Отменяет ввод дат для статистики платежей."""
    user_id = message.from_user.id
    if user_id not in ADMIN_IDS:
        return

    await state.clear()
    text = escape_md_v2("❌ Ввод дат отменен\\.")
    await send_message_with_fallback(
        message.bot, user_id, text,
        reply_markup=await create_admin_keyboard(user_id),
        parse_mode=ParseMode.MARKDOWN_V2
    )

# Регистрация обработчиков
@payments_router.callback_query(
    lambda c: c.data and c.data.startswith("payments_date_") or c.data in ["payments_manual_date", "admin_payments"]
)
async def payments_callback_handler(query: CallbackQuery, state: FSMContext) -> None:
    """Обработчик callback-запросов для платежей."""
    user_id = query.from_user.id
    if user_id not in ADMIN_IDS:
        await query.answer("⛔ Недостаточно прав", show_alert=True)
        return

    callback_data = query.data
    logger.debug(f"payments_callback_handler: user_id={user_id}, callback_data={callback_data}")

    try:
        if callback_data == "admin_payments":
            await show_payments_menu(query, state)
        elif callback_data == "payments_manual_date":
            await handle_manual_date_input(query, state)
        elif callback_data.startswith("payments_date_"):
            # Извлекаем даты из callback_data
            parts = callback_data.split("_")
            if len(parts) >= 4:
                start_date = parts[2]
                end_date = parts[3]
                await handle_payments_date(query, state, start_date, end_date)
            else:
                await query.answer("❌ Неверный формат данных", show_alert=True)
        else:
            logger.warning(f"Неизвестный callback_data: {callback_data}")
            await query.answer("❌ Неизвестная команда", show_alert=True)
    except Exception as e:
        logger.error(f"Ошибка в payments_callback_handler: {e}")
        await query.answer("❌ Произошла ошибка", show_alert=True)

# Регистрация обработчиков сообщений
@payments_router.message(BotStates.AWAITING_PAYMENT_DATES)
async def handle_payments_date_input_wrapper(message: Message, state: FSMContext) -> None:
    """Обертка для обработки ввода дат платежей."""
    await handle_payments_date_input(message, state)

@payments_router.message(Command("cancel"))
async def cancel_payments_wrapper(message: Message, state: FSMContext) -> None:
    """Обертка для отмены ввода дат платежей."""
    await cancel_payments(message, state)