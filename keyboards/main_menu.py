# keyboards/main_menu.py
"""
Клавиатуры главного меню и навигации
"""

import logging
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from config import ADMIN_IDS, ADMIN_PANEL_BUTTON_NAMES

from logger import get_logger
logger = get_logger('keyboards')

async def create_main_menu_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Создаёт клавиатуру главного меню для пользователя."""
    try:
        admin_panel_button_text = ADMIN_PANEL_BUTTON_NAMES.get(user_id, "Админ-панель")
        logger.debug(f"Создание главного меню для user_id={user_id} с админ-кнопкой '{admin_panel_button_text}'")

        keyboard = [
            [InlineKeyboardButton(text="📸 Фотогенерация", callback_data="photo_generate_menu")],
            [InlineKeyboardButton(text="🎬 Видеогенерация", callback_data="video_generate_menu")],
            [InlineKeyboardButton(text="🎭 Фото Преображение", callback_data="photo_transform")],
            [InlineKeyboardButton(text="👥 Мои аватары", callback_data="my_avatars")],
            [
                InlineKeyboardButton(text="👤 Личный кабинет", callback_data="user_profile"),
                InlineKeyboardButton(text="👥 Пригласить друзей", callback_data="referrals")
            ],
            [
                InlineKeyboardButton(text="💳 Купить пакет", callback_data="subscribe"),
                InlineKeyboardButton(text="💬 Поддержка", callback_data="support")
            ],
            [InlineKeyboardButton(text="❓ Частые вопросы", callback_data="faq")]
        ]

        if user_id in ADMIN_IDS:
            keyboard.append([InlineKeyboardButton(text=admin_panel_button_text, callback_data="admin_panel")])

        return InlineKeyboardMarkup(inline_keyboard=keyboard)
    except Exception as e:
        logger.error(f"Ошибка в create_main_menu_keyboard для user_id={user_id}: {e}", exc_info=True)
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Ошибка, вернуться в меню", callback_data="back_to_menu")]
        ])

async def create_photo_generate_menu_keyboard() -> InlineKeyboardMarkup:
    """Создаёт клавиатуру меню фотогенерации."""
    try:
        keyboard = [
            [InlineKeyboardButton(text="📸 Фотосессия (с аватаром)", callback_data="generate_with_avatar")],
            [InlineKeyboardButton(text="🖼 Фото по референсу", callback_data="photo_to_photo")],
            [InlineKeyboardButton(text="🔙 Главное меню", callback_data="back_to_menu")]
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)
    except Exception as e:
        logger.error(f"Ошибка в create_photo_generate_menu_keyboard: {e}", exc_info=True)
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Ошибка, вернуться в меню", callback_data="back_to_menu")]
        ])

async def create_video_generate_menu_keyboard() -> InlineKeyboardMarkup:
    """Создаёт клавиатуру меню видеогенерации."""
    try:
        keyboard = [
            [InlineKeyboardButton(text="🎬 AI-видео (Kling 2.1)", callback_data="ai_video_v2_1")],
            [InlineKeyboardButton(text="🔙 Главное меню", callback_data="back_to_menu")]
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)
    except Exception as e:
        logger.error(f"Ошибка в create_video_generate_menu_keyboard: {e}", exc_info=True)
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Ошибка, вернуться в меню", callback_data="back_to_menu")]
        ]) 
