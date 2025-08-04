#!/usr/bin/env python3
"""
Мониторинг воронки в реальном времени
Отслеживает отправку сообщений и предоставляет аналитику
"""

import asyncio
import sys
import os
import aiosqlite
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import json
import time

# Добавляем путь для импортов
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Импортируем конфигурацию
from onboarding_config import get_day_config, get_message_text, has_user_purchases, ONBOARDING_FUNNEL, MESSAGE_TEXTS

class RealTimeFunnelMonitor:
    """Монитор воронки в реальном времени"""
    
    def __init__(self, database_path: str):
        self.database_path = database_path
        self.monitoring_stats = {
            'start_time': datetime.now(),
            'welcome_messages_sent': 0,
            'reminders_sent': 0,
            'users_processed': 0,
            'users_filtered': 0,
            'errors': [],
            'message_log': [],
            'hourly_stats': {}
        }
    
    async def get_current_stats(self) -> Dict[str, Any]:
        """Получение текущей статистики из базы данных"""
        try:
            async with aiosqlite.connect(self.database_path) as conn:
                conn.row_factory = aiosqlite.Row
                c = await conn.cursor()
                
                # Общее количество пользователей
                await c.execute("SELECT COUNT(*) as total FROM users")
                total_users = (await c.fetchone())['total']
                
                # Пользователи без покупок
                await c.execute("""
                    SELECT COUNT(*) as count
                    FROM users u
                    WHERE u.user_id NOT IN (
                        SELECT user_id FROM payments WHERE status = 'succeeded'
                    )
                """)
                users_without_purchases = (await c.fetchone())['count']
                
                # Пользователи с приветственными сообщениями
                await c.execute("SELECT COUNT(*) as count FROM users WHERE welcome_message_sent = 1")
                users_with_welcome = (await c.fetchone())['count']
                
                # Пользователи с напоминаниями
                await c.execute("SELECT COUNT(*) as count FROM users WHERE last_reminder_type IS NOT NULL")
                users_with_reminders = (await c.fetchone())['count']
                
                # Статистика по типам напоминаний
                await c.execute("""
                    SELECT last_reminder_type, COUNT(*) as count
                    FROM users
                    WHERE last_reminder_type IS NOT NULL
                    GROUP BY last_reminder_type
                """)
                reminder_stats = {row['last_reminder_type']: row['count'] for row in await c.fetchall()}
                
                # Пользователи за последние 24 часа
                yesterday = datetime.now() - timedelta(days=1)
                await c.execute("""
                    SELECT COUNT(*) as count
                    FROM users
                    WHERE created_at >= ?
                """, (yesterday.strftime('%Y-%m-%d %H:%M:%S'),))
                new_users_24h = (await c.fetchone())['count']
                
                return {
                    'total_users': total_users,
                    'users_without_purchases': users_without_purchases,
                    'users_with_welcome': users_with_welcome,
                    'users_with_reminders': users_with_reminders,
                    'reminder_stats': reminder_stats,
                    'new_users_24h': new_users_24h
                }
                
        except Exception as e:
            self.monitoring_stats['errors'].append(f"Ошибка получения статистики: {e}")
            return {}
    
    async def simulate_funnel_execution(self):
        """Симуляция выполнения воронки"""
        print("\n🔄 СИМУЛЯЦИЯ ВЫПОЛНЕНИЯ ВОРОНКИ")
        print("="*50)
        
        try:
            # Получаем пользователей для приветственных сообщений
            async with aiosqlite.connect(self.database_path) as conn:
                conn.row_factory = aiosqlite.Row
                c = await conn.cursor()
                
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
                
                welcome_users = await c.fetchall()
            
            # Получаем пользователей для напоминаний
            async with aiosqlite.connect(self.database_path) as conn:
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
                
                reminder_users = await c.fetchall()
            
            # Обработка приветственных сообщений
            welcome_sent = 0
            for user in welcome_users:
                user_id = user['user_id']
                first_name = user['first_name']
                
                has_purchases = await has_user_purchases(user_id, self.database_path)
                if not has_purchases:
                    message_data = get_message_text("welcome", first_name)
                    
                    self.monitoring_stats['message_log'].append({
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
            
            # Обработка напоминаний
            reminders_sent = 0
            current_time = datetime.now()
            
            for user in reminder_users:
                user_id = user['user_id']
                first_name = user['first_name']
                created_at = user['created_at']
                last_reminder_type = user['last_reminder_type']
                
                # Проверяем условия фильтрации
                is_blocked = await self._is_user_blocked(user_id)
                if is_blocked:
                    continue
                
                has_purchases = await has_user_purchases(user_id, self.database_path)
                if has_purchases:
                    continue
                
                # Вычисляем дни с регистрации
                try:
                    registration_date = datetime.strptime(created_at, '%Y-%m-%d %H:%M:%S')
                    days_since_registration = (current_time.date() - registration_date.date()).days
                except ValueError:
                    continue
                
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
                    
                    self.monitoring_stats['message_log'].append({
                        'timestamp': datetime.now().isoformat(),
                        'user_id': user_id,
                        'user_name': first_name,
                        'message_type': message_type,
                        'text': message_data['text'][:100] + "...",
                        'button': message_data['button_text'],
                        'action': message_data['callback_data'],
                        'days_since_registration': days_since_registration
                    })
                    
                    print(f"📤 {message_type} отправлено пользователю {user_id} ({first_name})")
                    reminders_sent += 1
            
            self.monitoring_stats['welcome_messages_sent'] += welcome_sent
            self.monitoring_stats['reminders_sent'] += reminders_sent
            self.monitoring_stats['users_processed'] = len(welcome_users) + len(reminder_users)
            
            print(f"\n📊 Результаты симуляции:")
            print(f"  ✅ Welcome сообщений: {welcome_sent}")
            print(f"  ✅ Напоминаний: {reminders_sent}")
            print(f"  📋 Обработано пользователей: {len(welcome_users) + len(reminder_users)}")
            
            return welcome_sent + reminders_sent
            
        except Exception as e:
            error_msg = f"Ошибка симуляции воронки: {e}"
            self.monitoring_stats['errors'].append(error_msg)
            print(f"❌ {error_msg}")
            return 0
    
    async def _is_user_blocked(self, user_id: int) -> bool:
        """Проверка блокировки пользователя"""
        try:
            async with aiosqlite.connect(self.database_path) as conn:
                c = await conn.cursor()
                await c.execute("SELECT is_blocked FROM users WHERE user_id = ?", (user_id,))
                result = await c.fetchone()
                return bool(result[0]) if result else False
        except Exception as e:
            self.monitoring_stats['errors'].append(f"Ошибка проверки блокировки: {e}")
            return False
    
    def generate_live_report(self):
        """Генерация живого отчета"""
        print("\n" + "="*80)
        print("📊 ЖИВОЙ ОТЧЕТ МОНИТОРИНГА ВОРОНКИ")
        print("="*80)
        
        # Время работы
        uptime = datetime.now() - self.monitoring_stats['start_time']
        print(f"⏱️ Время работы мониторинга: {uptime}")
        
        # Статистика сообщений
        total_messages = self.monitoring_stats['welcome_messages_sent'] + self.monitoring_stats['reminders_sent']
        print(f"📤 Всего отправлено сообщений: {total_messages}")
        print(f"  👋 Welcome: {self.monitoring_stats['welcome_messages_sent']}")
        print(f"  📬 Напоминания: {self.monitoring_stats['reminders_sent']}")
        
        # Статистика пользователей
        print(f"👥 Обработано пользователей: {self.monitoring_stats['users_processed']}")
        print(f"⏭️ Отфильтровано пользователей: {self.monitoring_stats['users_filtered']}")
        
        # Последние сообщения
        if self.monitoring_stats['message_log']:
            print(f"\n📋 ПОСЛЕДНИЕ СООБЩЕНИЯ ({len(self.monitoring_stats['message_log'][-5:])}):")
            for msg in self.monitoring_stats['message_log'][-5:]:
                timestamp = datetime.fromisoformat(msg['timestamp']).strftime('%H:%M:%S')
                print(f"  [{timestamp}] {msg['message_type']} → {msg['user_name']} (ID: {msg['user_id']})")
        
        # Ошибки
        if self.monitoring_stats['errors']:
            print(f"\n❌ ОШИБКИ ({len(self.monitoring_stats['errors'])}):")
            for error in self.monitoring_stats['errors'][-3:]:  # Последние 3 ошибки
                print(f"  • {error}")
        
        # Анализ цен
        if self.monitoring_stats['message_log']:
            prices = []
            for msg in self.monitoring_stats['message_log']:
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
                print(f"  📋 Всего сообщений с ценами: {len(prices)}")
    
    async def run_continuous_monitoring(self, interval_seconds: int = 60):
        """Запуск непрерывного мониторинга"""
        print(f"🔍 ЗАПУСК НЕПРЕРЫВНОГО МОНИТОРИНГА (интервал: {interval_seconds}с)")
        print("="*60)
        
        try:
            while True:
                print(f"\n🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                print("-" * 40)
                
                # Получаем текущую статистику
                current_stats = await self.get_current_stats()
                if current_stats:
                    print(f"📊 Текущая статистика:")
                    print(f"  👥 Всего пользователей: {current_stats['total_users']}")
                    print(f"  💳 Без покупок: {current_stats['users_without_purchases']}")
                    print(f"  👋 С приветствием: {current_stats['users_with_welcome']}")
                    print(f"  📬 С напоминаниями: {current_stats['users_with_reminders']}")
                    print(f"  🆕 Новых за 24ч: {current_stats['new_users_24h']}")
                
                # Симулируем выполнение воронки
                messages_sent = await self.simulate_funnel_execution()
                
                # Генерируем отчет
                self.generate_live_report()
                
                # Сохраняем почасовую статистику
                current_hour = datetime.now().strftime('%Y-%m-%d %H:00')
                if current_hour not in self.monitoring_stats['hourly_stats']:
                    self.monitoring_stats['hourly_stats'][current_hour] = {
                        'messages_sent': 0,
                        'users_processed': 0,
                        'errors': 0
                    }
                
                self.monitoring_stats['hourly_stats'][current_hour]['messages_sent'] += messages_sent
                self.monitoring_stats['hourly_stats'][current_hour]['users_processed'] += self.monitoring_stats['users_processed']
                
                print(f"\n⏳ Ожидание {interval_seconds} секунд до следующей проверки...")
                await asyncio.sleep(interval_seconds)
                
        except KeyboardInterrupt:
            print("\n🛑 Мониторинг остановлен пользователем")
        except Exception as e:
            print(f"\n❌ Ошибка мониторинга: {e}")
            self.monitoring_stats['errors'].append(f"Критическая ошибка: {e}")

async def main():
    """Главная функция"""
    print("🔬 МОНИТОРИНГ ВОРОНКИ В РЕАЛЬНОМ ВРЕМЕНИ")
    print("="*50)
    
    # Проверяем наличие базы данных
    database_path = "bot_database.db"  # Путь к реальной базе данных
    if not os.path.exists(database_path):
        print(f"❌ База данных не найдена: {database_path}")
        print("Создаем тестовую базу данных...")
        database_path = "test_monitor.db"
        
        # Создаем тестовую базу
        async with aiosqlite.connect(database_path) as conn:
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
        
        print(f"✅ Создана тестовая база данных: {database_path}")
    
    monitor = RealTimeFunnelMonitor(database_path)
    
    # Запускаем мониторинг
    await monitor.run_continuous_monitoring(interval_seconds=30)  # Проверка каждые 30 секунд
    
    return 0

if __name__ == "__main__":
    sys.exit(asyncio.run(main())) 