import logging
import logging.handlers
import os
from datetime import datetime
from typing import Optional
import sys

# Создаем папку logs если её нет
if not os.path.exists('logs'):
    os.makedirs('logs')

class TelegramBlockedFilter(logging.Filter):
    """Фильтр для исключения логов о блокировке бота пользователем"""

    def filter(self, record):
        # Исключаем логи о блокировке бота
        blocked_keywords = [
            'bot was blocked by the user',
            'bot was stopped by the user',
            'Forbidden: bot was blocked by the user',
            'bot was blocked',
            'user blocked the bot',
            'Forbidden: bot was stopped by the user'
        ]

        message = record.getMessage().lower()
        for keyword in blocked_keywords:
            if keyword.lower() in message:
                return False
        return True

def setup_logger(name: str, log_file: str, level: int = logging.INFO,
                max_bytes: int = 10*1024*1024, backup_count: int = 12,
                rotation: str = 'monthly') -> logging.Logger:
    """Настройка логгера с ротацией файлов"""

    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Очищаем существующие handlers
    logger.handlers.clear()

    # Создаем formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Убеждаемся что директория для файла существует
    log_dir = os.path.dirname(log_file)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # Настраиваем ротацию
    if rotation == 'weekly':
        handler = logging.handlers.TimedRotatingFileHandler(
            log_file, when='W0', interval=1, backupCount=backup_count
        )
    elif rotation == 'monthly':
        handler = logging.handlers.TimedRotatingFileHandler(
            log_file, when='midnight', interval=1, backupCount=backup_count
        )
    else:
        handler = logging.handlers.RotatingFileHandler(
            log_file, maxBytes=max_bytes, backupCount=backup_count
        )

    handler.setFormatter(formatter)
    handler.addFilter(TelegramBlockedFilter())

    # Добавляем handler в консоль для отладки
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.addFilter(TelegramBlockedFilter())

    logger.addHandler(handler)
    logger.addHandler(console_handler)

    return logger

# Глобальные переменные для логгеров
_main_logger = None
_database_logger = None
_keyboards_logger = None
_generation_logger = None
_api_logger = None
_payments_logger = None
_errors_logger = None

def _initialize_loggers():
    """Инициализация всех логгеров"""
    global _main_logger, _database_logger, _keyboards_logger, _generation_logger, _api_logger, _payments_logger, _errors_logger

    # Основной логгер
    _main_logger = setup_logger('bot', 'bot.log', backup_count=4, rotation='size', max_bytes=5*1024*1024)  # 5MB

    # Специализированные логгеры
    _database_logger = setup_logger('database', 'logs/database.log')
    _keyboards_logger = setup_logger('keyboards', 'logs/keyboards.log')
    _generation_logger = setup_logger('generation', 'logs/generation.log')
    _api_logger = setup_logger('api', 'logs/api.log')
    _payments_logger = setup_logger('payments', 'logs/payments.log')
    _errors_logger = setup_logger('errors', 'logs/errors.log')

def reset_loggers():
    """Сброс логгеров для тестирования"""
    global _main_logger, _database_logger, _keyboards_logger, _generation_logger, _api_logger, _payments_logger, _errors_logger

    # Очищаем все логгеры
    for logger_name in ['bot', 'database', 'keyboards', 'generation', 'api', 'payments', 'errors']:
        logger = logging.getLogger(logger_name)
        logger.handlers.clear()

    # Сбрасываем глобальные переменные
    _main_logger = None
    _database_logger = None
    _keyboards_logger = None
    _generation_logger = None
    _api_logger = None
    _payments_logger = None
    _errors_logger = None

def get_logger(logger_type: str = 'main') -> logging.Logger:
    """Получение логгера по типу"""
    global _main_logger, _database_logger, _keyboards_logger, _generation_logger, _api_logger, _payments_logger, _errors_logger

    # Инициализируем логгеры если они еще не инициализированы
    if _main_logger is None:
        _initialize_loggers()

    loggers = {
        'main': _main_logger,
        'database': _database_logger,
        'keyboards': _keyboards_logger,
        'generation': _generation_logger,
        'api': _api_logger,
        'payments': _payments_logger,
        'errors': _errors_logger
    }
    return loggers.get(logger_type, _main_logger)

def log_user_action(user_id: int, action: str, logger_type: str = 'main',
                   level: str = 'info', **kwargs):
    """Логирование действий пользователя с дополнительными параметрами"""
    logger = get_logger(logger_type)
    message = f"User {user_id}: {action}"

    if kwargs:
        details = ', '.join([f"{k}={v}" for k, v in kwargs.items()])
        message += f" ({details})"

    if level == 'debug':
        logger.debug(message)
    elif level == 'warning':
        logger.warning(message)
    elif level == 'error':
        logger.error(message)
    else:
        logger.info(message)

def log_error(error: Exception, context: str = "", user_id: Optional[int] = None,
              logger_type: str = 'errors', exc_info: bool = True):
    """Логирование ошибок с контекстом"""
    logger = get_logger(logger_type)
    message = f"Error in {context}"
    if user_id:
        message += f" for user {user_id}"
    message += f": {str(error)}"

    logger.error(message, exc_info=exc_info)

def log_api_call(api_name: str, endpoint: str, user_id: Optional[int] = None,
                 success: bool = True, response_time: Optional[float] = None):
    """Логирование API вызовов"""
    logger = get_logger('api')
    status = "SUCCESS" if success else "FAILED"
    message = f"API {api_name} {endpoint}: {status}"

    if user_id:
        message += f" (user {user_id})"

    if response_time:
        message += f" ({response_time:.2f}s)"

    if success:
        logger.info(message)
    else:
        logger.error(message)

def log_payment(payment_id: str, user_id: int, amount: float,
                status: str, payment_method: str = ""):
    """Логирование платежей"""
    logger = get_logger('payments')
    message = f"Payment {payment_id}: user {user_id}, amount {amount}, status {status}"
    if payment_method:
        message += f", method {payment_method}"

    logger.info(message)

def log_generation(generation_type: str, user_id: int, model: str = "",
                   success: bool = True, duration: Optional[float] = None):
    """Логирование генераций"""
    logger = get_logger('generation')
    status = "SUCCESS" if success else "FAILED"
    message = f"Generation {generation_type}: user {user_id}, {status}"

    if model:
        message += f", model {model}"

    if duration:
        message += f" ({duration:.2f}s)"

    if success:
        logger.info(message)
    else:
        logger.error(message)

# Инициализация логгеров при импорте
_initialize_loggers()

# Инициализация логгеров при импорте
if __name__ == "__main__":
    # Тестовая запись в каждый логгер
    get_logger('main').info("Main logger initialized")
    get_logger('database').info("Database logger initialized")
    get_logger('keyboards').info("Keyboards logger initialized")
    get_logger('generation').info("Generation logger initialized")
    get_logger('api').info("API logger initialized")
    get_logger('payments').info("Payments logger initialized")
    get_logger('errors').info("Errors logger initialized")

    print("All loggers initialized successfully!")
