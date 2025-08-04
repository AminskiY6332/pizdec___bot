#!/bin/bash

# ===============================================
# ⚙️ УСТАНОВКА AXIDI BOT КАК СИСТЕМНЫЙ СЕРВИС
# ===============================================

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}===============================================${NC}"
echo -e "${BLUE}⚙️ УСТАНОВКА AXIDI BOT В SYSTEMD${NC}"
echo -e "${BLUE}===============================================${NC}"

# Проверка прав root
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}❌ Запуск от пользователя root${NC}"
   exit 1
fi

# Остановка существующего сервиса
echo -e "${YELLOW}🛑 Остановка существующего сервиса...${NC}"
systemctl stop axidi-bot 2>/dev/null || echo "Сервис еще не установлен"

# Копирование файла сервиса
echo -e "${YELLOW}📁 Копирование файла сервиса...${NC}"
cp axidi-bot.service /etc/systemd/system/
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Файл сервиса скопирован в /etc/systemd/system/${NC}"
else
    echo -e "${RED}❌ Ошибка копирования файла сервиса${NC}"
    exit 1
fi

# Перезагрузка systemd
echo -e "${YELLOW}🔄 Перезагрузка systemd...${NC}"
systemctl daemon-reload
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ systemd перезагружен${NC}"
else
    echo -e "${RED}❌ Ошибка перезагрузки systemd${NC}"
    exit 1
fi

# Включение автозапуска
echo -e "${YELLOW}🔧 Включение автозапуска...${NC}"
systemctl enable axidi-bot
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Автозапуск включен${NC}"
else
    echo -e "${RED}❌ Ошибка включения автозапуска${NC}"
    exit 1
fi

# Запуск сервиса
echo -e "${YELLOW}🚀 Запуск сервиса...${NC}"
systemctl start axidi-bot
sleep 5

# Проверка статуса
echo -e "${YELLOW}📊 Проверка статуса...${NC}"
if systemctl is-active --quiet axidi-bot; then
    echo -e "${GREEN}✅ Сервис успешно запущен${NC}"

    # Показать статус
    echo ""
    echo -e "${BLUE}📊 Статус сервиса:${NC}"
    systemctl status axidi-bot --no-pager -l

else
    echo -e "${RED}❌ Ошибка запуска сервиса${NC}"
    echo ""
    echo -e "${YELLOW}Логи ошибок:${NC}"
    journalctl -u axidi-bot --no-pager -l -n 20
    exit 1
fi

echo ""
echo -e "${GREEN}===============================================${NC}"
echo -e "${GREEN}✅ AXIDI BOT УСТАНОВЛЕН КАК СИСТЕМНЫЙ СЕРВИС${NC}"
echo -e "${GREEN}===============================================${NC}"
echo ""
echo -e "${YELLOW}📋 Команды управления сервисом:${NC}"
echo -e "${YELLOW}• systemctl start axidi-bot     - Запуск${NC}"
echo -e "${YELLOW}• systemctl stop axidi-bot      - Остановка${NC}"
echo -e "${YELLOW}• systemctl restart axidi-bot   - Перезапуск${NC}"
echo -e "${YELLOW}• systemctl status axidi-bot    - Статус${NC}"
echo -e "${YELLOW}• systemctl enable axidi-bot    - Автозапуск ВКЛ${NC}"
echo -e "${YELLOW}• systemctl disable axidi-bot   - Автозапуск ВЫКЛ${NC}"
echo ""
echo -e "${YELLOW}📋 Логи сервиса:${NC}"
echo -e "${YELLOW}• journalctl -u axidi-bot -f    - Просмотр логов${NC}"
echo -e "${YELLOW}• journalctl -u axidi-bot -n 50 - Последние 50 строк${NC}"
echo ""
echo -e "${BLUE}🔄 Сервис будет автоматически запускаться при перезагрузке${NC}"
echo -e "${GREEN}===============================================${NC}"
