# generation/images.py
from aiogram.exceptions import TelegramForbiddenError
import re
import aiohttp
import aiofiles
import uuid
import os
import logging
import time
import asyncio
import random
from typing import Optional, List, Dict, Tuple
from aiogram import Bot
from aiogram.types import Message, InputMediaPhoto, InlineKeyboardButton, InlineKeyboardMarkup, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest
import tenacity
import replicate
from replicate.exceptions import ReplicateError
from deep_translator import GoogleTranslator
from copy import deepcopy

from redis_caсhe import RedisActiveModelCache, RedisGenParamsCache, RedisUserCooldown
from config import REDIS

redis = REDIS
redis_user_cooldown = RedisUserCooldown(redis, cooldown_seconds=3)
redis_active_model_cache = RedisActiveModelCache(redis)
redis_gen_params_cache = RedisGenParamsCache(redis)


from generation_config import (
    IMAGE_GENERATION_MODELS, ASPECT_RATIOS,
    GENERATION_TYPE_TO_MODEL_KEY, MULTI_LORA_MODEL, HF_LORA_MODELS, LORA_CONFIG, LORA_PRIORITIES,
    LORA_STYLE_PRESETS, MAX_LORA_COUNT, USER_AVATAR_LORA_STRENGTH,
    CAMERA_SETUP_BASE, LUXURY_DETAILS_BASE, get_real_lora_model
)
from config import MAX_FILE_SIZE_BYTES, REPLICATE_API_TOKEN, REPLICATE_USERNAME_OR_ORG_NAME, ADMIN_IDS
from database import (
    check_database_user, update_user_credits, get_active_trainedmodel, log_generation, check_user_resources
)
from keyboards import (
    create_main_menu_keyboard, create_rating_keyboard,
    create_subscription_keyboard, create_user_profile_keyboard, create_photo_generate_menu_keyboard
)
from generation.utils import (
    TempFileManager, reset_generation_context,
    send_message_with_fallback, send_photo_with_retry, send_media_group_with_retry
)
from llama_helper import generate_assisted_prompt
from handlers.utils import clean_admin_context, safe_escape_markdown as escape_md

user_last_generation_lock = asyncio.Lock()

logger = logging.getLogger(__name__)

# СТАНДАРТНЫЕ ЛИМИТЫ
MAX_CONCURRENT_GENERATIONS = 80
REPLICATE_RATE_LIMIT = 40
USER_GENERATION_COOLDOWN = 3

# Семафоры для различных операций
generation_semaphore = asyncio.Semaphore(MAX_CONCURRENT_GENERATIONS)
replicate_semaphore = asyncio.Semaphore(REPLICATE_RATE_LIMIT)
download_semaphore = asyncio.Semaphore(80)
file_operation_semaphore = asyncio.Semaphore(150)

# Кэши для оптимизации
cache_lock = asyncio.Lock()
user_generation_lock = {}

# Очередь генераций
generation_queue = asyncio.Queue(maxsize=800)
queue_processor_running = False

# СУПЕР КОНФИГУРАЦИЯ (ИЗ 22 ПРОФ МОДЕЛЕЙ)
BASIC_LORA_CONFIG = {
    "base_realism": {
        "model": "prithivMLmods/Flux-Realism-FineDetailed",
        "strength": 0.85,
        "keywords": ["realistic", "detailed", "photographic"],
        "description": "Основа реализма"
    },
    "face_master": {
        "model": "prithivMLmods/Canopus-LoRA-Flux-FaceRealism",
        "strength": 0.8,
        "keywords": ["face", "portrait", "eyes"],
        "description": "Детализация лиц"
    },
    "skin_texture": {
        "model": "prithivMLmods/Flux-Skin-Real",
        "strength": 0.9,
        "keywords": ["skin", "texture", "pores"],
        "description": "Текстура кожи"
    },
    "style_enhance": {
        "model": "alvdansen/frosting_lane_flux",
        "strength": 0.75,
        "keywords": ["style", "professional", "photography"],
        "description": "Стиль и освещение"
    },
    "fashion_people": {
        "model": "prithivMLmods/Fashion-Hut-Modeling-LoRA",
        "strength": 0.7,
        "keywords": ["fashion", "people", "clothing"],
        "description": "Мода и люди"
    }
}

# БАЗОВЫЕ ПРЕСЕТЫ
BASIC_PRESETS = {
    "default": {
        "loras": ["base_realism", "style_enhance"],
        "guidance_scale": 2.5,
        "num_inference_steps": 30,
        "prompt_additions": "professional photography, high quality, detailed, natural lighting"
    },
    "portrait": {
        "loras": ["face_master", "skin_texture", "base_realism"],
        "guidance_scale": 2.6,
        "num_inference_steps": 22,
        "prompt_additions": "portrait photography, professional lighting, sharp focus, natural skin"
    },
    "fashion": {
        "loras": ["fashion_people", "style_enhance", "base_realism"],
        "guidance_scale": 2.4,
        "num_inference_steps": 28,
        "prompt_additions": "fashion photography, magazine quality, professional style"
    }
}

# БАЗОВЫЙ NEGATIVE PROMPT
BASIC_NEGATIVE_PROMPT = (
    "low quality, bad quality, worst quality, blurry, pixelated, noisy, distorted, "
    "deformed, mutated, ugly, bad anatomy, bad proportions, extra limbs, missing limbs, "
    "bad hands, extra fingers, missing fingers, bad face, distorted face, "
    "watermark, text, logo, signature, username, artist name, "
    "3d render, cartoon, anime, sketch, drawing, painting, artistic, illustration, "
    "cgi, fake, artificial, plastic skin, doll skin, unrealistic"
)

async def process_prompt_async(original_prompt: str, model_key: str, generation_type: str,
                             trigger_word: str = None, selected_gender: str = None,
                             user_input: str = None, user_data: Dict = None,
                             use_new_flux: bool = False) -> str:
    """Обрабатывает промпт с учетом пользовательского ввода и переводит его на английский."""

    logger.info(f"Обработка промпта: original_prompt='{original_prompt[:50]}...', user_input='{user_input[:50] if user_input else None}...', "
                f"generation_type={generation_type}, trigger_word={trigger_word}, selected_gender={selected_gender}")

    # Проверяем, нужно ли использовать Llama
    use_llama = user_data.get('use_llama_prompt', False)

    # Если есть пользовательский ввод и это кастомный промпт, используем его
    if user_data.get('came_from_custom_prompt') and user_input:
        base_prompt = user_input
        logger.debug(f"Используется пользовательский промпт: {base_prompt[:50]}...")
    else:
        base_prompt = original_prompt
        logger.debug(f"Используется исходный промпт: {base_prompt[:50]}...")

    # === ИСПОЛЬЗОВАНИЕ LLAMA ДЛЯ УЛУЧШЕНИЯ ПРОМПТА ===
    if use_llama and user_input:
        logger.info("🤖 Используем Llama для улучшения промпта")
        try:
            # Определяем пол для Llama
            llama_gender = 'person'  # По умолчанию
            if selected_gender:
                if selected_gender.lower() in ['man', 'male']:
                    llama_gender = 'man'
                elif selected_gender.lower() in ['woman', 'female']:
                    llama_gender = 'woman'

            # Вызываем асинхронную функцию улучшения промпта
            enhanced_prompt = await generate_assisted_prompt(
                user_query=user_input,
                gender=llama_gender,
                max_length_chars=1000,
                generation_type=generation_type
            )

            if enhanced_prompt and enhanced_prompt != user_input:
                base_prompt = enhanced_prompt
                logger.info(f"✨ Llama улучшила промпт: {base_prompt[:100]}...")
                # Сохраняем улучшенный промпт для последующего использования
                if user_data:
                    await user_data.update({'llama_enhanced_prompt': enhanced_prompt})
            else:
                logger.warning("Llama не смогла улучшить промпт, используем оригинальный")
        except Exception as e:
            logger.error(f"Ошибка при вызове Llama: {e}")
            # Продолжаем с оригинальным промптом

    # Обработка для photo_to_photo
    if generation_type == 'photo_to_photo':
        if use_new_flux and trigger_word:
            base = f"{trigger_word}, copy style from reference image"
            if base_prompt and base_prompt != "copy reference style":
                base += f", {base_prompt}"
            return base + ", natural skin texture, realistic, photographic quality"
        elif trigger_word:
            return f"{trigger_word}, copy style from reference, natural realistic photo"
        else:
            return "copy reference image style, natural realistic photo, authentic"

    # Формируем финальный промпт
    parts = []
    if trigger_word:
        parts.append(trigger_word)

    # Добавляем усилители фотореализма
    if not user_data.get('came_from_custom_prompt') and not use_llama:
        photorealistic_enhancers = [
            "professional photography",
            "photorealistic",
            "real person",
            "natural skin texture with visible pores",
            "realistic skin tone",
            "authentic human features",
            "not CGI",
            "not 3D render",
            "DSLR camera quality",
            "natural expression",
            "genuine emotion",
            "sharp focus",
            "high resolution"
        ]
        parts.extend(photorealistic_enhancers)

    if selected_gender:
        parts.append(selected_gender)

    parts.append(base_prompt)

    # Добавляем anti_cgi_details только если НЕ использовали Llama
    if not user_data.get('came_from_custom_prompt') and not use_llama:
        anti_cgi_details = (
            "shot with professional DSLR camera, natural daylight, "
            "real human skin with natural imperfections, "
            "unretouched authentic photography, photojournalism style, "
            "natural hair texture, realistic eye moisture, "
            "genuine facial expression, candid moment, "
            "no artificial enhancement, no beauty filters, "
            "raw unprocessed photo quality"
        )
        parts.append(anti_cgi_details)

    full_prompt = ", ".join(parts)
    full_prompt = re.sub(r'\s+', ' ', full_prompt).strip()

    # Проверяем наличие русского текста и переводим
    if re.search('[а-яА-Я]', full_prompt):
        try:
            loop = asyncio.get_event_loop()
            translator = GoogleTranslator(source='auto', target='en')
            # Выполняем перевод в отдельном потоке
            translated_prompt = await loop.run_in_executor(
                None,
                translator.translate,
                full_prompt[:4500]
            )
            if translated_prompt:
                full_prompt = translated_prompt
                logger.info(f"Промпт переведен на английский: {full_prompt[:50]}...")
            else:
                logger.warning(f"Перевод не удался, используется исходный промпт: {full_prompt[:50]}...")
        except Exception as e:
            logger.error(f"Ошибка перевода промпта: {e}")
            logger.info(f"Используется исходный промпт без перевода: {full_prompt[:50]}...")

    # Ограничиваем длину промпта
    if len(full_prompt) > 4000:
        full_prompt = full_prompt[:4000].rsplit(', ', 1)[0]
        logger.warning(f"Промпт обрезан до 4000 символов: {full_prompt[:50]}...")

    return full_prompt

async def prepare_model_params(use_new_flux: bool, model_key: str, generation_type: str,
                             prompt: str, num_outputs: int, aspect_ratio: str,
                             width: int, height: int, user_data: Dict) -> Optional[dict]:
    """Подготавливает параметры модели."""
    logger.info(f"Подготовка параметров модели (22 модели основных)")

    reference_image_url = user_data.get('reference_image_url')

    if use_new_flux:
        params = {
            "prompt": prompt,
            "model": "dev",
            "go_fast": True,
            "lora_scale": 0.98,
            "megapixels": "1",
            "num_outputs": num_outputs,
            "aspect_ratio": aspect_ratio,
            "output_format": "png",
            "guidance_scale": 4.5,
            "output_quality": 100,
            "prompt_strength": 0.91,
            "num_inference_steps": 38
        }
        if generation_type == 'photo_to_photo' and reference_image_url:
            params["image"] = reference_image_url
            params["prompt_strength"] = 0.75
    else:
        # Параметры для LoRA
        params = {
            "prompt": prompt,
            "num_outputs": num_outputs,
            "aspect_ratio": aspect_ratio,
            "lora_scale": 0.98,
            "output_format": "png",
            "guidance_scale": 4.5,
            "width": width,
            "height": height,
            "scheduler": "DDIM",
            "prompt_strength": 0.85,
            "output_quality": 100,
            "num_inference_steps": 40
        }

        # Выбираем базовый пресет
        prompt_lower = prompt.lower()
        if any(word in prompt_lower for word in ["face", "portrait", "person", "лицо", "портрет"]):
            selected_preset = "portrait"
        elif any(word in prompt_lower for word in ["fashion", "style", "dress", "outfit", "мода"]):
            selected_preset = "fashion"
        else:
            selected_preset = "default"

        preset = BASIC_PRESETS.get(selected_preset, BASIC_PRESETS["default"])
        params["guidance_scale"] = preset["guidance_scale"]
        params["num_inference_steps"] = preset["num_inference_steps"]

        # Добавляем дополнения
        if not user_data.get('came_from_custom_prompt'):
            params["prompt"] = f"{prompt}, {preset['prompt_additions']}"

        # Добавляем модели
        lora_index = 3

        # Добавляем аватар пользователя если нужно
        if generation_type in ['with_avatar', 'photo_to_photo']:
            trigger_word = user_data.get('trigger_word')
            old_model_id = user_data.get('old_model_id')
            old_model_version = user_data.get('old_model_version')
            if trigger_word and old_model_version:
                if old_model_id:
                    if '/' not in old_model_id:
                        avatar_lora = f"{REPLICATE_USERNAME_OR_ORG_NAME}/{old_model_id}:{old_model_version}"
                    else:
                        avatar_lora = f"{old_model_id}:{old_model_version}"
                    params[f"hf_lora_{lora_index}"] = avatar_lora
                    params[f"lora_scale_{lora_index}"] = USER_AVATAR_LORA_STRENGTH
                    lora_index += 1
                    logger.info(f"Добавлен пользовательский аватар (LoRA #{lora_index-1})")

        # Добавляем базовые LoRA
        if not user_data.get('came_from_custom_prompt'):
            for lora_name in preset.get("loras", []):
                if lora_index <= MAX_LORA_COUNT:
                    # Получаем реальную модель из 5 базовых
                    lora_cfg = get_real_lora_model(lora_name)
                    if lora_cfg and "model" in lora_cfg:
                        params[f"hf_lora_{lora_index}"] = lora_cfg["model"]
                        params[f"lora_scale_{lora_index}"] = lora_cfg["strength"]
                        logger.info(f"Добавлена модель {lora_name} (LoRA #{lora_index})")
                        lora_index += 1

        params["negative_prompt"] = BASIC_NEGATIVE_PROMPT

        if generation_type == 'photo_to_photo' and reference_image_url:
            params["image"] = reference_image_url
            params["strength"] = 0.75

        logger.info(f"=== ПАРАМЕТРЫ ГЕНЕРАЦИИ ===")
        logger.info(f"Используется {lora_index - 1} моделей из 22 доступных")
        logger.info(f"Preset: {selected_preset}")
        logger.info(f"Guidance Scale: {params['guidance_scale']}")
        logger.info(f"Inference Steps: {params['num_inference_steps']}")

    return params

async def start_queue_processor():
    """Запускает обработчик очереди генераций"""
    global queue_processor_running
    if not queue_processor_running:
        queue_processor_running = True
        for i in range(15):
            asyncio.create_task(process_generation_queue(i))
        logger.info("Запущены обработчики очереди генераций")

async def process_generation_queue(worker_id: int):
    """Обработчик очереди генераций"""
    while True:
        try:
            task = await generation_queue.get()
            if task is None:
                break
            message, state, num_outputs = task
            try:
                await _generate_image_internal(message, state, num_outputs)
            except Exception as e:
                logger.error(f"Worker {worker_id}: Ошибка обработки генерации: {e}", exc_info=True)
            finally:
                generation_queue.task_done()
        except Exception as e:
            logger.error(f"Worker {worker_id}: Критическая ошибка в обработчике очереди: {e}", exc_info=True)
            await asyncio.sleep(1)

async def get_user_generation_lock(user_id: int):
    """Получает или создает блокировку для пользователя"""
    if user_id not in user_generation_lock:
        user_generation_lock[user_id] = asyncio.Lock()
    return user_generation_lock[user_id]

async def check_user_cooldown(user_id: int) -> bool:
    if await redis_user_cooldown.is_on_cooldown(user_id):
        return False
    await redis_user_cooldown.set_cooldown(user_id)
    return True


async def get_active_model_cached(user_id: int):
    """Получает активную модель пользователя с кэшированием через Redis"""
    if redis_active_model_cache is not None:
        try:
            cached = await redis_active_model_cache.get(user_id)
            if cached:
                return cached
        except Exception as e:
            logger.warning(f"Ошибка получения кеша для user_id={user_id}: {e}")

    model_data = await get_active_trainedmodel(user_id)

    if redis_active_model_cache is not None:
        try:
            await redis_active_model_cache.set(user_id, model_data)
        except Exception as e:
            logger.warning(f"Ошибка сохранения кеша для user_id={user_id}: {e}")

    return model_data

async def clear_avatar_cache(user_id: int) -> None:
    """Принудительно очищает кэш аватаров для пользователя в Redis"""
    if redis_active_model_cache is not None:
        try:
            await redis_active_model_cache.set(user_id, None)
            logger.info(f"Redis-кэш аватаров очищен для user_id={user_id}")
        except Exception as e:
            logger.warning(f"Ошибка очистки кеша для user_id={user_id}: {e}")
    else:
        logger.debug(f"Кеш недоступен для user_id={user_id}")


async def download_image_async(session: aiohttp.ClientSession, url: str, filepath: str, retry_count: int = 3) -> Optional[str]:
    """Асинхронная загрузка изображения"""
    async with download_semaphore:
        for attempt in range(retry_count):
            try:
                timeout = aiohttp.ClientTimeout(total=30)
                async with session.get(url, timeout=timeout) as response:
                    if response.status == 200:
                        os.makedirs(os.path.dirname(filepath), exist_ok=True)
                        async with aiofiles.open(filepath, 'wb') as f:
                            async for chunk in response.content.iter_chunked(8192):
                                await f.write(chunk)
                        logger.debug(f"Успешно загружен файл: {filepath}")
                        return filepath
                    else:
                        logger.warning(f"HTTP {response.status} при загрузке {url}")
            except asyncio.TimeoutError:
                logger.warning(f"Таймаут загрузки {url}, попытка {attempt + 1}/{retry_count}")
            except Exception as e:
                logger.error(f"Ошибка загрузки {url}: {e}")

            if attempt < retry_count - 1:
                await asyncio.sleep(1 * (attempt + 1))

        return None

async def download_images_parallel(urls: List[str], user_id: int) -> List[str]:
    """Параллельная загрузка изображений"""
    paths = []
    tasks = []

    connector = aiohttp.TCPConnector(limit=15, limit_per_host=8)
    timeout = aiohttp.ClientTimeout(total=60)

    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        for i, url in enumerate(urls):
            filepath = f"generated/{user_id}_{uuid.uuid4().hex[:8]}_{i}.png"
            task = download_image_async(session, url, filepath)
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, str) and result:
                paths.append(result)
            elif isinstance(result, Exception):
                logger.error(f"Ошибка загрузки: {result}")

    return paths

async def generate_image(message: Message, state: FSMContext, num_outputs: int = 2, user_id: int = None) -> None:
    """Основная функция генерации изображения с 22 моделями"""
    user_data = await state.get_data()
    bot = message.bot
    bot_id = (await bot.get_me()).id
    user_id = user_id or message.from_user.id

    logger.info(f"=== ГЕНЕРАЦИЯ НАЧАЛАСЬ (22 модели) ===")
    logger.info(f"Инициатор: {user_id}")

    is_admin_generation = user_data.get('is_admin_generation', False)
    admin_generation_for_user = user_data.get('admin_generation_for_user')
    admin_user_id = user_data.get('original_admin_user', user_id)

    if is_admin_generation and admin_generation_for_user and user_id in ADMIN_IDS:
        message_recipient = admin_user_id
        target_user_id = admin_generation_for_user
        if target_user_id == bot_id:
            logger.error(f"Некорректный target_user_id: {target_user_id}")
            await send_message_with_fallback(
                bot, admin_user_id,
                escape_md("❌ Ошибка: неверный ID пользователя для генерации.", version=2),
                reply_markup=await create_main_menu_keyboard(admin_user_id),
                parse_mode=ParseMode.MARKDOWN_V2
            )
            return
        logger.info(f"АДМИНСКАЯ ГЕНЕРАЦИЯ: админ={message_recipient}, цель={target_user_id}")
        # Проверяем и обновляем данные аватара для целевого пользователя
        trained_model_data = await get_active_model_cached(target_user_id)
        if trained_model_data and trained_model_data[3] == 'success':
            await state.update_data(
                trigger_word=trained_model_data[5],
                model_version=trained_model_data[2],
                old_model_id=trained_model_data[4],
                old_model_version=trained_model_data[0],
                active_avatar_name=trained_model_data[8]
            )
    else:
        message_recipient = user_id
        target_user_id = user_id
        logger.info(f"ОБЫЧНАЯ ГЕНЕРАЦИЯ: пользователь={target_user_id}")
        # Сбрасываем админские поля
        admin_fields = [
            'is_admin_generation', 'admin_generation_for_user',
            'admin_target_user_id', 'giving_sub_to_user',
            'broadcast_type', 'awaiting_broadcast_message',
            'awaiting_search_query', 'admin_view_source'
        ]
        await state.update_data({field: None for field in admin_fields})

    # Проверка необходимых данных
    required_fields = ['prompt', 'aspect_ratio', 'generation_type', 'model_key']
    missing_fields = [field for field in required_fields if not user_data.get(field)]

    if missing_fields:
        logger.error(f"Отсутствуют поля: {missing_fields}")
        await send_message_with_fallback(
            bot, message_recipient,
            f"⚠️ Не хватает данных: {', '.join(missing_fields)}. Начни заново через /menu.",
            reply_markup=await create_main_menu_keyboard(message_recipient),
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    await start_queue_processor()

    if not await check_user_cooldown(message_recipient):
        await send_message_with_fallback(
            bot, message_recipient,
            "⏳ Подожди пару секунд перед следующей генерацией!",
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    generation_type = user_data.get('generation_type')
    if generation_type == 'with_avatar':
        required_photos = num_outputs
    elif generation_type == 'photo_to_photo':
        required_photos = 2
    else:
        required_photos = 1

    if not is_admin_generation:
        logger.info(f"Проверка ресурсов для user_id={target_user_id}, требуется фото: {required_photos}")
        if not await check_user_resources(bot, target_user_id, required_photos=required_photos):
            return

    if generation_queue.full():
        await send_message_with_fallback(
            bot, message_recipient,
            "😔 Сервер перегружен! Попробуй через минуту.",
            reply_markup=await create_main_menu_keyboard(message_recipient),
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    try:
        generation_data = deepcopy({
            'prompt': user_data.get('prompt'),
            'aspect_ratio': user_data.get('aspect_ratio'),
            'generation_type': user_data.get('generation_type'),
            'model_key': user_data.get('model_key'),
            'selected_gender': user_data.get('selected_gender'),
            'user_input_for_llama': user_data.get('user_input_for_llama'),
            'trigger_word': user_data.get('trigger_word'),
            'model_version': user_data.get('model_version'),
            'old_model_id': user_data.get('old_model_id'),
            'old_model_version': user_data.get('old_model_version'),
            'reference_image_url': user_data.get('reference_image_url'),
            'photo_path': user_data.get('photo_path'),
            'message_recipient': message_recipient,
            'generation_target_user': target_user_id,
            'original_admin_user': admin_user_id,
            'is_admin_generation': is_admin_generation,
            'admin_generation_for_user': admin_generation_for_user,
            'photos_to_deduct': required_photos if not is_admin_generation else 0,
            'current_style_set': user_data.get('current_style_set'),
            'came_from_custom_prompt': user_data.get('came_from_custom_prompt', False),
            'use_llama_prompt': user_data.get('use_llama_prompt', False),
            'last_generation_params': user_data.get('last_generation_params'),
            'active_avatar_name': user_data.get('active_avatar_name')
        })

        await state.update_data(generation_data)
        await generation_queue.put((message, state, num_outputs))

        queue_size = generation_queue.qsize()
        if queue_size > 10:
            if is_admin_generation:
                message_text = f"📊 Запрос генерации для пользователя {target_user_id} добавлен в очередь (позиция: ~{queue_size})."
            else:
                message_text = f"📊 Твой запрос добавлен в очередь (позиция: ~{queue_size}). Ожидай уведомления!"
            await send_message_with_fallback(
                bot, message_recipient,
                message_text,
                parse_mode=ParseMode.MARKDOWN_V2
            )

        logger.info(f"✅ Генерация добавлена в очередь: recipient={message_recipient}, target={target_user_id}")

    except asyncio.QueueFull:
        logger.error(f"Очередь переполнена для user_id={message_recipient}")
        await send_message_with_fallback(
            bot, message_recipient,
            "😔 Не удалось добавить в очередь. Попробуй ещё раз!",
            reply_markup=await create_main_menu_keyboard(message_recipient),
            parse_mode=ParseMode.MARKDOWN_V2
        )
    except Exception as e:
        logger.error(f"Непредвиденная ошибка в generate_image: {e}", exc_info=True)
        await send_message_with_fallback(
            bot, message_recipient,
            "❌ Произошла непредвиденная ошибка. Попробуйте позже.",
            reply_markup=await create_main_menu_keyboard(message_recipient),
            parse_mode=ParseMode.MARKDOWN_V2
        )

async def _generate_image_internal(message: Message, state: FSMContext, num_outputs: int = 2) -> None:
    """Внутренняя функция генерации изображения (оптимизированная версия с 5 базовыми моделями)"""
    from handlers.generation import handle_admin_generation_result

    async with asyncio.Lock():
        user_data = await state.get_data()
        message_recipient = user_data.get('message_recipient', message.from_user.id)
        target_user_id = user_data.get('generation_target_user', message.from_user.id)
        admin_user_id = user_data.get('original_admin_user', message.from_user.id)
        is_admin_generation = user_data.get('is_admin_generation', False)
        bot = message.bot
        bot_id = (await bot.get_me()).id

        preserved_data = {}

        if message_recipient == bot_id or target_user_id == bot_id:
            logger.error(f"Некорректный ID получателя или цели")
            return

        logger.info(f"=== ВНУТРЕННЯЯ ГЕНЕРАЦИЯ (22 модели) ===")
        logger.info(f"message_recipient={message_recipient}, target_user_id={target_user_id}")

        start_time = time.time()
        user_lock = await get_user_generation_lock(target_user_id)

        async with user_lock:
            async with generation_semaphore:
                logger.info(f"🎯 Генерация для user_id={target_user_id} с использованием оптимизированной системы")

                subscription_data = await check_database_user(target_user_id)
                if not isinstance(subscription_data, tuple) or len(subscription_data) < 9:
                    logger.error(f"Недостаточно данных подписки для user_id={target_user_id}")
                    await send_message_with_fallback(
                        bot, message_recipient,
                        escape_md("❌ Ошибка сервера! Попробуй /menu.", version=2),
                        reply_markup=await create_main_menu_keyboard(message_recipient),
                        parse_mode=ParseMode.MARKDOWN_V2
                    )
                    return

                generation_type = user_data.get('generation_type')
                prompt = user_data.get('prompt')
                aspect_ratio_key = user_data.get('aspect_ratio')
                model_key = user_data.get('model_key')
                style_name = user_data.get('style_name', 'Кастомный стиль')

                # Проверка критических данных
                missing_critical = []
                if not generation_type:
                    missing_critical.append('generation_type')
                if not prompt:
                    missing_critical.append('prompt')
                if not aspect_ratio_key:
                    missing_critical.append('aspect_ratio')
                if not model_key:
                    missing_critical.append('model_key')

                if missing_critical:
                    logger.error(f"Отсутствуют ключевые данные: {missing_critical}")
                    await send_message_with_fallback(
                        bot, message_recipient,
                        escape_md("⚠️ Критическая ошибка данных. Начни заново через /menu.", version=2),
                        reply_markup=await create_main_menu_keyboard(message_recipient),
                        parse_mode=ParseMode.MARKDOWN_V2
                    )
                    return

                # Проверка аватара для соответствующих типов генерации
                if generation_type in ['with_avatar', 'photo_to_photo']:
                    trained_model_data = await get_active_model_cached(target_user_id)
                    if not trained_model_data or trained_model_data[3] != 'success':
                        logger.error(f"Нет активного аватара для target_user_id={target_user_id}")
                        await send_message_with_fallback(
                            bot, message_recipient,
                            escape_md("❌ Активный аватар не готов! Создай его в Личном кабинете.", version=2),
                            reply_markup=await create_user_profile_keyboard(message_recipient, bot),
                            parse_mode=ParseMode.MARKDOWN_V2
                        )
                        await reset_generation_context(state, generation_type)
                        return

                required_photos = user_data.get('photos_to_deduct', num_outputs)

                if not is_admin_generation:
                    logger.info(f"Списание ресурсов для user_id={target_user_id}, требуется фото: {required_photos}")
                    await update_user_credits(target_user_id, "decrement_photo", amount=required_photos)

                selected_gender = user_data.get('selected_gender')
                user_input_for_helper = user_data.get('user_input_for_llama')

                # Обновление данных аватара
                if generation_type in ['with_avatar', 'photo_to_photo']:
                    trained_model_data = await get_active_model_cached(target_user_id)
                    if trained_model_data and trained_model_data[3] == 'success':
                        await state.update_data(
                            trigger_word=trained_model_data[5],
                            model_version=trained_model_data[2],
                            old_model_id=trained_model_data[4],
                            old_model_version=trained_model_data[0],
                            active_avatar_name=trained_model_data[8]
                        )

                # Сохраняем параметры генерации
                generation_params = {
                    'prompt': prompt,
                    'aspect_ratio': aspect_ratio_key,
                    'generation_type': generation_type,
                    'model_key': model_key,
                    'selected_gender': selected_gender,
                    'user_input_for_llama': user_input_for_helper,
                    'style_name': style_name,
                    'current_style_set': user_data.get('current_style_set'),
                    'came_from_custom_prompt': user_data.get('came_from_custom_prompt', False),
                    'use_llama_prompt': user_data.get('use_llama_prompt', False),
                    'duration': 0.0
                }

                preserved_data['last_generation_params'] = generation_params

                if model_key not in IMAGE_GENERATION_MODELS:
                    logger.error(f"Неверный model_key: {model_key}")
                    await send_message_with_fallback(
                        bot, message_recipient,
                        escape_md("❌ Ошибка конфигурации модели!", version=2),
                        reply_markup=await create_main_menu_keyboard(message_recipient),
                        parse_mode=ParseMode.MARKDOWN_V2
                    )
                    await reset_generation_context(state, generation_type)
                    return

                model_config = IMAGE_GENERATION_MODELS[model_key]
                replicate_model_id_to_run = model_config['id']
                trigger_word = user_data.get('trigger_word')
                use_new_flux_method = False

                # Определение модели для генерации с аватаром
                if generation_type in ['with_avatar', 'photo_to_photo']:
                    trained_model_data = await get_active_model_cached(target_user_id)
                    if not trained_model_data or trained_model_data[3] != 'success':
                        logger.error(f"КРИТИЧЕСКАЯ ОШИБКА: аватар не готов после проверки!")
                        await send_message_with_fallback(
                            bot, message_recipient,
                            escape_md("❌ Критическая ошибка: аватар не готов!", version=2),
                            reply_markup=await create_user_profile_keyboard(message_recipient, bot),
                            parse_mode=ParseMode.MARKDOWN_V2
                        )
                        await reset_generation_context(state, generation_type)
                        return

                    avatar_id, model_id, model_version, status, prediction_id, trigger_word, photo_paths, training_step, avatar_name = trained_model_data
                    await state.update_data(trigger_word=trigger_word, model_version=model_version, active_avatar_name=avatar_name)

                    is_fast_flux = is_new_fast_flux_model(model_id, model_version)
                    if is_fast_flux:
                        use_new_flux_method = True
                        if model_version:
                            if '/' not in model_id:
                                replicate_model_id_to_run = f"{REPLICATE_USERNAME_OR_ORG_NAME}/{model_id}:{model_version}"
                            else:
                                replicate_model_id_to_run = f"{model_id}:{model_version}"
                        else:
                            if '/' not in model_id:
                                replicate_model_id_to_run = f"{REPLICATE_USERNAME_OR_ORG_NAME}/{model_id}"
                            else:
                                replicate_model_id_to_run = model_id
                        logger.info(f"Using Fast Flux model: {replicate_model_id_to_run}")
                    else:
                        use_new_flux_method = False
                        replicate_model_id_to_run = MULTI_LORA_MODEL
                        logger.info(f"Using Multi-LoRA model (Модели): {replicate_model_id_to_run}")
                        await state.update_data(old_model_id=model_id, old_model_version=model_version)

                generation_message = await send_message_with_fallback(
                    bot, message_recipient,
                    escape_md(f"📸 Создаю {num_outputs} фото с помощью профессиональных ИИ моделей! Подготовка...", version=2),
                    parse_mode=ParseMode.MARKDOWN_V2
                )

                try:
                    user_data = await state.get_data()
                    processed_prompt = await process_prompt_async(
                        prompt, model_key, generation_type,
                        trigger_word, selected_gender, user_input_for_helper, user_data,
                        use_new_flux=use_new_flux_method
                    )

                    width, height = ASPECT_RATIOS.get(aspect_ratio_key, (1024, 1024))

                    input_params = await prepare_model_params(
                        use_new_flux_method, model_key, generation_type,
                        processed_prompt, num_outputs, aspect_ratio_key,
                        width, height, user_data
                    )

                    if input_params is None:
                        if isinstance(generation_message, Message):
                            await generation_message.delete()
                        await send_message_with_fallback(
                            bot, message_recipient,
                            escape_md("❌ Ошибка подготовки параметров!", version=2),
                            reply_markup=await create_main_menu_keyboard(message_recipient),
                            parse_mode=ParseMode.MARKDOWN_V2
                        )
                        await reset_generation_context(state, generation_type)
                        return

                    # Определяем стиль для логирования
                    style_name = user_data.get('style_name', 'custom')
                    if user_data.get('came_from_custom_prompt', False):
                        if user_data.get('use_llama_prompt', False):
                            style_for_log = "промпт+ИИ"
                        else:
                            style_for_log = "промпт"
                    else:
                        style_for_log = style_name

                    # Логируем генерацию с style и ratio
                    from database import log_user_action_with_style_ratio
                    await log_user_action_with_style_ratio(
                        user_id=target_user_id,
                        action="generate_image",
                        details={
                            'generation_type': generation_type,
                            'model_id': replicate_model_id_to_run,
                            'units': num_outputs,
                            'prompt': user_data.get('prompt', '')[:100]  # Ограничиваем длину промпта
                        },
                        style=style_for_log,
                        ratio=aspect_ratio_key
                    )

                    await log_generation(
                        target_user_id,
                        generation_type,
                        replicate_model_id_to_run,
                        num_outputs,
                        style=style_for_log,
                        ratio=aspect_ratio_key
                    )

                    if isinstance(generation_message, Message):
                        await generation_message.edit_text(
                            escape_md(
                                f"🎯 Генерирую ваши фото с помощью PixelPie_AI.\n"
                                f"📸 Используется иновационная ИИ нейросеть!\n"
                                f"⚡ PixelPie_AI создает ваш шедевр!", version=2
                            ),
                            parse_mode=ParseMode.MARKDOWN_V2
                        )

                    async with replicate_semaphore:
                        image_urls = await run_replicate_model_async(replicate_model_id_to_run, input_params)

                    if not image_urls:
                        logger.error("Пустой результат от Replicate")
                        if isinstance(generation_message, Message):
                            await generation_message.edit_text(
                                escape_md("❌ Ошибка генерации! Попробуй снова.", version=2),
                                reply_markup=await create_main_menu_keyboard(message_recipient),
                                parse_mode=ParseMode.MARKDOWN_V2
                            )
                        await reset_generation_context(state, generation_type)
                        return

                    if isinstance(generation_message, Message):
                        await generation_message.edit_text(
                            escape_md("✅ Готово! Загружаю результаты...", version=2),
                            parse_mode=ParseMode.MARKDOWN_V2
                        )

                    image_paths = await download_images_parallel(image_urls, target_user_id)

                    if not image_paths:
                        logger.error("Не удалось загрузить изображения")
                        if isinstance(generation_message, Message):
                            await generation_message.edit_text(
                                escape_md("❌ Ошибка загрузки! Печеньки возвращены.", version=2),
                                reply_markup=await create_main_menu_keyboard(message_recipient),
                                parse_mode=ParseMode.MARKDOWN_V2
                            )
                        if not is_admin_generation:
                            await update_user_credits(target_user_id, "increment_photo", amount=required_photos)
                        await reset_generation_context(state, generation_type)
                        return

                    duration = time.time() - start_time

                    try:
                        if isinstance(generation_message, Message):
                            await generation_message.delete()
                    except:
                        pass

                    # Обновляем параметры
                    generation_params.update({'image_urls': image_urls, 'duration': duration})
                    preserved_data.update({
                        'last_generation_params': generation_params,
                    })

                    if is_admin_generation:
                        preserved_data.update({
                            'is_admin_generation': True,
                            'admin_generation_for_user': target_user_id,
                            'message_recipient': admin_user_id,
                            'generation_target_user': target_user_id,
                            'original_admin_user': admin_user_id
                        })

                    # Сохраняем параметры перед очисткой контекста
                    await state.update_data(**preserved_data)

                    # Обработка результата
                    if is_admin_generation:
                        result_data = {
                            'success': True,
                            'image_urls': image_urls,
                            'prompt': processed_prompt,
                            'style': user_data.get('style_name', 'custom')
                        }
                        await handle_admin_generation_result(state, admin_user_id, target_user_id, result_data, bot)
                    else:
                        await send_generation_results(
                            bot, message_recipient, target_user_id, image_paths, duration, aspect_ratio_key,
                            generation_type, model_key, state, admin_user_id if is_admin_generation else None
                        )

                    logger.info(f"🎯 PixelPie_AI генерация завершена для user_id={target_user_id}: "
                               f"{len(image_paths)} фото за {duration:.1f} сек (22 модели)")

                    asyncio.create_task(cleanup_files(image_paths + [user_data.get('photo_path')]))

                except Exception as e:
                    logger.error(f"Ошибка генерации для user_id={target_user_id}: {e}", exc_info=True)
                    error_message = escape_md("❌ Ошибка! Печеньки возвращены на баланс.", version=2)
                    if isinstance(generation_message, Message):
                        try:
                            await generation_message.edit_text(
                                error_message,
                                reply_markup=await create_main_menu_keyboard(message_recipient),
                                parse_mode=ParseMode.MARKDOWN_V2
                            )
                        except:
                            await send_message_with_fallback(
                                bot, message_recipient,
                                error_message,
                                reply_markup=await create_main_menu_keyboard(message_recipient),
                                parse_mode=ParseMode.MARKDOWN_V2
                            )
                    if not is_admin_generation:
                        await update_user_credits(target_user_id, "increment_photo", amount=required_photos)
                    await reset_generation_context(state, generation_type)
                finally:
                    if preserved_data:
                        await state.update_data(**preserved_data)
                    await clean_admin_context(state)
                    logger.info("Админский контекст очищен после генерации")

async def send_generation_results(bot: Bot, message_recipient: int, target_user_id: int,
                                image_paths: List[str], duration: float, aspect_ratio: str,
                                generation_type: str, model_key: str, state: FSMContext,
                                admin_user_id: int = None) -> None:
    """Отправляет результаты генерации пользователю"""
    user_data = await state.get_data()
    state_value = user_data.get('state')

    try:
        if len(image_paths) == 1:
            caption = escape_md(f"📸 Ваша ИИ генерация фотографии готова! Время: {duration:.1f} сек", version=2)
            photo_file = FSInputFile(path=image_paths[0])
            await send_photo_with_retry(
                bot, message_recipient, photo_file, caption=caption,
                reply_markup=await create_rating_keyboard(generation_type, model_key, message_recipient, bot),
                parse_mode=ParseMode.MARKDOWN_V2
            )
            if admin_user_id and admin_user_id != message_recipient:
                await bot.send_photo(
                    chat_id=admin_user_id,
                    photo=photo_file,
                    caption=escape_md(f"Фото для ID {target_user_id}", version=2),
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                        InlineKeyboardButton(text="🔙 К действиям", callback_data=f"user_actions_{target_user_id}")
                    ]]),
                    parse_mode=ParseMode.MARKDOWN_V2
                )
        else:
            caption = escape_md(
                f"📸 {len(image_paths)} Ваших фотографий созданы! ({duration:.1f} сек)\n"
                f"🎯 Сделано при помощи PixelPie_AI", version=2
            )
            media = []
            for i, path in enumerate(image_paths):
                photo_file = FSInputFile(path=path)
                if i == 0:
                    media.append(InputMediaPhoto(media=photo_file, caption=caption, parse_mode=ParseMode.MARKDOWN_V2))
                else:
                    media.append(InputMediaPhoto(media=photo_file))

            await send_media_group_with_retry(bot, message_recipient, media)
            await send_message_with_fallback(
                bot, message_recipient,
                escape_md("⭐ Оцени результат ИИ фотогенерации:", version=2),
                reply_markup=await create_rating_keyboard(generation_type, model_key, message_recipient, bot),
                parse_mode=ParseMode.MARKDOWN_V2
            )

            if admin_user_id and admin_user_id != message_recipient:
                await send_media_group_with_retry(bot, admin_user_id, media)
                await bot.send_message(
                    chat_id=admin_user_id,
                    text=escape_md(f"Фото для пользователя {target_user_id} готовы", version=2),
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                        InlineKeyboardButton(text="🔙 К действиям", callback_data=f"user_actions_{target_user_id}")
                    ]]),
                    parse_mode=ParseMode.MARKDOWN_V2
                )

        await state.clear()
        if state_value:
            await state.update_data(state=state_value)

        logger.info(f"Результаты генерации отправлены для user_id={message_recipient}")

    except Exception as e:
        logger.error(f"Ошибка в send_generation_results: {e}", exc_info=True)
        await send_message_with_fallback(
            bot, message_recipient,
            escape_md("❌ Ошибка при отправке результатов. Попробуйте снова или обратитесь в поддержку: @AXIDI_Help", version=2),
            reply_markup=await create_main_menu_keyboard(message_recipient),
            parse_mode=ParseMode.MARKDOWN_V2
        )

async def cleanup_files(filepaths: List[Optional[str]]):
    """Асинхронное удаление временных файлов"""
    for filepath in filepaths:
        if filepath and os.path.exists(filepath):
            try:
                async with file_operation_semaphore:
                    await asyncio.get_event_loop().run_in_executor(None, os.remove, filepath)
                logger.debug(f"Удален файл: {filepath}")
            except Exception as e:
                logger.error(f"Ошибка удаления {filepath}: {e}")

async def run_replicate_model_async(model_id: str, input_params: dict) -> List[str]:
    """Асинхронный запуск модели Replicate"""
    @tenacity.retry(
        wait=tenacity.wait_exponential(multiplier=1, min=2, max=10),
        stop=tenacity.stop_after_attempt(3),
        retry=tenacity.retry_if_exception_type(ReplicateError),
        reraise=True
    )
    async def _run():
        loop = asyncio.get_event_loop()
        replicate_client = replicate.Client(api_token=REPLICATE_API_TOKEN)
        logger.info(f"🚀 Запуск ультра-реалистичной модели {model_id}")
        logger.debug(f"📸 Параметры: {input_params}")

        output = await loop.run_in_executor(
            None,
            lambda: replicate_client.run(model_id, input=input_params)
        )

        image_urls = []
        if isinstance(output, list):
            for item in output:
                if isinstance(item, str):
                    image_urls.append(item)
                elif hasattr(item, 'url'):
                    image_urls.append(item.url)

        logger.info(f"Получены URL изображений: {image_urls}")
        return image_urls

    return await _run()

async def upload_image_to_replicate(photo_path: str) -> str:
    """Загружает изображение возвращает URL"""
    async with replicate_semaphore:
        loop = asyncio.get_event_loop()

        if not os.path.exists(photo_path):
            raise FileNotFoundError(f"Файл не найден: {photo_path}")

        file_size = os.path.getsize(photo_path)
        if file_size > MAX_FILE_SIZE_BYTES:
            raise ValueError(f"Файл слишком большой: {file_size / 1024 / 1024:.2f} MB")

        replicate_client = replicate.Client(api_token=REPLICATE_API_TOKEN)

        def upload_sync():
            with open(photo_path, 'rb') as f:
                return replicate_client.files.create(file=f)

        file_response = await loop.run_in_executor(None, upload_sync)
        image_url = file_response.urls.get('get')

        if not image_url:
            raise ValueError("Replicate не вернул URL")

        logger.info(f"Изображение загружено: {image_url}")
        return image_url

def is_new_fast_flux_model(model_id: str, model_version: str = None) -> bool:
    """Проверяет, является ли модель новой быстрой Flux моделью"""
    if model_id and ("fastnew" in model_id.lower() or "fast-flux" in model_id.lower()):
        return True
    if model_version and len(model_version) == 64 and all(c in '0123456789abcdef' for c in model_version.lower()):
        return True
    if model_id and REPLICATE_USERNAME_OR_ORG_NAME and model_id.startswith(f"{REPLICATE_USERNAME_OR_ORG_NAME}/"):
        return True
    return False

# для совместимости
process_prompt = process_prompt_async
upload_image_to_replicate = upload_image_to_replicate

# Список "22 профессиональных моделей"
PROFESSIONAL_MODELS_LIST = [
    "Flux-Realism-FineDetailed", "Flux-Super-Realism-LoRA", "Flux-RealismLora",
    "Flux-Ultra-Realism", "flux-dev-photorealism", "Canopus-LoRA-Flux-FaceRealism",
    "Flux-Super-Portrait-LoRA", "Flux-Portrait-LoRA", "Flux-Perfect-Face",
    "Flux-Skin-Real", "Flux-BetterSkin-LoRA", "Flux-Natural-Skin-Texture",
    "frosting_lane_flux", "colorgrading", "flux-professional-lighting",
    "flux-professional-photography", "Fashion-Hut-Modeling-LoRA",
    "Flux-Realistic-People", "Flux-Hyperrealistic-Portrait",
    "Flux-NSFW-uncensored", "Flux-Dev-Real-Anime", "flux-lora-the-explorer"
]

logger.info("🎯 СИСТЕМА ГЕНЕРАЦИИ ЗАГРУЖЕНА!")
logger.info("📸 22 профессиональные модели активированы")
logger.info("🚀 Оптимизированная архитектура на базе 5 основных ядер")
logger.info("⚡ Готов к созданию изображений!")
