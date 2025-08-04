# keyboards/support.py
"""
Клавиатуры для поддержки, FAQ и рефералов
"""

import logging
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from logger import get_logger
logger = get_logger('keyboards')

async def create_faq_keyboard() -> InlineKeyboardMarkup:
    """Создаёт клавиатуру FAQ."""
    try:
        keyboard = [
            [InlineKeyboardButton(text="📸 Как создать фото?", callback_data="faq_photo")],
            [InlineKeyboardButton(text="🎬 Как создать видео?", callback_data="faq_video")],
            [InlineKeyboardButton(text="👤 Как создать аватар?", callback_data="faq_avatar")],
            [InlineKeyboardButton(text="💡 Советы по промптам", callback_data="faq_prompts")],
            [InlineKeyboardButton(text="❓ Частые проблемы", callback_data="faq_problems")],
            [InlineKeyboardButton(text="💎 О подписке", callback_data="faq_subscription")],
            [InlineKeyboardButton(text="🔙 Главное меню", callback_data="back_to_menu")]
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)
    except Exception as e:
        logger.error(f"Ошибка в create_faq_keyboard: {e}", exc_info=True)
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Ошибка, вернуться в меню", callback_data="back_to_menu")]
        ])

async def create_support_keyboard() -> InlineKeyboardMarkup:
    """Создаёт клавиатуру поддержки."""
    try:
        keyboard = [
            [InlineKeyboardButton(text="💬 Написать в поддержку", url="https://t.me/AXIDI_Help")],
            [InlineKeyboardButton(text="❓ Частые вопросы", callback_data="faq")],
            [InlineKeyboardButton(text="🔙 Главное меню", callback_data="back_to_menu")]
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)
    except Exception as e:
        logger.error(f"Ошибка в create_support_keyboard: {e}", exc_info=True)
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Ошибка, вернуться в меню", callback_data="back_to_menu")]
        ])

async def create_referral_keyboard(user_id: int, bot_username: str) -> InlineKeyboardMarkup:
    """Создаёт клавиатуру реферальной программы."""
    try:
        referral_link = f"t.me/{bot_username}?start=ref_{user_id}"

        keyboard = [
            [InlineKeyboardButton(text="🎁 Получай печеньки за друга!", callback_data="ignore")],
            [
                InlineKeyboardButton(
                    text="📤 Поделиться ссылкой",
                    url=f"https://t.me/share/url?url={referral_link}&text=Попробуй этот крутой бот для создания AI фото и видео! Получи бонусные печеньки при регистрации!"
                )
            ],
            [InlineKeyboardButton(text="📋 Скопировать ссылку", callback_data="copy_referral_link")],
            [InlineKeyboardButton(text="📊 Мои рефералы", callback_data="my_referrals")],
            [InlineKeyboardButton(text="🔙 Главное меню", callback_data="back_to_menu")]
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)
    except Exception as e:
        logger.error(f"Ошибка в create_referral_keyboard для user_id={user_id}: {e}", exc_info=True)
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Ошибка, вернуться в меню", callback_data="back_to_menu")]
        ]) 
