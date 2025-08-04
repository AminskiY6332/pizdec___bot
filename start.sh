#!/bin/bash

# ================================================================
# AXIDI BOT - MAIN STARTUP SCRIPT
# ================================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}================================================================${NC}"
echo -e "${CYAN}🚀 STARTING AXIDI PHOTO AI BOT${NC}"
echo -e "${CYAN}================================================================${NC}"

# Navigate to project directory
cd /root/axidi_pr_v1
echo -e "${GREEN}✅ Project directory: $(pwd)${NC}"

# Load environment variables
echo -e "${YELLOW}📋 Loading environment variables...${NC}"
if [ -f .env ]; then
    set -a
    source .env
    set +a
    echo -e "${GREEN}✅ Environment loaded from .env${NC}"
elif [ -f .bs ]; then
    set -a
    source .bs
    set +a
    echo -e "${GREEN}✅ Environment loaded from .bs${NC}"
else
    echo -e "${RED}❌ Environment file not found (.env or .bs)${NC}"
    exit 1
fi

# Validate critical variables
if [ -z "$TELEGRAM_BOT_TOKEN" ]; then
    echo -e "${RED}❌ TELEGRAM_BOT_TOKEN not set${NC}"
    exit 1
fi
echo -e "${GREEN}✅ TELEGRAM_BOT_TOKEN: ${TELEGRAM_BOT_TOKEN:0:10}...${NC}"

if [ -z "$YOOKASSA_SHOP_ID" ]; then
    echo -e "${RED}❌ YOOKASSA_SHOP_ID not set${NC}"
    exit 1
fi
echo -e "${GREEN}✅ YOOKASSA_SHOP_ID: $YOOKASSA_SHOP_ID${NC}"

# Stop old processes
echo -e "${YELLOW}🛑 Stopping old processes...${NC}"
pkill -f "python.*main.py" 2>/dev/null && echo -e "${GREEN}✅ Old bots stopped${NC}" || echo -e "${YELLOW}ℹ️ No old bots found${NC}"

# УДАЛЕНО: Gunicorn - теперь используется интегрированный aiohttp webhook
echo -e "${GREEN}✅ Webhook интегрирован в основной процесс бота (порт 8000)${NC}"

# Останавливаем старые Gunicorn процессы если они есть
if pgrep -f "gunicorn.*main:app" > /dev/null; then
    echo -e "${YELLOW}🛑 Stopping old Gunicorn processes...${NC}"
    pkill -f "gunicorn.*main:app"
    sleep 2
    echo -e "${GREEN}✅ Old Gunicorn stopped${NC}"
fi

echo -e "${CYAN}================================================================${NC}"
echo -e "${CYAN}🤖 STARTING TELEGRAM BOT${NC}"
echo -e "${CYAN}================================================================${NC}"

# Create logs directory
mkdir -p ./logs

# Start Telegram bot
echo -e "${BLUE}🚀 Starting Telegram bot...${NC}"
echo -e "${YELLOW}📁 File: $(pwd)/main.py${NC}"
echo -e "${YELLOW}🐍 Python: $(which python3)${NC}"

# Start in background with logging
PYTHONPATH=$(pwd) \
PYTHONUNBUFFERED=1 \
nohup python3 -u ./main.py > ./logs/telegram_bot.log 2>&1 &

TELEGRAM_PID=$!
echo -e "${GREEN}✅ Telegram bot started (PID: $TELEGRAM_PID)${NC}"

# Wait for initialization
echo -e "${YELLOW}⏳ Waiting for bot initialization (15 sec)...${NC}"
sleep 15

# Check status
if ps -p $TELEGRAM_PID > /dev/null; then
    echo -e "${GREEN}✅ Telegram bot running${NC}"

    # Check for conflicts in logs
    if grep -q "TelegramConflictError\|Conflict" ./logs/telegram_bot.log 2>/dev/null; then
        echo -e "${RED}❌ Conflict detected in logs${NC}"
        tail -10 ./logs/telegram_bot.log
        exit 1
    else
        echo -e "${GREEN}✅ No conflicts detected${NC}"
    fi

    # Show recent logs
    echo -e "${YELLOW}📋 Recent bot logs:${NC}"
    tail -5 ./logs/telegram_bot.log

else
    echo -e "${RED}❌ Telegram bot not running${NC}"
    echo -e "${YELLOW}Error logs:${NC}"
    tail -20 ./logs/telegram_bot.log
    exit 1
fi

echo -e "${CYAN}================================================================${NC}"
echo -e "${CYAN}🎉 SYSTEM STARTED SUCCESSFULLY!${NC}"
echo -e "${CYAN}================================================================${NC}"

echo -e "${GREEN}✅ System status:${NC}"
echo -e "• Telegram Bot: PID $TELEGRAM_PID (с интегрированным webhook)"
echo -e "• Port 8000: $(netstat -tulpn | grep ':8000' | wc -l) connections (aiohttp)"

echo -e "${YELLOW}📋 Management commands:${NC}"
echo -e "• Status: ${GREEN}./status.sh${NC}"
echo -e "• Stop: ${GREEN}./stop.sh${NC}"
echo -e "• Restart: ${GREEN}./restart.sh${NC}"
echo -e "• Debug: ${GREEN}./debug.sh${NC}"
echo -e "• Backup: ${GREEN}./backup.sh${NC}"

echo -e "${CYAN}🔗 Endpoints:${NC}"
echo -e "• Health: ${GREEN}http://localhost:8000/health${NC}"
echo -e "• Webhook: ${GREEN}https://axidiphotoai.ru/webhook${NC}"

echo -e "${CYAN}================================================================${NC}"
echo -e "${GREEN}🎯 BOT READY FOR USERS!${NC}"
echo -e "${CYAN}================================================================${NC}"
