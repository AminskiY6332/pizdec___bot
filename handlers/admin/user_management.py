# handlers/admin/user_management.py

import asyncio
import logging
import uuid
import re
from states import BotStates
from datetime import datetime
from typing import List, Dict, Optional
from aiogram import Router, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.enums import ParseMode
from aiogram.filters import Command
from database import (
    check_database_user, get_user_generation_stats, get_user_payments, get_user_trainedmodels,
    get_user_rating_and_registration, get_user_logs, delete_user_activity, block_user_access, is_user_blocked,
    update_user_credits, get_active_trainedmodel, search_users_by_query
)
from config import ADMIN_IDS
from keyboards import create_admin_user_actions_keyboard, create_admin_keyboard
from handlers.utils import (
    escape_message_parts, send_message_with_fallback, truncate_text,
    create_isolated_context, clean_admin_context
)
import aiosqlite
from keyboards import create_main_menu_keyboard

from logger import get_logger
logger = get_logger('main')

# Создание роутера для управления пользователями
user_management_router = Router()

async def show_user_actions(query: CallbackQuery, state: FSMContext) -> None:
    """Показывает действия, доступные админу для конкретного пользователя."""
    user_id = query.from_user.id
    if user_id not in ADMIN_IDS:
        await query.answer("⛔ Недостаточно прав", show_alert=True)
        await state.clear()
        text = escape_message_parts("❌ У вас нет прав.", version=2)
        await query.message.answer(
            text,
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    callback_data = query.data
    logger.debug(f"show_user_actions: user_id={user_id}, callback_data={callback_data}")

    try:
        parts = callback_data.split("_")
        if len(parts) < 3 or parts[0] != "user" or parts[1] != "actions":
            raise ValueError("Неверный формат callback_data")
        target_user_id = int(parts[2])
    except (ValueError, IndexError) as e:
        logger.error(f"Ошибка обработки callback_data: {callback_data}, error: {e}")
        await state.clear()
        text = escape_message_parts(
            "❌ Ошибка обработки команды.",
            " Попробуйте снова.",
            version=2
        )
        await send_message_with_fallback(
            query.bot, user_id, text,
            reply_markup=await create_admin_user_actions_keyboard(0, False),
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    target_user_info = await check_database_user(target_user_id)
    if not target_user_info or (target_user_info[3] is None and target_user_info[8] is None):
        await state.clear()
        text = escape_message_parts(
            f"❌ Пользователь ID `{target_user_id}` не найден.",
            version=2
        )
        await send_message_with_fallback(
            query.bot, user_id, text,
            reply_markup=await create_admin_user_actions_keyboard(target_user_id, False),
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    g_left, a_left, _, u_name, _, f_purchase_val, email_val, act_avatar_id, f_name, _, _, _, _, _ = target_user_info
    display_name = f_name or u_name or f"ID {target_user_id}"
    username_display = f"(@{u_name})" if u_name and u_name != "Без имени" else ""
    email_display = email_val or "Не указан"

    text_parts = [
        "👤 Детальная информация о пользователе\n\n",
        f"Имя: {display_name} {username_display}\n",
        f"ID: `{target_user_id}`\n",
        f"Email: {email_display}\n",
        "\n💰 Баланс:\n",
        f"  • Печеньки: `{g_left}`\n",
        f"  • Аватары: `{a_left}`\n"
    ]

    gen_stats = await get_user_generation_stats(target_user_id)
    if gen_stats:
        total_generations = gen_stats.get('total_generations', 0)
        successful_generations = gen_stats.get('successful_generations', 0)
        failed_generations = gen_stats.get('failed_generations', 0)
        text_parts.extend([
            "\n📊 Статистика генераций:\n",
            f"  • Всего: `{total_generations}`\n",
            f"  • Успешных: `{successful_generations}`\n",
            f"  • Неудачных: `{failed_generations}`\n"
        ])

    payments = await get_user_payments(target_user_id)
    if payments:
        total_payments = len(payments)
        total_amount = sum(payment[2] for payment in payments if payment[2])
        text_parts.extend([
            "\n💳 Платежи:\n",
            f"  • Всего платежей: `{total_payments}`\n",
            f"  • Общая сумма: `{total_amount}` руб.\n"
        ])

    text = "".join(text_parts)
    await send_message_with_fallback(
        query.bot, user_id, text,
        reply_markup=await create_admin_user_actions_keyboard(target_user_id, True),
        parse_mode=ParseMode.MARKDOWN_V2
    )

async def show_user_profile_admin(query: CallbackQuery, state: FSMContext, target_user_id: int) -> None:
    """Показывает профиль пользователя для админа."""
    user_id = query.from_user.id
    if user_id not in ADMIN_IDS:
        await query.answer("⛔ Недостаточно прав", show_alert=True)
        return

    target_user_info = await check_database_user(target_user_id)
    if not target_user_info:
        await query.answer("❌ Пользователь не найден", show_alert=True)
        return

    g_left, a_left, _, u_name, _, f_purchase_val, email_val, act_avatar_id, f_name, _, _, _, _, _ = target_user_info
    display_name = f_name or u_name or f"ID {target_user_id}"
    username_display = f"(@{u_name})" if u_name and u_name != "Без имени" else ""
    email_display = email_val or "Не указан"

    text_parts = [
        "👤 Профиль пользователя\n\n",
        f"Имя: {display_name} {username_display}\n",
        f"ID: `{target_user_id}`\n",
        f"Email: {email_display}\n",
        "\n💰 Баланс:\n",
        f"  • Печеньки: `{g_left}`\n",
        f"  • Аватары: `{a_left}`\n"
    ]

    # Получаем информацию о рейтинге и регистрации
    rating_info = await get_user_rating_and_registration(target_user_id)
    if rating_info:
        rating, registration_date = rating_info
        text_parts.extend([
            "\n📅 Информация:\n",
            f"  • Дата регистрации: `{registration_date}`\n",
            f"  • Рейтинг: `{rating}`\n"
        ])

    text = "".join(text_parts)
    await send_message_with_fallback(
        query.bot, user_id, text,
        reply_markup=await create_admin_user_actions_keyboard(target_user_id, True),
        parse_mode=ParseMode.MARKDOWN_V2
    )

async def show_user_avatars_admin(query: CallbackQuery, state: FSMContext, target_user_id: int) -> None:
    """Показывает аватары пользователя для админа."""
    user_id = query.from_user.id
    if user_id not in ADMIN_IDS:
        await query.answer("⛔ Недостаточно прав", show_alert=True)
        return

    trained_models = await get_user_trainedmodels(target_user_id)
    if not trained_models:
        text = escape_message_parts(
            f"❌ У пользователя ID `{target_user_id}` нет обученных аватаров.",
            version=2
        )
        await send_message_with_fallback(
            query.bot, user_id, text,
            reply_markup=await create_admin_user_actions_keyboard(target_user_id, True),
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    text_parts = [
        f"🎭 Аватары пользователя ID `{target_user_id}`\n\n"
    ]

    for i, model in enumerate(trained_models, 1):
        model_name = model[1] or f"Аватар {i}"
        created_date = model[2] or "Неизвестно"
        status = "✅ Активный" if model[3] else "❌ Неактивный"
        
        text_parts.extend([
            f"{i}\\. {model_name}\n",
            f"   📅 Создан: `{created_date}`\n",
            f"   📊 Статус: {status}\n\n"
        ])

    text = "".join(text_parts)
    await send_message_with_fallback(
        query.bot, user_id, text,
        reply_markup=await create_admin_user_actions_keyboard(target_user_id, True),
        parse_mode=ParseMode.MARKDOWN_V2
    )

async def show_user_logs(query: CallbackQuery, state: FSMContext, target_user_id: int) -> None:
    """Показывает логи пользователя для админа."""
    user_id = query.from_user.id
    if user_id not in ADMIN_IDS:
        await query.answer("⛔ Недостаточно прав", show_alert=True)
        return

    logs = await get_user_logs(target_user_id, limit=10)
    if not logs:
        text = escape_message_parts(
            f"❌ У пользователя ID `{target_user_id}` нет логов.",
            version=2
        )
        await send_message_with_fallback(
            query.bot, user_id, text,
            reply_markup=await create_admin_user_actions_keyboard(target_user_id, True),
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    text_parts = [
        f"📋 Последние логи пользователя ID `{target_user_id}`\n\n"
    ]

    for i, log in enumerate(logs, 1):
        log_type = log[1] or "Неизвестно"
        log_message = log[2] or "Нет сообщения"
        log_date = log[3] or "Неизвестно"
        
        # Обрезаем длинные сообщения
        if len(log_message) > 100:
            log_message = log_message[:97] + "..."
        
        text_parts.extend([
            f"{i}\\. **{log_type}**\n",
            f"   📝 {log_message}\n",
            f"   📅 `{log_date}`\n\n"
        ])

    text = "".join(text_parts)
    await send_message_with_fallback(
        query.bot, user_id, text,
        reply_markup=await create_admin_user_actions_keyboard(target_user_id, True),
        parse_mode=ParseMode.MARKDOWN_V2
    )

async def change_balance_admin(query: CallbackQuery, state: FSMContext) -> None:
    """Начинает процесс изменения баланса пользователя."""
    user_id = query.from_user.id
    if user_id not in ADMIN_IDS:
        await query.answer("⛔ Недостаточно прав", show_alert=True)
        return

    callback_data = query.data
    try:
        parts = callback_data.split("_")
        if len(parts) < 4 or parts[0] != "change" or parts[1] != "balance":
            raise ValueError("Неверный формат callback_data")
        target_user_id = int(parts[2])
        balance_type = parts[3]  # "g" для печенек, "a" для аватаров
    except (ValueError, IndexError) as e:
        logger.error(f"Ошибка обработки callback_data: {callback_data}, error: {e}")
        await query.answer("❌ Ошибка обработки команды", show_alert=True)
        return

    await state.update_data(
        target_user_id=target_user_id,
        balance_type=balance_type
    )

    balance_name = "печенек" if balance_type == "g" else "аватаров"
    text = escape_message_parts(
        f"💰 Введите количество {balance_name} для пользователя ID `{target_user_id}`\n\n"
        "Используйте положительные числа для добавления, отрицательные для вычитания.\n"
        "Например: `+10` или `-5`",
        version=2
    )

    await send_message_with_fallback(
        query.bot, user_id, text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Отмена", callback_data=f"user_actions_{target_user_id}")]
        ]),
        parse_mode=ParseMode.MARKDOWN_V2
    )
    await state.set_state(BotStates.AWAITING_BALANCE_CHANGE)

async def handle_balance_change_input(message: Message, state: FSMContext) -> None:
    """Обрабатывает ввод изменения баланса."""
    user_id = message.from_user.id
    if user_id not in ADMIN_IDS:
        return

    try:
        change_amount = int(message.text)
    except ValueError:
        text = escape_message_parts(
            "❌ Пожалуйста, введите целое число.\n"
            "Используйте положительные числа для добавления, отрицательные для вычитания.",
            version=2
        )
        await send_message_with_fallback(
            message.bot, user_id, text,
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    user_data = await state.get_data()
    target_user_id = user_data.get('target_user_id')
    balance_type = user_data.get('balance_type')

    if not target_user_id or not balance_type:
        await state.clear()
        text = escape_message_parts("❌ Ошибка: данные сессии утеряны.", version=2)
        await send_message_with_fallback(
            message.bot, user_id, text,
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    # Обновляем баланс в базе данных
    success = await update_user_credits(target_user_id, change_amount, balance_type)
    
    if success:
        balance_name = "печенек" if balance_type == "g" else "аватаров"
        operation = "добавлено" if change_amount > 0 else "вычтено"
        abs_amount = abs(change_amount)
        
        text = escape_message_parts(
            f"✅ Баланс пользователя ID `{target_user_id}` обновлен!\n\n"
            f"Операция: {operation} `{abs_amount}` {balance_name}",
            version=2
        )
    else:
        text = escape_message_parts(
            f"❌ Ошибка при обновлении баланса пользователя ID `{target_user_id}`",
            version=2
        )

    await send_message_with_fallback(
        message.bot, user_id, text,
        reply_markup=await create_admin_user_actions_keyboard(target_user_id, True),
        parse_mode=ParseMode.MARKDOWN_V2
    )
    await state.clear()

async def delete_user_admin(query: CallbackQuery, state: FSMContext, target_user_id: int) -> None:
    """Начинает процесс удаления пользователя."""
    user_id = query.from_user.id
    if user_id not in ADMIN_IDS:
        await query.answer("⛔ Недостаточно прав", show_alert=True)
        return

    target_user_info = await check_database_user(target_user_id)
    if not target_user_info:
        await query.answer("❌ Пользователь не найден", show_alert=True)
        return

    g_left, a_left, _, u_name, _, f_purchase_val, email_val, act_avatar_id, f_name, _, _, _, _, _ = target_user_info
    display_name = f_name or u_name or f"ID {target_user_id}"

    text = escape_message_parts(
        f"⚠️ Вы уверены, что хотите удалить пользователя?\n\n"
        f"Имя: {display_name}\n"
        f"ID: `{target_user_id}`\n"
        f"Баланс: {g_left} печенек, {a_left} аватаров\n\n"
        f"⚠️ Это действие нельзя отменить!",
        version=2
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"confirm_delete_user_{target_user_id}")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data=f"user_actions_{target_user_id}")]
    ])

    await send_message_with_fallback(
        query.bot, user_id, text,
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN_V2
    )

async def confirm_delete_user(query: CallbackQuery, state: FSMContext, target_user_id: int) -> None:
    """Подтверждает удаление пользователя."""
    user_id = query.from_user.id
    if user_id not in ADMIN_IDS:
        await query.answer("⛔ Недостаточно прав", show_alert=True)
        return

    # Удаляем активность пользователя
    success = await delete_user_activity(target_user_id)
    
    if success:
        text = escape_message_parts(
            f"✅ Пользователь ID `{target_user_id}` успешно удален!",
            version=2
        )
    else:
        text = escape_message_parts(
            f"❌ Ошибка при удалении пользователя ID `{target_user_id}`",
            version=2
        )

    await send_message_with_fallback(
        query.bot, user_id, text,
        reply_markup=await create_admin_keyboard(),
        parse_mode=ParseMode.MARKDOWN_V2
    )

async def block_user_admin(query: CallbackQuery, state: FSMContext) -> None:
    """Начинает процесс блокировки пользователя."""
    user_id = query.from_user.id
    if user_id not in ADMIN_IDS:
        await query.answer("⛔ Недостаточно прав", show_alert=True)
        return

    callback_data = query.data
    try:
        parts = callback_data.split("_")
        if len(parts) < 3 or parts[0] != "block" or parts[1] != "user":
            raise ValueError("Неверный формат callback_data")
        target_user_id = int(parts[2])
    except (ValueError, IndexError) as e:
        logger.error(f"Ошибка обработки callback_data: {callback_data}, error: {e}")
        await query.answer("❌ Ошибка обработки команды", show_alert=True)
        return

    target_user_info = await check_database_user(target_user_id)
    if not target_user_info:
        await query.answer("❌ Пользователь не найден", show_alert=True)
        return

    g_left, a_left, _, u_name, _, f_purchase_val, email_val, act_avatar_id, f_name, _, _, _, _, _ = target_user_info
    display_name = f_name or u_name or f"ID {target_user_id}"

    # Проверяем, заблокирован ли уже пользователь
    is_blocked = await is_user_blocked(target_user_id)
    if is_blocked:
        text = escape_message_parts(
            f"ℹ️ Пользователь уже заблокирован\n\n"
            f"Имя: {display_name}\n"
            f"ID: `{target_user_id}`",
            version=2
        )
        await send_message_with_fallback(
            query.bot, user_id, text,
            reply_markup=await create_admin_user_actions_keyboard(target_user_id, True),
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    text = escape_message_parts(
        f"🚫 Вы уверены, что хотите заблокировать пользователя?\n\n"
        f"Имя: {display_name}\n"
        f"ID: `{target_user_id}`\n"
        f"Баланс: {g_left} печенек, {a_left} аватаров\n\n"
        f"⚠️ Заблокированный пользователь не сможет использовать бота!",
        version=2
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚫 Да, заблокировать", callback_data=f"confirm_block_user_{target_user_id}")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data=f"user_actions_{target_user_id}")]
    ])

    await send_message_with_fallback(
        query.bot, user_id, text,
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN_V2
    )

async def confirm_block_user(query: CallbackQuery, state: FSMContext, bot: Bot, is_fake_query: bool = False) -> None:
    """Подтверждает блокировку пользователя."""
    user_id = query.from_user.id if not is_fake_query else query.from_user.id
    if user_id not in ADMIN_IDS:
        if not is_fake_query:
            await query.answer("⛔ Недостаточно прав", show_alert=True)
        return

    callback_data = query.data
    try:
        parts = callback_data.split("_")
        if len(parts) < 4 or parts[0] != "confirm" or parts[1] != "block" or parts[2] != "user":
            raise ValueError("Неверный формат callback_data")
        target_user_id = int(parts[3])
    except (ValueError, IndexError) as e:
        logger.error(f"Ошибка обработки callback_data: {callback_data}, error: {e}")
        if not is_fake_query:
            await query.answer("❌ Ошибка обработки команды", show_alert=True)
        return

    target_user_info = await check_database_user(target_user_id)
    if not target_user_info:
        if not is_fake_query:
            await query.answer("❌ Пользователь не найден", show_alert=True)
        return

    g_left, a_left, _, u_name, _, f_purchase_val, email_val, act_avatar_id, f_name, _, _, _, _, _ = target_user_info
    display_name = f_name or u_name or f"ID {target_user_id}"

    # Блокируем пользователя
    success = await block_user_access(target_user_id)
    
    if success:
        text = escape_message_parts(
            f"🚫 Пользователь успешно заблокирован!\n\n"
            f"Имя: {display_name}\n"
            f"ID: `{target_user_id}`",
            version=2
        )
        
        # Отправляем уведомление заблокированному пользователю
        try:
            block_notification = escape_message_parts(
                "🚫 Ваш аккаунт заблокирован администратором.\n\n"
                "Если вы считаете, что это произошло по ошибке, обратитесь в поддержку.",
                version=2
            )
            await send_message_with_fallback(
                bot, target_user_id, block_notification,
                parse_mode=ParseMode.MARKDOWN_V2
            )
        except Exception as e:
            logger.error(f"Не удалось отправить уведомление заблокированному пользователю {target_user_id}: {e}")
    else:
        text = escape_message_parts(
            f"❌ Ошибка при блокировке пользователя ID `{target_user_id}`",
            version=2
        )

    if not is_fake_query:
        await send_message_with_fallback(
            query.bot, user_id, text,
            reply_markup=await create_admin_keyboard(),
            parse_mode=ParseMode.MARKDOWN_V2
        )

async def search_users_admin(query: CallbackQuery, state: FSMContext) -> None:
    """Начинает процесс поиска пользователей."""
    user_id = query.from_user.id
    if user_id not in ADMIN_IDS:
        await query.answer("⛔ Недостаточно прав", show_alert=True)
        return

    text = escape_message_parts(
        "🔍 Поиск пользователей\n\n"
        "Введите поисковый запрос:\n"
        "• ID пользователя (например: 123456789)\n"
        "• Имя пользователя (например: @username)\n"
        "• Email пользователя\n"
        "• Часть имени или фамилии",
        version=2
    )

    await send_message_with_fallback(
        query.bot, user_id, text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Отмена", callback_data="admin_panel")]
        ]),
        parse_mode=ParseMode.MARKDOWN_V2
    )
    await state.set_state(BotStates.AWAITING_USER_SEARCH)

async def handle_user_search_input(message: Message, state: FSMContext) -> None:
    """Обрабатывает ввод поискового запроса."""
    user_id = message.from_user.id
    if user_id not in ADMIN_IDS:
        return

    search_query = message.text.strip()
    if not search_query:
        text = escape_message_parts(
            "❌ Пожалуйста, введите поисковый запрос.",
            version=2
        )
        await send_message_with_fallback(
            message.bot, user_id, text,
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    # Выполняем поиск пользователей
    users = await search_users_by_query(search_query, limit=10)
    
    if not users:
        text = escape_message_parts(
            f"❌ Пользователи по запросу \"{search_query}\" не найдены.",
            version=2
        )
        await send_message_with_fallback(
            message.bot, user_id, text,
            reply_markup=await create_admin_keyboard(),
            parse_mode=ParseMode.MARKDOWN_V2
        )
        await state.clear()
        return

    text_parts = [
        f"🔍 Результаты поиска по запросу \"{search_query}\"\n\n"
    ]

    for i, user in enumerate(users, 1):
        user_id_result, g_left, a_left, u_name, _, f_purchase_val, email_val, act_avatar_id, f_name, _, _, _, _, _ = user
        display_name = f_name or u_name or f"ID {user_id_result}"
        username_display = f"(@{u_name})" if u_name and u_name != "Без имени" else ""
        
        text_parts.extend([
            f"{i}\\. **{display_name}** {username_display}\n",
            f"   ID: `{user_id_result}`\n",
            f"   💰 Баланс: {g_left} печенек, {a_left} аватаров\n"
        ])
        
        if email_val:
            text_parts.append(f"   📧 Email: {email_val}\n")
        
        text_parts.append("\n")

    text = "".join(text_parts)
    
    # Создаем клавиатуру с кнопками для каждого найденного пользователя
    keyboard_buttons = []
    for user in users[:5]:  # Ограничиваем 5 пользователями для клавиатуры
        user_id_result = user[0]
        display_name = user[8] or user[3] or f"ID {user_id_result}"
        button_text = f"👤 {display_name[:20]}"  # Ограничиваем длину текста кнопки
        keyboard_buttons.append([InlineKeyboardButton(
            text=button_text,
            callback_data=f"user_actions_{user_id_result}"
        )])

    keyboard_buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="admin_panel")])
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

    await send_message_with_fallback(
        message.bot, user_id, text,
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN_V2
    )
    await state.clear()

async def confirm_reset_avatar(query: CallbackQuery, state: FSMContext, target_user_id: int) -> None:
    """Подтверждает сброс аватара пользователя."""
    user_id = query.from_user.id
    if user_id not in ADMIN_IDS:
        await query.answer("⛔ Недостаточно прав", show_alert=True)
        return

    target_user_info = await check_database_user(target_user_id)
    if not target_user_info:
        await query.answer("❌ Пользователь не найден", show_alert=True)
        return

    g_left, a_left, _, u_name, _, f_purchase_val, email_val, act_avatar_id, f_name, _, _, _, _, _ = target_user_info
    display_name = f_name or u_name or f"ID {target_user_id}"

    # Сбрасываем активный аватар пользователя
    async with aiosqlite.connect(DATABASE_PATH) as conn:
        await conn.execute(
            "UPDATE users SET active_avatar_id = NULL WHERE user_id = ?",
            (target_user_id,)
        )
        await conn.commit()

    text = escape_message_parts(
        f"🔄 Аватар пользователя сброшен!\n\n"
        f"Имя: {display_name}\n"
        f"ID: `{target_user_id}`\n\n"
        f"Пользователь сможет выбрать новый аватар при следующем использовании бота.",
        version=2
    )

    await send_message_with_fallback(
        query.bot, user_id, text,
        reply_markup=await create_admin_user_actions_keyboard(target_user_id, True),
        parse_mode=ParseMode.MARKDOWN_V2
    )

async def cancel(message: Message, state: FSMContext) -> None:
    """Отменяет текущую операцию."""
    user_id = message.from_user.id
    if user_id not in ADMIN_IDS:
        return

    await state.clear()
    text = escape_message_parts("❌ Операция отменена.", version=2)
    await send_message_with_fallback(
        message.bot, user_id, text,
        reply_markup=await create_admin_keyboard(),
        parse_mode=ParseMode.MARKDOWN_V2
    )

async def handle_block_reason_input(message: Message, state: FSMContext) -> None:
    """Обрабатывает ввод причины блокировки."""
    user_id = message.from_user.id
    if user_id not in ADMIN_IDS:
        return

    reason = message.text.strip()
    if not reason:
        text = escape_message_parts(
            "❌ Пожалуйста, введите причину блокировки.",
            version=2
        )
        await send_message_with_fallback(
            message.bot, user_id, text,
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    user_data = await state.get_data()
    target_user_id = user_data.get('target_user_id')

    if not target_user_id:
        await state.clear()
        text = escape_message_parts("❌ Ошибка: данные сессии утеряны.", version=2)
        await send_message_with_fallback(
            message.bot, user_id, text,
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    # Блокируем пользователя с указанной причиной
    success = await block_user_access(target_user_id, reason=reason)
    
    if success:
        text = escape_message_parts(
            f"🚫 Пользователь ID `{target_user_id}` заблокирован!\n\n"
            f"Причина: {reason}",
            version=2
        )
    else:
        text = escape_message_parts(
            f"❌ Ошибка при блокировке пользователя ID `{target_user_id}`",
            version=2
        )

    await send_message_with_fallback(
        message.bot, user_id, text,
        reply_markup=await create_admin_keyboard(),
        parse_mode=ParseMode.MARKDOWN_V2
    )
    await state.clear()

# Регистрация обработчиков
@user_management_router.callback_query(
    lambda c: c.data and c.data.startswith((
        'user_actions_', 'view_user_profile_', 'user_avatars_', 'user_logs_', 'change_balance_',
        'delete_user_', 'confirm_delete_user_', 'block_user_', 'confirm_block_user_', 'payments_',
        'visualize_', 'reset_avatar_', 'add_photos_to_user_', 'add_avatar_to_user_', 'chat_with_user_',
        'give_subscription_', 'activity_'
    ))
)
async def user_management_callback_handler(query: CallbackQuery, state: FSMContext) -> None:
    """Обработчик callback-запросов для управления пользователями."""
    user_id = query.from_user.id
    if user_id not in ADMIN_IDS:
        await query.answer("⛔ Недостаточно прав", show_alert=True)
        return

    callback_data = query.data
    logger.debug(f"user_management_callback_handler: user_id={user_id}, callback_data={callback_data}")

    try:
        if callback_data.startswith("user_actions_"):
            await show_user_actions(query, state)
        elif callback_data.startswith("view_user_profile_"):
            target_user_id = int(callback_data.split("_")[3])
            await show_user_profile_admin(query, state, target_user_id)
        elif callback_data.startswith("user_avatars_"):
            target_user_id = int(callback_data.split("_")[2])
            await show_user_avatars_admin(query, state, target_user_id)
        elif callback_data.startswith("user_logs_"):
            target_user_id = int(callback_data.split("_")[2])
            await show_user_logs(query, state, target_user_id)
        elif callback_data.startswith("change_balance_"):
            await change_balance_admin(query, state)
        elif callback_data.startswith("delete_user_"):
            target_user_id = int(callback_data.split("_")[2])
            await delete_user_admin(query, state, target_user_id)
        elif callback_data.startswith("confirm_delete_user_"):
            target_user_id = int(callback_data.split("_")[3])
            await confirm_delete_user(query, state, target_user_id)
        elif callback_data.startswith("block_user_"):
            await block_user_admin(query, state)
        elif callback_data.startswith("confirm_block_user_"):
            target_user_id = int(callback_data.split("_")[3])
            await confirm_block_user(query, state, query.bot)
        elif callback_data.startswith("reset_avatar_"):
            target_user_id = int(callback_data.split("_")[2])
            await confirm_reset_avatar(query, state, target_user_id)
        else:
            logger.warning(f"Неизвестный callback_data: {callback_data}")
            await query.answer("❌ Неизвестная команда", show_alert=True)
    except Exception as e:
        logger.error(f"Ошибка в user_management_callback_handler: {e}")
        await query.answer("❌ Произошла ошибка", show_alert=True)

# Регистрация обработчиков сообщений
@user_management_router.message(BotStates.AWAITING_BALANCE_CHANGE)
async def handle_balance_change_input_wrapper(message: Message, state: FSMContext) -> None:
    """Обертка для обработки ввода изменения баланса."""
    await handle_balance_change_input(message, state)

@user_management_router.message(BotStates.AWAITING_USER_SEARCH)
async def handle_user_search_input_wrapper(message: Message, state: FSMContext) -> None:
    """Обертка для обработки ввода поиска пользователей."""
    await handle_user_search_input(message, state)

@user_management_router.message(BotStates.AWAITING_BLOCK_REASON)
async def handle_block_reason_input_wrapper(message: Message, state: FSMContext) -> None:
    """Обертка для обработки ввода причины блокировки."""
    await handle_block_reason_input(message, state)

@user_management_router.message(Command("cancel"))
async def cancel_wrapper(message: Message, state: FSMContext) -> None:
    """Обертка для отмены операции."""
    await cancel(message, state)