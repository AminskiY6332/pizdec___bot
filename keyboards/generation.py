# keyboards/generation.py
"""
Клавиатуры для генерации контента (фото, видео, аватары)
"""

import logging
from typing import Optional
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from generation_config import NEW_MALE_AVATAR_STYLES, NEW_FEMALE_AVATAR_STYLES

from logger import get_logger
logger = get_logger('keyboards')

# Расширенные соотношения сторон
ASPECT_RATIOS = {
    "1:1": {
        "display": "1:1 📱 Квадрат",
        "description": "Идеально для Instagram постов и аватаров",
        "width": 1024,
        "height": 1024
    },
    "16:9": {
        "display": "16:9 🖥️ Широкоформатный",
        "description": "Стандарт для YouTube и презентаций",
        "width": 1920,
        "height": 1080
    },
    "4:3": {
        "display": "4:3 📺 Классический",
        "description": "Традиционный формат для фотографий",
        "width": 1024,
        "height": 768
    },
    "5:4": {
        "display": "5:4 🖼️ Альбомный",
        "description": "Отлично для печати фотографий",
        "width": 1280,
        "height": 1024
    },
    "9:16": {
        "display": "9:16 📲 Stories",
        "description": "Для Instagram Stories и TikTok",
        "width": 1080,
        "height": 1920
    },
    "9:21": {
        "display": "9:21 📱 Ультра-вертикальный",
        "description": "Для длинных вертикальных изображений",
        "width": 1080,
        "height": 2520
    },
    "3:4": {
        "display": "3:4 👤 Портретный",
        "description": "Классический портретный формат",
        "width": 768,
        "height": 1024
    },
    "4:5": {
        "display": "4:5 📖 Книжный",
        "description": "Популярный в Instagram для фото",
        "width": 1080,
        "height": 1350
    },
    "21:9": {
        "display": "21:9 🎬 Кинематографический",
        "description": "Широкий кинематографический формат",
        "width": 2560,
        "height": 1097
    },
    "2:3": {
        "display": "2:3 📷 Фото",
        "description": "Стандартный фотографический формат",
        "width": 1024,
        "height": 1536
    },
    "1.1:1": {
        "display": "1.1:1 📐 Слегка горизонтальный",
        "description": "Почти квадрат с небольшим уклоном",
        "width": 1126,
        "height": 1024
    }
}

async def create_style_selection_keyboard(generation_type: str = 'with_avatar') -> InlineKeyboardMarkup:
    """Создаёт клавиатуру выбора стиля для генерации."""
    try:
        prefix = 'admin_style' if generation_type == 'admin_with_user_avatar' else 'style'
        keyboard = [
            [
                InlineKeyboardButton(text="👤 Портрет", callback_data=f"{prefix}_portrait"),
                InlineKeyboardButton(text="😊 Повседневное", callback_data=f"{prefix}_casual")
            ],
            [
                InlineKeyboardButton(text="🎨 Художественное", callback_data=f"{prefix}_artistic"),
                InlineKeyboardButton(text="💼 Деловое", callback_data=f"{prefix}_business")
            ],
            [
                InlineKeyboardButton(text="🌅 На природе", callback_data=f"{prefix}_outdoor"),
                InlineKeyboardButton(text="🏠 В интерьере", callback_data=f"{prefix}_indoor")
            ],
            [
                InlineKeyboardButton(text="✏️ Свой промпт", callback_data=f"{prefix}_custom")
            ],
            [
                InlineKeyboardButton(
                    text="🔙 Назад",
                    callback_data="back_to_generation_menu" if generation_type != 'admin_with_user_avatar' else "admin_users_list"
                )
            ]
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)
    except Exception as e:
        logger.error(f"Ошибка в create_style_selection_keyboard: {e}", exc_info=True)
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Ошибка, вернуться в меню", callback_data="back_to_menu")]
        ])

async def create_aspect_ratio_keyboard(back_callback: str = "back_to_style_selection") -> InlineKeyboardMarkup:
    """Создаёт клавиатуру выбора соотношения сторон."""
    try:
        logger.debug(f"Создание клавиатуры соотношений сторон с back_callback={back_callback}")
        keyboard = []

        square_ratios = ["1:1"]
        landscape_ratios = ["16:9", "21:9", "4:3", "5:4"]
        portrait_ratios = ["9:16", "9:21", "3:4", "4:5", "2:3"]

        keyboard.append([InlineKeyboardButton(text="📐 КВАДРАТНЫЕ ФОРМАТЫ", callback_data="category_info")])
        for ratio in square_ratios:
            if ratio in ASPECT_RATIOS:
                display = f"{ratio} 📱 {'Квадрат' if ratio == 'square' else 'Квадратный'}"
                keyboard.append([InlineKeyboardButton(text=display, callback_data=f"aspect_{ratio}")])

        keyboard.append([InlineKeyboardButton(text="🖥️ ГОРИЗОНТАЛЬНЫЕ ФОРМАТЫ", callback_data="category_info")])
        row = []
        for ratio in landscape_ratios:
            if ratio in ASPECT_RATIOS:
                display = f"{ratio} 🖥️ {'Альбом' if ratio == 'landscape' else 'Горизонтальный'}"
                row.append(InlineKeyboardButton(text=display, callback_data=f"aspect_{ratio}"))
                if len(row) == 2:
                    keyboard.append(row)
                    row = []
        if row:
            keyboard.append(row)

        keyboard.append([InlineKeyboardButton(text="📱 ВЕРТИКАЛЬНЫЕ ФОРМАТЫ", callback_data="category_info")])
        row = []
        for ratio in portrait_ratios:
            if ratio in ASPECT_RATIOS:
                display = f"{ratio} 📲 {'Портрет' if ratio == 'portrait' else 'Вертикальный'}"
                row.append(InlineKeyboardButton(text=display, callback_data=f"aspect_{ratio}"))
                if len(row) == 2:
                    keyboard.append(row)
                    row = []
        if row:
            keyboard.append(row)

        keyboard.extend([
            [InlineKeyboardButton(text="ℹ️ Информация о форматах", callback_data="aspect_ratio_info")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data=back_callback)],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_menu")]
        ])

        logger.debug(f"Клавиатура соотношений сторон создана успешно: {len(keyboard)} строк")
        return InlineKeyboardMarkup(inline_keyboard=keyboard)
    except Exception as e:
        logger.error(f"Ошибка в create_aspect_ratio_keyboard: {e}", exc_info=True)
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Ошибка, вернуться в меню", callback_data="back_to_menu")]
        ])

async def create_avatar_style_choice_keyboard() -> InlineKeyboardMarkup:
    """Создаёт клавиатуру выбора пола для аватара."""
    try:
        keyboard = [
            [
                InlineKeyboardButton(text="👨 Мужчина", callback_data="select_new_male_avatar_styles"),
                InlineKeyboardButton(text="👩 Женщина", callback_data="select_new_female_avatar_styles")
            ],
            [InlineKeyboardButton(text="🔙 В меню генерации", callback_data="generate_menu")]
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)
    except Exception as e:
        logger.error(f"Ошибка в create_avatar_style_choice_keyboard: {e}", exc_info=True)
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Ошибка, вернуться в меню", callback_data="back_to_menu")]
        ])

async def create_new_male_avatar_styles_keyboard(page: int = 1) -> InlineKeyboardMarkup:
    """Создаёт клавиатуру стилей для мужских аватаров с пагинацией."""
    try:
        keyboard = []
        row = []

        styles_per_page = 20
        total_styles = len(NEW_MALE_AVATAR_STYLES)
        total_pages = (total_styles + styles_per_page - 1) // styles_per_page

        page = max(1, min(page, total_pages))

        start_idx = (page - 1) * styles_per_page
        end_idx = min(start_idx + styles_per_page, total_styles)

        styles_items = list(NEW_MALE_AVATAR_STYLES.items())
        styles_to_show = styles_items[start_idx:end_idx]

        for style_key, style_name in styles_to_show:
            row.append(InlineKeyboardButton(text=style_name, callback_data=f"style_new_male_{style_key}"))
            if len(row) == 2:
                keyboard.append(row)
                row = []

        if row:
            keyboard.append(row)

        nav_row = []
        if total_pages > 1:
            if page > 1:
                nav_row.append(InlineKeyboardButton(text="⏮ Первая", callback_data="male_styles_page_1"))
                nav_row.append(InlineKeyboardButton(text="◀️", callback_data=f"male_styles_page_{page-1}"))

            nav_row.append(InlineKeyboardButton(text=f"📄 {page}/{total_pages}", callback_data="page_info"))

            if page < total_pages:
                nav_row.append(InlineKeyboardButton(text="▶️", callback_data=f"male_styles_page_{page+1}"))
                nav_row.append(InlineKeyboardButton(text="⏭ Последняя", callback_data=f"male_styles_page_{total_pages}"))

        if nav_row:
            keyboard.append(nav_row)

        keyboard.extend([
            [InlineKeyboardButton(text="🤖 Свой промпт (Помощник AI)", callback_data="enter_custom_prompt_llama")],
            [InlineKeyboardButton(text="✍️ Свой промпт (вручную)", callback_data="enter_custom_prompt_manual")],
            [InlineKeyboardButton(text="🔙 Выбор категории", callback_data="generate_with_avatar")]
        ])

        return InlineKeyboardMarkup(inline_keyboard=keyboard)
    except Exception as e:
        logger.error(f"Ошибка в create_new_male_avatar_styles_keyboard: {e}", exc_info=True)
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Ошибка, вернуться в меню", callback_data="back_to_menu")]
        ])

async def create_new_female_avatar_styles_keyboard(page: int = 1) -> InlineKeyboardMarkup:
    """Создаёт клавиатуру стилей для женских аватаров с пагинацией."""
    try:
        keyboard = []
        row = []

        styles_per_page = 20
        total_styles = len(NEW_FEMALE_AVATAR_STYLES)
        total_pages = (total_styles + styles_per_page - 1) // styles_per_page

        page = max(1, min(page, total_pages))

        start_idx = (page - 1) * styles_per_page
        end_idx = min(start_idx + styles_per_page, total_styles)

        styles_items = list(NEW_FEMALE_AVATAR_STYLES.items())
        styles_to_show = styles_items[start_idx:end_idx]

        for style_key, style_name in styles_to_show:
            row.append(InlineKeyboardButton(text=style_name, callback_data=f"style_new_female_{style_key}"))
            if len(row) == 2:
                keyboard.append(row)
                row = []

        if row:
            keyboard.append(row)

        nav_row = []
        if total_pages > 1:
            if page > 1:
                nav_row.append(InlineKeyboardButton(text="⏮ Первая", callback_data="female_styles_page_1"))
                nav_row.append(InlineKeyboardButton(text="◀️", callback_data=f"female_styles_page_{page-1}"))

            nav_row.append(InlineKeyboardButton(text=f"📄 {page}/{total_pages}", callback_data="page_info"))

            if page < total_pages:
                nav_row.append(InlineKeyboardButton(text="▶️", callback_data=f"female_styles_page_{page+1}"))
                nav_row.append(InlineKeyboardButton(text="⏭ Последняя", callback_data=f"female_styles_page_{total_pages}"))

        if nav_row:
            keyboard.append(nav_row)

        keyboard.extend([
            [InlineKeyboardButton(text="🤖 Свой промпт (Помощник AI)", callback_data="enter_custom_prompt_llama")],
            [InlineKeyboardButton(text="✍️ Свой промпт (вручную)", callback_data="enter_custom_prompt_manual")],
            [InlineKeyboardButton(text="🔙 Выбор категории", callback_data="generate_with_avatar")]
        ])

        return InlineKeyboardMarkup(inline_keyboard=keyboard)
    except Exception as e:
        logger.error(f"Ошибка в create_new_female_avatar_styles_keyboard: {e}", exc_info=True)
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Ошибка, вернуться в меню", callback_data="back_to_menu")]
        ])

async def create_video_styles_keyboard() -> InlineKeyboardMarkup:
    """Создаёт клавиатуру выбора стилей для видеогенерации."""
    try:
        video_styles = [
            ("dynamic_action", "🏃‍♂️ Динамичное действие"),
            ("slow_motion", "🐢 Замедленное движение"),
            ("cinematic_pan", "🎥 Кинематографический панорамный вид"),
            ("facial_expression", "😊 Выразительная мимика"),
            ("object_movement", "⏳ Движение объекта"),
            ("dance_sequence", "💃 Танцевальная последовательность"),
            ("nature_flow", "🌊 Естественное течение"),
            ("urban_vibe", "🏙 Городская атмосфера"),
            ("fantasy_motion", "✨ Фантастическое движение"),
            ("retro_wave", "📼 Ретро-волна")
        ]

        keyboard = []
        row = []
        for style_key, style_name in video_styles:
            row.append(InlineKeyboardButton(text=style_name, callback_data=f"video_style_{style_key}"))
            if len(row) == 2:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)

        keyboard.extend([
            [InlineKeyboardButton(text="✍️ Свой промпт (вручную)", callback_data="enter_custom_prompt_manual")],
            [InlineKeyboardButton(text="🤖 Свой промпт (Помощник AI)", callback_data="enter_custom_prompt_llama")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="video_generate_menu")]
        ])

        return InlineKeyboardMarkup(inline_keyboard=keyboard)
    except Exception as e:
        logger.error(f"Ошибка в create_video_styles_keyboard: {e}", exc_info=True)
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Ошибка, вернуться в меню", callback_data="back_to_menu")]
        ])

async def create_prompt_selection_keyboard(
    back_callback_data: str = "back_to_menu",
    style_source_dict: Optional[dict] = None,
    style_prefix: str = "style_"
) -> InlineKeyboardMarkup:
    """Создаёт клавиатуру выбора промптов."""
    try:
        keyboard = []
        row = []

        if not style_source_dict:
            style_source_dict = {**NEW_MALE_AVATAR_STYLES, **NEW_FEMALE_AVATAR_STYLES}

        if not style_source_dict:
            keyboard.append([InlineKeyboardButton(text="⚠️ Стили не настроены", callback_data="no_styles_configured")])
        else:
            styles_to_show = list(style_source_dict.items())

            for style_key, style_name in styles_to_show:
                row.append(InlineKeyboardButton(text=style_name, callback_data=f"{style_prefix}{style_key}"))
                if len(row) == 2:
                    keyboard.append(row)
                    row = []

            if row:
                keyboard.append(row)

        keyboard.extend([
            [InlineKeyboardButton(text="✍️ Свой промпт (вручную)", callback_data="enter_custom_prompt_manual")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data=back_callback_data)]
        ])

        return InlineKeyboardMarkup(inline_keyboard=keyboard)
    except Exception as e:
        logger.error(f"Ошибка в create_prompt_selection_keyboard: {e}", exc_info=True)
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Ошибка, вернуться в меню", callback_data="back_to_menu")]
        ])

async def create_generation_in_progress_keyboard() -> InlineKeyboardMarkup:
    """Создаёт клавиатуру для процесса генерации."""
    try:
        keyboard = [
            [InlineKeyboardButton(text="⏸ Отмена (в меню)", callback_data="back_to_menu")]
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)
    except Exception as e:
        logger.error(f"Ошибка в create_generation_in_progress_keyboard: {e}", exc_info=True)
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Ошибка, вернуться в меню", callback_data="back_to_menu")]
        ]) 