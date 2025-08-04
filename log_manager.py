#!/usr/bin/env python3
"""
Система автоматического управления логами
- Сохранение логов в историю по дням
- Автоочистка основных файлов логов
- Организация по типам логов
"""

import os
import shutil
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from logger import get_logger

class LogManager:
    def __init__(self):
        self.log_dir = Path("logs")
        self.history_dir = Path("logs/history")
        self.main_log = Path("bot.log")

        # Создаем структуру директорий
        self._create_directories()

        # Логгер для самого менеджера логов
        self.logger = get_logger('main')

        # Файлы логов для управления
        self.log_files = {
            'main': self.main_log,
            'database': self.log_dir / 'database.log',
            'generation': self.log_dir / 'generation.log',
            'keyboards': self.log_dir / 'keyboards.log',
            'api': self.log_dir / 'api.log',
            'payments': self.log_dir / 'payments.log',
            'errors': self.log_dir / 'errors.log'
        }

        # Поддиректории для истории
        self.history_subdirs = {
            'main': self.history_dir / 'main',
            'database': self.history_dir / 'database',
            'generation': self.history_dir / 'generation',
            'keyboards': self.history_dir / 'keyboards',
            'api': self.history_dir / 'api',
            'payments': self.history_dir / 'payments',
            'errors': self.history_dir / 'errors'
        }

    def _create_directories(self):
        """Создает необходимые директории"""
        directories = [
            self.log_dir,
            self.history_dir,
            self.history_dir / 'main',
            self.history_dir / 'database',
            self.history_dir / 'generation',
            self.history_dir / 'keyboards',
            self.history_dir / 'api',
            self.history_dir / 'payments',
            self.history_dir / 'errors'
        ]

        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)

    def _get_history_filename(self, log_type: str) -> str:
        """Генерирует имя файла для исторического лога"""
        today = datetime.now().strftime('%Y-%m-%d')
        return f"{log_type}_{today}.log"

    def _archive_log_file(self, log_type: str, source_path: Path) -> bool:
        """Архивирует файл лога в историю"""
        try:
            if not source_path.exists():
                return False

            # Проверяем размер файла
            file_size = source_path.stat().st_size
            if file_size == 0:
                return False

            # Создаем имя файла для истории
            history_filename = self._get_history_filename(log_type)
            history_path = self.history_subdirs[log_type] / history_filename

            # Если файл истории уже существует, добавляем к нему
            if history_path.exists():
                # Читаем содержимое исходного файла
                with open(source_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Добавляем к существующему файлу истории
                with open(history_path, 'a', encoding='utf-8') as f:
                    f.write(f"\n{'='*80}\n")
                    f.write(f"АРХИВАЦИЯ: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"{'='*80}\n")
                    f.write(content)
            else:
                # Создаем новый файл истории
                shutil.copy2(source_path, history_path)

            self.logger.info(f"Архивирован лог {log_type}: {source_path} -> {history_path}")
            return True

        except Exception as e:
            self.logger.error(f"Ошибка архивирования лога {log_type}: {e}")
            return False

    def _clear_log_file(self, log_type: str, source_path: Path) -> bool:
        """Очищает файл лога"""
        try:
            if not source_path.exists():
                return False

                        # Очищаем файл, сохраняя только последние 10 строк
            try:
                with open(source_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
            except UnicodeDecodeError:
                try:
                    with open(source_path, 'r', encoding='latin-1') as f:
                        lines = f.readlines()
                except Exception as e:
                    self.logger.error(f"Не удается прочитать файл {source_path}: {e}")
                    return False

            # Сохраняем последние 10 строк
            if len(lines) > 10:
                with open(source_path, 'w', encoding='utf-8') as f:
                    f.write(f"# Файл очищен {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"# Сохранены последние 10 строк из {len(lines)} строк\n")
                    f.write("="*80 + "\n")
                    for line in lines[-10:]:
                        f.write(line)
            else:
                # Если строк меньше 10, просто очищаем
                with open(source_path, 'w', encoding='utf-8') as f:
                    f.write(f"# Файл очищен {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

            self.logger.info(f"Очищен лог {log_type}: {source_path}")
            return True

        except Exception as e:
            self.logger.error(f"Ошибка очистки лога {log_type}: {e}")
            return False

    def process_log_file(self, log_type: str):
        """Обрабатывает один файл лога: архивирует и очищает"""
        source_path = self.log_files[log_type]

        if not source_path.exists():
            return

        # Проверяем размер файла
        file_size = source_path.stat().st_size
        if file_size == 0:
            return

        # Архивируем файл
        archived = self._archive_log_file(log_type, source_path)

        if archived:
            # Очищаем файл
            self._clear_log_file(log_type, source_path)

    def process_all_logs(self):
        """Обрабатывает все файлы логов"""
        self.logger.info("Начинаю обработку всех логов...")

        processed_count = 0
        for log_type, source_path in self.log_files.items():
            try:
                self.process_log_file(log_type)
                processed_count += 1
            except Exception as e:
                self.logger.error(f"Ошибка обработки лога {log_type}: {e}")

        self.logger.info(f"Обработано логов: {processed_count}")

    def cleanup_old_history(self, days_to_keep: int = 30):
        """Удаляет старые файлы истории"""
        self.logger.info(f"Начинаю очистку истории старше {days_to_keep} дней...")

        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        deleted_count = 0

        for log_type, history_dir in self.history_subdirs.items():
            if not history_dir.exists():
                continue

            for history_file in history_dir.glob("*.log"):
                try:
                    # Парсим дату из имени файла
                    filename = history_file.stem
                    if '_' in filename:
                        date_str = filename.split('_')[-1]
                        try:
                            file_date = datetime.strptime(date_str, '%Y-%m-%d')
                            if file_date < cutoff_date:
                                history_file.unlink()
                                deleted_count += 1
                                self.logger.info(f"Удален старый файл истории: {history_file}")
                        except ValueError:
                            # Если не удается распарсить дату, пропускаем
                            continue
                except Exception as e:
                    self.logger.error(f"Ошибка при удалении {history_file}: {e}")

        self.logger.info(f"Удалено старых файлов истории: {deleted_count}")

    def get_history_stats(self):
        """Показывает статистику истории логов"""
        print("📊 СТАТИСТИКА ИСТОРИИ ЛОГОВ")
        print("=" * 60)

        total_files = 0
        total_size = 0

        for log_type, history_dir in self.history_subdirs.items():
            if not history_dir.exists():
                continue

            files = list(history_dir.glob("*.log"))
            if not files:
                continue

            # Подсчитываем размер
            dir_size = sum(f.stat().st_size for f in files)
            total_files += len(files)
            total_size += dir_size

            print(f"\n{log_type.upper()}:")
            print(f"  Файлов: {len(files)}")
            print(f"  Размер: {dir_size / (1024*1024):.2f} MB")

            # Показываем последние файлы
            recent_files = sorted(files, key=lambda x: x.stat().st_mtime, reverse=True)[:5]
            print(f"  Последние файлы:")
            for f in recent_files:
                modified = datetime.fromtimestamp(f.stat().st_mtime)
                size = f.stat().st_size / 1024  # KB
                print(f"    {f.name} ({size:.1f} KB, {modified.strftime('%Y-%m-%d')})")

        print(f"\nОБЩАЯ СТАТИСТИКА:")
        print(f"  Всего файлов: {total_files}")
        print(f"  Общий размер: {total_size / (1024*1024):.2f} MB")

    async def start_scheduler(self):
        """Запускает асинхронный планировщик задач"""
        scheduler = AsyncIOScheduler()

        # Очистка логов каждый час
        scheduler.add_job(
            self.process_all_logs,
            CronTrigger(minute=0),  # Каждый час в 00 минут
            id='process_logs',
            name='Очистка логов каждый час'
        )

        # Очистка старой истории каждый день в 2:00
        scheduler.add_job(
            self.cleanup_old_history,
            CronTrigger(hour=2, minute=0),  # Каждый день в 02:00
            id='cleanup_history',
            name='Очистка старой истории'
        )

        scheduler.start()

        self.logger.info("Асинхронный планировщик логов запущен")
        self.logger.info("Очистка логов: каждый час в 00 минут")
        self.logger.info("Очистка истории: каждый день в 02:00")

        try:
            # Держим планировщик запущенным
            while True:
                await asyncio.sleep(60)  # Проверяем каждую минуту
        except KeyboardInterrupt:
            scheduler.shutdown()
            self.logger.info("Планировщик логов остановлен")

def main():
    """Основная функция"""
    import argparse

    parser = argparse.ArgumentParser(description='Менеджер логов')
    parser.add_argument('--process', action='store_true', help='Обработать все логи сейчас')
    parser.add_argument('--cleanup-history', type=int, metavar='DAYS', help='Очистить историю старше N дней')
    parser.add_argument('--stats', action='store_true', help='Показать статистику истории')
    parser.add_argument('--start-scheduler', action='store_true', help='Запустить планировщик')

    args = parser.parse_args()

    manager = LogManager()

    if args.process:
        print("🔄 Обработка всех логов...")
        manager.process_all_logs()
        print("✅ Обработка завершена")

    elif args.cleanup_history:
        print(f"🗑️ Очистка истории старше {args.cleanup_history} дней...")
        manager.cleanup_old_history(args.cleanup_history)
        print("✅ Очистка завершена")

    elif args.stats:
        manager.get_history_stats()

    elif args.start_scheduler:
        print("🚀 Запуск планировщика логов...")
        asyncio.run(manager.start_scheduler())

    else:
        print("📋 Менеджер логов")
        print("=" * 40)
        print("Использование:")
        print("  --process              - Обработать все логи сейчас")
        print("  --cleanup-history N    - Очистить историю старше N дней")
        print("  --stats                - Показать статистику истории")
        print("  --start-scheduler      - Запустить планировщик")
        print()
        print("Примеры:")
        print("  python3 log_manager.py --process")
        print("  python3 log_manager.py --cleanup-history 30")
        print("  python3 log_manager.py --stats")
        print("  python3 log_manager.py --start-scheduler")

if __name__ == "__main__":
    main()
