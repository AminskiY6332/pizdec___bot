import os
from aiogram import Bot, BaseMiddleware
from aiogram.types import Message, InlineKeyboardMarkup, CallbackQuery, TelegramObject
from aiogram.exceptions import TelegramBadRequest, TelegramRetryAfter, TelegramNetworkError, TelegramForbiddenError
from aiogram.enums import ParseMode
import logging
import tenacity
from aiogram.fsm.context import FSMContext
import uuid
import copy
from typing import Optional, Dict, Any, Awaitable, Callable
import asyncio
import time
from datetime import datetime, timezone
from database import delete_user_activity, log_user_action, block_user_access

from config import TARIFFS, YOOKASSA_SHOP_ID, SECRET_KEY, YOOKASSA_TEST_TOKEN, ADMIN_IDS

from logger import get_logger
logger = get_logger('main')

import aiosqlite
from config import DATABASE_PATH

# Проверка наличия YooKassa
try:
    from yookassa import Configuration as YooKassaConfiguration, Payment as YooKassaPayment
    YOOKASSA_AVAILABLE = True
except ImportError:
    YOOKASSA_AVAILABLE = False
    logger.warning("Библиотека yookassa не установлена. Функции оплаты не будут работать.")

# Декоратор для retry при работе с Telegram API
retry_telegram_call = tenacity.retry(
    retry=tenacity.retry_if_exception_type((TelegramNetworkError, TelegramRetryAfter)),
    wait=tenacity.wait_exponential(multiplier=1, min=1, max=10),
    stop=tenacity.stop_after_attempt(3),
    before_sleep=tenacity.before_sleep_log(logger, logging.WARNING),
    reraise=True
)

def safe_escape_markdown(text: str, exclude_chars: Optional[list] = None, version: int = 2) -> str:
    if not text:
        return ""

    text = str(text)

    if version == 1:
        # Экранирование для Markdown
        special_chars = ['_', '*', '`', '[']
    else:
        # Экранирование для MarkdownV2
        special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']

    # Экранируем все специальные символы, но избегаем двойного экранирования
    for char in special_chars:
        # Проверяем, что символ еще не экранирован
        if char in text and f'\\{char}' not in text:
            text = text.replace(char, f'\\{char}')

    # Исключаем символы, которые не нужно экранировать
    if exclude_chars:
        for char in exclude_chars:
            text = text.replace(f'\\{char}', char)

    logger.debug(f"Escaped text (version={version}): {text[:200]}...")
    return text

def format_user_info_safe(name: str, username: str = None, user_id: int = None, email: str = None) -> str:
    """
    Безопасно форматирует информацию о пользователе для Markdown.
    """
    safe_name = safe_escape_markdown(str(name))

    text = f"👤 Детальная информация о пользователе\n"
    text += f"Имя: {safe_name}"

    if username:
        safe_username = safe_escape_markdown(str(username))
        text += f" \\(@{safe_username}\\)"

    text += f"\n"

    if user_id:
        safe_user_id = safe_escape_markdown(str(user_id))
        text += f"ID: `{safe_user_id}`\n"

    if email:
        safe_email = safe_escape_markdown(str(email))
        text += f"Email: {safe_email}\n"

    return text

def format_balance_info_safe(photo_balance: int, avatar_balance: int) -> str:
    """
    Безопасно форматирует информацию о балансе для Markdown.
    """
    text = "💰 Баланс:\n"
    text += f"  • Печеньки: `{safe_escape_markdown(str(photo_balance))}`\n"
    text += f"  • Аватары: `{safe_escape_markdown(str(avatar_balance))}`\n"

    return text

def format_stats_info_safe(stats_data: dict) -> str:
    """
    Безопасно форматирует статистику для Markdown.
    """
    text = "📊 Статистика генераций:\n"

    for key, value in stats_data.items():
        safe_key = safe_escape_markdown(str(key))
        safe_value = safe_escape_markdown(str(value))
        text += f"  • {safe_key}: `{safe_value}`\n"

    return text

async def format_user_detail_message(user_data: dict) -> str:
    """
    Форматирует детальную информацию о пользователе для админской панели.
    """
    name = user_data.get('first_name', 'Неизвестно')
    username = user_data.get('username', '')
    user_id = user_data.get('user_id', 0)
    email = user_data.get('email', '')
    photo_balance = user_data.get('photo_balance', 0)
    avatar_balance = user_data.get('avatar_balance', 0)

    stats = {
        'Фото по тексту': user_data.get('text_generations', 0),
        'Фото с лицом': user_data.get('face_generations', 0),
        'Аватары': user_data.get('avatar_generations', 0),
        'Видео': user_data.get('video_generations', 0)
    }

    message_text = format_user_info_safe(name, username, user_id, email)
    message_text += format_balance_info_safe(photo_balance, avatar_balance)
    message_text += format_stats_info_safe(stats)

    return message_text

@retry_telegram_call
async def safe_edit_message(
    message: Message,
    text: str,
    reply_markup: Optional[InlineKeyboardMarkup] = None,
    parse_mode: Optional[str] = ParseMode.MARKDOWN_V2,
    disable_web_page_preview: bool = True
) -> Optional[Message]:
    """
    Безопасно редактирует сообщение с обработкой ошибок Markdown.
    """
    if not message:
        return None

    try:
        return await message.edit_text(
            text=text,
            reply_markup=reply_markup,
            parse_mode=parse_mode,
            disable_web_page_preview=disable_web_page_preview
        )
    except TelegramBadRequest as e:
        error_str = str(e).lower()

        if "message is not modified" in error_str:
            logger.info(f"Сообщение не изменено (API): {e}")
            return message

        elif "can't parse entities" in error_str or "can't parse" in error_str:
            logger.warning(f"Ошибка парсинга Markdown: {e}")
            logger.debug(f"Проблемный текст: {text[:200]}...")

            try:
                return await message.edit_text(
                    text=text,
                    reply_markup=reply_markup,
                    parse_mode=None,
                    disable_web_page_preview=disable_web_page_preview
                )
            except Exception as e_plain:
                logger.error(f"Не удалось отредактировать без форматирования: {e_plain}")
                return None

        else:
            logger.error(f"BadRequest при редактировании сообщения: {e}")
            return None

    except Exception as e:
        logger.error(f"Неожиданная ошибка при редактировании сообщения: {e}", exc_info=True)
        return None

@retry_telegram_call
async def send_message_with_fallback(
    bot: Bot,
    chat_id: int,
    text: str,
    reply_markup: Optional[InlineKeyboardMarkup] = None,
    parse_mode: Optional[str] = ParseMode.MARKDOWN_V2,
    disable_web_page_preview: bool = True
) -> Optional[Message]:
    """
    Безопасно отправляет сообщение с обработкой ошибок парсинга Markdown.
    """
    logger.debug(f"send_message_with_fallback: chat_id={chat_id}, text={text[:200]}..., parse_mode={parse_mode}")

    # Проверка, не является ли chat_id идентификатором самого бота
    bot_info = await bot.get_me()
    if chat_id == bot_info.id:
        logger.error(f"Попытка отправить сообщение самому боту: chat_id={chat_id} совпадает с bot_id={bot_info.id}")
        return None

    try:
        await bot.send_chat_action(chat_id=chat_id, action="typing")
    except Exception as e:
        logger.debug(f"Не удалось отправить typing action: {e}")

    try:
        sent_message = await bot.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=reply_markup,
            parse_mode=parse_mode,
            disable_web_page_preview=disable_web_page_preview
        )
        logger.debug(f"Message sent successfully: chat_id={chat_id}, message_id={sent_message.message_id}")
        return sent_message
    except TelegramBadRequest as e:
        error_str = str(e).lower()

        if "can't parse entities" in error_str:
            logger.warning(f"Ошибка парсинга Markdown при отправке: {e}")
            logger.debug(f"Проблемный текст: {text[:200]}...")

            try:
                sent_message = await bot.send_message(
                    chat_id=chat_id,
                    text=text,
                    reply_markup=reply_markup,
                    parse_mode=None,
                    disable_web_page_preview=disable_web_page_preview
                )
                logger.debug(f"Message sent without formatting: chat_id={chat_id}, message_id={sent_message.message_id}")
                return sent_message
            except Exception as e_plain:
                logger.error(f"Не удалось отправить сообщение без форматирования: {e_plain}")
                try:
                    error_message = await bot.send_message(
                        chat_id=chat_id,
                        text="❌ Произошла ошибка при отправке сообщения. Пожалуйста, попробуйте позже.",
                        parse_mode=None
                    )
                    logger.debug(f"Fallback error message sent: chat_id={chat_id}, message_id={error_message.message_id}")
                    return error_message
                except Exception as e_fallback:
                    logger.error(f"Критическая ошибка: не удалось отправить даже простое сообщение: {e_fallback}")
                    return None
        else:
            logger.error(f"BadRequest при отправке сообщения: {e}")
            return None
    except TelegramForbiddenError as e:
        error_message = str(e)
        logger.error(f"Запрещено отправлять сообщение в chat_id={chat_id}: {error_message}")

        # Проверяем, заблокировал ли пользователь бота
        if "bot was blocked by the user" in error_message.lower() or "forbidden: bot was blocked by the user" in error_message.lower():
            await handle_user_blocked_bot(chat_id, error_message)

        return None
    except Exception as e:
        logger.error(f"Ошибка отправки сообщения для chat_id={chat_id}: {e}", exc_info=True)
        return None

async def safe_send_message(bot: Bot, chat_id: int, text: str, **kwargs) -> Optional[Message]:
    """
    Безопасная отправка сообщения с обработкой ошибок блокировки бота.

    Args:
        bot: Экземпляр бота
        chat_id: ID чата
        text: Текст сообщения
        **kwargs: Дополнительные параметры для send_message

    Returns:
        Message или None в случае ошибки
    """
    try:
        return await bot.send_message(chat_id=chat_id, text=text, **kwargs)
    except TelegramForbiddenError as e:
        error_message = str(e)
        logger.error(f"Запрещено отправлять сообщение в chat_id={chat_id}: {error_message}")

        # Проверяем, заблокировал ли пользователь бота
        if "bot was blocked by the user" in error_message.lower() or "forbidden: bot was blocked by the user" in error_message.lower():
            await handle_user_blocked_bot(chat_id, error_message)

        return None
    except Exception as e:
        logger.error(f"Ошибка отправки сообщения для chat_id={chat_id}: {e}", exc_info=True)
        return None

@retry_telegram_call
async def safe_answer_callback(query: CallbackQuery, text: Optional[str] = None, show_alert: bool = False) -> None:
    """
    Безопасно отвечает на callback query.
    """
    if query:
        try:
            await query.answer(text=text, show_alert=show_alert)
        except TelegramForbiddenError as e:
            error_message = str(e)
            logger.error(f"Запрещено отвечать на callback для chat_id={query.from_user.id}: {error_message}")

            # Проверяем, заблокировал ли пользователь бота
            if "bot was blocked by the user" in error_message.lower() or "forbidden: bot was blocked by the user" in error_message.lower():
                await handle_user_blocked_bot(query.from_user.id, error_message)
        except Exception as e:
            logger.warning(f"Не удалось ответить на CallbackQuery: {e}")

async def delete_message_safe(message: Message) -> None:
    """
    Безопасно удаляет сообщение.
    """
    if message:
        try:
            await message.delete()
        except Exception as e:
            logger.debug(f"Не удалось удалить сообщение: {e}")

async def send_typing_action(bot: Bot, chat_id: int) -> None:
    """
    Отправляет действие 'печатает'.
    """
    try:
        await bot.send_chat_action(chat_id=chat_id, action="typing")
    except Exception as e:
        logger.debug(f"Не удалось отправить typing action: {e}")

async def send_upload_photo_action(bot: Bot, chat_id: int) -> None:
    """
    Отправляет действие 'загружает фото'.
    """
    try:
        await bot.send_chat_action(chat_id=chat_id, action="upload_photo")
    except Exception as e:
        logger.debug(f"Не удалось отправить upload_photo action: {e}")

async def send_upload_video_action(bot: Bot, chat_id: int) -> None:
    """
    Отправляет действие 'загружает видео'.
    """
    try:
        await bot.send_chat_action(chat_id=chat_id, action="upload_video")
    except Exception as e:
        logger.debug(f"Не удалось отправить upload_video action: {e}")

async def clean_admin_context(context: FSMContext) -> None:

    try:
        if not isinstance(context, FSMContext):
            logger.error(f"Ожидался объект FSMContext, получен {type(context)}")
            return

        data = await context.get_data()
        admin_keys = [
            'admin_generation_for_user',
            'admin_target_user_id',
            'is_admin_generation',
            'generation_type',
            'model_key',
            'active_model_version',
            'active_trigger_word',
            'active_avatar_name',
            'style_key',
            'selected_prompt',
            'user_prompt',
            'face_image_path',
            'photo_to_photo_image_path',
            'awaiting_activity_dates',
            'awaiting_support_message'
        ]
        if data:
            new_data = {k: v for k, v in data.items() if k not in admin_keys}
            await context.set_data(new_data)
            if admin_keys:
                logger.debug(f"Очищены админские ключи: {admin_keys}")
            else:
                logger.debug("Контекст не содержал админских ключей для очистки")
        else:
            logger.debug("Контекст пуст, очистка не требуется")
    except Exception as e:
        logger.error(f"Ошибка очистки админского контекста: {e}", exc_info=True)

def create_isolated_context(original_context: Dict, target_user_id: int) -> Dict:
    """
    Создает изолированный контекст для админских операций.
    """
    return {
        'bot': original_context.get('bot'),
        'user_data': copy.deepcopy(original_context.get('user_data', {}).get(target_user_id, {})),
        'chat_data': {},
    }

async def check_user_permissions(message: Message, required_permissions: Optional[list] = None) -> bool:
    """
    Проверяет права пользователя.
    """
    user_id = message.from_user.id

    if required_permissions is None:
        return True

    if 'admin' in required_permissions and user_id not in ADMIN_IDS:
        await message.answer(
            safe_escape_markdown("❌ У вас нет прав для выполнения этой команды."),
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return False

    return True

def get_user_display_name(user: Dict) -> str:
    """
    Получает отображаемое имя пользователя.
    """
    if user.get('first_name'):
        name = user['first_name']
        if user.get('last_name'):
            name += f" {user['last_name']}"
        return name
    elif user.get('username'):
        return f"@{user['username']}"
    else:
        return f"User {user.get('id', 'Unknown')}"

def format_user_mention(user: Dict, escape: bool = True) -> str:
    """
    Форматирует упоминание пользователя.
    """
    display_name = get_user_display_name(user)

    if user.get('username'):
        mention = f"{display_name} (@{user['username']})"
    else:
        mention = f"{display_name} (ID: {user.get('id', 'Unknown')})"

    return safe_escape_markdown(mention) if escape else mention

def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Обрезает текст до указанной длины.
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix

def get_tariff_text(first_purchase: bool = False, is_paying_user: bool = False, time_since_registration: float = float('inf')) -> str:
    """Формирует текст тарифов с корректным экранированием для MarkdownV2."""
    header1 = safe_escape_markdown("🔥 Горячий выбор для идеальных фото и видео!", version=2)
    header2 = safe_escape_markdown("Хочешь крутые кадры без лишних хлопот? Выбирай выгодный пакет и получай фото или видео в один клик!", version=2)
    gift_text_unconditional = safe_escape_markdown(" При первой покупке ЛЮБОГО пакета (кроме 'Только аватар') - 1 аватар в подарок!", version=2)
    footer = safe_escape_markdown("Выбери свой тариф ниже, нажав на соответствующую кнопку ⤵️", version=2)

    # Создаем ссылку в формате MarkdownV2
    terms_link_text = safe_escape_markdown("пользовательским соглашением", version=2)
    terms_text = f"\n\n📄 Приобретая пакет, вы соглашаетесь с [{terms_link_text}](https://telegra.ph/Polzovatelskoe-soglashenie-07-26-12)"

    text_parts = [header1, header2, "\n"]

    # Фильтруем тарифы
    available_tariffs = {}
    for k, v in TARIFFS.items():
        if k == "admin_premium":
            continue
        if v.get("dev_only"):
            continue
        available_tariffs[k] = v

    # Фильтрация тарифов для неоплативших пользователей
    if not is_paying_user:
        if time_since_registration <= 1800:  # 30 минут
            available_tariffs = {k: v for k, v in available_tariffs.items() if k in ["комфорт"]}
        elif time_since_registration <= 5400:  # 30–90 минут
            available_tariffs = {k: v for k, v in available_tariffs.items() if k in ["комфорт", "лайт"]}
        # После 90 минут "мини" доступен

    for _, details in available_tariffs.items():
        text_parts.append(safe_escape_markdown(details['display'], version=2) + "\n")

    if first_purchase:
        text_parts.append(f"\n{gift_text_unconditional}\n")
    else:
        text_parts.append("\n")

    text_parts.append(footer)
    text_parts.append(terms_text)
    return "".join(text_parts)


async def check_resources(bot: Bot, user_id: int, required_photos: int = 0, required_avatars: int = 0) -> Optional[tuple]:
    """
    Проверяет, достаточно ли ресурсов у пользователя.
    """
    from database import check_database_user
    from keyboards import create_main_menu_keyboard, create_subscription_keyboard

    try:
        subscription_data = await check_database_user(user_id)
        logger.debug(f"[check_resources] Получены данные подписки для user_id={user_id}: {subscription_data}")

        if not subscription_data:
            logger.error(f"Нет данных подписки для user_id={user_id}")
            error_text = safe_escape_markdown("❌ Ошибка получения данных подписки. Попробуйте позже.", version=2)
            main_menu_kb = await create_main_menu_keyboard(user_id)
            await send_message_with_fallback(bot, user_id, error_text, reply_markup=main_menu_kb, parse_mode=ParseMode.MARKDOWN_V2)
            return None

        if len(subscription_data) < 9:
            logger.error(f"Неполные данные подписки для user_id={user_id}: {subscription_data}")
            error_text = safe_escape_markdown("❌ Ошибка сервера. Обратитесь в поддержку.", version=2)
            main_menu_kb = await create_main_menu_keyboard(user_id)
            await send_message_with_fallback(bot, user_id, error_text, reply_markup=main_menu_kb, parse_mode=ParseMode.MARKDOWN_V2)
            return None

        generations_left = subscription_data[0] if subscription_data[0] is not None else 0
        avatar_left = subscription_data[1] if subscription_data[1] is not None else 0

        logger.info(f"Проверка ресурсов для user_id={user_id}: фото={generations_left}, аватары={avatar_left}")
        logger.info(f"Требуется: фото={required_photos}, аватары={required_avatars}")

        error_message_parts = []

        if required_photos > 0 and generations_left < required_photos:
            error_message_parts.append(f"🚫 Недостаточно печенек! Нужно: {required_photos}, у тебя: {generations_left}")

        if required_avatars > 0 and avatar_left < required_avatars:
            error_message_parts.append(f"🚫 Недостаточно аватаров! Нужно: {required_avatars}, у тебя: {avatar_left}")

        if error_message_parts:
            error_summary = "\n".join(error_message_parts)
            first_purchase = subscription_data[5] if len(subscription_data) > 5 else True
            tariff_message_text = get_tariff_text(first_purchase)

            full_message = f"{safe_escape_markdown(error_summary, version=2)}\n\n{tariff_message_text}"
            subscription_kb = await create_subscription_keyboard(hide_mini_tariff=True)
            await send_message_with_fallback(bot, user_id, full_message, reply_markup=subscription_kb, parse_mode=ParseMode.MARKDOWN_V2)
            return None

        logger.debug(f"[check_resources] Ресурсы достаточны для user_id={user_id}, возвращаем: {subscription_data}")
        return subscription_data

    except Exception as e:
        logger.error(f"[check_resources] Ошибка проверки ресурсов user_id={user_id}: {e}", exc_info=True)
        error_text = safe_escape_markdown("❌ Ошибка сервера при проверке баланса! Попробуйте позже.", version=2)
        main_menu_kb = await create_main_menu_keyboard(user_id)
        await send_message_with_fallback(bot, user_id, error_text, reply_markup=main_menu_kb, parse_mode=ParseMode.MARKDOWN_V2)
        return None

async def check_active_avatar(bot: Bot, user_id: int) -> Optional[tuple]:
    """
    Проверяет наличие активного аватара у пользователя.
    """
    from database import get_active_trainedmodel
    from keyboards import create_user_profile_keyboard, create_main_menu_keyboard

    try:
        trained_model = await get_active_trainedmodel(user_id)
        if not trained_model or trained_model[3] != 'success':
            logger.warning(f"[check_active_avatar] Активный аватар не найден/не готов для user_id={user_id}")
            text = safe_escape_markdown("🚫 Сначала выбери или создай активный аватар в 'Личный кабинет' -> 'Мои аватары'!")
            reply_markup = await create_user_profile_keyboard(user_id, bot)
            await send_message_with_fallback(bot, user_id, text, reply_markup=reply_markup)
            return None

        logger.debug(f"[check_active_avatar] Найден активный аватар для user_id={user_id}: ID {trained_model[0]}")
        return trained_model

    except Exception as e:
        logger.error(f"[check_active_avatar] Ошибка проверки активного аватара user_id={user_id}: {e}", exc_info=True)
        text = safe_escape_markdown("❌ Ошибка сервера при проверке аватара!")
        reply_markup = await create_main_menu_keyboard(user_id)
        await send_message_with_fallback(bot, user_id, text, reply_markup=reply_markup)
        return None

def check_style_config(style_type: str) -> bool:
    """
    Проверяет корректность конфигурации стилей.
    """
    from generation_config import (
        NEW_MALE_AVATAR_STYLES, NEW_FEMALE_AVATAR_STYLES
    )
    from style import new_male_avatar_prompts, new_female_avatar_prompts

    config_map = {
        'new_male_avatar': (NEW_MALE_AVATAR_STYLES, new_male_avatar_prompts),
        'new_female_avatar': (NEW_FEMALE_AVATAR_STYLES, new_female_avatar_prompts),
    }

    if style_type not in config_map:
        if style_type == 'generic_avatar':
            logger.info(f"Тип стиля '{style_type}' больше не используется, пропускаем проверку")
            return True

        logger.error(f"Неизвестный тип стиля '{style_type}' в check_style_config")
        return False

    style_dict, prompt_dict_for_type = config_map[style_type]

    if not (style_dict and isinstance(style_dict, dict) and len(style_dict) > 0):
        logger.error(f"Словарь стилей для '{style_type}' ({type(style_dict).__name__}) отсутствует/пуст или не является словарем в config.py")
        return False

    if not (prompt_dict_for_type and isinstance(prompt_dict_for_type, dict) and len(prompt_dict_for_type) > 0):
        logger.error(f"Словарь промтов для '{style_type}' ({type(prompt_dict_for_type).__name__}) отсутствует/пуст или не является словарем в config.py")
        return False

    missing_keys = [key for key in style_dict if key not in prompt_dict_for_type]
    if missing_keys:
        logger.error(f"Для '{style_type}' отсутствуют промты для ключей: {missing_keys} в соответствующем словаре промтов.")
        return False

    return True

async def create_payment_link(user_id: int, email: str, amount_value: float, description: str, bot_username: str) -> tuple[str, str]:
    """
    Создает ссылку на оплату через YooKassa.
    Возвращает кортеж (payment_url, payment_id).
    """
    logger.debug(f"create_payment_link вызван: user_id={user_id}, email={email}, amount={amount_value}, description={description}, bot_username={bot_username}")

    if not YOOKASSA_AVAILABLE:
        logger.error(f"YooKassa недоступна для user_id={user_id}: библиотека не установлена")
        # ИСПРАВЛЕНО: возвращаем ошибку вместо тестовой ссылки
        raise Exception("Система платежей недоступна. Обратитесь к администратору.")

    # ИСПРАВЛЕНО: убираем проверку тестового токена в продакшене
    # Проверяем только в dev среде
    if os.getenv('ENVIRONMENT', 'development') != 'production':
        if YOOKASSA_TEST_TOKEN and YOOKASSA_TEST_TOKEN.startswith('test_'):
            logger.info(f"Используется тестовый токен YooKassa для user_id={user_id}")
            test_payment_id = f"test_{user_id}_{int(time.time())}"
            return f"https://test.payment.link/user_id={user_id}&amount={amount_value}&test=true&token={YOOKASSA_TEST_TOKEN}", test_payment_id

        # Проверяем, используются ли тестовые данные (старый способ)
        if YOOKASSA_SHOP_ID == '123456' or not SECRET_KEY:
            logger.info(f"Используются тестовые данные YooKassa для user_id={user_id}")
            test_payment_id = f"test_{user_id}_{int(time.time())}"
            return f"https://test.payment.link/user_id={user_id}&amount={amount_value}&test=true", test_payment_id

    # ИСПРАВЛЕНО: в продакшене строгая проверка конфигурации
    if not YOOKASSA_SHOP_ID or not SECRET_KEY:
        logger.error(f"YooKassa не настроена для user_id={user_id}: YOOKASSA_SHOP_ID={YOOKASSA_SHOP_ID}, SECRET_KEY={'***' if SECRET_KEY else None}")
        raise Exception("Система платежей не настроена. Обратитесь к администратору.")

    try:
        YooKassaConfiguration.account_id = YOOKASSA_SHOP_ID
        YooKassaConfiguration.secret_key = SECRET_KEY
        idempotency_key = str(uuid.uuid4())
        logger.debug(f"Инициализация YooKassa: account_id={YOOKASSA_SHOP_ID}, idempotency_key={idempotency_key}")

        # Подготавливаем основные данные платежа
        payment_data = {
            "amount": {
                "value": f"{amount_value:.2f}",
                "currency": "RUB"
            },
            "confirmation": {
                "type": "redirect",
                "return_url": f"https://t.me/{bot_username.lstrip('@')}"
            },
            "capture": True,
            "description": description[:128],
            "metadata": {
                "user_id": str(user_id),
                "description_for_user": description[:128]
            }
        }

        # Добавляем чек всегда (требование российского законодательства)
        # Если email не предоставлен или невалиден, используем email по умолчанию
        customer_email = email if (email and "@" in email and "." in email) else "noreply@axidiphotoai.ru"

        payment_data["receipt"] = {
            "customer": {"email": customer_email},
            "items": [{
                "description": description[:128],
                "quantity": "1.00",
                "amount": {
                    "value": f"{amount_value:.2f}",
                    "currency": "RUB"
                },
                "vat_code": "1",
                "payment_subject": "service",
                "payment_mode": "full_payment"
            }]
        }
        logger.debug(f"Добавлен чек для email={customer_email}")

        payment = YooKassaPayment.create(payment_data, idempotency_key)

        if not hasattr(payment, 'confirmation') or not hasattr(payment.confirmation, 'confirmation_url'):
            logger.error(f"Некорректный ответ YooKassa для user_id={user_id}: payment={payment}")
            # ИСПРАВЛЕНО: возвращаем ошибку вместо тестовой ссылки
            raise Exception("Ошибка создания платежа. Попробуйте позже.")

        logger.info(f"Платёж YooKassa успешно создан: ID={payment.id}, URL={payment.confirmation.confirmation_url}, user_id={user_id}")
        return payment.confirmation.confirmation_url, payment.id

    except Exception as e:
        logger.error(f"Ошибка создания платежа YooKassa для user_id={user_id}, amount={amount_value}: {e}", exc_info=True)
        # ИСПРАВЛЕНО: не возвращаем тестовую ссылку в продакшене, а выбрасываем исключение
        raise Exception(f"Ошибка создания платежа: {str(e)}")

async def handle_user_blocked_bot(user_id: int, error_message: str) -> None:
    """
    Обрабатывает случай, когда пользователь заблокировал бота.
    Блокирует пользователя в базе данных вместо удаления для сохранения данных.

    Args:
        user_id: ID пользователя, который заблокировал бота
        error_message: Сообщение об ошибке
    """
    try:
        logger.warning(f"Пользователь user_id={user_id} заблокировал бота. Блокируем аккаунт для сохранения данных. Ошибка: {error_message}")

        # Блокируем пользователя в базе данных с указанием причины
        block_reason = f"Пользователь заблокировал бота: {error_message}"
        success = await block_user_access(user_id, block=True, block_reason=block_reason)

        if success:
            logger.info(f"Пользователь user_id={user_id} заблокирован в базе данных (данные сохранены)")
            await log_user_action(user_id, "user_blocked_bot", {
                'action': 'block_user_account',
                'reason': 'user_blocked_bot',
                'block_reason': block_reason,
                'error_message': error_message,
                'timestamp': datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
            })
        else:
            logger.error(f"Не удалось заблокировать пользователя user_id={user_id}")

    except Exception as e:
        logger.error(f"Ошибка при блокировке пользователя user_id={user_id}: {e}", exc_info=True)

def test_markdown_escaping():
    """
    Тестовая функция для проверки корректности экранирования.
    """
    test_cases = [
        "Sh.Ai.ProTech (@ShAIPro)",
        "user@example.com",
        "ID: 123456789",
        "Balance: $10.50",
        "Text with (parentheses) and [brackets]",
        "Special chars: !@#$%^&*()_+-={}[]|\\:;\"'<>?,./",
    ]

    for test_text in test_cases:
        escaped = safe_escape_markdown(test_text)
        print(f"Original: {test_text}")
        print(f"Escaped:  {escaped}")
        print("---")

def debug_markdown_text(text: str) -> str:
    """
    Отладочная функция для анализа проблемных текстов с Markdown.
    """
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    found_chars = []

    for char in special_chars:
        if char in text and f'\\{char}' not in text:
            found_chars.append(char)

    if found_chars:
        logger.debug(f"Найдены неэкранированные символы: {found_chars}")
        logger.debug(f"Текст: {text[:200]}...")

    return text

def escape_message_parts(*parts: str, version: int = 2) -> str:

    if not parts:
        return ""

    escaped_parts = [safe_escape_markdown(str(part), version=version) for part in parts]
    result = "".join(escaped_parts)
    logger.debug(f"escape_message_parts: объединено {len(parts)} частей, результат: {result[:200]}...")
    return result

def unescape_markdown(text: str) -> str:

    if not text:
        return ""

    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in special_chars:
        text = text.replace(f'\\{char}', char)
    logger.debug(f"unescape_markdown: очищенный текст: {text[:200]}...")
    return text

# --- ПРОСТАЯ ЗАЩИТА ОТ ДУБЛЕЙ ---
class DuplicateProtectionMiddleware(BaseMiddleware):
    def __init__(self, protection_time: float = 1.0):
        self.protection_time = protection_time
        self._last_actions: Dict[str, float] = {}  # key: "user_id:action", value: timestamp
        super().__init__()

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        # Получаем user_id и action
        user_id = None
        action = None

        if isinstance(event, (Message, CallbackQuery)):
            user_id = event.from_user.id if event.from_user else None

            if isinstance(event, CallbackQuery):
                action = event.data
            elif isinstance(event, Message) and event.text:
                action = event.text[:50]  # Первые 50 символов текста

        if not user_id or not action:
            return await handler(event, data)

        # Создаем ключ для проверки дублей
        action_key = f"{user_id}:{action}"
        current_time = time.time()
        last_time = self._last_actions.get(action_key, 0)

        # Если то же действие было недавно - блокируем
        if current_time - last_time < self.protection_time:
            logger.info(f"Дубликат заблокирован: user_id={user_id}, action={action[:30]}...")
            if isinstance(event, CallbackQuery):
                try:
                    await event.answer("⏳ Обрабатывается...", show_alert=False)
                except Exception:
                    pass
            return

        # Обновляем время последнего действия
        self._last_actions[action_key] = current_time

        # Вызываем обработчик
        return await handler(event, data)

# Функция для создания middleware
def create_duplicate_protection_middleware(protection_time: float = 1.0) -> DuplicateProtectionMiddleware:
    """Создает middleware для защиты от дублирования действий."""
    return DuplicateProtectionMiddleware(protection_time=protection_time)

# --- СТАРЫЙ АНТИСПАМ ДЕКОРАТОР (ОСТАВЛЯЕМ ДЛЯ СОВМЕСТИМОСТИ) ---
_anti_spam_memory = {}

async def _set_anti_spam(user_id: int, timeout: float = 2.0):
    _anti_spam_memory[user_id] = time.time() + timeout
    await asyncio.sleep(timeout)
    if user_id in _anti_spam_memory and _anti_spam_memory[user_id] <= time.time():
        del _anti_spam_memory[user_id]

async def _is_anti_spam(user_id: int) -> bool:
    return user_id in _anti_spam_memory and _anti_spam_memory[user_id] > time.time()

def anti_spam(timeout: float = 2.0, except_states: tuple = ("avatar_training",)):
    """Декоратор для защиты от спама (устаревший, используйте middleware)."""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            user_id = None
            state = None
            query = None
            message = None
            for arg in args:
                if hasattr(arg, 'from_user'):
                    user_id = getattr(arg.from_user, 'id', None)
                if hasattr(arg, 'chat'):
                    user_id = getattr(arg.chat, 'id', None)
                if hasattr(arg, 'state'):
                    state = arg.state
                if hasattr(arg, 'data'):
                    query = arg
                if hasattr(arg, 'text'):
                    message = arg
            if 'user_id' in kwargs:
                user_id = kwargs['user_id']
            if 'state' in kwargs:
                state = kwargs['state']
            for arg in args:
                if hasattr(arg, 'get_state'):
                    state = arg
            current_state = None
            if state:
                try:
                    current_state = await state.get_state()
                except Exception:
                    pass
            if current_state and any(exc in str(current_state) for exc in except_states):
                return await func(*args, **kwargs)
            if user_id and await _is_anti_spam(user_id):
                if query is not None:
                    try:
                        await query.answer("⏳ Подождите, идет обработка...", show_alert=False)
                    except Exception:
                        pass
                return
            if user_id:
                asyncio.create_task(_set_anti_spam(user_id, timeout))
            return await func(*args, **kwargs)
        return wrapper
    return decorator


async def get_bot_summary_stats() -> str:
    """Получает общую статистику бота для отображения"""
    try:
        async with aiosqlite.connect(DATABASE_PATH) as conn:
            conn.row_factory = aiosqlite.Row
            c = await conn.cursor()

            # Общее количество пользователей
            await c.execute("SELECT COUNT(*) as total FROM users")
            total_users = (await c.fetchone())['total']

            # Количество оплативших пользователей
            await c.execute("""
                SELECT COUNT(DISTINCT user_id) as paid_users
                FROM payments
                WHERE status = 'succeeded'
            """)
            paid_users = (await c.fetchone())['paid_users']

            # Общее количество платежей
            await c.execute("""
                SELECT COUNT(*) as total_payments, COALESCE(SUM(amount), 0) as total_amount
                FROM payments
                WHERE status = 'succeeded'
            """)
            payment_stats = await c.fetchone()
            total_payments = payment_stats['total_payments']
            total_amount = payment_stats['total_amount']

            # Количество созданных аватаров
            await c.execute("""
                SELECT 
                    COUNT(*) as total_avatars,
                    COUNT(CASE WHEN status = 'success' THEN 1 END) as successful_avatars
                FROM user_trainedmodels
            """)
            avatar_stats = await c.fetchone()
            total_avatars = avatar_stats['total_avatars']
            successful_avatars = avatar_stats['successful_avatars']

            # Количество генераций за последние 30 дней
            await c.execute("""
                SELECT COUNT(*) as recent_generations
                FROM generation_log 
                WHERE created_at >= date('now', '-30 days')
            """)
            recent_generations = (await c.fetchone())['recent_generations']
            
            # Статистика за сегодня
            await c.execute("""
                SELECT COUNT(*) as new_users_today
                FROM users 
                WHERE date(created_at) = date('now')
            """)
            new_users_today = (await c.fetchone())['new_users_today']
            
            await c.execute("""
                SELECT COUNT(*) as payments_today
                FROM payments 
                WHERE status = 'succeeded' AND date(created_at) = date('now')
            """)
            payments_today = (await c.fetchone())['payments_today']
            
            await c.execute("""
                SELECT COUNT(DISTINCT user_id) as subscriptions_today
                FROM payments 
                WHERE status = 'succeeded' AND date(created_at) = date('now')
            """)
            subscriptions_today = (await c.fetchone())['subscriptions_today']
            
            # Процент оплативших
            paid_percentage = (paid_users / total_users * 100) if total_users > 0 else 0
            
            # Формируем простой текст без форматирования
            summary = f"""🛠 Админ-панель:

📊 Общая статистика бота:
👥 Всего пользователей: {total_users}
💰 Оплатили: {paid_users} ({paid_percentage:.1f}%)
💳 Всего платежей: {total_payments} на {total_amount:.0f}₽

🎭 Аватары:
🖼 Всего создано: {total_avatars}
✅ Успешных: {successful_avatars}

📈 Активность:
🔥 Генераций за 30 дней: {recent_generations}

📅 За сегодня:
🆕 Новых пользователей: {new_users_today}
💳 Оплат: {payments_today}
📝 Подписок: {subscriptions_today}

Выберите действие:"""

            return summary

    except Exception as e:
        logger.error(f"Ошибка получения статистики бота: {e}", exc_info=True)
        return f"""🛠 Админ-панель:

❌ Ошибка загрузки статистики

Выберите действие:"""


async def smart_message_send(
    query_or_message,
    text: str,
    reply_markup: Optional[InlineKeyboardMarkup] = None,
    parse_mode: Optional[ParseMode] = None,
    **kwargs
) -> Message:
    """
    Умная отправка сообщения - редактирует существующее или отправляет новое.
    
    Args:
        query_or_message: CallbackQuery или Message объект
        text: Текст сообщения
        reply_markup: Клавиатура
        parse_mode: Режим парсинга
        **kwargs: Дополнительные параметры
    
    Returns:
        Message объект
    """
    try:
        # Определяем тип объекта и получаем message
        if isinstance(query_or_message, CallbackQuery):
            message = query_or_message.message
            query = query_or_message
        else:
            message = query_or_message
            query = None
        
        # Попытка отредактировать существующее сообщение
        if message and hasattr(message, 'edit_text'):
            try:
                edited_message = await message.edit_text(
                    text=text,
                    reply_markup=reply_markup,
                    parse_mode=parse_mode,
                    **kwargs
                )
                if query:
                    await query.answer()
                return edited_message
            except TelegramBadRequest as e:
                # Если редактирование не удалось, отправляем новое сообщение
                logger.debug(f"Не удалось отредактировать сообщение: {e}")
                
        # Отправка нового сообщения
        if query:
            new_message = await query.message.answer(
                text=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode,
                **kwargs
            )
            await query.answer()
        else:
            new_message = await message.answer(
                text=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode,
                **kwargs
            )
        
        return new_message
        
    except Exception as e:
        logger.error(f"Ошибка в smart_message_send: {e}", exc_info=True)
        # В крайнем случае пытаемся отправить простое сообщение
        if query:
            return await query.message.answer("❌ Произошла ошибка при отправке сообщения")
        else:
            return await message.answer("❌ Произошла ошибка при отправке сообщения")


async def delete_message_and_send_new(
    query_or_message,
    text: str,
    reply_markup: Optional[InlineKeyboardMarkup] = None,
    parse_mode: Optional[ParseMode] = None,
    **kwargs
) -> Message:
    """
    Удаляет предыдущее сообщение и отправляет новое.
    Используется для действий, требующих отдельного сообщения (создание аватара, смена email и т.д.)
    
    Args:
        query_or_message: CallbackQuery или Message объект
        text: Текст нового сообщения
        reply_markup: Клавиатура
        parse_mode: Режим парсинга
        **kwargs: Дополнительные параметры
    
    Returns:
        Message объект нового сообщения
    """
    try:
        # Определяем тип объекта и получаем message
        if isinstance(query_or_message, CallbackQuery):
            message = query_or_message.message
            query = query_or_message
        else:
            message = query_or_message
            query = None
        
        # Пытаемся удалить предыдущее сообщение
        if message:
            try:
                await message.delete()
                logger.debug("Предыдущее сообщение успешно удалено")
            except Exception as e:
                logger.debug(f"Не удалось удалить предыдущее сообщение: {e}")
        
        # Отправляем новое сообщение
        if query:
            new_message = await query.message.answer(
                text=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode,
                **kwargs
            )
            await query.answer()
        else:
            new_message = await message.answer(
                text=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode,
                **kwargs
            )
        
        return new_message
        
    except Exception as e:
        logger.error(f"Ошибка в delete_message_and_send_new: {e}", exc_info=True)
        # В крайнем случае пытаемся отправить простое сообщение
        if query:
            return await query.message.answer("❌ Произошла ошибка при отправке сообщения")
        else:
            return await message.answer("❌ Произошла ошибка при отправке сообщения")


async def smart_message_send_with_photo(
    query_or_message,
    photo,
    caption: str = None,
    reply_markup: Optional[InlineKeyboardMarkup] = None,
    parse_mode: Optional[ParseMode] = None,
    **kwargs
) -> Message:
    """
    Умная отправка сообщения с фото - пытается отредактировать или отправляет новое.
    
    Args:
        query_or_message: CallbackQuery или Message объект
        photo: Фото для отправки
        caption: Подпись к фото
        reply_markup: Клавиатура
        parse_mode: Режим парсинга
        **kwargs: Дополнительные параметры
    
    Returns:
        Message объект
    """
    try:
        # Определяем тип объекта и получаем message
        if isinstance(query_or_message, CallbackQuery):
            message = query_or_message.message
            query = query_or_message
        else:
            message = query_or_message
            query = None
        
        # Попытка отредактировать медиа в существующем сообщении
        if message and hasattr(message, 'edit_media') and message.photo:
            try:
                from aiogram.types import InputMediaPhoto
                media = InputMediaPhoto(media=photo, caption=caption, parse_mode=parse_mode)
                await message.edit_media(media=media, reply_markup=reply_markup, **kwargs)
                if query:
                    await query.answer()
                return message
            except TelegramBadRequest as e:
                logger.debug(f"Не удалось отредактировать медиа: {e}")
        
        # Попытка отредактировать подпись если фото то же самое
        elif message and hasattr(message, 'edit_caption') and message.photo:
            try:
                await message.edit_caption(
                    caption=caption,
                    reply_markup=reply_markup,
                    parse_mode=parse_mode,
                    **kwargs
                )
                if query:
                    await query.answer()
                return message
            except TelegramBadRequest as e:
                logger.debug(f"Не удалось отредактировать подпись: {e}")
        
        # Отправка нового сообщения с фото
        if query:
            new_message = await query.message.answer_photo(
                photo=photo,
                caption=caption,
                reply_markup=reply_markup,
                parse_mode=parse_mode,
                **kwargs
            )
            await query.answer()
        else:
            new_message = await message.answer_photo(
                photo=photo,
                caption=caption,
                reply_markup=reply_markup,
                parse_mode=parse_mode,
                **kwargs
            )
        
        return new_message
        
    except Exception as e:
        logger.error(f"Ошибка в smart_message_send_with_photo: {e}", exc_info=True)
        # В крайнем случае пытаемся отправить простое сообщение
        if query:
            return await query.message.answer("❌ Произошла ошибка при отправке фото")
        else:
            return await message.answer("❌ Произошла ошибка при отправке фото")
