#!/bin/bash

echo "🔧 НАСТРОЙКА ВЕБХУКА ДЛЯ YOOKASSA (ПРОДАКШН)"
echo "=============================================="

# Проверяем, запущен ли бот
echo "1. Проверяем, запущен ли бот..."
if curl -s https://pixelpieai.ru/health > /dev/null; then
    echo "✅ Бот запущен и доступен"
else
    echo "❌ Бот не доступен по адресу https://pixelpieai.ru"
    echo "Запустите бот: python3 main.py"
    exit 1
fi

# Продакшн webhook URL
PRODUCTION_WEBHOOK_URL="https://pixelpieai.ru/webhook"

echo "2. Продакшн webhook URL: $PRODUCTION_WEBHOOK_URL"
echo ""
echo "3. Обновите вебхук в YooKassa:"
echo "   URL: $PRODUCTION_WEBHOOK_URL"
echo ""
echo "4. Тестирование webhook:"
echo "   curl -X POST $PRODUCTION_WEBHOOK_URL \\"
echo "     -H 'Content-Type: application/json' \\"
echo "     -d '{\"test\": true}'"
echo ""
echo "5. Проверка статуса:"
echo "   curl -X GET https://pixelpieai.ru/health"
echo ""
echo "✅ Продакшн настройки готовы!"
echo "⚠️  Убедитесь, что домен pixelpieai.ru настроен правильно"
