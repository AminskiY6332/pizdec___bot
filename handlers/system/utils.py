from aiogram import Router
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.enums import ParseMode
from config import ADMIN_IDS
from handlers.utils import safe_escape_markdown as escape_md
from database import is_user_blocked
from keyboards import create_main_menu_keyboard, create_admin_keyboard
from logger import get_logger

logger = get_logger('main')

# Создание роутера для утилитарных callback'ов
utils_callbacks_router = Router()

async def handle_utils_callback(query: CallbackQuery, state: FSMContext) -> None:
    """Обрабатывает общие и вспомогательные callback-запросы."""
    user_id = query.from_user.id
    await query.answer()

    if await is_user_blocked(user_id):
        logger.info(f"Заблокированный пользователь user_id={user_id} пытался выполнить callback: {query.data}")
        return

    callback_data = query.data
    logger.info(f"Callback от user_id={user_id}: {callback_data}")

    try:
        if callback_data == "back_to_menu":
            await handle_back_to_menu_callback(query, state, user_id)
        elif callback_data == "support":
            await handle_support_callback(query, state, user_id)
        elif callback_data == "faq":
            await handle_faq_callback(query, state, user_id)
        elif callback_data.startswith("faq_"):
            topic = callback_data.replace("faq_", "")
            await handle_faq_topic_callback(query, state, user_id, topic)
        elif callback_data == "help":
            from handlers.commands import help_command
            await help_command(query.message, state)
        elif callback_data == "user_guide":
            await handle_user_guide_callback(query, state, user_id)
        elif callback_data == "share_result":
            await handle_share_result_callback(query, state, user_id)
        elif callback_data == "payment_history":
            await handle_payment_history_callback(query, state, user_id)
        elif callback_data == "category_info":
            await handle_category_info_callback(query, state, user_id)
        elif callback_data == "compare_tariffs":
            await handle_compare_tariffs_callback(query, state, user_id)
        elif callback_data == "aspect_ratio_info":
            await handle_aspect_ratio_info_callback(query, state, user_id)
        elif callback_data == "check_training":
            from handlers.commands import check_training
            await check_training(query.message, state, user_id)
        else:
            logger.error(f"Неизвестный callback_data: {callback_data} для user_id={user_id}")
            await query.message.answer(
                escape_md("❌ Неизвестное действие. Попробуйте снова или обратитесь в поддержку.", version=2),
                reply_markup=await create_main_menu_keyboard(user_id),
                parse_mode=ParseMode.MARKDOWN_V2
            )

    except Exception as e:
        logger.error(f"Ошибка в обработчике callback для user_id={user_id}, data={callback_data}: {e}", exc_info=True)
        await query.message.answer(
            escape_md("❌ Произошла ошибка. Попробуйте снова или обратитесь в поддержку.", version=2),
            reply_markup=await create_main_menu_keyboard(user_id),
            parse_mode=ParseMode.MARKDOWN_V2
        )

# TODO: Добавить остальные функции из callbacks_utils.py
async def handle_back_to_menu_callback(query: CallbackQuery, state: FSMContext, user_id: int) -> None:
    """Возврат в главное меню. TODO: Перенести полную реализацию"""
    logger.warning(f"handle_back_to_menu_callback не реализован для user_id={user_id}")
    await query.message.answer(
        escape_md("⚠️ Функция временно недоступна. Используйте /menu", version=2),
        parse_mode=ParseMode.MARKDOWN_V2
    )

async def handle_support_callback(query: CallbackQuery, state: FSMContext, user_id: int) -> None:
    """Поддержка. TODO: Перенести полную реализацию"""
    logger.warning(f"handle_support_callback не реализован для user_id={user_id}")
    await query.message.answer(
        escape_md("⚠️ Поддержка временно недоступна", version=2),
        parse_mode=ParseMode.MARKDOWN_V2
    )

async def handle_faq_callback(query: CallbackQuery, state: FSMContext, user_id: int) -> None:
    """Частые вопросы. TODO: Перенести полную реализацию"""
    logger.warning(f"handle_faq_callback не реализован для user_id={user_id}")
    await query.message.answer(
        escape_md("⚠️ FAQ временно недоступен", version=2),
        parse_mode=ParseMode.MARKDOWN_V2
    )

async def handle_faq_topic_callback(query: CallbackQuery, state: FSMContext, user_id: int, topic: str) -> None:
    """Обработчик конкретной темы FAQ. TODO: Перенести полную реализацию"""
    logger.warning(f"handle_faq_topic_callback не реализован для user_id={user_id}, topic={topic}")
    await query.message.answer(
        escape_md("⚠️ FAQ тема временно недоступна", version=2),
        parse_mode=ParseMode.MARKDOWN_V2
    )

async def handle_user_guide_callback(query: CallbackQuery, state: FSMContext, user_id: int) -> None:
    """Руководство пользователя. TODO: Перенести полную реализацию"""
    logger.warning(f"handle_user_guide_callback не реализован для user_id={user_id}")
    await query.message.answer(
        escape_md("⚠️ Руководство временно недоступно", version=2),
        parse_mode=ParseMode.MARKDOWN_V2
    )

async def handle_share_result_callback(query: CallbackQuery, state: FSMContext, user_id: int) -> None:
    """Поделиться результатом. TODO: Перенести полную реализацию"""
    logger.warning(f"handle_share_result_callback не реализован для user_id={user_id}")
    await query.message.answer(
        escape_md("⚠️ Функция 'Поделиться' временно недоступна", version=2),
        parse_mode=ParseMode.MARKDOWN_V2
    )

async def handle_payment_history_callback(query: CallbackQuery, state: FSMContext, user_id: int) -> None:
    """История платежей. TODO: Перенести полную реализацию"""
    logger.warning(f"handle_payment_history_callback не реализован для user_id={user_id}")
    await query.message.answer(
        escape_md("⚠️ История платежей временно недоступна", version=2),
        parse_mode=ParseMode.MARKDOWN_V2
    )

async def handle_category_info_callback(query: CallbackQuery, state: FSMContext, user_id: int) -> None:
    """Информация о категориях. TODO: Перенести полную реализацию"""
    logger.warning(f"handle_category_info_callback не реализован для user_id={user_id}")
    await query.message.answer(
        escape_md("⚠️ Информация о категориях временно недоступна", version=2),
        parse_mode=ParseMode.MARKDOWN_V2
    )

async def handle_compare_tariffs_callback(query: CallbackQuery, state: FSMContext, user_id: int) -> None:
    """Сравнение тарифов. TODO: Перенести полную реализацию"""
    logger.warning(f"handle_compare_tariffs_callback не реализован для user_id={user_id}")
    await query.message.answer(
        escape_md("⚠️ Сравнение тарифов временно недоступно", version=2),
        parse_mode=ParseMode.MARKDOWN_V2
    )

async def handle_aspect_ratio_info_callback(query: CallbackQuery, state: FSMContext, user_id: int) -> None:
    """Информация о соотношениях сторон. TODO: Перенести полную реализацию"""
    logger.warning(f"handle_aspect_ratio_info_callback не реализован для user_id={user_id}")
    await query.message.answer(
        escape_md("⚠️ Информация о соотношениях временно недоступна", version=2),
        parse_mode=ParseMode.MARKDOWN_V2
    )

async def cancel(message: Message, state: FSMContext) -> None:
    """Отменяет все активные действия и сбрасывает контекст."""
    user_id = message.from_user.id
    await state.clear()
    text = escape_md("✅ Все действия отменены.", version=2)
    reply_markup = await create_admin_keyboard() if user_id in ADMIN_IDS else await create_main_menu_keyboard(user_id)
    await message.answer(
        text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN_V2
    )
    logger.debug("Действия отменены для user_id=%s", user_id)

# Регистрация обработчиков
@utils_callbacks_router.callback_query(
    lambda c: c.data in [
        "back_to_menu", "support", "faq", "help", "user_guide", "share_result",
        "payment_history", "category_info", "compare_tariffs",
        "aspect_ratio_info", "check_training"
    ] or c.data.startswith("faq_")
)
async def utils_callback_handler(query: CallbackQuery, state: FSMContext) -> None:
    await handle_utils_callback(query, state)