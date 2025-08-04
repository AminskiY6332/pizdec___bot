# keyboards/utils.py
"""
Утилитарные клавиатуры и вспомогательные функции
"""

import logging
import os
from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.enums import ParseMode

from logger import get_logger
logger = get_logger('keyboards')

async def create_photo_upload_keyboard() -> InlineKeyboardMarkup:
    """Создаёт клавиатуру для загрузки фотографий."""
    try:
        keyboard = [
            [InlineKeyboardButton(text="❌ Отмена загрузки", callback_data="cancel_upload")],
            [InlineKeyboardButton(text="❓ Помощь", callback_data="help_upload")]
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)
    except Exception as e:
        logger.error(f"Ошибка в create_photo_upload_keyboard: {e}", exc_info=True)
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Ошибка, вернуться в меню", callback_data="back_to_menu")]
        ])

async def create_video_status_keyboard() -> InlineKeyboardMarkup:
    """Создаёт клавиатуру для статуса видео."""
    try:
        keyboard = [
            [InlineKeyboardButton(text="📋 Мои видео", callback_data="my_videos")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_menu")]
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)
    except Exception as e:
        logger.error(f"Ошибка в create_video_status_keyboard: {e}", exc_info=True)
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Ошибка, вернуться в меню", callback_data="back_to_menu")]
        ])

async def send_avatar_training_message(bot, user_id: int, text: str, reply_markup=None, parse_mode=ParseMode.MARKDOWN) -> None:
    """Отправляет сообщение с изображением аватара для обучения."""
    try:
        avatar_image_path = "/root/axidi_test/images/avatar.img"

        if os.path.exists(avatar_image_path):
            try:
                with open(avatar_image_path, 'rb') as photo:
                    await bot.send_photo(
                        chat_id=user_id,
                        photo=photo,
                        caption=text,
                        reply_markup=reply_markup,
                        parse_mode=parse_mode
                    )
                return
            except Exception as e:
                logger.error(f"Не удалось отправить avatar.img для user_id={user_id}: {e}", exc_info=True)

        await bot.send_message(
            chat_id=user_id,
            text=text,
            reply_markup=reply_markup,
            parse_mode=parse_mode
        )
    except Exception as e:
        logger.error(f"Ошибка в send_avatar_training_message для user_id={user_id}: {e}", exc_info=True)
        await bot.send_message(
            chat_id=user_id,
            text="❌ Произошла ошибка при отправке сообщения. Попробуйте позже.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_menu")]
            ]),
            parse_mode=ParseMode.MARKDOWN
        ) 
