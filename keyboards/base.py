# keyboards/base.py
"""
Базовые клавиатуры для Telegram бота
Содержит простые и часто используемые клавиатуры
"""

import logging
from typing import Optional
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from logger import get_logger
logger = get_logger('keyboards')

async def create_back_keyboard(
    callback_data: str = "back_to_menu",
    text: str = "🔙 Назад"
) -> InlineKeyboardMarkup:
    """Создаёт простую клавиатуру с кнопкой 'Назад'."""
    try:
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=text, callback_data=callback_data)]
        ])
    except Exception as e:
        logger.error(f"Ошибка в create_back_keyboard: {e}", exc_info=True)
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Ошибка, вернуться в меню", callback_data="back_to_menu")]
        ])

async def create_confirmation_keyboard(
    confirm_callback: str = "confirm_action",
    cancel_callback: str = "cancel_action",
    confirm_text: str = "✅ Да",
    cancel_text: str = "❌ Нет"
) -> InlineKeyboardMarkup:
    """Создаёт клавиатуру подтверждения с кнопками 'Да' и 'Нет'."""
    try:
        return InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text=confirm_text, callback_data=confirm_callback),
                InlineKeyboardButton(text=cancel_text, callback_data=cancel_callback)
            ]
        ])
    except Exception as e:
        logger.error(f"Ошибка в create_confirmation_keyboard: {e}", exc_info=True)
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Ошибка, вернуться в меню", callback_data="back_to_menu")]
        ])

async def create_error_keyboard() -> InlineKeyboardMarkup:
    """Создаёт клавиатуру для страниц с ошибками."""
    try:
        keyboard = [
            [InlineKeyboardButton(text="💬 Поддержка", callback_data="support")],
            [InlineKeyboardButton(text="🔄 Попробовать снова", callback_data="back_to_menu")],
            [InlineKeyboardButton(text="❓ Частые вопросы", callback_data="faq")]
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)
    except Exception as e:
        logger.error(f"Ошибка в create_error_keyboard: {e}", exc_info=True)
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Ошибка, вернуться в меню", callback_data="back_to_menu")]
        ]) 
