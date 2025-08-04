# handlers/user/generation.py

import asyncio
import logging
from typing import Optional, List, Dict, Tuple
from aiogram import Router, Bot
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from aiogram.fsm.context import FSMContext
from aiogram.enums import ParseMode
from database import check_database_user, get_active_trainedmodel, update_user_credits
from config import ADMIN_IDS
from handlers.utils import (
    safe_escape_markdown as escape_md, send_message_with_fallback, check_resources, clean_admin_context
)
from keyboards import (
    create_admin_keyboard, create_main_menu_keyboard, create_avatar_style_choice_keyboard,
    create_new_male_avatar_styles_keyboard, create_new_female_avatar_styles_keyboard,
    create_aspect_ratio_keyboard, create_rating_keyboard
)
from generation.images import generate_image, process_prompt_async, prepare_model_params
from generation.utils import reset_generation_context

from logger import get_logger
logger = get_logger('generation')

# Создание роутера для генерации
generation_router = Router()

async def generate_photo_for_user(query: CallbackQuery, state: FSMContext, target_user_id: int) -> None:

    admin_id = query.from_user.id
    bot_id = (await query.bot.get_me()).id
    logger.debug(f"Инициирована генерация фото для target_user_id={target_user_id} администратором user_id={admin_id}")

    # Проверка прав администратора
    if admin_id not in ADMIN_IDS:
        await query.answer("⛔ Недостаточно прав", show_alert=True)
        return

    # Проверка, что target_user_id не является ID бота
    if target_user_id == bot_id:
        logger.error(f"Некорректный target_user_id: {target_user_id} (ID бота)")
        await send_message_with_fallback(
            query.bot, admin_id,
            escape_md(f"❌ Неверный ID пользователя: `{target_user_id}`.", version=2),
            update_or_query=query,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 К действиям", callback_data=f"user_actions_{target_user_id}")]
            ]),
            parse_mode=ParseMode.MARKDOWN_V2
        )
        await query.answer()
        return

    # Проверяем существование пользователя
    target_user_info = await check_database_user(target_user_id)
    if not target_user_info or (target_user_info[3] is None and target_user_info[8] is None):
        await send_message_with_fallback(
            query.bot, admin_id,
            escape_md(f"❌ Пользователь ID `{target_user_id}` не найден.", version=2),
            update_or_query=query,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 К действиям", callback_data=f"user_actions_{target_user_id}")]
            ]),
            parse_mode=ParseMode.MARKDOWN_V2
        )
        await query.answer()
        return

    # Проверяем наличие активного аватара у целевого пользователя
    active_model_data = await get_active_trainedmodel(target_user_id)
    if not active_model_data or active_model_data[3] != 'success':
        await send_message_with_fallback(
            query.bot, admin_id,
            escape_md(f"❌ У пользователя ID `{target_user_id}` нет активного аватара.", version=2),
            update_or_query=query,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 К действиям", callback_data=f"user_actions_{target_user_id}")]
            ]),
            parse_mode=ParseMode.MARKDOWN_V2
        )
        await query.answer()
        return

    # Очищаем контекст перед началом генерации
    await clean_admin_context(state)
    logger.info(f"Контекст очищен перед админской генерацией для user_id={target_user_id}")

    # Сохраняем данные для генерации
    await state.update_data(
        admin_generation_for_user=target_user_id,
        generation_type='with_avatar',
        model_key='flux-trained',
        active_model_version=active_model_data[0],  # model_version
        active_trigger_word=active_model_data[1],   # trigger_word
        active_avatar_name=active_model_data[2],    # avatar_name
        old_model_id=active_model_data[4],         # model_id
        old_model_version=active_model_data[0],    # model_version
        is_admin_generation=True,
        message_recipient=admin_id,
    )

    # Отправляем сообщение о начале генерации
    await send_message_with_fallback(
        query.bot, admin_id,
        escape_md(f"🎨 Начинаю генерацию фото для пользователя ID `{target_user_id}`\n\n"
                 f"Аватар: `{active_model_data[2]}`\n"
                 f"Триггер: `{active_model_data[1]}`", version=2),
        update_or_query=query,
        reply_markup=create_avatar_style_choice_keyboard(),
        parse_mode=ParseMode.MARKDOWN_V2
    )
    await query.answer()

async def handle_admin_style_selection(query: CallbackQuery, state: FSMContext) -> None:
    """Обработка выбора стиля администратором"""
    admin_id = query.from_user.id
    
    if admin_id not in ADMIN_IDS:
        await query.answer("⛔ Недостаточно прав", show_alert=True)
        return

    data = query.data
    logger.debug(f"Админ {admin_id} выбрал стиль: {data}")

    if data.startswith("style_new_male_"):
        style = data.replace("style_new_male_", "")
        await state.update_data(selected_style=style, gender="male")
        await send_message_with_fallback(
            query.bot, admin_id,
            escape_md(f"🎨 Выбран стиль: `{style}`\n\nТеперь выберите соотношение сторон:", version=2),
            update_or_query=query,
            reply_markup=create_aspect_ratio_keyboard(),
            parse_mode=ParseMode.MARKDOWN_V2
        )
    elif data.startswith("style_new_female_"):
        style = data.replace("style_new_female_", "")
        await state.update_data(selected_style=style, gender="female")
        await send_message_with_fallback(
            query.bot, admin_id,
            escape_md(f"🎨 Выбран стиль: `{style}`\n\nТеперь выберите соотношение сторон:", version=2),
            update_or_query=query,
            reply_markup=create_aspect_ratio_keyboard(),
            parse_mode=ParseMode.MARKDOWN_V2
        )
    elif data == "select_new_male_avatar_styles":
        await send_message_with_fallback(
            query.bot, admin_id,
            escape_md("🎨 Выберите стиль для мужского аватара:", version=2),
            update_or_query=query,
            reply_markup=create_new_male_avatar_styles_keyboard(),
            parse_mode=ParseMode.MARKDOWN_V2
        )
    elif data == "select_new_female_avatar_styles":
        await send_message_with_fallback(
            query.bot, admin_id,
            escape_md("🎨 Выберите стиль для женского аватара:", version=2),
            update_or_query=query,
            reply_markup=create_new_female_avatar_styles_keyboard(),
            parse_mode=ParseMode.MARKDOWN_V2
        )
    elif data.startswith(("male_styles_page_", "female_styles_page_")):
        # Обработка пагинации стилей
        page = int(data.split("_")[-1])
        gender = "male" if data.startswith("male_styles_page_") else "female"
        
        if gender == "male":
            await send_message_with_fallback(
                query.bot, admin_id,
                escape_md(f"🎨 Страница {page} мужских стилей:", version=2),
                update_or_query=query,
                reply_markup=create_new_male_avatar_styles_keyboard(page),
                parse_mode=ParseMode.MARKDOWN_V2
            )
        else:
            await send_message_with_fallback(
                query.bot, admin_id,
                escape_md(f"🎨 Страница {page} женских стилей:", version=2),
                update_or_query=query,
                reply_markup=create_new_female_avatar_styles_keyboard(page),
                parse_mode=ParseMode.MARKDOWN_V2
            )

    await query.answer()

async def handle_admin_custom_prompt(message: Message, state: FSMContext) -> None:
    """Обработка кастомного промпта от администратора"""
    admin_id = message.from_user.id
    
    if admin_id not in ADMIN_IDS:
        return

    prompt = message.text.strip()
    if len(prompt) < 10:
        await message.answer("❌ Промпт должен содержать минимум 10 символов")
        return

    await state.update_data(custom_prompt=prompt)
    
    # Получаем данные о генерации
    data = await state.get_data()
    target_user_id = data.get('admin_generation_for_user')
    
    await message.answer(
        escape_md(f"✅ Промпт сохранен: `{prompt}`\n\n"
                 f"Начинаю генерацию для пользователя ID `{target_user_id}`", version=2),
        parse_mode=ParseMode.MARKDOWN_V2
    )

    # Запускаем генерацию
    await start_admin_generation(message.bot, state, admin_id, target_user_id)

async def handle_admin_aspect_ratio_selection(query: CallbackQuery, state: FSMContext) -> None:
    """Обработка выбора соотношения сторон администратором"""
    admin_id = query.from_user.id
    
    if admin_id not in ADMIN_IDS:
        await query.answer("⛔ Недостаточно прав", show_alert=True)
        return

    data = query.data
    if data.startswith("aspect_"):
        aspect_ratio = data.replace("aspect_", "")
        await state.update_data(aspect_ratio=aspect_ratio)
        
        # Получаем данные о генерации
        state_data = await state.get_data()
        target_user_id = state_data.get('admin_generation_for_user')
        
        await send_message_with_fallback(
            query.bot, admin_id,
            escape_md(f"📐 Выбрано соотношение: `{aspect_ratio}`\n\n"
                     f"Теперь введите кастомный промпт для генерации фото пользователя ID `{target_user_id}`:", version=2),
            update_or_query=query,
            parse_mode=ParseMode.MARKDOWN_V2
        )

    await query.answer()

async def handle_admin_generation_result(state: FSMContext, admin_id: int, target_user_id: int, result_data: Dict, bot: Bot) -> None:
    """Обработка результата генерации для администратора"""
    
    # Отправляем результат администратору
    await send_message_with_fallback(
        bot, admin_id,
        escape_md(f"✅ Генерация завершена для пользователя ID `{target_user_id}`\n\n"
                 f"📊 Результат:\n"
                 f"• Изображений: {len(result_data.get('image_paths', []))}\n"
                 f"• Время: {result_data.get('duration', 0):.2f}с\n"
                 f"• Стиль: {result_data.get('style', 'N/A')}\n"
                 f"• Соотношение: {result_data.get('aspect_ratio', 'N/A')}", version=2),
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 К действиям", callback_data=f"user_actions_{target_user_id}")]
        ])
    )

    # Очищаем контекст
    await reset_generation_context(state)
    logger.info(f"Админская генерация завершена для user_id={target_user_id}")

async def process_image_generation(
    bot: Bot,
    state: FSMContext,
    user_id: int,
    image_paths: List[str],
    duration: float,
    aspect_ratio: str,
    generation_type: str,
    model_key: str,
    admin_user_id: Optional[int] = None
) -> None:
    """Обработка результата генерации изображений"""
    
    try:
        # Отправляем изображения пользователю
        for i, image_path in enumerate(image_paths, 1):
            with open(image_path, 'rb') as photo:
                await bot.send_photo(
                    chat_id=user_id,
                    photo=photo,
                    caption=f"🎨 Изображение {i}/{len(image_paths)}\n"
                           f"⏱ Время генерации: {duration:.2f}с\n"
                           f"📐 Соотношение: {aspect_ratio}"
                )

        # Отправляем клавиатуру с рейтингом
        await bot.send_message(
            chat_id=user_id,
            text="⭐ Оцените качество генерации:",
            reply_markup=create_rating_keyboard()
        )

        # Если это админская генерация, уведомляем администратора
        if admin_user_id:
            await handle_admin_generation_result(
                state, admin_user_id, user_id,
                {
                    'image_paths': image_paths,
                    'duration': duration,
                    'aspect_ratio': aspect_ratio,
                    'generation_type': generation_type,
                    'model_key': model_key
                },
                bot
            )

    except Exception as e:
        logger.error(f"Ошибка при отправке изображений: {e}")
        await bot.send_message(
            chat_id=user_id,
            text="❌ Произошла ошибка при отправке изображений"
        )

async def start_admin_generation(bot: Bot, state: FSMContext, admin_id: int, target_user_id: int) -> None:
    """Запуск генерации от имени администратора"""
    
    try:
        data = await state.get_data()
        custom_prompt = data.get('custom_prompt', '')
        aspect_ratio = data.get('aspect_ratio', '1:1')
        style = data.get('selected_style', '')
        
        # Подготавливаем параметры модели
        model_params = await prepare_model_params(
            target_user_id,
            data.get('active_model_version'),
            data.get('active_trigger_word'),
            style
        )
        
        # Генерируем изображение
        result = await generate_image(
            prompt=custom_prompt,
            model_params=model_params,
            aspect_ratio=aspect_ratio,
            user_id=target_user_id
        )
        
        if result and result.get('image_paths'):
            await process_image_generation(
                bot=bot,
                state=state,
                user_id=target_user_id,
                image_paths=result['image_paths'],
                duration=result.get('duration', 0),
                aspect_ratio=aspect_ratio,
                generation_type='admin_generation',
                model_key='flux-trained',
                admin_user_id=admin_id
            )
        else:
            await send_message_with_fallback(
                bot, admin_id,
                escape_md(f"❌ Ошибка генерации для пользователя ID `{target_user_id}`", version=2),
                parse_mode=ParseMode.MARKDOWN_V2
            )
            
    except Exception as e:
        logger.error(f"Ошибка админской генерации: {e}")
        await send_message_with_fallback(
            bot, admin_id,
            escape_md(f"❌ Ошибка генерации: {str(e)}", version=2),
            parse_mode=ParseMode.MARKDOWN_V2
        )

async def cancel(message: Message, state: FSMContext) -> None:
    """Отмена генерации"""
    await reset_generation_context(state)
    await message.answer("❌ Генерация отменена")

# Регистрация обработчиков
@generation_router.callback_query(
    lambda c: c.data and c.data.startswith((
        "admin_generate:", "admin_send_gen:", "select_new_male_avatar_styles",
        "select_new_female_avatar_styles", "style_new_male_", "style_new_female_",
        "male_styles_page_", "female_styles_page_", "enter_custom_prompt_manual",
        "enter_custom_prompt_llama", "aspect_"
    ))
)
async def generation_callback_handler(query: CallbackQuery, state: FSMContext) -> None:
    """Обработчик callback'ов для генерации"""
    
    data = query.data
    admin_id = query.from_user.id
    
    if admin_id not in ADMIN_IDS:
        await query.answer("⛔ Недостаточно прав", show_alert=True)
        return

    if data.startswith("admin_generate:"):
        target_user_id = int(data.split(":")[1])
        await generate_photo_for_user(query, state, target_user_id)
    elif data.startswith(("style_new_male_", "style_new_female_", "select_new_male_avatar_styles", 
                         "select_new_female_avatar_styles", "male_styles_page_", "female_styles_page_")):
        await handle_admin_style_selection(query, state)
    elif data.startswith("aspect_"):
        await handle_admin_aspect_ratio_selection(query, state)
    elif data in ["enter_custom_prompt_manual", "enter_custom_prompt_llama"]:
        await send_message_with_fallback(
            query.bot, admin_id,
            escape_md("✍️ Введите кастомный промпт для генерации:", version=2),
            update_or_query=query,
            parse_mode=ParseMode.MARKDOWN_V2
        )

@generation_router.message(lambda m: m.text and not m.text.startswith('/'))
async def handle_admin_prompt_message(message: Message, state: FSMContext) -> None:
    """Обработка текстовых сообщений для админской генерации"""
    
    admin_id = message.from_user.id
    if admin_id not in ADMIN_IDS:
        return

    data = await state.get_data()
    if data.get('is_admin_generation'):
        await handle_admin_custom_prompt(message, state)