#!/bin/bash

# ================================================================
# AXIDI BOT - RESTART SCRIPT
# ================================================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}================================================================${NC}"
echo -e "${CYAN}🔄 RESTARTING INTEGRATED AXIDI BOT${NC}"
echo -e "${CYAN}================================================================${NC}"

cd /root/axidi_pr_v1

# Stop services
echo -e "${YELLOW}🛑 Stopping services...${NC}"
./stop.sh

# Wait for complete shutdown
echo -e "${YELLOW}⏳ Waiting for complete shutdown...${NC}"
sleep 5

# Verify shutdown
if pgrep -f "python.*main.py\|gunicorn.*main:app" > /dev/null; then
    echo -e "${RED}❌ Some processes still running, forcing shutdown...${NC}"
    pkill -9 -f "python.*main.py"
    pkill -9 -f "gunicorn.*main:app"  # Clean legacy processes
    sleep 3
fi

# Start services
echo -e "${YELLOW}🚀 Starting services...${NC}"
./start.sh

echo -e "${CYAN}================================================================${NC}"
echo -e "${GREEN}🎉 INTEGRATED SYSTEM RESTART COMPLETED!${NC}"
echo -e "${GREEN}🚀 Bot + webhook running with maximum performance${NC}"
echo -e "${CYAN}================================================================${NC}"
