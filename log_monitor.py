#!/usr/bin/env python3
"""
Мониторинг логов в реальном времени
Показывает новые записи в логах по мере их появления
"""

import os
import time
import re
from datetime import datetime
from collections import defaultdict
import argparse

class LogMonitor:
    def __init__(self, log_dir="logs", main_log="bot.log"):
        self.log_dir = log_dir
        self.main_log = main_log
        self.file_positions = {}
        self.log_files = {
            'main': main_log,
            'database': f'{log_dir}/database.log',
            'generation': f'{log_dir}/generation.log',
            'keyboards': f'{log_dir}/keyboards.log',
            'api': f'{log_dir}/api.log',
            'payments': f'{log_dir}/payments.log',
            'errors': f'{log_dir}/errors.log'
        }

        # Цвета для разных типов логов
        self.colors = {
            'main': '\033[36m',      # Cyan
            'database': '\033[32m',   # Green
            'generation': '\033[33m', # Yellow
            'keyboards': '\033[35m',  # Magenta
            'api': '\033[34m',        # Blue
            'payments': '\033[31m',   # Red
            'errors': '\033[91m'      # Bright Red
        }

        self.reset_color = '\033[0m'

        # Инициализация позиций файлов
        self._init_file_positions()

    def _init_file_positions(self):
        """Инициализирует позиции файлов"""
        for log_type, file_path in self.log_files.items():
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        f.seek(0, 2)  # Перемещаемся в конец файла
                        self.file_positions[log_type] = f.tell()
                except Exception:
                    self.file_positions[log_type] = 0
            else:
                self.file_positions[log_type] = 0

    def _get_new_lines(self, log_type, file_path):
        """Получает новые строки из файла лога"""
        if not os.path.exists(file_path):
            return []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                f.seek(self.file_positions[log_type])
                new_lines = f.readlines()
                self.file_positions[log_type] = f.tell()
                return new_lines
        except UnicodeDecodeError:
            try:
                with open(file_path, 'r', encoding='latin-1') as f:
                    f.seek(self.file_positions[log_type])
                    new_lines = f.readlines()
                    self.file_positions[log_type] = f.tell()
                    return new_lines
            except Exception:
                return []
        except Exception:
            return []

    def _format_log_line(self, log_type, line):
        """Форматирует строку лога для вывода"""
        color = self.colors.get(log_type, '')

        # Убираем лишние символы и обрезаем длинные строки
        line = line.strip()
        if len(line) > 150:
            line = line[:147] + "..."

        timestamp = datetime.now().strftime('%H:%M:%S')
        return f"{color}[{timestamp}] {log_type.upper()}: {line}{self.reset_color}"

    def _parse_log_level(self, line):
        """Парсит уровень логирования из строки"""
        level_pattern = re.compile(r' - (\w+) - ')
        match = level_pattern.search(line)
        if match:
            return match.group(1)
        return 'INFO'

    def _should_show_line(self, line, filters):
        """Проверяет, нужно ли показывать строку согласно фильтрам"""
        if not filters:
            return True

        line_lower = line.lower()

        for filter_type, filter_value in filters.items():
            if filter_type == 'level':
                if filter_value.upper() not in line.upper():
                    return False
            elif filter_type == 'contains':
                if filter_value.lower() not in line_lower:
                    return False
            elif filter_type == 'exclude':
                if filter_value.lower() in line_lower:
                    return False
            elif filter_type == 'user_id':
                if f"user {filter_value}" not in line and f"user_id={filter_value}" not in line:
                    return False

        return True

    def monitor(self, filters=None, show_all=False):
        """Запускает мониторинг логов"""
        print(f"🔍 МОНИТОРИНГ ЛОГОВ В РЕАЛЬНОМ ВРЕМЕНИ")
        print(f"📁 Директория: {self.log_dir}")
        print(f"⏰ Начало: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🎯 Фильтры: {filters if filters else 'Нет'}")
        print("=" * 80)
        print()

        try:
            while True:
                new_entries = []

                # Проверяем все файлы логов
                for log_type, file_path in self.log_files.items():
                    new_lines = self._get_new_lines(log_type, file_path)

                    for line in new_lines:
                        if self._should_show_line(line, filters):
                            formatted_line = self._format_log_line(log_type, line)
                            new_entries.append((datetime.now(), formatted_line))

                # Выводим новые записи
                if new_entries:
                    for timestamp, line in new_entries:
                        print(line)
                        print()

                time.sleep(1)  # Проверяем каждую секунду

        except KeyboardInterrupt:
            print("\n\n🛑 Мониторинг остановлен пользователем")
            print(f"⏰ Конец: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

def main():
    parser = argparse.ArgumentParser(description='Мониторинг логов в реальном времени')
    parser.add_argument('--log-dir', default='logs', help='Директория с логами')
    parser.add_argument('--main-log', default='bot.log', help='Основной файл лога')
    parser.add_argument('--level', help='Фильтр по уровню (INFO, ERROR, WARNING)')
    parser.add_argument('--contains', help='Строка, которая должна содержаться в логе')
    parser.add_argument('--exclude', help='Строка, которая должна исключаться из лога')
    parser.add_argument('--user-id', help='ID пользователя для фильтрации')
    parser.add_argument('--all', action='store_true', help='Показать все существующие логи')

    args = parser.parse_args()

    monitor = LogMonitor(args.log_dir, args.main_log)

    # Собираем фильтры
    filters = {}
    if args.level:
        filters['level'] = args.level
    if args.contains:
        filters['contains'] = args.contains
    if args.exclude:
        filters['exclude'] = args.exclude
    if args.user_id:
        filters['user_id'] = args.user_id

    # Если нужно показать все существующие логи
    if args.all:
        print("📋 СУЩЕСТВУЮЩИЕ ЛОГИ:")
        print("=" * 80)

        for log_type, file_path in monitor.log_files.items():
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                        if lines:
                            print(f"\n{monitor.colors.get(log_type, '')}{log_type.upper()}:{monitor.reset_color}")
                            for line in lines[-10:]:  # Последние 10 строк
                                if monitor._should_show_line(line, filters):
                                    formatted = monitor._format_log_line(log_type, line.strip())
                                    print(f"  {formatted}")
                except Exception as e:
                    print(f"Ошибка чтения {file_path}: {e}")

        print("\n" + "=" * 80)

    # Запускаем мониторинг
    monitor.monitor(filters)

if __name__ == "__main__":
    main()
