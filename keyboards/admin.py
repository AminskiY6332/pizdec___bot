# keyboards/admin.py
"""
Клавиатуры для админ-панели
"""

import logging
from typing import Optional
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from config import ADMIN_IDS, ADMIN_PANEL_BUTTON_NAMES

from logger import get_logger
logger = get_logger('keyboards')

async def create_admin_keyboard(user_id: Optional[int] = None) -> InlineKeyboardMarkup:
    """Создаёт клавиатуру админ-панели."""
    try:
        admin_panel_button_text = ADMIN_PANEL_BUTTON_NAMES.get(user_id, "Админ-панель")
        logger.debug(f"Создание админ-клавиатуры для user_id={user_id}")

        keyboard = [
            [
                InlineKeyboardButton(text="📊 Отчет пользователей", callback_data="admin_stats"),
                InlineKeyboardButton(text="🔍 Поиск пользователей", callback_data="admin_search_user")
            ],
            [
                InlineKeyboardButton(text="📈 Отчет платежей", callback_data="admin_payments"),
                InlineKeyboardButton(text="📊 Отчет активности", callback_data="admin_activity_stats")
            ],
            [
                InlineKeyboardButton(text="🔗 Отчет рефералов", callback_data="admin_referral_stats"),
                InlineKeyboardButton(text="📉 Визуализация", callback_data="admin_visualization")
            ],
            [
                InlineKeyboardButton(text="💰 Расходы Replicate", callback_data="admin_replicate_costs"),
                InlineKeyboardButton(text="🧹 Проблемные аватары", callback_data="admin_failed_avatars")
            ],
            [
                InlineKeyboardButton(text="📢 Рассылка всем", callback_data="broadcast_all"),
                InlineKeyboardButton(text="📢 Оплатившим", callback_data="broadcast_paid")
            ],
            [
                InlineKeyboardButton(text="📢 Не оплатившим", callback_data="broadcast_non_paid"),
                InlineKeyboardButton(text="📢 Рассылка с оплатой", callback_data="broadcast_with_payment")
            ],
            [InlineKeyboardButton(text="🗂 Управление рассылками", callback_data="list_broadcasts")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_menu")]
        ]

        return InlineKeyboardMarkup(inline_keyboard=keyboard)
    except Exception as e:
        logger.error(f"Ошибка в create_admin_keyboard для user_id={user_id}: {e}", exc_info=True)
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Ошибка, вернуться в меню", callback_data="back_to_menu")]
        ])

async def create_admin_user_actions_keyboard(target_user_id: int, is_blocked: bool) -> InlineKeyboardMarkup:
    """Создаёт клавиатуру действий с пользователем для админа."""
    try:
        block_text = "🔓 Разблокировать" if is_blocked else "🔒 Заблокировать"
        block_callback = f"block_user_{target_user_id}_unblock" if is_blocked else f"block_user_{target_user_id}_block"

        keyboard = [
            [
                InlineKeyboardButton(text="👤 Профиль", callback_data=f"view_user_profile_{target_user_id}"),
                InlineKeyboardButton(text="🖼 Аватары", callback_data=f"user_avatars_{target_user_id}")
            ],
            [
                InlineKeyboardButton(text="📸 Генерация фото", callback_data=f"admin_generate:{target_user_id}"),
                InlineKeyboardButton(text="🎬 Генерация видео", callback_data=f"admin_video:{target_user_id}")
            ],
            [
                InlineKeyboardButton(text="💰 Баланс", callback_data=f"change_balance_{target_user_id}"),
                InlineKeyboardButton(text="📜 Логи", callback_data=f"user_logs_{target_user_id}")
            ],
            [
                InlineKeyboardButton(text="💬 Написать", callback_data=f"chat_with_user_{target_user_id}"),
                InlineKeyboardButton(text=block_text, callback_data=block_callback)
            ],
            [
                InlineKeyboardButton(text="🔄 Сброс аватаров", callback_data=f"reset_avatar_{target_user_id}"),
                InlineKeyboardButton(text="🗑 Удалить", callback_data=f"delete_user_{target_user_id}")
            ]
        ]

        return InlineKeyboardMarkup(inline_keyboard=keyboard)
    except Exception as e:
        logger.error(f"Ошибка в create_admin_user_actions_keyboard для target_user_id={target_user_id}: {e}", exc_info=True)
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Ошибка, вернуться в меню", callback_data="back_to_menu")]
        ]) 