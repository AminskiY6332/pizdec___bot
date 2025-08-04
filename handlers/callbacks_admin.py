# handlers/callbacks_admin.py

import asyncio
import logging
import os
import time
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from aiogram import Router, Bot, F
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.exceptions import TelegramBadRequest
from aiogram.enums import ParseMode
from config import ADMIN_IDS, TARIFFS
from generation.images import generate_image

from database import (
    check_database_user, update_user_balance, add_rating, get_user_trainedmodels,
    get_active_trainedmodel, delete_trained_model, get_user_video_tasks,
    get_user_rating_and_registration, get_user_generation_stats, get_user_payments,
    is_user_blocked, user_cache, update_user_credits, check_user_resources, is_old_user,
    get_user_info
)
from handlers.admin_panel import (
    admin_panel, show_admin_stats, admin_show_failed_avatars,
    admin_confirm_delete_all_failed, admin_execute_delete_all_failed
)
from handlers.user_management import (
    show_user_actions, show_user_profile_admin, show_user_avatars_admin,
    change_balance_admin, show_user_logs, delete_user_admin,
    block_user_admin, confirm_block_user, search_users_admin, confirm_reset_avatar, confirm_delete_user
)
from handlers.broadcast import (
    initiate_broadcast, broadcast_message_admin, broadcast_to_paid_users, broadcast_to_non_paid_users
)
from handlers.payments import show_payments_menu, handle_payments_date, handle_manual_date_input, show_replicate_costs
from handlers.visualization import (
    show_visualization, visualize_payments, visualize_registrations, visualize_generations, show_activity_stats
)
from handlers.generation import generate_photo_for_user
from handlers.utils import (
    escape_message_parts, anti_spam
)
from keyboards import create_admin_keyboard
from report import report_generator, send_report_to_admin, delete_report_file

from logger import get_logger
logger = get_logger('main')

async def show_dev_test_payment(query: CallbackQuery, state: FSMContext) -> None:
    """Показывает тестовый тариф для главного разработчика."""
    user_id = query.from_user.id

    # Проверяем, что это главный разработчик
    if user_id != 5667999089:
        await query.answer("❌ Доступно только главному разработчику", show_alert=True)
        return

    from config import TARIFFS
    from handlers.utils import safe_escape_markdown as escape_md

    test_tariff = TARIFFS.get("тест")

    if not test_tariff:
        await query.message.answer("❌ Тестовый тариф не найден в конфигурации.")
        return

    text = escape_md(f"""🧪 ТЕСТОВЫЙ ТАРИФ ДЛЯ ПРОВЕРКИ ПЛАТЕЖЕЙ

💎 {test_tariff['display']}
📝 Описание: {test_tariff['description']}
💰 Сумма: {test_tariff['amount']:.2f}₽
🍪 Печеньки: {test_tariff['photos']}

🔗 Это специальный тариф для проверки работы платежной системы.
Используйте его для тестирования webhook и обработки платежей.""", version=2)

    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=test_tariff["display"], callback_data=test_tariff["callback"])],
        [InlineKeyboardButton(text="🔙 Админ-панель", callback_data="admin_panel")]
    ])

    await query.message.edit_text(
        text,
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN_V2
    )

    logger.info(f"Тестовый тариф показан главному разработчику user_id={user_id} через админ-панель")
    await query.answer()

# Создание роутера для callback'ов админ-панели
admin_callbacks_router = Router()

async def handle_admin_callback(query: CallbackQuery, state: FSMContext) -> Optional[int]:
    """Обрабатывает callback-запросы админ-панели."""
    user_id = query.from_user.id
    bot = query.bot

    if user_id not in ADMIN_IDS:
        await query.answer("⛔ Недостаточно прав", show_alert=True)
        return

    callback_data = query.data
    logger.info(f"Callback от user_id={user_id}: {callback_data}")

    try:
        if callback_data == "admin_panel":
            await state.clear()
            await state.update_data(user_id=user_id)
            await admin_panel(query.message, state, user_id=user_id)
        elif callback_data == "admin_stats":
            await state.update_data(user_id=user_id)
            await handle_admin_report_users(query, state)
        elif callback_data.startswith("admin_stats_page_"):
            await state.update_data(user_id=user_id)
            await handle_admin_report_users(query, state)
        elif callback_data == "admin_replicate_costs":
            await state.update_data(user_id=user_id)
            await show_replicate_costs(query, state)
        elif callback_data == "admin_payments":
            await state.update_data(user_id=user_id)
            await handle_admin_report_payments(query, state)
        elif callback_data.startswith("payments_date_"):
            dates = callback_data.replace("payments_date_", "").split("_")
            start_date, end_date = dates[0], dates[1]
            await state.update_data(user_id=user_id)
            await handle_payments_date(query, state, start_date, end_date)
        elif callback_data == "payments_manual_date":
            await state.update_data(user_id=user_id)
            await handle_manual_date_input(query, state)
        elif callback_data == "admin_activity_stats":
            await state.update_data(user_id=user_id)
            await handle_admin_report_activity(query, state)
        elif callback_data.startswith("activity_"):
            parts = callback_data.split("_")
            if len(parts) == 3:
                days = int(parts[2])
                end_date = datetime.now().strftime('%Y-%m-%d')
                start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
                await state.update_data(user_id=user_id)
                await show_activity_stats(query, state)
        elif callback_data == "admin_referral_stats":
            await state.update_data(user_id=user_id)
            await handle_admin_report_referrals(query, state)
        elif callback_data == "admin_visualization":
            await state.update_data(user_id=user_id)
            await show_visualization(query, state)
        elif callback_data.startswith("delete_report_"):
            filename = callback_data.replace("delete_report_", "")
            await handle_delete_report(query, state, filename)
        elif callback_data.startswith("user_actions_"):
            await state.update_data(user_id=user_id)
            await show_user_actions(query, state)
        elif callback_data.startswith("view_user_profile_"):
            target_user_id = int(callback_data.split("_")[-1])
            await state.update_data(user_id=user_id)
            await show_user_profile_admin(query, state, target_user_id)
        elif callback_data.startswith("user_avatars_"):
            target_user_id = int(callback_data.split("_")[-1])
            await state.update_data(user_id=user_id)
            await show_user_avatars_admin(query, state, target_user_id)
        elif callback_data.startswith("change_balance_"):
            await state.update_data(user_id=user_id)
            await change_balance_admin(query, state)
        elif callback_data.startswith("user_logs_"):
            target_user_id = int(callback_data.split("_")[-1])
            await state.update_data(user_id=user_id)
            await show_user_logs(query, state, target_user_id)
        elif callback_data.startswith("admin_generate:"):
            target_user_id = int(callback_data.split(":")[1])
            await state.update_data(user_id=user_id)
            await generate_photo_for_user(query, state, target_user_id)
        elif callback_data.startswith("admin_send_gen:"):
            target_user_id = int(callback_data.split(":")[1])
            user_data = await state.get_data()
            generation_data = user_data.get(f'last_admin_generation_{target_user_id}')
            if generation_data and generation_data.get('image_urls'):
                try:
                    await query.bot.send_photo(
                        chat_id=target_user_id,
                        photo=generation_data['image_urls'][0],
                        caption=escape_message_parts(
                            "🎁 Для вас создано новое изображение!",
                            version=2
                        ),
                        parse_mode=ParseMode.MARKDOWN_V2
                    )
                    await query.answer("✅ Изображение отправлено пользователю!", show_alert=True)
                except Exception as e:
                    await query.answer(f"❌ Ошибка: {str(e)}.", show_alert=True)
            else:
                await query.answer("❌ Данные генерации не найдены.", show_alert=True)
        elif callback_data.startswith("admin_video:"):
            target_user_id = int(callback_data.split(":")[1])
            await state.update_data(user_id=user_id)
            await generate_video_for_user(query, state, target_user_id)
        elif callback_data.startswith("delete_user_"):
            target_user_id = int(callback_data.split("_")[-1])
            await state.update_data(user_id=user_id)
            await delete_user_admin(query, state, target_user_id)
        elif callback_data.startswith("confirm_delete_user_"):
            target_user_id = int(callback_data.split("_")[-1])
            await state.update_data(user_id=user_id)
            await confirm_delete_user(query, state, target_user_id)
        elif callback_data.startswith("block_user_"):
            await state.update_data(user_id=user_id)
            await block_user_admin(query, state)
        elif callback_data.startswith("confirm_block_user_"):
            await state.update_data(user_id=user_id)
            await confirm_block_user(query, state, bot)
        elif callback_data.startswith("reset_avatar_"):
            target_user_id = int(callback_data.split("_")[-1])
            await state.update_data(user_id=user_id)
            await confirm_reset_avatar(query, state, target_user_id)
        elif callback_data == "admin_failed_avatars":
            await state.update_data(user_id=user_id)
            await admin_show_failed_avatars(query, state)
        elif callback_data == "dev_test_payment":
            await state.update_data(user_id=user_id)
            await show_dev_test_payment(query, state)
        elif callback_data == "admin_delete_all_failed":
            await state.update_data(user_id=user_id)
            await admin_confirm_delete_all_failed(query, state)
        elif callback_data == "admin_confirm_delete_all":
            await state.update_data(user_id=user_id)
            await admin_execute_delete_all_failed(query, state)
        elif callback_data == "send_broadcast_no_text":
            user_data = await state.get_data()
            broadcast_type = user_data.get('broadcast_type')
            media_type = user_data.get('admin_media_type')
            media_id = user_data.get('admin_media_id')
            if not broadcast_type:
                await query.answer("❌ Тип рассылки не определён.", show_alert=True)
                text = escape_message_parts(
                    "❌ Ошибка: тип рассылки не определён.",
                    version=2
                )
                await query.message.edit_text(
                    text,
                    reply_markup=await create_admin_keyboard(user_id),
                    parse_mode=ParseMode.MARKDOWN_V2
                )
                return
            await query.answer("📢 Запускаю рассылку без текста...")
            if broadcast_type == 'all':
                asyncio.create_task(broadcast_message_admin(bot, "", user_id, media_type, media_id))
            elif broadcast_type == 'paid':
                asyncio.create_task(broadcast_to_paid_users(bot, "", user_id, media_type, media_id))
            elif broadcast_type == 'non_paid':
                asyncio.create_task(broadcast_to_non_paid_users(bot, "", user_id, media_type, media_id))
            elif broadcast_type.startswith('with_payment_'):
                audience_type = broadcast_type.replace('with_payment_', '')
                reply_markup = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="Да, хочу! 💳", callback_data="subscribe")]
                ])
                if audience_type == 'all':
                    asyncio.create_task(broadcast_message_admin(bot, "", user_id, media_type, media_id, reply_markup))
                elif audience_type == 'paid':
                    asyncio.create_task(broadcast_to_paid_users(bot, "", user_id, media_type, media_id, reply_markup))
                elif audience_type == 'non_paid':
                    asyncio.create_task(broadcast_to_non_paid_users(bot, "", user_id, media_type, media_id, reply_markup))
            await state.clear()
            text = escape_message_parts(
                "📢 Рассылка запущена!",
                version=2
            )
            await query.message.edit_text(
                text,
                reply_markup=await create_admin_keyboard(user_id),
                parse_mode=ParseMode.MARKDOWN_V2
            )
        elif callback_data == "admin_give_subscription":
            await state.update_data(user_id=user_id)
            await handle_admin_give_subscription_callback(query, state, user_id)
        elif callback_data.startswith("give_subscription_for_user_"):
            target_user_id = int(callback_data.split("_")[-1])
            await state.update_data(user_id=user_id)
            await handle_admin_give_sub_to_user_callback(query, state, user_id, target_user_id)
        elif callback_data.startswith("add_photos_to_user_"):
            target_user_id = int(callback_data.split("_")[-1])
            await state.update_data(user_id=user_id)
            await handle_admin_add_resources_callback(query, state, user_id, target_user_id, "photo", 20)
        elif callback_data.startswith("add_avatar_to_user_"):
            target_user_id = int(callback_data.split("_")[-1])
            await state.update_data(user_id=user_id)
            await handle_admin_add_resources_callback(query, state, user_id, target_user_id, "avatar", 1)
        elif callback_data.startswith("chat_with_user_"):
            target_user_id = int(callback_data.split("_")[-1])
            await state.update_data(user_id=user_id)
            await handle_admin_chat_with_user_callback(query, state, user_id, target_user_id)
        elif callback_data == "admin_search_user":
            await state.update_data(user_id=user_id)
            await search_users_admin(query, state)
        elif callback_data.startswith("confirm_addcook_"):
            parts = callback_data.split("_")
            target_user_id = int(parts[2])
            amount = int(parts[3])
            await state.update_data(user_id=user_id)
            await handle_confirm_addcook(query, state, user_id, target_user_id, amount)
        elif callback_data.startswith("confirm_delcook_"):
            parts = callback_data.split("_")
            target_user_id = int(parts[2])
            amount = int(parts[3])
            await state.update_data(user_id=user_id)
            await handle_confirm_delcook(query, state, user_id, target_user_id, amount)
        elif callback_data.startswith("confirm_addnew_"):
            target_user_id = int(callback_data.split("_")[2])
            await state.update_data(user_id=user_id)
            await handle_confirm_addnew(query, state, user_id, target_user_id)
        elif callback_data.startswith("confirm_delnew_"):
            target_user_id = int(callback_data.split("_")[2])
            await state.update_data(user_id=user_id)
            await handle_confirm_delnew(query, state, user_id, target_user_id)
        elif callback_data == "cancel_admin_operation":
            await state.update_data(user_id=user_id)
            await handle_cancel_admin_operation(query, state, user_id)
        else:
            logger.error(f"Неизвестный admin callback_data: {callback_data} для user_id={user_id}")
            text = escape_message_parts(
                "❌ Неизвестное административное действие.",
                " Попробуйте снова.",
                version=2
            )
            await query.message.edit_text(
                text,
                reply_markup=await create_admin_keyboard(user_id),
                parse_mode=ParseMode.MARKDOWN_V2
            )
    except Exception as e:
        logger.error(f"Ошибка обработки callback для user_id={user_id}: {e}", exc_info=True)
        text = escape_message_parts(
            "❌ Произошла ошибка.",
            " Попробуйте снова или обратитесь в поддержку.",
            version=2
        )
        await query.message.edit_text(
            text,
            reply_markup=await create_admin_keyboard(user_id),
            parse_mode=ParseMode.MARKDOWN_V2
        )

async def handle_admin_add_resources_callback(query: CallbackQuery, state: FSMContext, user_id: int, target_user_id: int, resource_type: str, amount: int) -> None:
    """Обработчик добавления ресурсов (фото или аватары) для указанного пользователя."""
    logger.debug(f"Добавление {amount} {resource_type} для target_user_id={target_user_id} администратором user_id={user_id}")
    await send_typing_action(query.bot, user_id)
    target_user_info = await check_database_user(target_user_id)
    if not target_user_info or (target_user_info[3] is None and target_user_info[8] is None):
        text = escape_message_parts(
            f"❌ Пользователь ID `{target_user_id}` не найден.",
            version=2
        )
        await query.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 К действиям", callback_data=f"user_actions_{target_user_id}")]]),
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return
    action = "increment_photo" if resource_type == "photo" else "increment_avatar"
    resource_name = "фото" if resource_type == "photo" else "аватар"
    try:
        success = await update_user_balance(target_user_id, action, amount=amount)
        logger.debug(f"update_user_balance для user_id={target_user_id}, action={action}, amount={amount}, результат={success}")
        if not success:
            raise Exception("Не удалось обновить ресурсы в базе данных")
        text = escape_message_parts(
            f"✅ Добавлено {amount} {resource_name} пользователю ID `{target_user_id}`.",
            version=2
        )
        await query.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 К действиям", callback_data=f"user_actions_{target_user_id}")]]),
            parse_mode=ParseMode.MARKDOWN_V2
        )
        try:
            await query.bot.send_message(
                chat_id=target_user_id,
                text=escape_message_parts(
                    f"🎉 Администратор добавил вам {amount} {resource_name}!",
                    version=2
                ),
                parse_mode=ParseMode.MARKDOWN_V2
            )
        except Exception as e:
            logger.warning(f"Не удалось уведомить пользователя {target_user_id}: {e}")
        logger.info(f"Успешно добавлено {amount} {resource_type} для user_id={target_user_id}")
    except Exception as e:
        logger.error(f"Ошибка добавления {resource_type} для user_id={target_user_id}: {e}", exc_info=True)
        text = escape_message_parts(
            f"❌ Ошибка при добавлении {resource_name} для пользователя ID `{target_user_id}`: {str(e)}.",
            version=2
        )
        await query.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 К действиям", callback_data=f"user_actions_{target_user_id}")]]),
            parse_mode=ParseMode.MARKDOWN_V2
        )

async def handle_admin_chat_with_user_callback(query: CallbackQuery, state: FSMContext, user_id: int, target_user_id: int) -> None:
    """Обработчик отправки сообщения пользователю."""
    await state.update_data(awaiting_chat_message=target_user_id, user_id=user_id)
    text = escape_message_parts(
        f"💬 Отправка сообщения пользователю ID `{target_user_id}`.\n\n",
        "Введите текст сообщения:",
        version=2
    )
    await query.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="❌ Отмена", callback_data=f"user_actions_{target_user_id}")]]
        ),
        parse_mode=ParseMode.MARKDOWN_V2
    )
    await query.answer()

async def handle_admin_style_selection(query: CallbackQuery, state: FSMContext) -> None:
    """Обработка выбора стиля для админской генерации."""
    user_id = query.from_user.id

    if user_id not in ADMIN_IDS:
        await query.answer("❌ Нет доступа.", show_alert=True)
        return

    style = query.data.replace('admin_style_', '')
    user_data = await state.get_data()
    target_user_id = user_data.get('admin_generation_for_user')

    if not target_user_id:
        await query.answer("❌ Ошибка: не найден целевой пользователь.", show_alert=True)
        return

    if style == 'custom':
        text = escape_message_parts(
            f"✏️ Введите свой промпт для генерации:\n\n",
            f"Триггер-слово `{user_data.get('active_trigger_word', '')}` будет добавлено автоматически.",
            version=2
        )
        await query.message.edit_text(
            text,
            parse_mode=ParseMode.MARKDOWN_V2
        )
        await state.update_data(awaiting_admin_prompt=True, admin_generation_style='custom', user_id=user_id)
    else:
        text = escape_message_parts(
            f"⏳ Генерирую изображение в стиле `{style}`...",
            version=2
        )
        await query.message.edit_text(
            text,
            parse_mode=ParseMode.MARKDOWN_V2
        )

        await state.update_data(style_name=style, prompt=get_style_prompt(style), user_id=user_id)
        await generate_image(query, state)

def get_style_prompt(style: str) -> str:
    """Получает промпт для заданного стиля."""
    style_prompts_dict = {
        'portrait': "professional portrait photo, studio lighting, high quality",
        'casual': "casual photo, natural lighting, relaxed pose",
        'artistic': "artistic photo, creative composition, dramatic lighting",
        'business': "business portrait, formal attire, professional setting",
        'outdoor': "outdoor photo, natural environment, golden hour lighting",
        'indoor': "indoor photo, cozy interior, warm lighting",
    }
    return style_prompts_dict.get(style, "high quality photo")

async def handle_admin_custom_prompt(message: Message, state: FSMContext) -> None:
    """Обработка кастомного промпта от админа."""
    user_data = await state.get_data()
    if not user_data.get('awaiting_admin_prompt'):
        return

    user_id = message.from_user.id
    if user_id not in ADMIN_IDS:
        return

    custom_prompt = message.text
    target_user_id = user_data.get('admin_generation_for_user')

    if not target_user_id:
        return

    status_message = await message.answer(
        escape_message_parts(
            "⏳ Генерирую изображение с вашим промптом...",
            version=2
        ),
        parse_mode=ParseMode.MARKDOWN_V2
    )

    await state.update_data(awaiting_admin_prompt=False, prompt=custom_prompt, style_name='custom', user_id=user_id)

    await generate_image(message, state)

    try:
        await status_message.delete()
    except:
        pass

async def handle_admin_send_generation(query: CallbackQuery, state: FSMContext) -> None:
    """Обработчик для отправки генерации пользователю."""
    from handlers.generation import process_image_generation
    from generation.utils import download_images_parallel

    admin_user_id = query.from_user.id
    await query.answer()

    if admin_user_id not in ADMIN_IDS:
        logger.error(f"Попытка доступа без прав: user_id={admin_user_id}")
        await query.answer("❌ Нет доступа.", show_alert=True)
        return

    parts = query.data.split(':')
    target_user_id = int(parts[1])
    user_data = await state.get_data()
    generation_data = user_data.get(f'last_admin_generation_{target_user_id}')

    logger.info(f"handle_admin_send_generation: admin_user_id={admin_user_id}, target_user_id={target_user_id}")
    logger.debug(f"Данные генерации: {generation_data}")

    if not generation_data or not generation_data.get('image_urls'):
        logger.error(f"Нет данных генерации для target_user_id={target_user_id}")
        text = escape_message_parts(
            f"❌ Нет данных генерации для пользователя ID `{target_user_id}`.",
            version=2
        )
        await query.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 К действиям", callback_data=f"user_actions_{target_user_id}")]
            ]),
            parse_mode=ParseMode.MARKDOWN_V2
        )
        await query.answer("❌ Данные генерации не найдены.", show_alert=True)
        return

    # Загружаем изображения, если пути отсутствуют
    image_paths = user_data.get('last_admin_image_paths', [])
    if not image_paths:
        logger.info(f"Загрузка изображений для target_user_id={target_user_id}")
        image_paths = await download_images_parallel(generation_data['image_urls'], target_user_id)
        if not image_paths:
            logger.error(f"Не удалось загрузить изображения для target_user_id={target_user_id}")
            text = escape_message_parts(
                f"❌ Ошибка загрузки изображений для пользователя ID `{target_user_id}`.",
                version=2
            )
            await query.message.edit_text(
                text,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 К действиям", callback_data=f"user_actions_{target_user_id}")]
                ]),
                parse_mode=ParseMode.MARKDOWN_V2
            )
            await query.answer("❌ Ошибка загрузки изображений.", show_alert=True)
            return
        await state.update_data(last_admin_image_paths=image_paths)

    # Гарантируем сохранение админского контекста
    await state.update_data(
        is_admin_generation=True,
        admin_generation_for_user=target_user_id,
        message_recipient=admin_user_id,
        generation_target_user=target_user_id,
        original_admin_user=admin_user_id,
        user_id=admin_user_id
    )

    try:
        logger.info(f"Вызов process_image_generation для target_user_id={target_user_id}")
        # Вызываем process_image_generation для отправки фото и уведомления администратору
        await process_image_generation(
            bot=query.bot,
            state=state,
            user_id=target_user_id,
            image_paths=image_paths,
            duration=generation_data.get('duration', 0.0),
            aspect_ratio=generation_data.get('aspect_ratio', '1:1'),
            generation_type=generation_data.get('generation_type', 'with_avatar'),
            model_key=generation_data.get('model_key', 'flux-trained'),
            admin_user_id=admin_user_id
        )
        # Обновляем сообщение в чате администратора
        text = escape_message_parts(
            f"✅ Изображения успешно отправлены пользователю ID `{target_user_id}`.\n",
            f"🎨 Стиль: {generation_data.get('style', 'Кастомный стиль')}",
            version=2
        )
        await query.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 К действиям", callback_data=f"user_actions_{target_user_id}")]
            ]),
            parse_mode=ParseMode.MARKDOWN_V2
        )
        await query.answer("✅ Изображения отправлены пользователю!", show_alert=True)
    except Exception as e:
        logger.error(f"Ошибка отправки генерации пользователю ID {target_user_id}: {e}", exc_info=True)
        text = escape_message_parts(
            f"❌ Ошибка при отправке изображений пользователю ID `{target_user_id}`: {str(e)}.",
            version=2
        )
        await query.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 К действиям", callback_data=f"user_actions_{target_user_id}")]
            ]),
            parse_mode=ParseMode.MARKDOWN_V2
        )
        await query.answer(f"❌ Ошибка: {str(e)}.", show_alert=True)

async def handle_admin_regenerate(query: CallbackQuery, state: FSMContext) -> None:
    """Обработчик для повторной генерации админом."""
    await query.answer()

    if query.from_user.id not in ADMIN_IDS:
        return

    target_user_id = int(query.data.split(':')[1])
    await state.update_data(user_id=query.from_user.id)
    await generate_photo_for_user(query, state, target_user_id)

async def handle_admin_give_subscription_callback(query: CallbackQuery, state: FSMContext, user_id: int) -> None:
    """Обработчик выдачи подписки пользователю."""
    text = escape_message_parts(
        "📝 Введите ID пользователя для выдачи подписки:",
        version=2
    )
    await query.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton("❌ Отмена", callback_data="admin_panel")]]),
        parse_mode=ParseMode.MARKDOWN_V2
    )
    await state.update_data(awaiting_subscription_user_id=True, user_id=user_id)

async def handle_admin_give_sub_to_user_callback(query: CallbackQuery, state: FSMContext, user_id: int, target_user_id: int) -> None:
    """Обработчик подтверждения выдачи подписки конкретному пользователю."""
    target_user_info = await check_database_user(target_user_id)
    if not target_user_info or (target_user_info[3] is None and target_user_info[8] is None):
        text = escape_message_parts(
            f"❌ Пользователь ID `{target_user_id}` не найден.",
            version=2
        )
        await query.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton("🔙 К админ-панели", callback_data="admin_panel")]]),
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(f"🎫 {tariff['name']}", callback_data=f"confirm_sub_{target_user_id}_{tariff_id}")]
        for tariff_id, tariff in TARIFFS.items()
    ] + [[InlineKeyboardButton("❌ Отмена", callback_data="admin_panel")]])

    text = escape_message_parts(
        f"👤 Выберите тариф для пользователя ID `{target_user_id}`:",
        version=2
    )
    await query.message.edit_text(
        text,
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN_V2
    )

# Новые функции для обработки отчетов
async def handle_admin_report_users(query: CallbackQuery, state: FSMContext) -> None:
    """Обработчик отчета пользователей"""
    try:
        await query.answer("📊 Создаю отчет пользователей...")

        # Показываем сообщение о создании отчета
        await query.message.edit_text(
            "📊 Создаю отчет пользователей...\n⏳ Пожалуйста, подождите...",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⏳ Создание отчета...", callback_data="ignore")]
            ])
        )

        # Создаем отчет
        filepath = await report_generator.create_users_report()

        # Отправляем отчет
        await send_report_to_admin(query.bot, query.from_user.id, filepath, "Отчет пользователей")

        # Отвечаем на callback
        await query.answer("✅ Отчет пользователей создан и отправлен!")

    except Exception as e:
        logger.error(f"Ошибка создания отчета пользователей: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка создания отчета: {str(e)}")

async def handle_admin_report_activity(query: CallbackQuery, state: FSMContext) -> None:
    """Обработчик отчета активности"""
    try:
        await query.answer("📊 Создаю отчет активности...")

        await query.message.edit_text(
            "📊 Создаю отчет активности...\n⏳ Пожалуйста, подождите...",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⏳ Создание отчета...", callback_data="ignore")]
            ])
        )

        filepath = await report_generator.create_activity_report()
        await send_report_to_admin(query.bot, query.from_user.id, filepath, "Отчет активности")
        await query.answer("✅ Отчет активности создан и отправлен!")

    except Exception as e:
        logger.error(f"Ошибка создания отчета активности: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка создания отчета: {str(e)}")

async def handle_admin_report_payments(query: CallbackQuery, state: FSMContext) -> None:
    """Обработчик отчета платежей"""
    try:
        await query.answer("📈 Создаю отчет платежей...")

        await query.message.edit_text(
            "📈 Создаю отчет платежей...\n⏳ Пожалуйста, подождите...",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⏳ Создание отчета...", callback_data="ignore")]
            ])
        )

        filepath = await report_generator.create_payments_report()
        await send_report_to_admin(query.bot, query.from_user.id, filepath, "Отчет платежей")
        await query.answer("✅ Отчет платежей создан и отправлен!")

    except Exception as e:
        logger.error(f"Ошибка создания отчета платежей: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка создания отчета: {str(e)}")

async def handle_admin_report_referrals(query: CallbackQuery, state: FSMContext) -> None:
    """Обработчик отчета рефералов"""
    try:
        await query.answer("🔗 Создаю отчет рефералов...")

        await query.message.edit_text(
            "🔗 Создаю отчет рефералов...\n⏳ Пожалуйста, подождите...",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⏳ Создание отчета...", callback_data="ignore")]
            ])
        )

        filepath = await report_generator.create_referrals_report()
        await send_report_to_admin(query.bot, query.from_user.id, filepath, "Отчет рефералов")
        await query.answer("✅ Отчет рефералов создан и отправлен!")

    except Exception as e:
        logger.error(f"Ошибка создания отчета рефералов: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка создания отчета: {str(e)}")

async def handle_delete_report(query: CallbackQuery, state: FSMContext, filename: str) -> None:
    """Обработчик удаления файла отчета"""
    try:
        import os
        import tempfile
        filepath = os.path.join(tempfile.gettempdir(), filename)
        await delete_report_file(filepath)
        await query.answer("🗑 Файл отчета удален!")

    except Exception as e:
        logger.error(f"Ошибка удаления файла отчета: {e}")
        await query.answer(f"❌ Ошибка удаления файла: {str(e)}")

# Регистрация обработчиков
@admin_callbacks_router.callback_query(
    lambda c: c.data and c.data.startswith((
        'admin_', 'user_actions_', 'view_user_profile_', 'user_avatars_', 'user_logs_', 'change_balance_',
        'delete_user_', 'block_user_', 'confirm_delete_user_', 'confirm_block_user_', 'payments_',
        'visualize_', 'reset_avatar_', 'add_photos_to_user_', 'add_avatar_to_user_', 'chat_with_user_',
        'give_subscription_', 'activity_', 'delete_report_', 'confirm_addcook_', 'confirm_delcook_',
        'confirm_addnew_', 'confirm_delnew_', 'cancel_admin_operation'
    )) and not c.data.startswith('admin_style_')
)
async def admin_callback_handler(query: CallbackQuery, state: FSMContext) -> None:
    await handle_admin_callback(query, state)

async def handle_confirm_addcook(query: CallbackQuery, state: FSMContext, admin_user_id: int, target_user_id: int, amount: int) -> None:
    """Обработчик подтверждения добавления печенек"""
    try:
        # Получаем информацию о пользователе
        target_user_info = await get_user_info(target_user_id)
        if not target_user_info:
            text = escape_message_parts(f"❌ Пользователь с ID {target_user_id} не найден.", version=2)
            await query.message.edit_text(text, parse_mode=ParseMode.MARKDOWN_V2)
            await query.answer("❌ Пользователь не найден", show_alert=True)
            return

        # Добавляем печеньки
        success = await update_user_credits(target_user_id, "increment_photo", amount)

        if success:
            # Получаем обновленную информацию
            updated_user_info = await get_user_info(target_user_id)
            current_cookies = updated_user_info.get('generations_left', 0) if updated_user_info else 0

            display_name = target_user_info.get('first_name') or target_user_info.get('username') or f"ID {target_user_id}"
            username_display = f"(@{target_user_info.get('username')})" if target_user_info.get('username') else ""

            success_text = escape_message_parts(f"""✅ Печеньки успешно добавлены!

👤 Пользователь: {display_name} {username_display}
🆔 ID: {target_user_id}
➕ Добавлено: {amount} печенек
📊 Текущий баланс: {current_cookies} печенек

Операция выполнена администратором ID {admin_user_id}""", version=2)

            await query.message.edit_text(success_text, parse_mode=ParseMode.MARKDOWN_V2)
            await query.answer("✅ Печеньки добавлены!", show_alert=True)

            logger.info(f"Админ {admin_user_id} добавил {amount} печенек пользователю {target_user_id}")
        else:
            error_text = escape_message_parts(f"❌ Ошибка при добавлении печенек пользователю {target_user_id}", version=2)
            await query.message.edit_text(error_text, parse_mode=ParseMode.MARKDOWN_V2)
            await query.answer("❌ Ошибка операции", show_alert=True)

    except Exception as e:
        logger.error(f"Ошибка в handle_confirm_addcook: {e}", exc_info=True)
        error_text = escape_message_parts("❌ Произошла ошибка при выполнении операции", version=2)
        await query.message.edit_text(error_text, parse_mode=ParseMode.MARKDOWN_V2)
        await query.answer("❌ Ошибка", show_alert=True)

async def handle_confirm_delcook(query: CallbackQuery, state: FSMContext, admin_user_id: int, target_user_id: int, amount: int) -> None:
    """Обработчик подтверждения удаления печенек"""
    try:
        # Получаем информацию о пользователе
        target_user_info = await get_user_info(target_user_id)
        if not target_user_info:
            text = escape_message_parts(f"❌ Пользователь с ID {target_user_id} не найден.", version=2)
            await query.message.edit_text(text, parse_mode=ParseMode.MARKDOWN_V2)
            await query.answer("❌ Пользователь не найден", show_alert=True)
            return

        current_cookies = target_user_info.get('generations_left', 0)

        # Проверяем достаточность средств
        if amount > current_cookies:
            error_text = escape_message_parts(f"❌ Недостаточно печенек для списания.\nУ пользователя: {current_cookies} печенек\nПопытка списать: {amount} печенек", version=2)
            await query.message.edit_text(error_text, parse_mode=ParseMode.MARKDOWN_V2)
            await query.answer("❌ Недостаточно средств", show_alert=True)
            return

        # Удаляем печеньки
        success = await update_user_credits(target_user_id, "decrement_photo", amount)

        if success:
            # Получаем обновленную информацию
            updated_user_info = await get_user_info(target_user_id)
            new_cookies = updated_user_info.get('generations_left', 0) if updated_user_info else 0

            display_name = target_user_info.get('first_name') or target_user_info.get('username') or f"ID {target_user_id}"
            username_display = f"(@{target_user_info.get('username')})" if target_user_info.get('username') else ""

            success_text = escape_message_parts(f"""✅ Печеньки успешно удалены!

👤 Пользователь: {display_name} {username_display}
🆔 ID: {target_user_id}
➖ Удалено: {amount} печенек
📊 Текущий баланс: {new_cookies} печенек

Операция выполнена администратором ID {admin_user_id}""", version=2)

            await query.message.edit_text(success_text, parse_mode=ParseMode.MARKDOWN_V2)
            await query.answer("✅ Печеньки удалены!", show_alert=True)

            logger.info(f"Админ {admin_user_id} удалил {amount} печенек у пользователя {target_user_id}")
        else:
            error_text = escape_message_parts(f"❌ Ошибка при удалении печенек у пользователя {target_user_id}", version=2)
            await query.message.edit_text(error_text, parse_mode=ParseMode.MARKDOWN_V2)
            await query.answer("❌ Ошибка операции", show_alert=True)

    except Exception as e:
        logger.error(f"Ошибка в handle_confirm_delcook: {e}", exc_info=True)
        error_text = escape_message_parts("❌ Произошла ошибка при выполнении операции", version=2)
        await query.message.edit_text(error_text, parse_mode=ParseMode.MARKDOWN_V2)
        await query.answer("❌ Ошибка", show_alert=True)

async def handle_confirm_addnew(query: CallbackQuery, state: FSMContext, admin_user_id: int, target_user_id: int) -> None:
    """Обработчик подтверждения добавления аватара"""
    try:
        # Получаем информацию о пользователе
        target_user_info = await get_user_info(target_user_id)
        if not target_user_info:
            text = escape_message_parts(f"❌ Пользователь с ID {target_user_id} не найден.", version=2)
            await query.message.edit_text(text, parse_mode=ParseMode.MARKDOWN_V2)
            await query.answer("❌ Пользователь не найден", show_alert=True)
            return

        # Добавляем 1 аватар и убираем статус первой покупки
        success_avatar = await update_user_credits(target_user_id, "increment_avatar", 1)
        success_purchase = await update_user_credits(target_user_id, "set_first_purchase_completed")
        
        success = success_avatar and success_purchase

        if success:
            # Получаем обновленную информацию
            updated_user_info = await get_user_info(target_user_id)
            current_avatars = updated_user_info.get('avatar_left', 0) if updated_user_info else 0

            display_name = target_user_info.get('first_name') or target_user_info.get('username') or f"ID {target_user_id}"
            username_display = f"(@{target_user_info.get('username')})" if target_user_info.get('username') else ""

            success_text = escape_message_parts(f"""✅ Аватар успешно добавлен!

👤 Пользователь: {display_name} {username_display}
🆔 ID: {target_user_id}
➕ Добавлено: 1 аватар
📊 Текущий баланс: {current_avatars} аватаров

Операция выполнена администратором ID {admin_user_id}""", version=2)

            await query.message.edit_text(success_text, parse_mode=ParseMode.MARKDOWN_V2)
            await query.answer("✅ Аватар добавлен!", show_alert=True)

            logger.info(f"Админ {admin_user_id} добавил 1 аватар пользователю {target_user_id}")
        else:
            error_text = escape_message_parts(f"❌ Ошибка при добавлении аватара пользователю {target_user_id}", version=2)
            await query.message.edit_text(error_text, parse_mode=ParseMode.MARKDOWN_V2)
            await query.answer("❌ Ошибка операции", show_alert=True)

    except Exception as e:
        logger.error(f"Ошибка в handle_confirm_addnew: {e}", exc_info=True)
        error_text = escape_message_parts("❌ Произошла ошибка при выполнении операции", version=2)
        await query.message.edit_text(error_text, parse_mode=ParseMode.MARKDOWN_V2)
        await query.answer("❌ Ошибка", show_alert=True)

async def handle_confirm_delnew(query: CallbackQuery, state: FSMContext, admin_user_id: int, target_user_id: int) -> None:
    """Обработчик подтверждения удаления аватара"""
    try:
        # Получаем информацию о пользователе
        target_user_info = await get_user_info(target_user_id)
        if not target_user_info:
            text = escape_message_parts(f"❌ Пользователь с ID {target_user_id} не найден.", version=2)
            await query.message.edit_text(text, parse_mode=ParseMode.MARKDOWN_V2)
            await query.answer("❌ Пользователь не найден", show_alert=True)
            return

        current_avatars = target_user_info.get('avatar_left', 0)
        
        # Проверяем достаточность аватаров
        if current_avatars <= 0:
            error_text = escape_message_parts(f"❌ У пользователя нет аватаров для удаления.\nТекущий баланс: {current_avatars} аватаров", version=2)
            await query.message.edit_text(error_text, parse_mode=ParseMode.MARKDOWN_V2)
            await query.answer("❌ Недостаточно аватаров", show_alert=True)
            return

        # Удаляем 1 аватар (НЕ возвращаем статус первой покупки)
        success = await update_user_credits(target_user_id, "decrement_avatar", 1)
        
        if success:
            # Получаем обновленную информацию
            updated_user_info = await get_user_info(target_user_id)
            new_avatars = updated_user_info.get('avatar_left', 0) if updated_user_info else 0
            
            display_name = target_user_info.get('first_name') or target_user_info.get('username') or f"ID {target_user_id}"
            username_display = f"(@{target_user_info.get('username')})" if target_user_info.get('username') else ""
            
            success_text = escape_message_parts(f"""✅ Аватар успешно удален!

👤 Пользователь: {display_name} {username_display}
🆔 ID: {target_user_id}
➖ Удалено: 1 аватар
📊 Текущий баланс: {new_avatars} аватаров

Операция выполнена администратором ID {admin_user_id}""", version=2)
            
            await query.message.edit_text(success_text, parse_mode=ParseMode.MARKDOWN_V2)
            await query.answer("✅ Аватар удален!", show_alert=True)
            
            logger.info(f"Админ {admin_user_id} удалил 1 аватар у пользователя {target_user_id}")
        else:
            error_text = escape_message_parts(f"❌ Ошибка при удалении аватара у пользователя {target_user_id}", version=2)
            await query.message.edit_text(error_text, parse_mode=ParseMode.MARKDOWN_V2)
            await query.answer("❌ Ошибка операции", show_alert=True)
            
    except Exception as e:
        logger.error(f"Ошибка в handle_confirm_delnew: {e}", exc_info=True)
        error_text = escape_message_parts("❌ Произошла ошибка при выполнении операции", version=2)
        await query.message.edit_text(error_text, parse_mode=ParseMode.MARKDOWN_V2)
        await query.answer("❌ Ошибка", show_alert=True)

async def handle_cancel_admin_operation(query: CallbackQuery, state: FSMContext, admin_user_id: int) -> None:
    """Обработчик отмены админской операции"""
    try:
        cancel_text = escape_message_parts("❌ Операция отменена", version=2)
        await query.message.edit_text(cancel_text, parse_mode=ParseMode.MARKDOWN_V2)
        await query.answer("Операция отменена", show_alert=False)
        logger.info(f"Админ {admin_user_id} отменил операцию")
    except Exception as e:
        logger.error(f"Ошибка в handle_cancel_admin_operation: {e}", exc_info=True)

@admin_callbacks_router.callback_query(lambda c: c.data and c.data.startswith('admin_style_'))
async def admin_style_selection_handler(query: CallbackQuery, state: FSMContext) -> None:
    await handle_admin_style_selection(query, state)
