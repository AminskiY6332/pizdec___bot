#!/usr/bin/env python3
"""
Скрипт для генерации различных отчетов по рефакторингу
Создает еженедельные отчеты, метрики качества кода, анализ прогресса
"""

import os
import json
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import re

class ReportGenerator:
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.reports_dir = self.project_root / "reports"
        self.reports_dir.mkdir(exist_ok=True)

    def run_command(self, command: List[str]) -> Tuple[bool, str]:
        """Выполнить команду и вернуть результат"""
        try:
            result = subprocess.run(
                command,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=True
            )
            return True, result.stdout.strip()
        except subprocess.CalledProcessError as e:
            return False, e.stderr.strip()

    def get_git_commits_since(self, since_date: str) -> List[Dict]:
        """Получить коммиты с определенной даты"""
        success, output = self.run_command([
            "git", "log",
            f"--since={since_date}",
            "--format=%H|%s|%an|%ad",
            "--date=iso"
        ])

        commits = []
        if success and output:
            for line in output.split('\n'):
                if line.strip():
                    parts = line.split('|', 3)
                    if len(parts) == 4:
                        commits.append({
                            'hash': parts[0][:7],
                            'message': parts[1],
                            'author': parts[2],
                            'date': parts[3]
                        })

        return commits

    def analyze_code_changes(self, since_date: str) -> Dict:
        """Анализ изменений в коде с определенной даты"""
        success, output = self.run_command([
            "git", "diff", "--stat",
            f"--since={since_date}",
            "HEAD~1", "HEAD"
        ])

        changes = {
            'files_changed': 0,
            'lines_added': 0,
            'lines_deleted': 0,
            'files_list': []
        }

        if success and output:
            lines = output.split('\n')
            for line in lines:
                if '|' in line and ('+' in line or '-' in line):
                    changes['files_changed'] += 1
                    filename = line.split('|')[0].strip()
                    changes['files_list'].append(filename)
                elif 'insertion' in line or 'deletion' in line:
                    # Парсинг строки типа "5 files changed, 123 insertions(+), 45 deletions(-)"
                    if 'insertion' in line:
                        match = re.search(r'(\d+) insertion', line)
                        if match:
                            changes['lines_added'] = int(match.group(1))
                    if 'deletion' in line:
                        match = re.search(r'(\d+) deletion', line)
                        if match:
                            changes['lines_deleted'] = int(match.group(1))

        return changes

    def calculate_code_metrics(self) -> Dict:
        """Вычислить метрики качества кода"""
        metrics = {
            'total_files': 0,
            'total_lines': 0,
            'python_files': 0,
            'complexity_high': 0,
            'duplications': 0,
            'test_coverage': 0.0,
            'main_py_lines': 0,
            'database_py_lines': 0
        }

        # Подсчет файлов и строк
        for file_path in self.project_root.rglob("*.py"):
            if any(exclude in str(file_path) for exclude in ['venv', '__pycache__', '.git']):
                continue

            metrics['python_files'] += 1

            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    line_count = len(lines)
                    metrics['total_lines'] += line_count

                    # Специальные файлы
                    if file_path.name == 'main.py':
                        metrics['main_py_lines'] = line_count
                    elif file_path.name == 'database.py':
                        metrics['database_py_lines'] = line_count

                    # Поиск дублирований (упрощенный)
                    content = ''.join(lines)
                    error_patterns = [
                        r'❌ Произошла ошибка',
                        r'❌ Ошибка генерации',
                        r'Печеньки возвращены'
                    ]

                    for pattern in error_patterns:
                        matches = len(re.findall(pattern, content))
                        if matches > 0:
                            metrics['duplications'] += matches - 1  # Первое не считается дублированием

            except Exception as e:
                print(f"Ошибка анализа файла {file_path}: {e}")

        # Попытка получить покрытие тестами
        try:
            success, _ = self.run_command(["python", "-m", "pytest", "--cov=.", "--cov-report=json", "--quiet"])
            if success:
                coverage_file = self.project_root / "coverage.json"
                if coverage_file.exists():
                    with open(coverage_file, 'r') as f:
                        coverage_data = json.load(f)
                        metrics['test_coverage'] = coverage_data.get('totals', {}).get('percent_covered', 0)
        except Exception:
            pass

        return metrics

    def generate_weekly_report(self, week_number: int = None) -> str:
        """Генерация еженедельного отчета"""
        if week_number is None:
            # Вычислить номер недели от начала проекта (27.01.2025)
            start_date = datetime(2025, 1, 27)
            current_date = datetime.now()
            week_number = ((current_date - start_date).days // 7) + 1

        # Дата начала недели
        start_date = datetime(2025, 1, 27) + timedelta(weeks=week_number-1)
        end_date = start_date + timedelta(days=6)

        # Получить коммиты за неделю
        commits = self.get_git_commits_since(start_date.strftime('%Y-%m-%d'))

        # Анализ изменений
        changes = self.analyze_code_changes(start_date.strftime('%Y-%m-%d'))

        # Метрики кода
        metrics = self.calculate_code_metrics()

        # Определить текущий этап
        current_stage = self.determine_current_stage(week_number)

        report = f"""# 📊 ЕЖЕНЕДЕЛЬНЫЙ ОТЧЕТ #{week_number}

**Период**: {start_date.strftime('%d.%m.%Y')} - {end_date.strftime('%d.%m.%Y')}
**Дата создания**: {datetime.now().strftime('%d.%m.%Y %H:%M')}
**Текущий этап**: {current_stage}

---

## 🎯 ПРОГРЕСС ЗА НЕДЕЛЮ

### Выполненные задачи:
"""

        # Анализ коммитов для определения выполненных задач
        task_categories = {
            'документация': 0,
            'рефакторинг': 0,
            'тестирование': 0,
            'исправления': 0,
            'архитектура': 0
        }

        for commit in commits:
            message = commit['message'].lower()
            if any(word in message for word in ['документ', 'план', 'анализ', 'отчет']):
                task_categories['документация'] += 1
            elif any(word in message for word in ['рефактор', 'переработ', 'реструктур']):
                task_categories['рефакторинг'] += 1
            elif any(word in message for word in ['тест', 'покрытие', 'проверк']):
                task_categories['тестирование'] += 1
            elif any(word in message for word in ['исправ', 'фикс', 'баг']):
                task_categories['исправления'] += 1
            elif any(word in message for word in ['архитектур', 'структур', 'модул']):
                task_categories['архитектура'] += 1

        for category, count in task_categories.items():
            if count > 0:
                report += f"- **{category.title()}**: {count} задач\n"

        report += f"""

### Изменения в коде:
- **Файлов изменено**: {changes['files_changed']}
- **Строк добавлено**: {changes['lines_added']}
- **Строк удалено**: {changes['lines_deleted']}
- **Коммитов**: {len(commits)}

### Ключевые коммиты:
"""

        for commit in commits[:5]:  # Показать последние 5 коммитов
            report += f"- `{commit['hash']}` {commit['message']} ({commit['author']})\n"

        report += f"""

---

## 📊 ТЕКУЩИЕ МЕТРИКИ

| Метрика | Значение | Изменение | Цель |
|---------|----------|-----------|------|
| Размер main.py | {metrics['main_py_lines']} строк | - | <300 строк |
| Размер database.py | {metrics['database_py_lines']} строк | - | <500 строк |
| Дублирование кода | {metrics['duplications']} мест | - | 0 мест |
| Покрытие тестами | {metrics['test_coverage']:.1f}% | - | 80% |
| Всего Python файлов | {metrics['python_files']} | - | - |
| Всего строк кода | {metrics['total_lines']:,} | - | - |

---

## 🎯 ДОСТИЖЕНИЯ НЕДЕЛИ

### ✅ Выполнено:
"""

        # Определить достижения на основе метрик
        achievements = []

        if metrics['main_py_lines'] < 1362:
            achievements.append("Уменьшен размер main.py")
        if metrics['database_py_lines'] < 3213:
            achievements.append("Уменьшен размер database.py")
        if metrics['duplications'] < 50:
            achievements.append("Сокращено дублирование кода")
        if metrics['test_coverage'] > 0:
            achievements.append("Добавлено покрытие тестами")

        if not achievements:
            achievements = ["Создана инфраструктура для рефакторинга", "Проведен анализ кодовой базы"]

        for achievement in achievements:
            report += f"- {achievement}\n"

        report += f"""

### 🚧 В процессе:
- Подготовка к следующему этапу
- Анализ и планирование изменений

---

## 📋 ПЛАНЫ НА СЛЕДУЮЩУЮ НЕДЕЛЮ

### Приоритетные задачи:
"""

        # Планы на основе текущего этапа
        next_week_plans = self.get_next_week_plans(current_stage, week_number + 1)
        for plan in next_week_plans:
            report += f"- {plan}\n"

        report += f"""

### Ожидаемые результаты:
- Продвижение по текущему этапу
- Улучшение метрик качества кода
- Подготовка к следующему этапу

---

## 🚨 РИСКИ И ПРОБЛЕМЫ

### Текущие риски:
- **Временные рамки**: Средний риск превышения сроков
- **Сложность**: Высокая сложность некоторых задач
- **Тестирование**: Необходимо больше времени на тестирование

### Решенные проблемы:
- Создана структура проекта рефакторинга
- Настроена система отслеживания прогресса

---

## 📈 ТРЕНДЫ

### Положительные тренды:
- Улучшение структуры проекта
- Увеличение покрытия документацией
- Систематический подход к рефакторингу

### Области для улучшения:
- Скорость выполнения задач
- Покрытие тестами
- Автоматизация процессов

---

## 👥 КОМАНДА

### Активность команды:
"""

        # Анализ активности по авторам коммитов
        authors = {}
        for commit in commits:
            author = commit['author']
            authors[author] = authors.get(author, 0) + 1

        for author, count in authors.items():
            report += f"- **{author}**: {count} коммитов\n"

        if not authors:
            report += "- Активность будет отслеживаться в следующих отчетах\n"

        report += f"""

---

## 🔄 СЛЕДУЮЩИЕ ШАГИ

1. **Завершить текущие задачи** этапа {current_stage}
2. **Подготовиться к следующему этапу**
3. **Провести ретроспективу** недели
4. **Обновить планы** при необходимости

---

*Отчет сгенерирован автоматически {datetime.now().strftime('%d.%m.%Y в %H:%M')}*
*Скрипт: `scripts/generate_report.py`*
"""

        return report

    def determine_current_stage(self, week_number: int) -> str:
        """Определить текущий этап на основе номера недели"""
        stages = {
            1: "Этап 0: Подготовка",
            2: "Этап 1: Критические исправления",
            3: "Этап 1: Критические исправления",
            4: "Этап 2: Архитектурные улучшения",
            5: "Этап 2: Архитектурные улучшения",
            6: "Этап 2: Архитектурные улучшения",
            7: "Этап 3: Оптимизация",
            8: "Этап 3: Оптимизация",
            9: "Этап 4: Тестирование",
            10: "Этап 5: Документация"
        }

        return stages.get(week_number, f"Неделя {week_number}")

    def get_next_week_plans(self, current_stage: str, week_number: int) -> List[str]:
        """Получить планы на следующую неделю"""
        plans_by_stage = {
            "Этап 0: Подготовка": [
                "Завершить создание документации",
                "Настроить инфраструктуру разработки",
                "Провести полный аудит кода",
                "Подготовиться к началу Этапа 1"
            ],
            "Этап 1: Критические исправления": [
                "Устранить дублирование сообщений об ошибках",
                "Создать систему централизованной обработки ошибок",
                "Начать рефакторинг main.py",
                "Создать базовые core модули"
            ],
            "Этап 2: Архитектурные улучшения": [
                "Создать слой сервисов",
                "Рефакторинг database.py",
                "Добавить систему валидации",
                "Обновить handlers"
            ],
            "Этап 3: Оптимизация": [
                "Добавить кэширование",
                "Оптимизировать производительность",
                "Улучшить систему логирования",
                "Настроить мониторинг"
            ],
            "Этап 4: Тестирование": [
                "Написать unit тесты",
                "Создать integration тесты",
                "Провести нагрузочное тестирование",
                "Достичь 80% покрытия тестами"
            ],
            "Этап 5: Документация": [
                "Создать техническую документацию",
                "Обновить README",
                "Создать руководство по развертыванию",
                "Провести финальную ретроспективу"
            ]
        }

        return plans_by_stage.get(current_stage, ["Продолжить работу по плану"])

    def generate_metrics_report(self) -> str:
        """Генерация отчета по метрикам качества кода"""
        metrics = self.calculate_code_metrics()

        report = f"""# 📊 ОТЧЕТ ПО МЕТРИКАМ КАЧЕСТВА КОДА

**Дата создания**: {datetime.now().strftime('%d.%m.%Y %H:%M')}

---

## 📈 ОСНОВНЫЕ МЕТРИКИ

### Размер кодовой базы:
- **Всего Python файлов**: {metrics['python_files']}
- **Всего строк кода**: {metrics['total_lines']:,}
- **Средний размер файла**: {metrics['total_lines'] // metrics['python_files'] if metrics['python_files'] > 0 else 0} строк

### Проблемные файлы:
- **main.py**: {metrics['main_py_lines']} строк (цель: <300)
- **database.py**: {metrics['database_py_lines']} строк (цель: <500)

### Качество кода:
- **Дублирование кода**: {metrics['duplications']} мест (цель: 0)
- **Покрытие тестами**: {metrics['test_coverage']:.1f}% (цель: 80%)

---

## 🎯 ПРОГРЕСС К ЦЕЛЯМ

| Метрика | Текущее | Цель | Прогресс | Статус |
|---------|---------|------|----------|--------|
| main.py | {metrics['main_py_lines']} | <300 | {max(0, (1362 - metrics['main_py_lines']) / 1062 * 100):.1f}% | {'✅' if metrics['main_py_lines'] < 300 else '🔄'} |
| database.py | {metrics['database_py_lines']} | <500 | {max(0, (3213 - metrics['database_py_lines']) / 2713 * 100):.1f}% | {'✅' if metrics['database_py_lines'] < 500 else '🔄'} |
| Дублирование | {metrics['duplications']} | 0 | {max(0, (50 - metrics['duplications']) / 50 * 100):.1f}% | {'✅' if metrics['duplications'] == 0 else '🔄'} |
| Тесты | {metrics['test_coverage']:.1f}% | 80% | {metrics['test_coverage'] / 80 * 100:.1f}% | {'✅' if metrics['test_coverage'] >= 80 else '🔄'} |

---

## 📊 ДЕТАЛЬНЫЙ АНАЛИЗ

### Распределение размеров файлов:
"""

        # Анализ размеров файлов
        file_sizes = []
        for file_path in self.project_root.rglob("*.py"):
            if any(exclude in str(file_path) for exclude in ['venv', '__pycache__', '.git']):
                continue
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = len(f.readlines())
                    file_sizes.append((str(file_path.relative_to(self.project_root)), lines))
            except Exception:
                continue

        # Сортировка по размеру
        file_sizes.sort(key=lambda x: x[1], reverse=True)

        report += "\n**Топ-10 самых больших файлов:**\n"
        for i, (filename, lines) in enumerate(file_sizes[:10], 1):
            status = "🔴" if lines > 500 else "🟡" if lines > 200 else "🟢"
            report += f"{i}. {status} `{filename}` - {lines} строк\n"

        report += f"""

### Рекомендации по улучшению:
"""

        recommendations = []
        if metrics['main_py_lines'] > 300:
            recommendations.append("🔴 **Критично**: Разделить main.py на модули")
        if metrics['database_py_lines'] > 500:
            recommendations.append("🔴 **Критично**: Рефакторинг database.py в репозитории")
        if metrics['duplications'] > 10:
            recommendations.append("🟡 **Важно**: Устранить дублирование кода")
        if metrics['test_coverage'] < 50:
            recommendations.append("🟡 **Важно**: Увеличить покрытие тестами")

        if not recommendations:
            recommendations.append("✅ **Отлично**: Все основные метрики в норме")

        for rec in recommendations:
            report += f"- {rec}\n"

        report += f"""

---

## 🔄 ТРЕНДЫ

*Тренды будут доступны после нескольких запусков анализа*

---

*Отчет сгенерирован автоматически {datetime.now().strftime('%d.%m.%Y в %H:%M')}*
"""

        return report

    def save_report(self, report_content: str, filename: str):
        """Сохранить отчет в файл"""
        report_file = self.reports_dir / filename
        try:
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(report_content)
            print(f"✅ Отчет сохранен: {report_file}")
            return True
        except Exception as e:
            print(f"❌ Ошибка сохранения отчета: {e}")
            return False

def main():
    """Главная функция"""
    import argparse

    parser = argparse.ArgumentParser(description="Генерация отчетов по рефакторингу")
    parser.add_argument("--weekly", type=int, help="Создать еженедельный отчет (номер недели)")
    parser.add_argument("--metrics", action="store_true", help="Создать отчет по метрикам")
    parser.add_argument("--all", action="store_true", help="Создать все отчеты")
    parser.add_argument("--project-root", default=".", help="Корневая папка проекта")

    args = parser.parse_args()

    generator = ReportGenerator(args.project_root)

    if args.weekly is not None:
        report = generator.generate_weekly_report(args.weekly)
        filename = f"weekly_report_week_{args.weekly}_{datetime.now().strftime('%Y%m%d')}.md"
        generator.save_report(report, filename)

    if args.metrics:
        report = generator.generate_metrics_report()
        filename = f"metrics_report_{datetime.now().strftime('%Y%m%d_%H%M')}.md"
        generator.save_report(report, filename)

    if args.all:
        # Еженедельный отчет
        week_num = ((datetime.now() - datetime(2025, 1, 27)).days // 7) + 1
        weekly_report = generator.generate_weekly_report(week_num)
        weekly_filename = f"weekly_report_week_{week_num}_{datetime.now().strftime('%Y%m%d')}.md"
        generator.save_report(weekly_report, weekly_filename)

        # Отчет по метрикам
        metrics_report = generator.generate_metrics_report()
        metrics_filename = f"metrics_report_{datetime.now().strftime('%Y%m%d_%H%M')}.md"
        generator.save_report(metrics_report, metrics_filename)

        print("🎉 Все отчеты созданы!")

    if not any([args.weekly is not None, args.metrics, args.all]):
        print("Используйте --help для просмотра доступных команд")
        print("Пример: python scripts/generate_report.py --weekly 1")

if __name__ == "__main__":
    main()
