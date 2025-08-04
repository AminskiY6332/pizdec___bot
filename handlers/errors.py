import logging
from aiogram import Bot
from aiogram.types import Message, CallbackQuery
from aiogram.exceptions import TelegramBadRequest
from aiogram.enums import ParseMode
from handlers.utils import safe_escape_markdown as escape_md, send_message_with_fallback

from logger import get_logger
logger = get_logger('errors')

async def error_handler(error: Exception) -> None:
    """Логирует ошибки, вызванные обновлениями."""
    logger.error(msg="Exception while handling an update:", exc_info=error)

    # В aiogram 3.x мы не можем получить update из error_handler
    # Поэтому просто логируем ошибку без отправки сообщения пользователю
    logger.error(f"Ошибка в боте: {error}")
