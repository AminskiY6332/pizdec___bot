# keyboards/user_profile.py
"""
Клавиатуры для профиля пользователя и управления аватарами
"""

import logging
from typing import Optional
from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from database import check_user_resources, get_user_payments, get_user_trainedmodels, get_active_trainedmodel, check_database_user

from logger import get_logger
logger = get_logger('keyboards')

async def create_user_profile_keyboard(user_id: int, bot: Bot) -> InlineKeyboardMarkup:
    """Создаёт клавиатуру личного кабинета пользователя."""
    try:
        subscription_data = await check_database_user(user_id)
        generations_left, avatar_left = (0, 0)

        if subscription_data and len(subscription_data) >= 2:
            generations_left, avatar_left = subscription_data[0], subscription_data[1]
    except Exception as e:
        logger.error(f"Ошибка получения подписки в create_user_profile_keyboard для user_id={user_id}: {e}")
        generations_left, avatar_left = ('?', '?')

    try:
        keyboard = [
            [
                InlineKeyboardButton(
                    text=f"💰 Баланс: {generations_left} печенек, {avatar_left} аватар",
                    callback_data="check_subscription"
                )
            ],
            [InlineKeyboardButton(text="📊 Моя статистика", callback_data="user_stats")],
            [InlineKeyboardButton(text="💳 История платежей", callback_data="payment_history")],
            [InlineKeyboardButton(text="📋 Статус обучения", callback_data="check_training")],
            [InlineKeyboardButton(text="👥 Мои аватары", callback_data="my_avatars")],
            [InlineKeyboardButton(text="➕ Создать аватар", callback_data="train_flux")],
            [InlineKeyboardButton(text="📧 Изменить email", callback_data="change_email")],
            [InlineKeyboardButton(text="📄 Пользовательское соглашение", url="https://telegra.ph/Polzovatelskoe-soglashenie-07-26-12")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_menu")]
        ]

        logger.debug(f"Клавиатура личного кабинета создана для user_id={user_id}")
        return InlineKeyboardMarkup(inline_keyboard=keyboard)
    except Exception as e:
        logger.error(f"Ошибка в create_user_profile_keyboard для user_id={user_id}: {e}", exc_info=True)
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Ошибка, вернуться в меню", callback_data="back_to_menu")]
        ])

async def create_avatar_selection_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Создаёт клавиатуру выбора аватара пользователя."""
    try:
        models = await get_user_trainedmodels(user_id)
        active_model_data = await get_active_trainedmodel(user_id)
        active_avatar_id = active_model_data[0] if active_model_data else None
    except Exception as e:
        logger.error(f"Ошибка получения моделей в create_avatar_selection_keyboard для user_id={user_id}: {e}")
        models = []
        active_avatar_id = None

    try:
        keyboard = []
        ready_avatars_exist = False

        if models:
            for model_tuple in models:
                if len(model_tuple) >= 9:
                    avatar_id, _, _, status, _, _, _, _, avatar_name = model_tuple[:9]
                    display_name = avatar_name if avatar_name else f"Аватар {avatar_id}"

                    if status == 'success':
                        ready_avatars_exist = True
                        if avatar_id == active_avatar_id:
                            button_text = f"✅ {display_name} (активный)"
                        else:
                            button_text = f"🔘 Выбрать: {display_name}"
                        keyboard.append([
                            InlineKeyboardButton(text=button_text, callback_data=f"select_avatar_{avatar_id}")
                        ])
                else:
                    logger.warning(f"Неполные данные модели для user_id={user_id}: {model_tuple}")

        if not ready_avatars_exist:
            keyboard.append([InlineKeyboardButton(text="ℹ️ У вас нет готовых аватаров", callback_data="no_ready_avatars_info")])

        keyboard.extend([
            [InlineKeyboardButton(text="➕ Создать новый аватар", callback_data="train_flux")],
            [InlineKeyboardButton(text="📋 Статус всех аватаров", callback_data="check_training")],
            [InlineKeyboardButton(text="🔙 В личный кабинет", callback_data="user_profile")]
        ])

        return InlineKeyboardMarkup(inline_keyboard=keyboard)
    except Exception as e:
        logger.error(f"Ошибка в create_avatar_selection_keyboard для user_id={user_id}: {e}", exc_info=True)
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Ошибка, вернуться в меню", callback_data="back_to_menu")]
        ])

async def create_training_keyboard(user_id: int, photo_count: int) -> InlineKeyboardMarkup:
    """Создаёт клавиатуру для процесса обучения аватара."""
    try:
        keyboard = []

        if photo_count >= 10:
            keyboard.append([InlineKeyboardButton(text="🚀 Начать обучение!", callback_data="confirm_start_training")])

        if photo_count < 20:
            keyboard.append([
                InlineKeyboardButton(
                    text=f"📸 Добавить еще ({photo_count}/20)",
                    callback_data="continue_upload"
                )
            ])

        keyboard.append([InlineKeyboardButton(text="❌ Отмена", callback_data="user_profile")])

        logger.debug(f"Клавиатура обучения создана для user_id={user_id}, photo_count={photo_count}")
        return InlineKeyboardMarkup(inline_keyboard=keyboard)
    except Exception as e:
        logger.error(f"Ошибка в create_training_keyboard для user_id={user_id}: {e}", exc_info=True)
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Ошибка, вернуться в меню", callback_data="back_to_menu")]
        ])

async def create_rating_keyboard(
    generation_type: Optional[str] = None,
    model_key: Optional[str] = None,
    user_id: Optional[int] = None,
    bot: Optional[Bot] = None
) -> InlineKeyboardMarkup:
    """Создаёт клавиатуру для оценки сгенерированного контента."""
    try:
        keyboard = [
            [
                InlineKeyboardButton(text="1⭐", callback_data="rate_1"),
                InlineKeyboardButton(text="2⭐", callback_data="rate_2"),
                InlineKeyboardButton(text="3⭐", callback_data="rate_3"),
                InlineKeyboardButton(text="4⭐", callback_data="rate_4"),
                InlineKeyboardButton(text="5⭐", callback_data="rate_5")
            ],
            [
                InlineKeyboardButton(text="🔄 Повторить", callback_data="repeat_last_generation"),
                InlineKeyboardButton(text="✨ Новая генерация", callback_data="generate_menu")
            ]
        ]

        if user_id and bot:
            try:
                subscription_data = await check_user_resources(bot, user_id, required_photos=5)
                if isinstance(subscription_data, tuple) and len(subscription_data) >= 2:
                    generations_left = subscription_data[0]
                    if generations_left < 5:
                        keyboard.append([InlineKeyboardButton(text="💳 Пополнить", callback_data="subscribe")])
                else:
                    logger.warning(f"Некорректные данные подписки для user_id={user_id}: {subscription_data}")
            except Exception as e:
                logger.error(f"Ошибка проверки баланса в create_rating_keyboard для user_id={user_id}: {e}", exc_info=True)

        keyboard.append([InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_menu")])
        return InlineKeyboardMarkup(inline_keyboard=keyboard)
    except Exception as e:
        logger.error(f"Ошибка в create_rating_keyboard для user_id={user_id}: {e}", exc_info=True)
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Ошибка, вернуться в меню", callback_data="back_to_menu")]
        ])

async def create_payment_success_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Создаёт клавиатуру после успешной оплаты."""
    try:
        keyboard = [
            [InlineKeyboardButton(text="➕ Создать аватар", callback_data="train_flux")],
            [InlineKeyboardButton(text="✨ Сгенерировать фото", callback_data="generate_menu")],
            [InlineKeyboardButton(text="🏠 В меню", callback_data="back_to_menu")]
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)
    except Exception as e:
        logger.error(f"Ошибка в create_payment_success_keyboard для user_id={user_id}: {e}", exc_info=True)
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Ошибка, вернуться в меню", callback_data="back_to_menu")]
        ]) 
