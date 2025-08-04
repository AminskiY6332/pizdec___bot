#!/bin/bash

# ================================================================
# AXIDI BOT - BACKUP SCRIPT
# ================================================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}================================================================${NC}"
echo -e "${CYAN}💾 AXIDI BOT - BACKUP SYSTEM${NC}"
echo -e "${CYAN}================================================================${NC}"

cd /root/axidi_pr_v1

# Create backup directory
BACKUP_DIR="./backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="axidi_backup_$TIMESTAMP"
FULL_BACKUP_PATH="$BACKUP_DIR/$BACKUP_NAME"

mkdir -p "$BACKUP_DIR"

echo -e "${YELLOW}📁 Creating backup: $BACKUP_NAME${NC}"

# Create backup directory structure
mkdir -p "$FULL_BACKUP_PATH"

echo -e "${BLUE}💾 Backing up components:${NC}"

# 1. Database backup
echo -e "${YELLOW}🗄️ Backing up database...${NC}"
if [ -f "users.db" ]; then
    cp "users.db" "$FULL_BACKUP_PATH/"
    echo -e "${GREEN}✅ Database backed up ($(du -h users.db | cut -f1))${NC}"
else
    echo -e "${RED}❌ Database not found${NC}"
fi

# 2. Configuration files
echo -e "${YELLOW}⚙️ Backing up configuration...${NC}"
CONFIG_FILES=(".env" ".bs" "simple_production.py" "config.py")
for file in "${CONFIG_FILES[@]}"; do
    if [ -f "$file" ]; then
        cp "$file" "$FULL_BACKUP_PATH/"
        echo -e "${GREEN}✅ $file backed up${NC}"
    else
        echo -e "${YELLOW}⚠️ $file not found${NC}"
    fi
done

# 3. Management scripts
echo -e "${YELLOW}📜 Backing up management scripts...${NC}"
SCRIPT_FILES=("start.sh" "stop.sh" "restart.sh" "status.sh" "debug.sh" "backup.sh")
for script in "${SCRIPT_FILES[@]}"; do
    if [ -f "$script" ]; then
        cp "$script" "$FULL_BACKUP_PATH/"
        echo -e "${GREEN}✅ $script backed up${NC}"
    fi
done

# 4. Logs (recent only)
echo -e "${YELLOW}📋 Backing up recent logs...${NC}"
if [ -d "logs" ]; then
    mkdir -p "$FULL_BACKUP_PATH/logs"
    # Copy only recent logs (last 7 days)
    find logs -name "*.log" -mtime -7 -exec cp {} "$FULL_BACKUP_PATH/logs/" \;
    LOG_COUNT=$(find "$FULL_BACKUP_PATH/logs" -name "*.log" | wc -l)
    echo -e "${GREEN}✅ $LOG_COUNT recent log files backed up${NC}"
fi

if [ -d "/var/log/axidi" ]; then
    mkdir -p "$FULL_BACKUP_PATH/system_logs"
    find /var/log/axidi -name "*.log" -mtime -7 -exec cp {} "$FULL_BACKUP_PATH/system_logs/" \; 2>/dev/null || true
    SYS_LOG_COUNT=$(find "$FULL_BACKUP_PATH/system_logs" -name "*.log" 2>/dev/null | wc -l)
    echo -e "${GREEN}✅ $SYS_LOG_COUNT system log files backed up${NC}"
fi

# 5. System information
echo -e "${YELLOW}ℹ️ Saving system information...${NC}"
INFO_FILE="$FULL_BACKUP_PATH/system_info.txt"
{
    echo "=== AXIDI BOT BACKUP INFORMATION ==="
    echo "Backup created: $(date)"
    echo "System: $(uname -a)"
    echo "Python: $(python3 --version 2>&1)"
    echo "Working directory: $(pwd)"
    echo ""
    echo "=== PROCESS STATUS AT BACKUP TIME ==="
    ps aux | grep -E "(gunicorn|python.*main.py)" | grep -v grep || echo "No bot processes running"
    echo ""
    echo "=== NETWORK STATUS ==="
    netstat -tulpn | grep ":8000" || echo "Port 8000 not in use"
    echo ""
    echo "=== ENVIRONMENT VARIABLES ==="
    echo "TELEGRAM_BOT_TOKEN: ${TELEGRAM_BOT_TOKEN:0:10}... (length: ${#TELEGRAM_BOT_TOKEN})"
    echo "YOOKASSA_SHOP_ID: $YOOKASSA_SHOP_ID"
    echo ""
    echo "=== DISK USAGE ==="
    df -h $(pwd)
    echo ""
    echo "=== DIRECTORY LISTING ==="
    ls -la
} > "$INFO_FILE"
echo -e "${GREEN}✅ System info saved${NC}"

# Create compressed archive
echo -e "${YELLOW}🗜️ Creating compressed archive...${NC}"
cd "$BACKUP_DIR"
tar -czf "$BACKUP_NAME.tar.gz" "$BACKUP_NAME"
rm -rf "$BACKUP_NAME"

ARCHIVE_SIZE=$(du -h "$BACKUP_NAME.tar.gz" | cut -f1)
echo -e "${GREEN}✅ Compressed backup created: $BACKUP_NAME.tar.gz ($ARCHIVE_SIZE)${NC}"

# Cleanup old backups (keep last 10)
echo -e "${YELLOW}🧹 Cleaning up old backups...${NC}"
BACKUP_COUNT=$(ls -1 axidi_backup_*.tar.gz 2>/dev/null | wc -l)
if [ "$BACKUP_COUNT" -gt 10 ]; then
    ls -1t axidi_backup_*.tar.gz | tail -n +11 | xargs rm -f
    CLEANED=$(($BACKUP_COUNT - 10))
    echo -e "${GREEN}✅ Removed $CLEANED old backup(s)${NC}"
else
    echo -e "${GREEN}✅ No cleanup needed ($BACKUP_COUNT backups total)${NC}"
fi

cd - > /dev/null

echo -e "${CYAN}================================================================${NC}"
echo -e "${GREEN}💾 BACKUP COMPLETED SUCCESSFULLY!${NC}"
echo -e "${CYAN}================================================================${NC}"

echo -e "${GREEN}📄 Backup details:${NC}"
echo -e "• File: ${GREEN}$BACKUP_DIR/$BACKUP_NAME.tar.gz${NC}"
echo -e "• Size: ${GREEN}$ARCHIVE_SIZE${NC}"
echo -e "• Location: ${GREEN}$(pwd)/$BACKUP_DIR/${NC}"

echo -e "${YELLOW}📋 Available backups:${NC}"
ls -lht "$BACKUP_DIR"/axidi_backup_*.tar.gz | head -5

echo -e "${BLUE}🔄 To restore from backup:${NC}"
echo -e "1. Extract: ${YELLOW}tar -xzf $BACKUP_DIR/$BACKUP_NAME.tar.gz${NC}"
echo -e "2. Copy files back to project directory"
echo -e "3. Run: ${YELLOW}./start.sh${NC}"

echo -e "${CYAN}================================================================${NC}"
