# 🐋 Dockerfile для Telegram бота AXIDI
FROM python:3.11-slim

# Метаданные
LABEL maintainer="AXIDI Team"
LABEL description="AXIDI Telegram Bot - AI Photo Generation"
LABEL version="1.0"

# Переменные окружения
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DEBIAN_FRONTEND=noninteractive

# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    libmagic1 \
    libmagic-dev \
    pkg-config \
    supervisor \
    nginx \
    && rm -rf /var/lib/apt/lists/*

# Создаем пользователя для безопасности
RUN groupadd -r botuser && useradd -r -g botuser -d /app -s /bin/bash botuser

# Создаем рабочую директорию
WORKDIR /app

# Копируем requirements.txt
COPY requirements.txt .

# Устанавливаем Python зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем проект
COPY . .

# Создаем необходимые директории
RUN mkdir -p \
    /app/logs \
    /app/logs/history/api \
    /app/logs/history/database \
    /app/logs/history/errors \
    /app/logs/history/generation \
    /app/logs/history/keyboards \
    /app/logs/history/main \
    /app/logs/history/payments \
    /app/logs/manager \
    /app/logs/monitoring \
    /app/backups \
    /app/uploads \
    /app/temp \
    /app/generated \
    /app/images \
    /var/log/supervisor

# Копируем конфигурации
COPY docker/supervisor.conf /etc/supervisor/conf.d/
COPY docker/nginx.conf /etc/nginx/sites-available/default

# Устанавливаем права доступа
RUN chown -R botuser:botuser /app && \
    chmod +x /app/*.sh && \
    chmod +x /app/docker/*.sh

# Создаем скрипт запуска
COPY docker/start.sh /start.sh
RUN chmod +x /start.sh

# Переключаемся на пользователя botuser для основных операций
USER botuser

# Проверка здоровья контейнера
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:5001/health || exit 1

# Открываем порты
EXPOSE 5001 80

# Переключаемся обратно на root для запуска supervisor
USER root

# Запуск
CMD ["/start.sh"]
