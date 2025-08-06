# handlers/admin/broadcast.py

import asyncio
import json
import logging
import pytz
import os
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from aiogram import Router, Bot, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.enums import ParseMode
from aiogram.filters import Command, StateFilter
from aiogram.fsm.state import State, StatesGroup
from aiogram.exceptions import TelegramBadRequest
from database import (
    get_all_users_stats, get_broadcasts_with_buttons, get_broadcast_buttons, get_paid_users, get_non_paid_users, save_broadcast_button
)
from config import ADMIN_IDS, DATABASE_PATH, ALLOWED_BROADCAST_CALLBACKS, BROADCAST_CALLBACK_ALIASES
from keyboards import (
    create_admin_keyboard, create_dynamic_broadcast_keyboard, create_admin_user_actions_keyboard, create_broadcast_with_payment_audience_keyboard
)
from handlers.utils import (
    escape_message_parts, send_message_with_fallback, unescape_markdown, anti_spam
)
from states import BotStates

from logger import get_logger
logger = get_logger('main')

# Создание роутера для рассылок
broadcast_router = Router()

async def clear_user_data(state: FSMContext, user_id: int):
    """Очищает данные состояния FSM для пользователя, если не активно ожидание сообщения рассылки."""
    current_state = await state.get_state()
    if current_state == BotStates.AWAITING_BROADCAST_MESSAGE:
        logger.debug(f"Пропуск очистки состояния для user_id={user_id}, так как активно состояние {current_state}")
        return
    await state.clear()
    logger.info(f"Очистка данных для user_id={user_id} по таймеру")

async def initiate_broadcast(query: CallbackQuery, state: FSMContext) -> None:
    """Инициирует рассылку (общую, для оплативших, не оплативших или с кнопкой оплаты)."""
    user_id = query.from_user.id
    callback_data = query.data

    if user_id not in ADMIN_IDS:
        await query.message.answer(
            escape_message_parts("❌ У вас нет прав.", version=2),
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    current_state = await state.get_state()
    if current_state in [
        BotStates.AWAITING_BROADCAST_MESSAGE,
        BotStates.AWAITING_BROADCAST_MEDIA_CONFIRM,
        BotStates.AWAITING_BROADCAST_SCHEDULE,
        BotStates.AWAITING_BROADCAST_AUDIENCE,
        BotStates.AWAITING_BROADCAST_BUTTONS,
        BotStates.AWAITING_BROADCAST_BUTTON_INPUT
    ]:
        logger.debug(f"initiate_broadcast: состояние {current_state} уже активно, пропуск очистки для user_id={user_id}")
    else:
        await state.clear()

    if callback_data == "broadcast_with_payment":
        text = escape_message_parts(
            "📢 Выберите аудиторию для рассылки с кнопкой оплаты:",
            version=2
        )
        reply_markup = await create_broadcast_with_payment_audience_keyboard()
        await send_message_with_fallback(
            query.bot, user_id, text,
            reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN_V2
        )
        await state.update_data(awaiting_broadcast_audience=True, user_id=user_id)
        await state.set_state(BotStates.AWAITING_BROADCAST_AUDIENCE)
    else:
        broadcast_type = callback_data.replace("broadcast_", "") if callback_data.startswith("broadcast_") else callback_data
        await state.update_data(
            awaiting_broadcast_message=True,
            broadcast_type=broadcast_type,
            user_id=user_id,
            buttons=[]  # Инициализируем пустой список кнопок
        )

        # Запускаем таймер очистки состояния через 20 минут
        async def delayed_clear_user_data():
            await asyncio.sleep(1200)  # 20 минут
            current_state_after_delay = await state.get_state()
            if current_state_after_delay in [
                BotStates.AWAITING_BROADCAST_MESSAGE,
                BotStates.AWAITING_BROADCAST_AUDIENCE,
                BotStates.AWAITING_BROADCAST_BUTTONS,
                BotStates.AWAITING_BROADCAST_BUTTON_INPUT
            ]:
                await clear_user_data(state, user_id)

        asyncio.create_task(delayed_clear_user_data())

        text = escape_message_parts(
            "📢 Введите текст сообщения для рассылки.\n",
            "⚠️ Сначала отправьте текст, затем медиа (фото/видео).\n",
            "Для отмены используйте /cancel.",
            version=2
        )
        reply_markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Отмена", callback_data="cancel_broadcast")]
        ])

        await send_message_with_fallback(
            query.bot, user_id, text,
            reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN_V2
        )
        await state.set_state(BotStates.AWAITING_BROADCAST_MESSAGE)

    await query.answer()
    logger.info(f"initiate_broadcast: user_id={user_id}, callback_data={callback_data}")

async def broadcast_message_admin(bot: Bot, message_text: str, admin_user_id: int, media_type: str = None, media_id: str = None, buttons: List[Dict[str, str]] = None) -> None:
    """Выполняет рассылку всем пользователям."""
    buttons = buttons or []
    all_users_data, _ = await get_all_users_stats(page=1, page_size=1000000)
    target_users = [user[0] for user in all_users_data]
    sent_count = 0
    failed_count = 0
    total_to_send = len(target_users)
    logger.info(f"Начало общей рассылки от админа {admin_user_id} для {total_to_send} пользователей.")
    await send_message_with_fallback(
        bot, admin_user_id,
        escape_message_parts(
            f"🚀 Начинаю рассылку для ~`{total_to_send}` пользователей...",
            version=2
        ),
        parse_mode=ParseMode.MARKDOWN_V2
    )
    for target_user_id in target_users:
        try:
            reply_markup = await create_dynamic_broadcast_keyboard(buttons, target_user_id) if buttons else None
            try:
                # Пытаемся отправить с MarkdownV2
                if media_type == 'photo' and media_id:
                    await bot.send_photo(
                        chat_id=target_user_id, photo=media_id,
                        caption=message_text, parse_mode=ParseMode.MARKDOWN_V2,
                        reply_markup=reply_markup
                    )
                elif media_type == 'video' and media_id:
                    await bot.send_video(
                        chat_id=target_user_id, video=media_id,
                        caption=message_text, parse_mode=ParseMode.MARKDOWN_V2,
                        reply_markup=reply_markup
                    )
                else:
                    await bot.send_message(
                        chat_id=target_user_id, text=message_text, parse_mode=ParseMode.MARKDOWN_V2,
                        reply_markup=reply_markup
                    )
            except TelegramBadRequest as e:
                # Fallback: отправка без Markdown
                logger.warning(f"Ошибка Markdown для user_id={target_user_id}: {e}. Пробуем без парсинга.")
                raw_text = unescape_markdown(message_text)
                if media_type == 'photo' and media_id:
                    await bot.send_photo(
                        chat_id=target_user_id, photo=media_id,
                        caption=raw_text, parse_mode=None,
                        reply_markup=reply_markup
                    )
                elif media_type == 'video' and media_id:
                    await bot.send_video(
                        chat_id=target_user_id, video=media_id,
                        caption=raw_text, parse_mode=None,
                        reply_markup=reply_markup
                    )
                else:
                    await bot.send_message(
                        chat_id=target_user_id, text=raw_text, parse_mode=None,
                        reply_markup=reply_markup
                    )
            sent_count += 1
            if sent_count % 20 == 0:
                await asyncio.sleep(1)
        except Exception as e:
            logger.error(f"Ошибка отправки сообщения пользователю {target_user_id}: {e}", exc_info=True)
            failed_count += 1
    summary_text = escape_message_parts(
        f"🏁 Рассылка завершена!\n",
        f"✅ Отправлено: `{sent_count}`\n",
        f"❌ Не удалось отправить: `{failed_count}`",
        version=2
    )
    await send_message_with_fallback(
        bot, admin_user_id, summary_text, reply_markup=await create_admin_keyboard(),
        parse_mode=ParseMode.MARKDOWN_V2
    )
    logger.info(f"Общая рассылка завершена. Отправлено: {sent_count}, Ошибок: {failed_count}")

async def broadcast_to_paid_users(bot: Bot, message_text: str, admin_user_id: int, media_type: str = None, media_id: str = None, buttons: List[Dict[str, str]] = None) -> None:
    """Выполняет рассылку только оплатившим пользователям."""
    buttons = buttons or []
    target_users = await get_paid_users()
    sent_count = 0
    failed_count = 0
    total_to_send = len(target_users)
    logger.info(f"Начало рассылки для оплативших от админа {admin_user_id} для {total_to_send} пользователей.")
    await send_message_with_fallback(
        bot, admin_user_id,
        escape_message_parts(
            f"🚀 Начинаю рассылку для ~`{total_to_send}` оплативших пользователей...",
            version=2
        ),
        parse_mode=ParseMode.MARKDOWN_V2
    )
    signature = "🍪 PixelPie"
    caption = message_text + ("\n\n" + signature if message_text.strip() else "\n" + signature)
    escaped_caption = escape_message_parts(caption, version=2)
    for target_user_id in target_users:
        try:
            reply_markup = await create_dynamic_broadcast_keyboard(buttons, target_user_id) if buttons else None
            if media_type == 'photo' and media_id:
                await bot.send_photo(
                    chat_id=target_user_id, photo=media_id,
                    caption=escaped_caption, parse_mode=ParseMode.MARKDOWN_V2,
                    reply_markup=reply_markup
                )
            elif media_type == 'video' and media_id:
                await bot.send_video(
                    chat_id=target_user_id, video=media_id,
                    caption=escaped_caption, parse_mode=ParseMode.MARKDOWN_V2,
                    reply_markup=reply_markup
                )
            else:
                await bot.send_message(
                    chat_id=target_user_id, text=escaped_caption, parse_mode=ParseMode.MARKDOWN_V2,
                    reply_markup=reply_markup
                )
            sent_count += 1
            if sent_count % 20 == 0:
                await asyncio.sleep(1)
        except Exception as e:
            logger.error(f"Ошибка отправки сообщения пользователю {target_user_id}: {e}", exc_info=True)
            failed_count += 1
    summary_text = escape_message_parts(
        f"🏁 Рассылка для оплативших завершена!\n",
        f"✅ Отправлено: `{sent_count}`\n",
        f"❌ Не удалось отправить: `{failed_count}`",
        version=2
    )
    await send_message_with_fallback(
        bot, admin_user_id, summary_text, reply_markup=await create_admin_keyboard(),
        parse_mode=ParseMode.MARKDOWN_V2
    )
    logger.info(f"Рассылка для оплативших завершена. Отправлено: {sent_count}, Ошибок: {failed_count}")

async def broadcast_to_non_paid_users(bot: Bot, message_text: str, admin_user_id: int, media_type: str = None, media_id: str = None, buttons: List[Dict[str, str]] = None) -> None:
    """Выполняет рассылку только не оплатившим пользователям."""
    buttons = buttons or []
    target_users = await get_non_paid_users()
    sent_count = 0
    failed_count = 0
    total_to_send = len(target_users)
    logger.info(f"Начало рассылки для не оплативших от админа {admin_user_id} для {total_to_send} пользователей.")
    await send_message_with_fallback(
        bot, admin_user_id,
        escape_message_parts(
            f"🚀 Начинаю рассылку для ~`{total_to_send}` не оплативших пользователей...",
            version=2
        ),
        parse_mode=ParseMode.MARKDOWN_V2
    )
    signature = "🍪 PixelPie"
    caption = message_text + ("\n\n" + signature if message_text.strip() else "\n" + signature)
    escaped_caption = escape_message_parts(caption, version=2)
    for target_user_id in target_users:
        try:
            reply_markup = await create_dynamic_broadcast_keyboard(buttons, target_user_id) if buttons else None
            if media_type == 'photo' and media_id:
                await bot.send_photo(
                    chat_id=target_user_id, photo=media_id,
                    caption=escaped_caption, parse_mode=ParseMode.MARKDOWN_V2,
                    reply_markup=reply_markup
                )
            elif media_type == 'video' and media_id:
                await bot.send_video(
                    chat_id=target_user_id, video=media_id,
                    caption=escaped_caption, parse_mode=ParseMode.MARKDOWN_V2,
                    reply_markup=reply_markup
                )
            else:
                await bot.send_message(
                    chat_id=target_user_id, text=escaped_caption, parse_mode=ParseMode.MARKDOWN_V2,
                    reply_markup=reply_markup
                )
            sent_count += 1
            if sent_count % 20 == 0:
                await asyncio.sleep(1)
        except Exception as e:
            logger.error(f"Ошибка отправки сообщения пользователю {target_user_id}: {e}", exc_info=True)
            failed_count += 1
    summary_text = escape_message_parts(
        f"🏁 Рассылка для не оплативших завершена!\n",
        f"✅ Отправлено: `{sent_count}`\n",
        f"❌ Не удалось отправить: `{failed_count}`",
        version=2
    )
    await send_message_with_fallback(
        bot, admin_user_id, summary_text, reply_markup=await create_admin_keyboard(),
        parse_mode=ParseMode.MARKDOWN_V2
    )
    logger.info(f"Рассылка для не оплативших завершена. Отправлено: {sent_count}, Ошибок: {failed_count}")

async def broadcast_with_payment(
    bot: Bot,
    message_text: str,
    admin_user_id: int,
    media_type: Optional[str] = None,
    media_id: Optional[str] = None,
    buttons: List[Dict[str, str]] = None
) -> None:
    """Выполняет рассылку всем пользователям с кнопкой для перехода к тарифам."""
    buttons = buttons or []
    all_users_data, _ = await get_all_users_stats(page=1, page_size=1000000)
    target_users = [user[0] for user in all_users_data]
    sent_count = 0
    failed_count = 0
    total_to_send = len(target_users)
    logger.info(f"Начало рассылки с оплатой от админа {admin_user_id} для {total_to_send} пользователей.")
    await send_message_with_fallback(
        bot, admin_user_id,
        escape_message_parts(
            f"🚀 Начинаю рассылку с оплатой для ~`{total_to_send}` пользователей...",
            version=2
        ),
        parse_mode=ParseMode.MARKDOWN_V2
    )
    signature = "🍪 PixelPie"
    caption = message_text + ("\n\n" + signature if message_text.strip() else "\n" + signature)
    escaped_caption = escape_message_parts(caption, version=2)
    for target_user_id in target_users:
        try:
            reply_markup = await create_dynamic_broadcast_keyboard(buttons, target_user_id) if buttons else None
            if media_type == 'photo' and media_id:
                await bot.send_photo(
                    chat_id=target_user_id, photo=media_id,
                    caption=escaped_caption, parse_mode=ParseMode.MARKDOWN_V2,
                    reply_markup=reply_markup
                )
            elif media_type == 'video' and media_id:
                await bot.send_video(
                    chat_id=target_user_id, video=media_id,
                    caption=escaped_caption, parse_mode=ParseMode.MARKDOWN_V2,
                    reply_markup=reply_markup
                )
            else:
                await bot.send_message(
                    chat_id=target_user_id, text=escaped_caption,
                    parse_mode=ParseMode.MARKDOWN_V2, reply_markup=reply_markup
                )
            sent_count += 1
            if sent_count % 20 == 0:
                await asyncio.sleep(1)
        except Exception as e:
            logger.error(f"Ошибка отправки сообщения пользователю {target_user_id}: {e}", exc_info=True)
            failed_count += 1
    summary_text = escape_message_parts(
        f"🏁 Рассылка с оплатой завершена!\n",
        f"✅ Отправлено: `{sent_count}`\n",
        f"❌ Не удалось отправить: `{failed_count}`",
        version=2
    )
    await send_message_with_fallback(
        bot, admin_user_id, summary_text,
        reply_markup=await create_admin_keyboard(), parse_mode=ParseMode.MARKDOWN_V2
    )
    logger.info(f"Рассылка с оплатой завершена. Отправлено: {sent_count}, Ошибок: {failed_count}")

# TODO: Добавить остальные функции из handlers/broadcast.py