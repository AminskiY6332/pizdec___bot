"""
Обработчики для функции "Фото Преображение"
PixelPie AI Bot - версия для aiogram
"""

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, BufferedInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.enums import ParseMode
import logging
import os
import uuid
from datetime import datetime
import asyncio
import time
from typing import Optional
import io

from generation.photo_transform import PhotoTransformGenerator
from database import check_database_user, update_user_credits, is_user_blocked
from config import ADMIN_IDS
from handlers.utils import escape_message_parts

from logger import get_logger
logger = get_logger('generation')

# Инициализация роутера
photo_transform_router = Router(name='photo_transform')

# Состояния FSM для процесса генерации
class PhotoTransformStates(StatesGroup):
    waiting_for_photo = State()
    choosing_style = State()
    choosing_aspect_ratio = State()
    processing = State()

# Инициализация генератора (должен быть установлен при подключении роутера)
photo_generator: Optional[PhotoTransformGenerator] = None

def init_photo_generator(replicate_api_key: str):
    """Инициализация генератора фото"""
    global photo_generator
    photo_generator = PhotoTransformGenerator(replicate_api_key)

from utils import get_cookie_progress_bar

def get_progress_bar(percent: int) -> str:
    """
    Создает прогресс-бар из печенек

    Args:
        percent: Процент выполнения (0-100)

    Returns:
        Строка с прогресс-баром
    """
    return get_cookie_progress_bar(percent)

async def update_progress(progress_message: Message, state: FSMContext, expected_duration: int = 67):
    """
    Фоновая задача для динамического обновления прогресс-бара.

    Args:
        progress_message: Сообщение для редактирования.
        state: FSMContext для проверки состояния.
        expected_duration: Ожидаемое время в секундах.
    """
    start_time = time.time()
    while True:
        elapsed = time.time() - start_time
        percent = min(int((elapsed / expected_duration) * 100), 99)
        current_state = await state.get_state()
        if current_state != PhotoTransformStates.processing:
            break

        progress_text = (
            f"⏳ Генерация в процессе...\n"
            f"{get_progress_bar(percent)} – Обработка фото нашей нейросетью...\n"
            f"Это займет около 1 минуты. Пожалуйста, подождите 😊"
        )
        try:
            await progress_message.edit_text(
                escape_message_parts(progress_text, version=2),
                parse_mode=ParseMode.MARKDOWN_V2
            )
        except Exception as e:
            logger.debug(f"Не удалось обновить прогресс: {e}")
            break

        await asyncio.sleep(5)

# Обработчик callback для начала преображения
@photo_transform_router.callback_query(F.data == "photo_transform")
async def start_photo_transform(callback: CallbackQuery, state: FSMContext):
    """Начало процесса преображения фото"""
    try:
        await callback.answer()
        user_id = callback.from_user.id

        # Проверка блокировки
        if await is_user_blocked(user_id):
            return

        # Проверка баланса
        user_data = await check_database_user(user_id)
        if not user_data or user_data[0] <= 0:
            await callback.message.answer(
                escape_message_parts("❌ У вас недостаточно печенек для генерации. Пополните баланс!", version=2),
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="💳 Купить пакет", callback_data="subscribe")],
                    [InlineKeyboardButton(text="🔙 Главное меню", callback_data="back_to_menu")]
                ])
            )
            return

        # Очищаем предыдущее состояние
        await state.clear()

        # Обновленное приветственное сообщение
        welcome_text = """🎭 Фото Преображение от PixelPie AI

Превратите ваше селфи в произведение искусства! 🎨

Просто отправьте одно фото, и наша нейросеть создаст уникальный образ в выбранном стиле.

Доступные стили преображения:
▪️ 🤍 Фотошоп Pro — Журнальная ретушь уровня Vogue
▪️ 🎨 AI Art — Цифровое искусство как на Artstation
▪️ 🎬 Кино — Кадр из голливудского блокбастера
▪️ 🖼️ Портрет — Арт-фотография музейного уровня
▪️ ⚡ Киберпанк — Атмосфера Blade Runner 2049
▪️ 🧱 LEGO — Официальная коллекционная фигурка

📸 Отправьте ваше фото для начала!"""

        # Кнопка отмены
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отменить", callback_data="transform_cancel")]
        ])

        await callback.message.answer(
            escape_message_parts(welcome_text, version=2),
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=keyboard
        )

        # Устанавливаем состояние ожидания фото
        await state.set_state(PhotoTransformStates.waiting_for_photo)

    except Exception as e:
        logger.error(f"Ошибка при старте photo transform: {str(e)}")
        await callback.message.answer(
            escape_message_parts("❌ Произошла ошибка. Попробуйте позже.", version=2),
            parse_mode=ParseMode.MARKDOWN_V2
        )

# Обработчик получения фото
@photo_transform_router.message(PhotoTransformStates.waiting_for_photo, F.photo)
async def handle_photo(message: Message, state: FSMContext):
    """Обработка полученного фото"""
    try:
        user_id = message.from_user.id

        # Получаем файл фото
        photo = message.photo[-1]
        file_id = photo.file_id

        # Сохраняем file_id в состоянии
        await state.update_data(photo_file_id=file_id)

        # Показываем выбор стилей
        style_text = """✨ Отлично! Фото получено.

Теперь выберите стиль преображения:"""

        # Получаем клавиатуру со стилями
        keyboard_data = photo_generator.get_style_keyboard()
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=btn["text"], callback_data=btn["callback_data"])
             for btn in row]
            for row in keyboard_data
        ])

        try:
            await message.delete()
            await message.edit_text(
                escape_message_parts(style_text, version=2),
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=keyboard
            )
        except Exception:
            await message.answer(
                escape_message_parts(style_text, version=2),
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=keyboard
            )

        # Переходим к выбору стиля
        await state.set_state(PhotoTransformStates.choosing_style)

    except Exception as e:
        logger.error(f"Ошибка при обработке фото: {str(e)}")
        await message.answer(
            escape_message_parts("❌ Ошибка при обработке фото. Попробуйте еще раз.", version=2),
            parse_mode=ParseMode.MARKDOWN_V2
        )
        await state.clear()

# Обработчик неправильного типа сообщения при ожидании фото
@photo_transform_router.message(PhotoTransformStates.waiting_for_photo)
async def handle_wrong_content(message: Message):
    """Обработка неправильного типа контента"""
    await message.answer(
        escape_message_parts(
            "📸 Пожалуйста, отправьте фото для преображения.\n\n"
            "Поддерживаются только изображения в формате JPG/PNG.",
            version=2
        ),
        parse_mode=ParseMode.MARKDOWN_V2
    )

# Обработчик выбора стиля
@photo_transform_router.callback_query(PhotoTransformStates.choosing_style, F.data.startswith("transform_style:"))
async def handle_style_selection(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора стиля и переход к выбору aspect_ratio"""
    try:
        await callback.answer()
        user_id = callback.from_user.id

        # Получаем выбранный стиль
        style = callback.data.split(":")[1]

        # Сохраняем стиль в состоянии
        await state.update_data(selected_style=style)

        # Показываем описание формата с эмодзи
        aspect_text = photo_generator.get_aspect_ratio_description()

        keyboard_data = photo_generator.get_aspect_ratio_keyboard(style)
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=btn["text"], callback_data=btn["callback_data"])
             for btn in row]
            for row in keyboard_data
        ])

        await callback.message.edit_text(
            escape_message_parts(aspect_text, version=2),
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=keyboard
        )

        # Переходим к выбору aspect_ratio
        await state.set_state(PhotoTransformStates.choosing_aspect_ratio)

    except Exception as e:
        logger.error(f"Ошибка при выборе стиля: {str(e)}")
        await callback.message.edit_text(
            escape_message_parts("❌ Ошибка при выборе стиля. Начните заново.", version=2),
            parse_mode=ParseMode.MARKDOWN_V2
        )
        await state.clear()

# Обработчик выбора aspect_ratio и запуск генерации
@photo_transform_router.callback_query(PhotoTransformStates.choosing_aspect_ratio, F.data.startswith("transform_ratio:"))
async def handle_aspect_ratio_selection(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора соотношения сторон и запуск генерации"""
    try:
        await callback.answer()
        user_id = callback.from_user.id
        bot = callback.bot

        # Получаем данные из callback
        parts = callback.data.split(":")
        style = parts[1]
        aspect_ratio = parts[2]

        # Фиксированное разрешение
        resolution = "720p"

        # Получаем данные из состояния
        data = await state.get_data()
        photo_file_id = data.get("photo_file_id")

        if not photo_file_id:
            await callback.message.edit_text(
                escape_message_parts("❌ Ошибка: фото не найдено. Начните заново.", version=2),
                parse_mode=ParseMode.MARKDOWN_V2
            )
            await state.clear()
            return

        # Показываем описание стиля
        style_description = photo_generator.get_style_description(style)

        await callback.message.edit_text(
            escape_message_parts(style_description, version=2),
            parse_mode=ParseMode.MARKDOWN_V2
        )

        await asyncio.sleep(1)

        # Начало генерации
        start_text = (
            "⏳ Начинаю генерацию...\n"
            "Это Займет Минуту. Пожалуйста, подождите 😊"
        )
        progress_message = await callback.message.answer(
            escape_message_parts(start_text, version=2),
            parse_mode=ParseMode.MARKDOWN_V2
        )

        # Устанавливаем состояние обработки
        await state.set_state(PhotoTransformStates.processing)
        await state.update_data(selected_style=style, selected_aspect_ratio=aspect_ratio, selected_resolution=resolution)

        # Запускаем фоновую задачу прогресса
        progress_task = asyncio.create_task(update_progress(progress_message, state))

        start_time = time.time()

        try:
            # Получаем файл от Telegram
            logger.info(f"Получение файла от Telegram для user_id={user_id}")
            file = await bot.get_file(photo_file_id)

            # Создаем BytesIO объект для загрузки
            file_io = io.BytesIO()

            # Скачиваем файл в BytesIO
            await bot.download_file(file.file_path, destination=file_io)

            # Получаем байты
            file_io.seek(0)
            image_bytes = file_io.read()
            logger.info(f"Размер исходного изображения: {len(image_bytes)} байт")

            # Запускаем генерацию
            logger.info(f"Запуск генерации для пользователя {user_id} в стиле {style}")
            result = await photo_generator.generate_image(
                image_bytes=image_bytes,
                style=style,
                user_id=user_id,
                aspect_ratio=aspect_ratio,
                resolution=resolution
            )

            # Останавливаем прогресс
            progress_task.cancel()
            elapsed_time = time.time() - start_time
            min_sec = f"{int(elapsed_time // 60)} мин {int(elapsed_time % 60)} сек"

            if result["success"]:
                # Обновляем на 100%
                try:
                    await progress_message.edit_text(
                        escape_message_parts(
                            f"🎨 Генерация завершена!\n\n{get_progress_bar(100)}\nЗаняло {min_sec}.",
                            version=2
                        ),
                        parse_mode=ParseMode.MARKDOWN_V2
                    )
                    await asyncio.sleep(1)
                except:
                    pass

                # Скачиваем результат
                result_url = result.get('result_url')
                logger.info(f"URL результата: {result_url}")
                result_image = await photo_generator.download_generated_image(result_url)
                logger.info(f"Изображение скачано, размер: {len(result_image)} байт")

                # Списываем печеньку
                success = await update_user_credits(user_id, "decrement_photo", amount=1)
                logger.info(f"Списание печеньки для user_id={user_id}: {success}")

                # Отправляем результат
                caption = f"""✨ Готово!

Ваше фото в стиле {result['style_name']}

🎨 Сгенерировано с помощью PixelPie AI

Хотите попробовать другой стиль? Отправьте новое фото!"""

                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [
                        InlineKeyboardButton(text="🎭 Новое преображение", callback_data="photo_transform"),
                        InlineKeyboardButton(text="📱 В главное меню", callback_data="back_to_menu")
                    ]
                ])

                photo_input = BufferedInputFile(result_image, filename="transformed.jpg")

                await bot.send_photo(
                    chat_id=user_id,
                    photo=photo_input,
                    caption=escape_message_parts(caption, version=2),
                    parse_mode=ParseMode.MARKDOWN_V2,
                    reply_markup=keyboard
                )

                # Удаляем предыдущие сообщения
                try:
                    await callback.message.delete()
                except:
                    pass
                try:
                    await progress_message.delete()
                except:
                    pass

                logger.info(f"Успешная генерация для пользователя {user_id} в стиле {style}")

            else:
                # Ошибка генерации
                error_text = f"""❌ Ошибка генерации

К сожалению, не удалось создать изображение.
Ошибка: {result.get('error', 'Неизвестная ошибка')}

Печенька возвращена на баланс 🍪
Попробуйте еще раз или выберите другой стиль."""

                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [
                        InlineKeyboardButton(text="🔄 Попробовать снова", callback_data="photo_transform"),
                        InlineKeyboardButton(text="📱 В главное меню", callback_data="back_to_menu")
                    ]
                ])

                await progress_message.edit_text(
                    escape_message_parts(error_text, version=2),
                    parse_mode=ParseMode.MARKDOWN_V2,
                    reply_markup=keyboard
                )

                # Возвращаем печеньку
                success = await update_user_credits(user_id, "increment_photo", amount=1)
                logger.info(f"Возврат печеньки для user_id={user_id}: {success}")

                logger.error(f"Ошибка генерации для пользователя {user_id}: {result.get('error')}")

        except Exception as e:
            logger.error(f"Критическая ошибка при генерации: {str(e)}")

            # Останавливаем прогресс
            if progress_task:
                try:
                    progress_task.cancel()
                except:
                    pass

            # Удаляем сообщение с прогрессом
            if progress_message:
                try:
                    await progress_message.delete()
                except:
                    pass

            # Возвращаем печеньку
            try:
                success = await update_user_credits(user_id, "increment_photo", amount=1)
                logger.info(f"Возврат печеньки после ошибки для user_id={user_id}: {success}")
            except:
                pass

            # Сообщение об ошибке
            await callback.message.edit_text(
                escape_message_parts(
                    "❌ Произошла ошибка при генерации.\n\n"
                    "Печенька возвращена на баланс 🍪\n"
                    "Пожалуйста, попробуйте позже.",
                    version=2
                ),
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [
                        InlineKeyboardButton(text="🔄 Попробовать снова", callback_data="photo_transform"),
                        InlineKeyboardButton(text="📱 В главное меню", callback_data="back_to_menu")
                    ]
                ])
            )

        # Очищаем состояние
        await state.clear()

    except Exception as e:
        logger.error(f"Общая ошибка в handle_aspect_ratio_selection: {str(e)}")

        # Останавливаем прогресс если есть
        if 'progress_task' in locals() and progress_task:
            try:
                progress_task.cancel()
            except:
                pass

        # Удаляем сообщение прогресса если есть
        if 'progress_message' in locals() and progress_message:
            try:
                await progress_message.delete()
            except:
                pass

        # Возвращаем печеньку
        try:
            await update_user_credits(user_id, "increment_photo", amount=1)
            logger.info(f"Возврат печеньки после общей ошибки для user_id={user_id}")
        except:
            pass

        try:
            await callback.message.edit_text(
                escape_message_parts("❌ Произошла ошибка при генерации. Печенька возвращена 🍪", version=2),
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="📱 В главное меню", callback_data="back_to_menu")]
                ])
            )
        except:
            await callback.message.answer(
                escape_message_parts("❌ Произошла ошибка при генерации. Печенька возвращена 🍪", version=2),
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="📱 В главное меню", callback_data="back_to_menu")]
                ])
            )

        await state.clear()

# Обработчик отмены
@photo_transform_router.callback_query(F.data == "transform_cancel")
async def handle_cancel(callback: CallbackQuery, state: FSMContext):
    """Обработка отмены операции"""
    await callback.answer("Операция отменена")
    await callback.message.edit_text(
        escape_message_parts(
            "❌ Операция отменена.\n\n"
            "Вы можете начать заново, нажав на кнопку «🎭 Фото Преображение» в главном меню.",
            version=2
        ),
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📱 В главное меню", callback_data="back_to_menu")]
        ])
    )
    await state.clear()

# Экспорт роутера
__all__ = ['photo_transform_router', 'init_photo_generator']
