# === ПРОДАКШН КОНФИГУРАЦИЯ ===
"""
Файл с продакшн настройками для бота
Используется для мониторинга и управления в продакшн среде
"""

import os
from datetime import datetime, timedelta

# === ОСНОВНЫЕ ПРОДАКШН НАСТРОЙКИ ===
PRODUCTION_MODE = True
ENVIRONMENT = "production"

# === НАСТРОЙКИ МОНИТОРИНГА ===
HEALTH_CHECK_INTERVAL = 300  # 5 минут
# ИСПРАВЛЕНО: заменяем localhost на продакшн URL
HEALTH_CHECK_ENDPOINT = "https://pixelpieai.ru/health"
LOG_RETENTION_DAYS = 30
BACKUP_RETENTION_DAYS = 7

# === НАСТРОЙКИ ПРОИЗВОДИТЕЛЬНОСТИ ===
MAX_CONCURRENT_GENERATIONS = 10
MAX_CONCURRENT_TASKS = 200
RATE_LIMIT_MAX_REQUESTS = 50
RATE_LIMIT_WINDOW_MINUTES = 1

# === НАСТРОЙКИ БЕЗОПАСНОСТИ ===
ADMIN_IDS = [444593004, 331123326, 7787636839, 5667999089]
ERROR_LOG_ADMIN = [5667999089]

# === НАСТРОЙКИ УВЕДОМЛЕНИЙ ===
NOTIFICATION_HOUR = 12
TIMEZONE = 'Europe/Moscow'

# === НАСТРОЙКИ ЛОГИРОВАНИЯ ===
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_FILE = "logs/production.log"

# === НАСТРОЙКИ БАЗЫ ДАННЫХ ===
DATABASE_PATH = "users.db"
BACKUP_ENABLED = True
BACKUP_INTERVAL_HOURS = 24

# === НАСТРОЙКИ WEBHOOK ===
WEBHOOK_URL = "https://pixelpieai.ru/webhook"
WEBHOOK_SECRET = os.getenv('YOOKASSA_SECRET', '')

# === НАСТРОЙКИ ПЛАТЕЖЕЙ ===
YOOKASSA_ENABLED = True
# ИСПРАВЛЕНО: убираем тестовый fallback
YOOKASSA_SHOP_ID = os.getenv('YOOKASSA_SHOP_ID')
if not YOOKASSA_SHOP_ID:
    raise ValueError("YOOKASSA_SHOP_ID должен быть установлен в production среде")

SECRET_KEY = os.getenv('SECRET_KEY')
if not SECRET_KEY:
    raise ValueError("SECRET_KEY должен быть установлен в production среде")

YOOKASSA_SECRET_KEY = SECRET_KEY  # Алиас для совместимости

# === НАСТРОЙКИ ГЕНЕРАЦИИ ===
REPLICATE_API_TOKEN = os.getenv('REPLICATE_API_TOKEN', '')
REPLICATE_USERNAME_OR_ORG_NAME = os.getenv('REPLICATE_USERNAME_OR_ORG_NAME', 'axidiagensy')

# === НАСТРОЙКИ АНТИСПАМА ===
ANTISPAM_MESSAGE_LIMIT = 10
ANTISPAM_GENERATION_LIMIT = 5

# === НАСТРОЙКИ РЕФЕРАЛЬНОЙ СИСТЕМЫ ===
REFERRAL_BONUS_PHOTOS = 10
REFERRAL_BONUS_FOR_REFERRER = 5

# === ФУНКЦИИ ДЛЯ ПРОДАКШН ===
def get_production_status():
    """Получает статус продакшн системы"""
    return {
        "environment": ENVIRONMENT,
        "production_mode": PRODUCTION_MODE,
        "health_check_interval": HEALTH_CHECK_INTERVAL,
        "max_concurrent_generations": MAX_CONCURRENT_GENERATIONS,
        "rate_limit_requests": RATE_LIMIT_MAX_REQUESTS,
        "admin_count": len(ADMIN_IDS),
        "webhook_url": WEBHOOK_URL,
        "yookassa_enabled": YOOKASSA_ENABLED,
        "backup_enabled": BACKUP_ENABLED
    }

def validate_production_config():
    """Валидирует продакшн конфигурацию"""
    errors = []

    if not REPLICATE_API_TOKEN:
        errors.append("REPLICATE_API_TOKEN не настроен")

    if not YOOKASSA_SHOP_ID or YOOKASSA_SHOP_ID == '123456':
        errors.append("YOOKASSA_SHOP_ID не настроен корректно")

    if not SECRET_KEY:
        errors.append("SECRET_KEY не настроен корректно")

    return errors

def get_production_info():
    """Возвращает информацию о продакшн настройках"""
    return {
        "timestamp": datetime.now().isoformat(),
        "environment": ENVIRONMENT,
        "config": get_production_status(),
        "validation_errors": validate_production_config()
    }

if __name__ == "__main__":
    print("=== ПРОДАКШН КОНФИГУРАЦИЯ ===")
    info = get_production_info()
    print(f"Environment: {info['environment']}")
    print(f"Production Mode: {info['config']['production_mode']}")
    print(f"Webhook URL: {info['config']['webhook_url']}")
    print(f"YooKassa Enabled: {info['config']['yookassa_enabled']}")

    errors = info['validation_errors']
    if errors:
        print("\n❌ ОШИБКИ КОНФИГУРАЦИИ:")
        for error in errors:
            print(f"  - {error}")
    else:
        print("\n✅ Конфигурация корректна")
