# keyboards/payments.py
"""
Клавиатуры для платежей и подписок
"""

import logging
from typing import Optional
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from config import TARIFFS, ADMIN_IDS
from database import check_database_user, get_user_payments

from logger import get_logger
logger = get_logger('keyboards')

async def create_subscription_keyboard(hide_mini_tariff: bool = False) -> InlineKeyboardMarkup:
    """Создаёт клавиатуру с тарифами для подписки."""
    try:
        keyboard = [
            [
                InlineKeyboardButton(
                    text="💎 Выберите тариф",
                    callback_data="ignore"
                )
            ]
        ]

        # Определяем, какие тарифы показывать
        available_tariffs = {k: v for k, v in TARIFFS.items() if k != "admin_premium"}
        if hide_mini_tariff:
            available_tariffs = {k: v for k, v in available_tariffs.items() if k != "мини"}

        for plan_key, plan_details in available_tariffs.items():
            keyboard.append([
                InlineKeyboardButton(
                    text=plan_details["display"],
                    callback_data=plan_details["callback"]
                )
            ])

        keyboard.append([
            InlineKeyboardButton(text="🔙 В меню", callback_data="back_to_menu")
        ])

        logger.debug(f"Клавиатура тарифов создана успешно: {len(keyboard)} строк, hide_mini_tariff={hide_mini_tariff}")
        return InlineKeyboardMarkup(inline_keyboard=keyboard)
    except Exception as e:
        logger.error(f"Ошибка в create_subscription_keyboard: {e}", exc_info=True)
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Ошибка, вернуться в меню", callback_data="back_to_menu")]
        ])

async def create_payment_only_keyboard(user_id: int, time_since_registration: float, days_since_registration: int, last_reminder_type: str = None, is_old_user: bool = False) -> InlineKeyboardMarkup:
    """
    Создаёт клавиатуру с кнопками оплаты для неоплативших пользователей.

    Args:
        user_id: ID пользователя
        time_since_registration: Время с момента регистрации в секундах
        days_since_registration: Количество дней с момента регистрации
        last_reminder_type: Тип последнего отправленного напоминания
        is_old_user: Флаг, указывающий, является ли пользователь старым (зарегистрирован до отсечки)

    Returns:
        InlineKeyboardMarkup: Клавиатура с кнопками оплаты
    """
    try:
        # Проверяем статус оплаты
        subscription_data = await check_database_user(user_id)
        payments = await get_user_payments(user_id)
        is_paying_user = bool(payments) or (subscription_data and len(subscription_data) > 5 and not bool(subscription_data[5]))
        logger.debug(f"create_payment_only_keyboard: user_id={user_id}, is_paying_user={is_paying_user}, days_since_registration={days_since_registration}, time_since_registration={time_since_registration}, is_old_user={is_old_user}")

        if is_paying_user:
            return await create_subscription_keyboard(hide_mini_tariff=False)

        keyboard = []
        available_tariffs = {k: v for k, v in TARIFFS.items() if k != "admin_premium"}

        # Для старых пользователей показываем все тарифы
        if is_old_user:
            keyboard.extend([
                [InlineKeyboardButton(text=available_tariffs["комфорт"]["display"], callback_data="pay_1199")],
                [InlineKeyboardButton(text=available_tariffs["лайт"]["display"], callback_data="pay_599")],
                [InlineKeyboardButton(text=available_tariffs["мини"]["display"], callback_data="pay_399")],
                [InlineKeyboardButton(text=available_tariffs["аватар"]["display"], callback_data="pay_590")]
            ])
            logger.debug(f"Создана клавиатура с полным списком тарифов для старого пользователя user_id={user_id}")
        else:
            # Логика для новых пользователей: показываем один тариф
            if days_since_registration == 0:
                logger.debug(f"Day 0: time_since_registration={time_since_registration}")
                if time_since_registration <= 1800:  # До 30 минут
                    tariff_key = "комфорт"
                    callback_data = "pay_1199"
                elif time_since_registration <= 5400:  # 30–90 минут
                    tariff_key = "лайт"
                    callback_data = "pay_599"
                else:  # После 90 минут
                    tariff_key = "мини"
                    callback_data = "pay_399"
            elif days_since_registration == 1:
                tariff_key = "лайт"
                callback_data = "pay_599"
            elif 2 <= days_since_registration <= 4:
                tariff_key = "мини"
                callback_data = "pay_399"
            else:
                # Для новых пользователей с days_since_registration >= 5 показываем все тарифы
                keyboard.extend([
                    [InlineKeyboardButton(text=available_tariffs["комфорт"]["display"], callback_data="pay_1199")],
                    [InlineKeyboardButton(text=available_tariffs["лайт"]["display"], callback_data="pay_599")],
                    [InlineKeyboardButton(text=available_tariffs["мини"]["display"], callback_data="pay_399")],
                    [InlineKeyboardButton(text=available_tariffs["аватар"]["display"], callback_data="pay_590")]
                ])
                logger.debug(f"Создана клавиатура с полным списком тарифов для нового пользователя user_id={user_id} с days_since_registration={days_since_registration}")
                keyboard.append([InlineKeyboardButton(text="🔙 В меню", callback_data="back_to_menu_safe")])
                keyboard.append([InlineKeyboardButton(text="ℹ️ Информация о тарифах", callback_data="tariff_info")])
                return InlineKeyboardMarkup(inline_keyboard=keyboard)

            tariff = TARIFFS.get(tariff_key)
            if not tariff:
                logger.error(f"Тариф {tariff_key} не найден для user_id={user_id}")
                return InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="❌ Ошибка", callback_data="error")]
                ])

            keyboard.append([InlineKeyboardButton(text=tariff["display"], callback_data=callback_data)])

        # Условное добавление кнопок "В меню" и "Информация о тарифах"
        generations_left = subscription_data[0] if subscription_data and len(subscription_data) > 0 else 0
        avatar_left = subscription_data[1] if subscription_data and len(subscription_data) > 1 else 0
        if generations_left > 0 or avatar_left > 0 or user_id in ADMIN_IDS:
            keyboard.append([InlineKeyboardButton(text="🔙 В меню", callback_data="back_to_menu_safe")])
            keyboard.append([InlineKeyboardButton(text="ℹ️ Информация о тарифах", callback_data="tariff_info")])
        else:
            keyboard.append([InlineKeyboardButton(text="🔐 Купи пакет для доступа", callback_data="subscribe")])

        logger.debug(f"Клавиатура оплаты создана для user_id={user_id}: days={days_since_registration}, time={time_since_registration}, is_old_user={is_old_user}")
        return InlineKeyboardMarkup(inline_keyboard=keyboard)
    except Exception as e:
        logger.error(f"Ошибка в create_payment_only_keyboard для user_id={user_id}: {e}", exc_info=True)
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Ошибка", callback_data="error")]
        ]) 
