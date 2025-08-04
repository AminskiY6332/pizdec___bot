from logger import get_logger
logger = get_logger('errors')

async def error_handler(error: Exception) -> None:
    """Логирует ошибки, вызванные обновлениями."""
    logger.error(msg="Exception while handling an update:", exc_info=error)

    # В aiogram 3.x мы не можем получить update из error_handler
    # Поэтому просто логируем ошибку без отправки сообщения пользователю
    logger.error(f"Ошибка в боте: {error}")