#!/bin/bash

# ================================================================
# AXIDI BOT - STATUS CHECK SCRIPT
# ================================================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}================================================================${NC}"
echo -e "${CYAN}📊 AXIDI PHOTO AI BOT - STATUS${NC}"
echo -e "${CYAN}================================================================${NC}"

cd /root/axidi_pr_v1

# Check processes
echo -e "${BLUE}🔍 Process Status:${NC}"
echo -e "${BLUE}=================================${NC}"

# Интегрированный webhook (больше не используется отдельный Gunicorn)
GUNICORN_PIDS=$(pgrep -f "gunicorn.*main:app" 2>/dev/null || true)
if [ ! -z "$GUNICORN_PIDS" ]; then
    echo -e "${YELLOW}⚠️ Старый Gunicorn: Обнаружен устаревший процесс (PID: $GUNICORN_PIDS) - рекомендуется остановить${NC}"
else
    echo -e "${GREEN}✅ Gunicorn: Не запущен (используется интегрированный webhook)${NC}"
fi

# Telegram Bot с интегрированным webhook
TELEGRAM_PIDS=$(pgrep -f "python.*main.py" 2>/dev/null || true)
if [ ! -z "$TELEGRAM_PIDS" ]; then
    echo -e "${GREEN}✅ Telegram Bot + Webhook: Running (PID: $TELEGRAM_PIDS)${NC}"
    echo -e "${GREEN}   📡 Интегрированный aiohttp webhook на порту 8000${NC}"
else
    echo -e "${RED}❌ Telegram Bot + Webhook: Not running${NC}"
fi

# Network status
echo -e "${BLUE}🌐 Network Status:${NC}"
echo -e "${BLUE}=================================${NC}"

# Port 8000 (интегрированный aiohttp webhook)
if netstat -tulpn | grep -q ":8000.*LISTEN"; then
    PORT_INFO=$(netstat -tulpn | grep ":8000.*LISTEN")
    PROCESS_INFO=$(echo "$PORT_INFO" | awk '{print $7}')
    echo -e "${GREEN}✅ Port 8000: Listening (aiohttp webhook)${NC}"
    echo -e "${YELLOW}   Process: $PROCESS_INFO${NC}"
    echo -e "${YELLOW}   $PORT_INFO${NC}"
else
    echo -e "${RED}❌ Port 8000: Not listening${NC}"
fi

# Service status
echo -e "${BLUE}🧪 Service Health:${NC}"
echo -e "${BLUE}=================================${NC}"

# Health check
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    HEALTH_RESPONSE=$(curl -s http://localhost:8000/health)
    if echo "$HEALTH_RESPONSE" | grep -q '"status":"ok"'; then
        echo -e "${GREEN}✅ Health Endpoint: OK${NC}"
        echo -e "${YELLOW}   Response: $HEALTH_RESPONSE${NC}"
    else
        echo -e "${YELLOW}⚠️ Health Endpoint: Responding but status unknown${NC}"
        echo -e "${YELLOW}   Response: $HEALTH_RESPONSE${NC}"
    fi
else
    echo -e "${RED}❌ Health Endpoint: Not responding${NC}"
fi

# Webhook test
WEBHOOK_RESPONSE=$(curl -s -w "%{http_code}" -X POST http://localhost:8000/webhook \
    -H "Content-Type: application/json" \
    -d '{"test":"status_check"}' 2>/dev/null || echo "000")

if [ "$WEBHOOK_RESPONSE" != "000" ]; then
    echo -e "${GREEN}✅ Webhook Endpoint: Responding (HTTP $WEBHOOK_RESPONSE)${NC}"
else
    echo -e "${RED}❌ Webhook Endpoint: Not responding${NC}"
fi

# Environment check
echo -e "${BLUE}⚙️ Environment:${NC}"
echo -e "${BLUE}=================================${NC}"

# Load environment
if [ -f .env ]; then
    source .env
    echo -e "${GREEN}✅ Environment: Loaded from .env${NC}"
elif [ -f .bs ]; then
    source .bs
    echo -e "${GREEN}✅ Environment: Loaded from .bs${NC}"
else
    echo -e "${RED}❌ Environment: No config file found${NC}"
fi

# Check critical variables
if [ ! -z "$TELEGRAM_BOT_TOKEN" ]; then
    echo -e "${GREEN}✅ TELEGRAM_BOT_TOKEN: Set (${TELEGRAM_BOT_TOKEN:0:10}...)${NC}"
else
    echo -e "${RED}❌ TELEGRAM_BOT_TOKEN: Not set${NC}"
fi

if [ ! -z "$YOOKASSA_SHOP_ID" ]; then
    echo -e "${GREEN}✅ YOOKASSA_SHOP_ID: Set ($YOOKASSA_SHOP_ID)${NC}"
else
    echo -e "${RED}❌ YOOKASSA_SHOP_ID: Not set${NC}"
fi

# Logs status
echo -e "${BLUE}📋 Recent Activity:${NC}"
echo -e "${BLUE}=================================${NC}"

# Bot logs
if [ -f "./logs/telegram_bot.log" ]; then
    echo -e "${GREEN}✅ Bot logs available${NC}"
    echo -e "${YELLOW}   Last 3 log entries:${NC}"
    tail -3 ./logs/telegram_bot.log | while read line; do
        echo -e "${YELLOW}   > $line${NC}"
    done
else
    echo -e "${RED}❌ Bot logs not found${NC}"
fi

# Webhook logs (интегрированы в основные логи бота)
echo -e "${GREEN}✅ Webhook logs: Интегрированы в основные логи бота${NC}"
if grep -q "aiohttp.access" ./logs/telegram_bot.log 2>/dev/null; then
    echo -e "${GREEN}   Recent webhook activity:${NC}"
    grep "aiohttp.access" ./logs/telegram_bot.log | tail -2 | while read line; do
        echo -e "${YELLOW}   > $line${NC}"
    done
else
    echo -e "${YELLOW}   No recent webhook activity${NC}"
fi

# Overall status
echo -e "${CYAN}================================================================${NC}"

if [ ! -z "$TELEGRAM_PIDS" ] && netstat -tulpn | grep -q ":8000.*LISTEN"; then
    echo -e "${GREEN}🎉 SYSTEM STATUS: FULLY OPERATIONAL${NC}"
    echo -e "${GREEN}🚀 Интегрированный бот с webhook готов к работе!${NC}"
    echo -e "${GREEN}⚡ Максимальная производительность достигнута${NC}"
elif [ ! -z "$TELEGRAM_PIDS" ]; then
    echo -e "${YELLOW}⚠️ SYSTEM STATUS: BOT RUNNING, WEBHOOK CHECK NEEDED${NC}"
    echo -e "${YELLOW}Bot процесс активен, но порт 8000 не слушает${NC}"
else
    echo -e "${RED}❌ SYSTEM STATUS: NOT RUNNING${NC}"
    echo -e "${YELLOW}Use ./start.sh to start the integrated system${NC}"
fi

# Предупреждение о старых процессах
if [ ! -z "$GUNICORN_PIDS" ]; then
    echo -e "${YELLOW}⚠️ ВНИМАНИЕ: Обнаружены устаревшие Gunicorn процессы${NC}"
    echo -e "${YELLOW}   Рекомендуется остановить их: pkill -f 'gunicorn.*main:app'${NC}"
fi

echo -e "${CYAN}================================================================${NC}"

echo -e "${YELLOW}📋 Management Commands:${NC}"
echo -e "• Start: ${GREEN}./start.sh${NC}"
echo -e "• Stop: ${GREEN}./stop.sh${NC}"
echo -e "• Restart: ${GREEN}./restart.sh${NC}"
echo -e "• Debug: ${GREEN}./debug.sh${NC}"
echo -e "• Backup: ${GREEN}./backup.sh${NC}"
