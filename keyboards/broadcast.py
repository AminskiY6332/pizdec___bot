# keyboards/broadcast.py
"""
Клавиатуры для рассылок и уведомлений
"""

import logging
from typing import List, Dict
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from config import ADMIN_IDS, ALLOWED_BROADCAST_CALLBACKS
from database import check_database_user, get_user_payments

from logger import get_logger
logger = get_logger('keyboards')

async def create_broadcast_keyboard() -> InlineKeyboardMarkup:
    """Создаёт клавиатуру для рассылки."""
    try:
        keyboard = [
            [InlineKeyboardButton(text="📤 Отправить без текста", callback_data="send_broadcast_no_text")],
            [InlineKeyboardButton(text="🔙 Отмена", callback_data="admin_panel")]
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)
    except Exception as e:
        logger.error(f"Ошибка в create_broadcast_keyboard: {e}", exc_info=True)
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Ошибка, вернуться в меню", callback_data="back_to_menu")]
        ])

async def create_broadcast_with_payment_audience_keyboard() -> InlineKeyboardMarkup:
    """Создаёт клавиатуру выбора аудитории для рассылки с кнопкой оплаты."""
    try:
        keyboard = [
            [InlineKeyboardButton(text="👥 Всем", callback_data="broadcast_with_payment_all")],
            [InlineKeyboardButton(text="💳 Оплатившим", callback_data="broadcast_with_payment_paid")],
            [InlineKeyboardButton(text="🆓 Не оплатившим", callback_data="broadcast_with_payment_non_paid")],
            [InlineKeyboardButton(text="🔙 Отмена", callback_data="admin_panel")]
        ]
        logger.debug("Клавиатура выбора аудитории для рассылки с кнопкой оплаты создана успешно")
        return InlineKeyboardMarkup(inline_keyboard=keyboard)
    except Exception as e:
        logger.error(f"Ошибка в create_broadcast_with_payment_audience_keyboard: {e}", exc_info=True)
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Ошибка, вернуться в меню", callback_data="back_to_menu")]
        ])

async def create_dynamic_broadcast_keyboard(buttons: List[Dict[str, str]], user_id: int) -> InlineKeyboardMarkup:
    """Создаёт клавиатуру для рассылки на основе списка кнопок с учётом статуса оплаты пользователя."""
    try:
        keyboard = []
        row = []
        # Проверяем статус оплаты и ресурсы пользователя
        subscription_data = await check_database_user(user_id)
        payments = await get_user_payments(user_id)
        is_paying_user = bool(payments) or (subscription_data and len(subscription_data) > 5 and not bool(subscription_data[5]))
        has_resources = subscription_data and len(subscription_data) > 1 and (subscription_data[0] > 0 or subscription_data[1] > 0)
        is_admin = user_id in ADMIN_IDS

        for button in buttons[:3]:  # Ограничиваем до 3 кнопок
            button_text = button["text"][:64]  # Ограничиваем длину текста кнопки
            callback_data = button["callback_data"][:64]  # Ограничиваем длину callback
            # Заменяем все callback'и из ALLOWED_BROADCAST_CALLBACKS (кроме 'subscribe') на 'subscribe' для неоплативших без ресурсов
            if (not is_paying_user and not has_resources and not is_admin and
                callback_data in ALLOWED_BROADCAST_CALLBACKS and callback_data != "subscribe"):
                callback_data = "subscribe"
                logger.debug(f"Заменён callback_data='{button['callback_data']}' на 'subscribe' для user_id={user_id}")
            row.append(InlineKeyboardButton(text=button_text, callback_data=callback_data))
            if len(row) == 2:  # Максимум 2 кнопки в строке
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)
        logger.debug(f"Создана динамическая клавиатура для user_id={user_id} с {len(buttons)} кнопками: {buttons}")
        return InlineKeyboardMarkup(inline_keyboard=keyboard)
    except Exception as e:
        logger.error(f"Ошибка в create_dynamic_broadcast_keyboard для user_id={user_id}: {e}", exc_info=True)
        return InlineKeyboardMarkup(inline_keyboard=[]) 