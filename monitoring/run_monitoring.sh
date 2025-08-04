#!/bin/bash

# Скрипт для запуска мониторинга воронки онбординга
# Запускается по расписанию через cron

# Путь к проекту
PROJECT_DIR="/Users/aleksandrsim/AXIDI/update/axidi_project"

# Переходим в директорию проекта
cd "$PROJECT_DIR"

# Активируем виртуальное окружение
source .venv/bin/activate

# Запускаем мониторинг
echo "$(date): Запуск мониторинга воронки онбординга" >> logs/monitoring/monitoring_cron.log
python monitoring/onboarding_monitor.py >> logs/monitoring/monitoring_cron.log 2>&1
echo "$(date): Мониторинг завершен" >> logs/monitoring/monitoring_cron.log
echo "---" >> logs/monitoring/monitoring_cron.log
