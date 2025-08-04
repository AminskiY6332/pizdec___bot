#!/usr/bin/env python3
"""
Одноразовый скрипт для изменения имени бота через Telegram Bot API
Автор: AXIDI
"""

import asyncio
import aiohttp
import sys

# Токен бота
BOT_TOKEN = "7778101895:AAF1pdK3KWIPH32Or-71gAWltwvBrZAtUr4"

# Новое имя бота
NEW_BOT_NAME = "PixelPie by AXIDI 🍪 НЕЙРОФОТОСЕССИЯ"

async def set_bot_name(token: str, name: str) -> bool:
    """
    Изменяет имя бота через Telegram Bot API

    Args:
        token: Токен бота
        name: Новое имя бота

    Returns:
        bool: True если успешно, False если ошибка
    """
    url = f"https://api.telegram.org/bot{token}/setMyName"

    data = {
        "name": name
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=data) as response:
                result = await response.json()

                if response.status == 200 and result.get("ok"):
                    print(f"✅ Имя бота успешно изменено на: '{name}'")
                    return True
                else:
                    print(f"❌ Ошибка при изменении имени бота:")
                    print(f"   Status: {response.status}")
                    print(f"   Response: {result}")
                    return False

    except Exception as e:
        print(f"❌ Исключение при запросе к API: {e}")
        return False

async def get_current_bot_info(token: str):
    """
    Получает текущую информацию о боте

    Args:
        token: Токен бота
    """
    url = f"https://api.telegram.org/bot{token}/getMe"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                result = await response.json()

                if response.status == 200 and result.get("ok"):
                    bot_info = result["result"]
                    print(f"📋 Текущая информация о боте:")
                    print(f"   ID: {bot_info.get('id')}")
                    print(f"   Username: @{bot_info.get('username')}")
                    print(f"   Имя: {bot_info.get('first_name', 'Не установлено')}")
                    print(f"   Описание: {bot_info.get('description', 'Не установлено')}")
                    return bot_info
                else:
                    print(f"❌ Ошибка получения информации о боте: {result}")
                    return None

    except Exception as e:
        print(f"❌ Исключение при получении информации о боте: {e}")
        return None

async def main():
    """Основная функция скрипта"""
    print("🤖 Скрипт изменения имени бота AXIDI")
    print("=" * 50)

    # Получаем текущую информацию о боте
    print("📡 Получение текущей информации о боте...")
    current_info = await get_current_bot_info(BOT_TOKEN)

    if not current_info:
        print("❌ Не удалось получить информацию о боте. Проверьте токен.")
        sys.exit(1)

    print()

    # Подтверждение изменения
    print(f"🔄 Изменение имени бота на: '{NEW_BOT_NAME}'")
    print()

    # Изменяем имя бота
    success = await set_bot_name(BOT_TOKEN, NEW_BOT_NAME)

    if success:
        print()
        print("🎉 Имя бота успешно изменено!")

        # Проверяем результат
        print("📡 Проверка изменений...")
        await asyncio.sleep(1)  # Небольшая задержка
        updated_info = await get_current_bot_info(BOT_TOKEN)

        if updated_info and updated_info.get('first_name') == NEW_BOT_NAME:
            print("✅ Изменения подтверждены!")
        else:
            print("⚠️ Изменения пока не отображаются, но запрос был успешным")

    else:
        print("❌ Не удалось изменить имя бота")
        sys.exit(1)

if __name__ == "__main__":
    print("🚀 Запуск скрипта...")
    asyncio.run(main())
    print("✨ Скрипт завершен!")
