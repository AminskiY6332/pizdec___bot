#!/bin/bash

# ================================================================
# AXIDI BOT - DEBUG MODE SCRIPT
# ================================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}================================================================${NC}"
echo -e "${CYAN}🔧 INTEGRATED AXIDI BOT - DEBUG MODE${NC}"
echo -e "${CYAN}================================================================${NC}"

cd /root/axidi_pr_v1

# Load environment
if [ -f .env ]; then
    set -a && source .env && set +a
    echo -e "${GREEN}✅ Environment loaded from .env${NC}"
elif [ -f .bs ]; then
    set -a && source .bs && set +a
    echo -e "${GREEN}✅ Environment loaded from .bs${NC}"
else
    echo -e "${RED}❌ No environment file found${NC}"
    exit 1
fi

# Stop any running instances
echo -e "${YELLOW}🛑 Stopping existing processes...${NC}"
pkill -f "python.*main.py" 2>/dev/null || echo "No bot processes found"
# УДАЛЕНО: Gunicorn больше не используется - теперь интегрированный webhook

# Create debug log directory
mkdir -p ./debug_logs
DEBUG_LOG="./debug_logs/debug_$(date +%Y%m%d_%H%M%S).log"

echo -e "${YELLOW}📝 Debug session log: $DEBUG_LOG${NC}"

# Function for timestamped logging
log_debug() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$DEBUG_LOG"
}

echo -e "${CYAN}================================================================${NC}"
echo -e "${CYAN}🔍 SYSTEM DIAGNOSTICS${NC}"
echo -e "${CYAN}================================================================${NC}"

log_debug "=== STARTING DEBUG SESSION ==="

# System info
echo -e "${BLUE}💻 System Information:${NC}"
log_debug "System: $(uname -a)"
log_debug "Python: $(python3 --version)"
log_debug "Current directory: $(pwd)"
log_debug "User: $(whoami)"

# Environment check
echo -e "${BLUE}⚙️ Environment Check:${NC}"
log_debug "TELEGRAM_BOT_TOKEN: ${TELEGRAM_BOT_TOKEN:0:10}... (length: ${#TELEGRAM_BOT_TOKEN})"
log_debug "YOOKASSA_SHOP_ID: $YOOKASSA_SHOP_ID"
log_debug "SECRET_KEY: ${SECRET_KEY:0:10}... (length: ${#SECRET_KEY})"

# Dependencies check
echo -e "${BLUE}📦 Dependencies Check:${NC}"
python3 -c "
import sys
print(f'Python version: {sys.version}')

dependencies = [
    'aiogram', 'yookassa', 'aiosqlite', 'flask',
    'gunicorn', 'redis', 'requests', 'pillow'
]

for dep in dependencies:
    try:
        module = __import__(dep)
        version = getattr(module, '__version__', 'unknown')
        print(f'✅ {dep}: {version}')
    except ImportError as e:
        print(f'❌ {dep}: {e}')
" | tee -a "$DEBUG_LOG"

# Port check
echo -e "${BLUE}🌐 Port Status:${NC}"
log_debug "Port 8000 status:"
netstat -tulpn | grep ":8000" | tee -a "$DEBUG_LOG" || log_debug "Port 8000 free"

# Start Gunicorn in debug mode
echo -e "${CYAN}================================================================${NC}"
echo -e "${CYAN}🚀 STARTING GUNICORN (DEBUG MODE)${NC}"
echo -e "${CYAN}================================================================${NC}"

log_debug "Starting Gunicorn with debug logging..."

# Start Gunicorn with debug settings
gunicorn -c simple_production.py main:app \
    --log-level debug \
    --access-logfile "$DEBUG_LOG" \
    --error-logfile "$DEBUG_LOG" \
    --timeout 300 \
    --daemon

sleep 3

# Verify Gunicorn startup
if pgrep -f "gunicorn.*main:app" > /dev/null; then
    GUNICORN_PID=$(pgrep -f "gunicorn.*main:app" | head -1)
    log_debug "✅ Gunicorn started (PID: $GUNICORN_PID)"

    # Test endpoints
    echo -e "${YELLOW}🧪 Testing endpoints...${NC}"

    # Health check
    if curl -s http://localhost:8000/health > /dev/null; then
        HEALTH_RESP=$(curl -s http://localhost:8000/health)
        log_debug "✅ Health endpoint: $HEALTH_RESP"
    else
        log_debug "❌ Health endpoint failed"
    fi

    # Webhook test
    WEBHOOK_RESP=$(curl -s -X POST http://localhost:8000/webhook \
        -H "Content-Type: application/json" \
        -d '{"test":"debug_mode"}')
    log_debug "Webhook test response: $WEBHOOK_RESP"

else
    log_debug "❌ Gunicorn failed to start"
    echo -e "${RED}❌ Gunicorn startup failed${NC}"
    exit 1
fi

# Start Telegram bot in debug mode
echo -e "${CYAN}================================================================${NC}"
echo -e "${CYAN}🤖 STARTING TELEGRAM BOT (DEBUG MODE)${NC}"
echo -e "${CYAN}================================================================${NC}"

log_debug "Starting Telegram bot with debug logging..."

# Start bot with detailed logging and output to console
echo -e "${YELLOW}📋 Bot output (CTRL+C to stop):${NC}"
echo -e "${YELLOW}Debug log: $DEBUG_LOG${NC}"
echo -e "${CYAN}----------------------------------------------------------------${NC}"

# Run bot with debug output
PYTHONPATH=$(pwd) \
PYTHONUNBUFFERED=1 \
python3 -u ./main.py 2>&1 | while IFS= read -r line; do
    echo "$line"
    log_debug "BOT: $line"
done
