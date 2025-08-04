#!/usr/bin/env python3
"""
Живое тестирование воронки с мониторингом в реальном времени
Позволяет отслеживать отправку сообщений и анализировать работу воронки
"""

import asyncio
import sys
import os
import aiosqlite
import tempfile
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import json

# Добавляем путь для импортов
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Импортируем конфигурацию
from onboarding_config import get_day_config, get_message_text, has_user_purchases, ONBOARDING_FUNNEL, MESSAGE_TEXTS

class LiveFunnelMonitor:
    """Монитор воронки в реальном времени"""
    
    def __init__(self):
        self.test_db = None
        self.monitoring_data = {
            'users_processed': 0,
            'messages_sent': 0,
            'users_filtered_out': 0,
            'errors': [],
            'message_log': []
        }
    
    async def setup_monitoring_database(self):
        """Создание базы данных для мониторинга"""
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        temp_file.close()
        self.test_db = temp_file.name
        
        async with aiosqlite.connect(self.test_db) as conn:
            # Создаем таблицы как в реальной системе
            await conn.execute("""
                CREATE TABLE users (
                    user_id INTEGER PRIMARY KEY,
                    first_name TEXT,
                    username TEXT,
                    created_at TEXT,
                    welcome_message_sent INTEGER DEFAULT 0,
                    first_purchase INTEGER DEFAULT 1,
                    is_blocked INTEGER DEFAULT 0,
                    last_reminder_type TEXT,
                    last_reminder_sent TEXT,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            await conn.execute("""
                CREATE TABLE payments (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER,
                    amount REAL,
                    status TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            """)
            
            await conn.commit()
        
        print(f"✅ База данных для мониторинга создана: {self.test_db}")
    
    async def create_diverse_test_data(self):
        """Создание разнообразных тестовых данных для полного покрытия"""
        now = datetime.now()
        
        async with aiosqlite.connect(self.test_db) as conn:
            # Создаем пользователей с разными сценариями
            test_scenarios = [
                # Сценарий 1: Новый пользователь (должен получить welcome)
                {
                    'user_id': 3001, 'name': 'Новый Алексей', 'username': 'new_alex',
                    'created_at': (now - timedelta(hours=2)).strftime('%Y-%m-%d %H:%M:%S'),
                    'welcome_sent': 0, 'blocked': 0, 'last_reminder': None,
                    'expected': 'welcome'
                },
                
                # Сценарий 2: Пользователь для reminder_day2
                {
                    'user_id': 3002, 'name': 'День2 Мария', 'username': 'day2_maria',
                    'created_at': (now - timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S'),
                    'welcome_sent': 1, 'blocked': 0, 'last_reminder': None,
                    'expected': 'reminder_day2'
                },
                
                # Сценарий 3: Пользователь для reminder_day3
                {
                    'user_id': 3003, 'name': 'День3 Иван', 'username': 'day3_ivan',
                    'created_at': (now - timedelta(days=2)).strftime('%Y-%m-%d %H:%M:%S'),
                    'welcome_sent': 1, 'blocked': 0, 'last_reminder': 'reminder_day2',
                    'expected': 'reminder_day3'
                },
                
                # Сценарий 4: Пользователь для reminder_day4
                {
                    'user_id': 3004, 'name': 'День4 Елена', 'username': 'day4_elena',
                    'created_at': (now - timedelta(days=3)).strftime('%Y-%m-%d %H:%M:%S'),
                    'welcome_sent': 1, 'blocked': 0, 'last_reminder': 'reminder_day3',
                    'expected': 'reminder_day4'
                },
                
                # Сценарий 5: Пользователь для reminder_day5
                {
                    'user_id': 3005, 'name': 'День5 Петр', 'username': 'day5_petr',
                    'created_at': (now - timedelta(days=5)).strftime('%Y-%m-%d %H:%M:%S'),
                    'welcome_sent': 1, 'blocked': 0, 'last_reminder': 'reminder_day4',
                    'expected': 'reminder_day5'
                },
                
                # Сценарий 6: Пользователь с покупкой (НЕ должен получать)
                {
                    'user_id': 3006, 'name': 'С покупкой Анна', 'username': 'paid_anna',
                    'created_at': (now - timedelta(days=2)).strftime('%Y-%m-%d %H:%M:%S'),
                    'welcome_sent': 1, 'blocked': 0, 'last_reminder': None,
                    'expected': 'none', 'has_payment': True
                },
                
                # Сценарий 7: Заблокированный пользователь
                {
                    'user_id': 3007, 'name': 'Заблокированный Сергей', 'username': 'blocked_sergey',
                    'created_at': (now - timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S'),
                    'welcome_sent': 0, 'blocked': 1, 'last_reminder': None,
                    'expected': 'none'
                },
                
                # Сценарий 8: Пользователь, уже получивший текущее напоминание
                {
                    'user_id': 3008, 'name': 'Уже получил Ольга', 'username': 'already_got_olga',
                    'created_at': (now - timedelta(days=2)).strftime('%Y-%m-%d %H:%M:%S'),
                    'welcome_sent': 1, 'blocked': 0, 'last_reminder': 'reminder_day3',
                    'expected': 'none'
                },
                
                # Сценарий 9: Пользователь для тестирования edge case
                {
                    'user_id': 3009, 'name': 'Edge Case Дмитрий', 'username': 'edge_dmitry',
                    'created_at': (now - timedelta(days=10)).strftime('%Y-%m-%d %H:%M:%S'),
                    'welcome_sent': 1, 'blocked': 0, 'last_reminder': 'reminder_day5',
                    'expected': 'none'
                }
            ]
            
            for scenario in test_scenarios:
                await conn.execute("""
                    INSERT INTO users (user_id, first_name, username, created_at, welcome_message_sent,
                                     first_purchase, is_blocked, last_reminder_type, last_reminder_sent)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    scenario['user_id'], scenario['name'], scenario['username'],
                    scenario['created_at'], scenario['welcome_sent'], 1,
                    scenario['blocked'], scenario['last_reminder'], None
                ))
                
                # Добавляем покупку если нужно
                if scenario.get('has_payment'):
                    await conn.execute("""
                        INSERT INTO payments (user_id, amount, status)
                        VALUES (?, ?, ?)
                    """, (scenario['user_id'], 599.0, "succeeded"))
            
            await conn.commit()
        
        print("✅ Разнообразные тестовые данные созданы")
        print("📊 Сценарии тестирования:")
        for scenario in test_scenarios:
            print(f"  {scenario['name']} (ID: {scenario['user_id']}) - ожидается: {scenario['expected']}")
    
    async def simulate_welcome_message_sending(self):
        """Симуляция отправки приветственных сообщений"""
        print("\n👋 СИМУЛЯЦИЯ ПРИВЕТСТВЕННЫХ СООБЩЕНИЙ")
        print("="*50)
        
        async with aiosqlite.connect(self.test_db) as conn:
            conn.row_factory = aiosqlite.Row
            c = await conn.cursor()
            
            # Получаем пользователей для приветственного сообщения
            await c.execute("""
                SELECT user_id, first_name, username, created_at
                FROM users
                WHERE welcome_message_sent = 0
                AND first_purchase = 1
                AND created_at <= datetime('now', '-1 hour')
                AND is_blocked = 0
                AND user_id NOT IN (
                    SELECT user_id FROM payments WHERE status = 'succeeded'
                )
            """)
            
            users = await c.fetchall()
        
        welcome_sent = 0
        for user in users:
            user_id = user['user_id']
            first_name = user['first_name']
            
            # Проверяем дополнительные условия
            has_purchases = await has_user_purchases(user_id, self.test_db)
            if not has_purchases:
                message_data = get_message_text("welcome", first_name)
                
                # Логируем отправку
                self.monitoring_data['message_log'].append({
                    'timestamp': datetime.now().isoformat(),
                    'user_id': user_id,
                    'user_name': first_name,
                    'message_type': 'welcome',
                    'text': message_data['text'][:100] + "...",
                    'button': message_data['button_text'],
                    'action': message_data['callback_data']
                })
                
                print(f"📤 Welcome отправлено пользователю {user_id} ({first_name})")
                welcome_sent += 1
                
                # Обновляем статус в базе
                async with aiosqlite.connect(self.test_db) as conn:
                    c = await conn.cursor()
                    await c.execute(
                        "UPDATE users SET welcome_message_sent = 1 WHERE user_id = ?",
                        (user_id,)
                    )
                    await conn.commit()
        
        self.monitoring_data['messages_sent'] += welcome_sent
        print(f"✅ Отправлено {welcome_sent} приветственных сообщений")
        
        return welcome_sent
    
    async def simulate_daily_reminders_sending(self):
        """Симуляция отправки ежедневных напоминаний"""
        print("\n📬 СИМУЛЯЦИЯ ЕЖЕДНЕВНЫХ НАПОМИНАНИЙ")
        print("="*50)
        
        # Получаем пользователей для напоминаний
        async with aiosqlite.connect(self.test_db) as conn:
            conn.row_factory = aiosqlite.Row
            c = await conn.cursor()
            
            await c.execute("""
                SELECT user_id, first_name, username, created_at, last_reminder_type
                FROM users
                WHERE is_blocked = 0
                AND user_id NOT IN (
                    SELECT user_id FROM payments WHERE status = 'succeeded'
                )
                AND created_at IS NOT NULL
            """)
            
            users = await c.fetchall()
        
        current_time = datetime.now()
        reminders_sent = 0
        filtered_out = 0
        
        for user in users:
            user_id = user['user_id']
            first_name = user['first_name']
            created_at = user['created_at']
            last_reminder_type = user['last_reminder_type']
            
            print(f"\n👤 Обработка пользователя {user_id} ({first_name})...")
            
            # Проверяем условия фильтрации
            is_blocked = await self._is_user_blocked(user_id)
            if is_blocked:
                print(f"  ❌ Пользователь заблокирован")
                filtered_out += 1
                continue
            
            is_old_user = await self._is_old_user(user_id)
            if is_old_user:
                print(f"  ❌ Старый пользователь")
                filtered_out += 1
                continue
            
            has_purchases = await has_user_purchases(user_id, self.test_db)
            if has_purchases:
                print(f"  ❌ Пользователь имеет покупки")
                filtered_out += 1
                continue
            
            # Вычисляем дни с регистрации
            try:
                registration_date = datetime.strptime(created_at, '%Y-%m-%d %H:%M:%S')
                days_since_registration = (current_time.date() - registration_date.date()).days
            except ValueError:
                print(f"  ❌ Неверный формат даты: {created_at}")
                filtered_out += 1
                continue
            
            print(f"  📅 Дней с регистрации: {days_since_registration}")
            print(f"  📝 Последнее напоминание: {last_reminder_type}")
            
            # Определяем тип напоминания
            message_type = None
            if days_since_registration == 1 and last_reminder_type != "reminder_day2":
                message_type = "reminder_day2"
            elif days_since_registration == 2 and last_reminder_type != "reminder_day3":
                message_type = "reminder_day3"
            elif days_since_registration == 3 and last_reminder_type != "reminder_day4":
                message_type = "reminder_day4"
            elif days_since_registration >= 4 and last_reminder_type != "reminder_day5":
                message_type = "reminder_day5"
            
            if message_type:
                message_data = get_message_text(message_type, first_name)
                
                # Логируем отправку
                self.monitoring_data['message_log'].append({
                    'timestamp': datetime.now().isoformat(),
                    'user_id': user_id,
                    'user_name': first_name,
                    'message_type': message_type,
                    'text': message_data['text'][:100] + "...",
                    'button': message_data['button_text'],
                    'action': message_data['callback_data'],
                    'days_since_registration': days_since_registration
                })
                
                print(f"  ✅ Отправляем {message_type}")
                print(f"  💰 Цена: {message_data['text'].split('₽')[0].split()[-1]}₽")
                
                # Обновляем статус в базе
                async with aiosqlite.connect(self.test_db) as conn:
                    c = await conn.cursor()
                    await c.execute(
                        "UPDATE users SET last_reminder_type = ?, last_reminder_sent = ? WHERE user_id = ?",
                        (message_type, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), user_id)
                    )
                    await conn.commit()
                
                reminders_sent += 1
            else:
                print(f"  ⏭️ Напоминание не требуется")
                filtered_out += 1
        
        self.monitoring_data['messages_sent'] += reminders_sent
        self.monitoring_data['users_filtered_out'] += filtered_out
        self.monitoring_data['users_processed'] = len(users)
        
        print(f"\n📊 Итого:")
        print(f"  ✅ Отправлено напоминаний: {reminders_sent}")
        print(f"  ⏭️ Отфильтровано пользователей: {filtered_out}")
        print(f"  📋 Обработано пользователей: {len(users)}")
        
        return reminders_sent
    
    async def _is_user_blocked(self, user_id: int) -> bool:
        """Проверка блокировки пользователя"""
        async with aiosqlite.connect(self.test_db) as conn:
            c = await conn.cursor()
            await c.execute("SELECT is_blocked FROM users WHERE user_id = ?", (user_id,))
            result = await c.fetchone()
            return bool(result[0]) if result else False
    
    async def _is_old_user(self, user_id: int) -> bool:
        """Проверка старого пользователя"""
        # В тесте все пользователи новые
        return False
    
    def generate_detailed_report(self):
        """Генерация детального отчета"""
        print("\n" + "="*80)
        print("📊 ДЕТАЛЬНЫЙ ОТЧЕТ МОНИТОРИНГА ВОРОНКИ")
        print("="*80)
        
        # Статистика
        print(f"📈 СТАТИСТИКА:")
        print(f"  👥 Обработано пользователей: {self.monitoring_data['users_processed']}")
        print(f"  📤 Отправлено сообщений: {self.monitoring_data['messages_sent']}")
        print(f"  ⏭️ Отфильтровано пользователей: {self.monitoring_data['users_filtered_out']}")
        
        # Анализ сообщений
        if self.monitoring_data['message_log']:
            print(f"\n📋 ЛОГ СООБЩЕНИЙ ({len(self.monitoring_data['message_log'])}):")
            
            # Группируем по типам
            message_types = {}
            for msg in self.monitoring_data['message_log']:
                msg_type = msg['message_type']
                if msg_type not in message_types:
                    message_types[msg_type] = []
                message_types[msg_type].append(msg)
            
            for msg_type, messages in message_types.items():
                print(f"\n  📝 {msg_type.upper()} ({len(messages)} сообщений):")
                for msg in messages:
                    print(f"    👤 {msg['user_name']} (ID: {msg['user_id']}) - {msg['text'][:60]}...")
                    if 'days_since_registration' in msg:
                        print(f"      📅 Дней с регистрации: {msg['days_since_registration']}")
        
        # Анализ цен
        if self.monitoring_data['message_log']:
            prices = []
            for msg in self.monitoring_data['message_log']:
                if '₽' in msg['text']:
                    try:
                        price = int(msg['text'].split('₽')[0].split()[-1])
                        prices.append(price)
                    except:
                        pass
            
            if prices:
                print(f"\n💰 АНАЛИЗ ЦЕН:")
                print(f"  📊 Средняя цена: {sum(prices) / len(prices):.0f}₽")
                print(f"  📈 Максимальная цена: {max(prices)}₽")
                print(f"  📉 Минимальная цена: {min(prices)}₽")
                print(f"  📋 Все цены: {sorted(prices)}")
        
        # Ошибки
        if self.monitoring_data['errors']:
            print(f"\n❌ ОШИБКИ ({len(self.monitoring_data['errors'])}):")
            for error in self.monitoring_data['errors']:
                print(f"  • {error}")
        
        # Сохранение отчета в файл
        report_file = f"funnel_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(self.monitoring_data, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 Отчет сохранен в файл: {report_file}")
    
    async def cleanup(self):
        """Очистка"""
        if self.test_db and os.path.exists(self.test_db):
            os.unlink(self.test_db)
            print("✅ База данных мониторинга удалена")

async def main():
    """Главная функция"""
    print("🔬 ЖИВОЕ ТЕСТИРОВАНИЕ ВОРОНКИ")
    print("="*50)
    
    monitor = LiveFunnelMonitor()
    
    try:
        # Подготовка
        await monitor.setup_monitoring_database()
        await monitor.create_diverse_test_data()
        
        # Запуск симуляций
        welcome_count = await monitor.simulate_welcome_message_sending()
        reminders_count = await monitor.simulate_daily_reminders_sending()
        
        # Генерация отчета
        monitor.generate_detailed_report()
        
        print(f"\n🏁 ИТОГОВЫЙ РЕЗУЛЬТАТ:")
        print(f"✅ Welcome сообщений: {welcome_count}")
        print(f"✅ Напоминаний: {reminders_count}")
        print(f"✅ Всего отправлено: {welcome_count + reminders_count}")
        
        return 0
        
    finally:
        await monitor.cleanup()

if __name__ == "__main__":
    sys.exit(asyncio.run(main())) 