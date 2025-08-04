#!/bin/bash

# ================================================================
# AXIDI BOT - STOP SCRIPT
# ================================================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}================================================================${NC}"
echo -e "${CYAN}🛑 STOPPING AXIDI PHOTO AI BOT${NC}"
echo -e "${CYAN}================================================================${NC}"

cd /root/axidi_pr_v1

echo -e "${YELLOW}🔍 Checking running processes...${NC}"

# Stop Telegram bot + интегрированный webhook
TELEGRAM_PIDS=$(pgrep -f "python.*main.py" 2>/dev/null || true)
if [ ! -z "$TELEGRAM_PIDS" ]; then
    echo -e "${YELLOW}🤖 Stopping Telegram bot + integrated webhook...${NC}"
    pkill -f "python.*main.py"
    sleep 3

    # Force kill if still running
    REMAINING=$(pgrep -f "python.*main.py" 2>/dev/null || true)
    if [ ! -z "$REMAINING" ]; then
        echo -e "${YELLOW}⚡ Force stopping integrated bot...${NC}"
        pkill -9 -f "python.*main.py"
    fi
    echo -e "${GREEN}✅ Telegram bot + webhook stopped${NC}"
else
    echo -e "${YELLOW}ℹ️ Integrated bot not running${NC}"
fi

# Stop устаревшие Gunicorn процессы (если есть)
GUNICORN_PIDS=$(pgrep -f "gunicorn.*main:app" 2>/dev/null || true)
if [ ! -z "$GUNICORN_PIDS" ]; then
    echo -e "${YELLOW}🗑️ Stopping legacy Gunicorn processes...${NC}"
    pkill -f "gunicorn.*main:app"
    sleep 3

    # Force kill if still running
    REMAINING=$(pgrep -f "gunicorn.*main:app" 2>/dev/null || true)
    if [ ! -z "$REMAINING" ]; then
        echo -e "${YELLOW}⚡ Force stopping legacy Gunicorn...${NC}"
        pkill -9 -f "gunicorn.*main:app"
    fi
    echo -e "${GREEN}✅ Legacy Gunicorn stopped${NC}"
else
    echo -e "${GREEN}✅ No legacy Gunicorn processes found${NC}"
fi

# Check port 8000
echo -e "${YELLOW}🌐 Checking port 8000...${NC}"
if netstat -tulpn | grep -q ":8000.*LISTEN"; then
    echo -e "${YELLOW}⚡ Freeing port 8000...${NC}"
    fuser -k 8000/tcp 2>/dev/null || true
    sleep 2
fi

# Final verification
TELEGRAM_CHECK=$(pgrep -f "python.*main.py" 2>/dev/null || true)
GUNICORN_CHECK=$(pgrep -f "gunicorn.*main:app" 2>/dev/null || true)
PORT_CHECK=$(netstat -tulpn | grep ":8000.*LISTEN" 2>/dev/null || true)

if [ -z "$TELEGRAM_CHECK" ] && [ -z "$GUNICORN_CHECK" ] && [ -z "$PORT_CHECK" ]; then
    echo -e "${CYAN}================================================================${NC}"
    echo -e "${GREEN}🎉 INTEGRATED SYSTEM STOPPED SUCCESSFULLY!${NC}"
    echo -e "${CYAN}================================================================${NC}"
    echo -e "${GREEN}✅ Telegram bot + webhook: stopped${NC}"
    echo -e "${GREEN}✅ Legacy processes: cleaned${NC}"
    echo -e "${GREEN}✅ Port 8000: free${NC}"
    echo -e "${GREEN}🚀 Ready for restart with integrated architecture${NC}"
else
    echo -e "${CYAN}================================================================${NC}"
    echo -e "${YELLOW}⚠️ PARTIAL SHUTDOWN${NC}"
    echo -e "${CYAN}================================================================${NC}"

    if [ ! -z "$TELEGRAM_CHECK" ]; then
        echo -e "${RED}❌ Integrated bot still running (PID: $TELEGRAM_CHECK)${NC}"
    fi

    if [ ! -z "$GUNICORN_CHECK" ]; then
        echo -e "${YELLOW}⚠️ Legacy Gunicorn still running (PID: $GUNICORN_CHECK)${NC}"
    fi

    if [ ! -z "$PORT_CHECK" ]; then
        echo -e "${RED}❌ Port 8000 still in use${NC}"
    fi
fi

echo -e "${YELLOW}📋 Next steps:${NC}"
echo -e "• Start: ${GREEN}./start.sh${NC}"
echo -e "• Status: ${GREEN}./status.sh${NC}"
