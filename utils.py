# utils.py
import logging
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

def clear_user_data(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Очищает данные FSM из context.user_data."""
    context.user_data.pop('awaiting_broadcast_message', None)
    context.user_data.pop('awaiting_broadcast_media_confirm', None)
    context.user_data.pop('awaiting_broadcast_schedule', None)
    context.user_data.pop('broadcast_type', None)
    context.user_data.pop('broadcast_message', None)
    context.user_data.pop('broadcast_media', None)
    context.user_data.pop('awaiting_payments_date', None)
    context.user_data.pop('awaiting_user_search', None)
    context.user_data.pop('awaiting_balance_change', None)
    context.user_data.pop('target_user_id', None)
    context.user_data.pop('awaiting_activity_dates', None)
    context.user_data.pop('awaiting_block_reason', None)
    context.user_data.pop('block_action', None)
    context.user_data.pop('awaiting_admin_prompt', None)
    logger.debug("FSM состояния очищены из context.user_data")

def get_cookie_progress_bar(percent: int) -> str:
    """
    Создает универсальный прогресс-бар из печенек и кружочков

    Args:
        percent: Процент выполнения (0-100)

    Returns:
        Строка с прогресс-баром
    """
    total_cookies = 10
    filled = int(percent / 10)
    empty = total_cookies - filled

    bar = "🍪" * filled + "⚪" * empty
    return f"{bar} {percent}%"
