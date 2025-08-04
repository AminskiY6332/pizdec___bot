# handlers/user/payments.py

"""
Модуль для проверки статуса платежей и обновления сообщений
"""
import asyncio
from typing import Optional
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest
from handlers.utils import escape_message_parts, send_message_with_fallback
from database import get_user_payments, check_database_user
from config import TARIFFS
from logger import get_logger

logger = get_logger('payment_checker')

async def check_payment_status_and_update_message(
    bot: Bot,
    user_id: int,
    payment_id: str,
    message_id: int,
    tariff_key: str
) -> None:
    """
    Проверяет статус платежа и обновляет сообщение через 10 минут.
    """
    logger.info(f"Проверка статуса платежа {payment_id} для user_id={user_id}, message_id={message_id}")

    try:
        # Проверяем статус платежа в базе данных
        user_payments = await get_user_payments(user_id)
        payment_found = False

        for payment in user_payments:
            if payment[0] == payment_id and payment[5] == 'succeeded':  # payment_id и status
                payment_found = True
                break

        if payment_found:
            # Платеж успешен - показываем успешное сообщение
            await handle_successful_payment_message(bot, user_id, message_id, tariff_key)
        else:
            # Платеж не прошел или время истекло
            await handle_expired_payment_message(bot, user_id, message_id)

    except Exception as e:
        logger.error(f"Ошибка проверки статуса платежа {payment_id}: {e}", exc_info=True)

async def handle_successful_payment_message(
    bot: Bot,
    user_id: int,
    message_id: int,
    tariff_key: str
) -> None:
    """
    Обновляет сообщение для успешного платежа.
    """
    try:
        # Получаем информацию о тарифе
        tariff = TARIFFS.get(tariff_key, {})
        tariff_name = tariff.get("display", "Неизвестный тариф")
        photos_count = tariff.get("photos", 0)

        # Получаем текущий баланс пользователя
        user_data = await check_database_user(user_id)
        if user_data:
            current_photos = user_data[0] if len(user_data) > 0 else 0  # generations_left
            current_avatars = user_data[1] if len(user_data) > 1 else 0  # avatar_left
        else:
            current_photos = 0
            current_avatars = 0

        # Формируем текст успешной оплаты
        success_text = escape_message_parts(
            "✅ Платеж успешно обработан!\n\n",
            f"🎉 Пакет: {tariff_name}\n",
            f"📦 Получено: {photos_count} печенек\n\n",
            f"💰 Ваш текущий баланс:\n",
            f"🍪 Печенки: {current_photos}\n",
            f"👤 Аватары: {current_avatars}\n\n",
            "🚀 Готово к генерации!",
            version=2
        )

        # Клавиатура для перехода к генерации
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎨 Начать генерацию", callback_data="back_to_menu")],
            [InlineKeyboardButton(text="💎 Купить еще", callback_data="subscribe")]
        ])

        await bot.edit_message_text(
            chat_id=user_id,
            message_id=message_id,
            text=success_text,
            reply_markup=keyboard,
            parse_mode=ParseMode.MARKDOWN_V2
        )

        logger.info(f"Сообщение об успешной оплате обновлено для user_id={user_id}")

    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            logger.debug(f"Сообщение не изменилось для user_id={user_id}")
        else:
            logger.error(f"Ошибка Telegram при обновлении сообщения для user_id={user_id}: {e}")
    except Exception as e:
        logger.error(f"Ошибка обновления сообщения об успешной оплате для user_id={user_id}: {e}", exc_info=True)

async def handle_expired_payment_message(
    bot: Bot,
    user_id: int,
    message_id: int
) -> None:
    """
    Обновляет сообщение для истекшего платежа.
    """
    try:
        # Формируем текст истекшего платежа
        expired_text = escape_message_parts(
            "⏰ Время ожидания платежа истекло\n\n",
            "💳 Платеж не был обработан или был отклонен\n\n",
            "🔄 Попробуйте оплатить снова:",
            version=2
        )

        # Клавиатура для повторной оплаты
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💳 Оплатить снова", callback_data="subscribe")],
            [InlineKeyboardButton(text="🔙 Вернуться в меню", callback_data="back_to_menu")]
        ])

        await bot.edit_message_text(
            chat_id=user_id,
            message_id=message_id,
            text=expired_text,
            reply_markup=keyboard,
            parse_mode=ParseMode.MARKDOWN_V2
        )

        logger.info(f"Сообщение об истекшем платеже обновлено для user_id={user_id}")

    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            logger.debug(f"Сообщение не изменилось для user_id={user_id}")
        else:
            logger.error(f"Ошибка Telegram при обновлении сообщения для user_id={user_id}: {e}")
    except Exception as e:
        logger.error(f"Ошибка обновления сообщения об истекшем платеже для user_id={user_id}: {e}", exc_info=True)

async def schedule_payment_check(
    bot: Bot,
    user_id: int,
    payment_id: str,
    message_id: int,
    tariff_key: str,
    delay_seconds: int = 600  # 10 минут по умолчанию
) -> None:
    """
    Планирует проверку статуса платежа через указанное время.
    """
    logger.info(f"Планирование проверки платежа {payment_id} через {delay_seconds} секунд для user_id={user_id}")
    
    await asyncio.sleep(delay_seconds)
    await check_payment_status_and_update_message(bot, user_id, payment_id, message_id, tariff_key)