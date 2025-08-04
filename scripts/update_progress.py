#!/usr/bin/env python3
"""
Скрипт для автоматического обновления прогресса рефакторинга
Анализирует Git коммиты, файлы проекта и обновляет PROGRESS_TRACKER.md
"""

import os
import re
import json
import subprocess
from datetime import datetime, timezone
from typing import Dict, List, Tuple, Optional
from pathlib import Path

class ProgressTracker:
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.progress_file = self.project_root / "PROGRESS_TRACKER.md"
        self.master_plan_file = self.project_root / "REFACTORING_MASTER_PLAN.md"

    def get_git_info(self) -> Dict:
        """Получить информацию о текущем состоянии Git"""
        try:
            # Текущая ветка
            current_branch = subprocess.check_output(
                ["git", "branch", "--show-current"],
                cwd=self.project_root,
                text=True
            ).strip()

            # Последний коммит
            last_commit = subprocess.check_output(
                ["git", "log", "-1", "--format=%H|%s|%ad", "--date=iso"],
                cwd=self.project_root,
                text=True
            ).strip()

            commit_hash, commit_msg, commit_date = last_commit.split("|", 2)

            # Все ветки рефакторинга
            refactoring_branches = subprocess.check_output(
                ["git", "branch", "-a"],
                cwd=self.project_root,
                text=True
            ).strip().split("\n")

            refactoring_branches = [
                branch.strip().replace("* ", "").replace("remotes/origin/", "")
                for branch in refactoring_branches
                if "refactoring/" in branch
            ]

            return {
                "current_branch": current_branch,
                "last_commit": {
                    "hash": commit_hash[:7],
                    "message": commit_msg,
                    "date": commit_date
                },
                "refactoring_branches": refactoring_branches
            }
        except subprocess.CalledProcessError as e:
            print(f"Ошибка получения Git информации: {e}")
            return {}

    def analyze_codebase(self) -> Dict:
        """Анализ текущего состояния кодовой базы"""
        stats = {
            "total_files": 0,
            "python_files": 0,
            "total_lines": 0,
            "main_py_lines": 0,
            "database_py_lines": 0,
            "duplications_found": 0,
            "test_coverage": 0
        }

        # Подсчет файлов и строк
        for file_path in self.project_root.rglob("*.py"):
            if "venv" in str(file_path) or "__pycache__" in str(file_path):
                continue

            stats["python_files"] += 1

            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = len(f.readlines())
                    stats["total_lines"] += lines

                    if file_path.name == "main.py":
                        stats["main_py_lines"] = lines
                    elif file_path.name == "database.py":
                        stats["database_py_lines"] = lines
            except Exception as e:
                print(f"Ошибка чтения файла {file_path}: {e}")

        # Поиск дублирований (упрощенный)
        stats["duplications_found"] = self.find_duplications()

        # Покрытие тестами (если есть pytest)
        stats["test_coverage"] = self.get_test_coverage()

        return stats

    def find_duplications(self) -> int:
        """Поиск дублирований в коде"""
        duplications = 0
        error_patterns = [
            r"❌ Произошла ошибка",
            r"❌ Ошибка генерации",
            r"Печеньки возвращены"
        ]

        for pattern in error_patterns:
            count = 0
            for file_path in self.project_root.rglob("*.py"):
                if "venv" in str(file_path) or "__pycache__" in str(file_path):
                    continue

                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        count += len(re.findall(pattern, content))
                except Exception:
                    continue

            if count > 1:
                duplications += count - 1  # Первое вхождение не считается дублированием

        return duplications

    def get_test_coverage(self) -> float:
        """Получить покрытие тестами"""
        try:
            # Попытка запустить pytest с coverage
            result = subprocess.run(
                ["python", "-m", "pytest", "--cov=.", "--cov-report=json", "--quiet"],
                cwd=self.project_root,
                capture_output=True,
                text=True
            )

            coverage_file = self.project_root / "coverage.json"
            if coverage_file.exists():
                with open(coverage_file, 'r') as f:
                    coverage_data = json.load(f)
                    return coverage_data.get("totals", {}).get("percent_covered", 0)
        except Exception:
            pass

        return 0.0

    def calculate_stage_progress(self) -> Dict:
        """Вычислить прогресс по этапам на основе Git коммитов и файлов"""
        stages = {
            "stage_0": {"completed": 0, "total": 15, "name": "Подготовка"},
            "stage_1": {"completed": 0, "total": 25, "name": "Критические исправления"},
            "stage_2": {"completed": 0, "total": 30, "name": "Архитектурные улучшения"},
            "stage_3": {"completed": 0, "total": 25, "name": "Оптимизация"},
            "stage_4": {"completed": 0, "total": 20, "name": "Тестирование"},
            "stage_5": {"completed": 0, "total": 15, "name": "Документация"}
        }

        # Анализ выполненных задач на основе существующих файлов

        # Этап 0: Подготовка
        if self.master_plan_file.exists():
            stages["stage_0"]["completed"] += 1
        if (self.project_root / "CODEBASE_ANALYSIS.md").exists():
            stages["stage_0"]["completed"] += 1
        if (self.project_root / "DEPENDENCY_MAP.md").exists():
            stages["stage_0"]["completed"] += 1
        if (self.project_root / "MIGRATION_PLAN.md").exists():
            stages["stage_0"]["completed"] += 1

        # Этап 1: Критические исправления
        if (self.project_root / "core" / "messages.py").exists():
            stages["stage_1"]["completed"] += 2
        if (self.project_root / "core" / "exceptions.py").exists():
            stages["stage_1"]["completed"] += 2
        if (self.project_root / "core" / "app.py").exists():
            stages["stage_1"]["completed"] += 3

        # Этап 2: Архитектурные улучшения
        if (self.project_root / "services").exists():
            stages["stage_2"]["completed"] += 5
        if (self.project_root / "database" / "repositories").exists():
            stages["stage_2"]["completed"] += 5

        # Этап 3: Оптимизация
        if (self.project_root / "tests").exists() and len(list((self.project_root / "tests").glob("*.py"))) > 0:
            stages["stage_3"]["completed"] += 3

        # Этап 4: Тестирование
        coverage = self.get_test_coverage()
        if coverage > 0:
            stages["stage_4"]["completed"] = int(coverage / 100 * stages["stage_4"]["total"])

        # Этап 5: Документация
        docs_count = len(list(self.project_root.glob("*.md")))
        if docs_count >= 5:
            stages["stage_5"]["completed"] = min(docs_count - 2, stages["stage_5"]["total"])

        return stages

    def generate_progress_report(self) -> str:
        """Генерация отчета о прогрессе"""
        git_info = self.get_git_info()
        codebase_stats = self.analyze_codebase()
        stage_progress = self.calculate_stage_progress()

        # Вычисление общего прогресса
        total_completed = sum(stage["completed"] for stage in stage_progress.values())
        total_tasks = sum(stage["total"] for stage in stage_progress.values())
        overall_progress = (total_completed / total_tasks * 100) if total_tasks > 0 else 0

        # Генерация отчета
        report = f"""# 📊 ТРЕКЕР ПРОГРЕССА РЕФАКТОРИНГА

**Дата создания**: 2025-01-27
**Последнее обновление**: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}
**Версия**: 1.1 (автообновление)
**Текущий статус**: {'🟢 Завершен' if overall_progress >= 100 else '🟡 В процессе' if overall_progress > 0 else '⚪ Не начат'}

---

## 🎯 ОБЩИЙ ПРОГРЕСС

**Общий прогресс**: {overall_progress:.1f}% ({total_completed}/{total_tasks} задач)

### Сводка по этапам:
| Этап | Статус | Прогресс | Задач выполнено | Всего задач | Название |
|------|--------|----------|-----------------|-------------|----------|"""

        for stage_id, stage_data in stage_progress.items():
            progress_pct = (stage_data["completed"] / stage_data["total"] * 100) if stage_data["total"] > 0 else 0
            status = "✅ Завершен" if progress_pct >= 100 else "🟡 В процессе" if progress_pct > 0 else "⚪ Не начат"

            report += f"""
| **{stage_data["name"]}** | {status} | {progress_pct:.0f}% | {stage_data["completed"]}/{stage_data["total"]} | {stage_data["total"]} | {stage_data["name"]} |"""

        report += f"""

---

## 🔄 GIT ИНФОРМАЦИЯ

### Текущее состояние:
- **Текущая ветка**: `{git_info.get('current_branch', 'unknown')}`
- **Последний коммит**: `{git_info.get('last_commit', {}).get('hash', 'unknown')}` - {git_info.get('last_commit', {}).get('message', 'unknown')}
- **Дата коммита**: {git_info.get('last_commit', {}).get('date', 'unknown')}

### Ветки рефакторинга:
"""

        for branch in git_info.get('refactoring_branches', []):
            status = "✅ АКТИВНА" if branch == git_info.get('current_branch') else "⚪ СОЗДАНА"
            report += f"- `{branch}` - {status}\n"

        report += f"""

---

## 📊 МЕТРИКИ КОДОВОЙ БАЗЫ

### Текущие метрики:
| Метрика | Текущее значение | Целевое значение | Прогресс |
|---------|------------------|------------------|----------|
| Общее количество файлов | {codebase_stats['python_files']} | - | - |
| Общее количество строк | {codebase_stats['total_lines']:,} | - | - |
| Размер main.py | {codebase_stats['main_py_lines']} строк | <300 строк | {'✅' if codebase_stats['main_py_lines'] < 300 else '❌'} |
| Размер database.py | {codebase_stats['database_py_lines']} строк | <500 строк | {'✅' if codebase_stats['database_py_lines'] < 500 else '❌'} |
| Дублирование кода | {codebase_stats['duplications_found']} мест | 0 мест | {'✅' if codebase_stats['duplications_found'] == 0 else '❌'} |
| Покрытие тестами | {codebase_stats['test_coverage']:.1f}% | 80% | {'✅' if codebase_stats['test_coverage'] >= 80 else '❌'} |

---

## 🚀 СЛЕДУЮЩИЕ ШАГИ

### На основе текущего прогресса:
"""

        # Определение следующих шагов на основе прогресса
        if stage_progress["stage_0"]["completed"] < stage_progress["stage_0"]["total"]:
            report += """
1. **Завершить Этап 0**: Подготовка и анализ
   - Создать Git стратегию
   - Настроить инфраструктуру
   - Провести полный аудит кода
"""
        elif stage_progress["stage_1"]["completed"] < stage_progress["stage_1"]["total"]:
            report += """
1. **Продолжить Этап 1**: Критические исправления
   - Устранить дублирование сообщений
   - Создать систему обработки ошибок
   - Рефакторинг main.py
"""
        elif stage_progress["stage_2"]["completed"] < stage_progress["stage_2"]["total"]:
            report += """
1. **Продолжить Этап 2**: Архитектурные улучшения
   - Создать слой сервисов
   - Рефакторинг database.py
   - Добавить валидацию
"""
        else:
            report += """
1. **Продолжить следующий этап** согласно плану
"""

        report += f"""

---

## 📈 АВТОМАТИЧЕСКИЙ АНАЛИЗ

Этот отчет был автоматически сгенерирован на основе:
- Анализа Git коммитов и веток
- Сканирования файловой структуры проекта
- Подсчета строк кода и дублирований
- Анализа покрытия тестами

**Время генерации**: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}
**Скрипт**: `scripts/update_progress.py`

---

*Для обновления прогресса запустите: `python scripts/update_progress.py`*
"""

        return report

    def update_progress_file(self):
        """Обновить файл с прогрессом"""
        try:
            report = self.generate_progress_report()

            with open(self.progress_file, 'w', encoding='utf-8') as f:
                f.write(report)

            print(f"✅ Прогресс обновлен: {self.progress_file}")
            return True

        except Exception as e:
            print(f"❌ Ошибка обновления прогресса: {e}")
            return False

    def create_daily_report(self):
        """Создать ежедневный отчет"""
        today = datetime.now().strftime('%Y-%m-%d')
        report_file = self.project_root / f"reports/daily_report_{today}.md"

        # Создать папку reports если не существует
        report_file.parent.mkdir(exist_ok=True)

        git_info = self.get_git_info()
        codebase_stats = self.analyze_codebase()
        stage_progress = self.calculate_stage_progress()

        total_completed = sum(stage["completed"] for stage in stage_progress.values())
        total_tasks = sum(stage["total"] for stage in stage_progress.values())
        overall_progress = (total_completed / total_tasks * 100) if total_tasks > 0 else 0

        daily_report = f"""# 📊 ЕЖЕДНЕВНЫЙ ОТЧЕТ - {today}

## Общий прогресс: {overall_progress:.1f}%

### Выполнено сегодня:
- Обновлен трекер прогресса
- Проанализирована кодовая база

### Текущие метрики:
- Строк в main.py: {codebase_stats['main_py_lines']}
- Строк в database.py: {codebase_stats['database_py_lines']}
- Найдено дублирований: {codebase_stats['duplications_found']}
- Покрытие тестами: {codebase_stats['test_coverage']:.1f}%

### Планы на завтра:
- Продолжить текущий этап
- Исправить найденные проблемы

---
*Автоматически сгенерировано {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""

        try:
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(daily_report)
            print(f"✅ Ежедневный отчет создан: {report_file}")
        except Exception as e:
            print(f"❌ Ошибка создания ежедневного отчета: {e}")

def main():
    """Главная функция"""
    import argparse

    parser = argparse.ArgumentParser(description="Обновление прогресса рефакторинга")
    parser.add_argument("--daily", action="store_true", help="Создать ежедневный отчет")
    parser.add_argument("--project-root", default=".", help="Корневая папка проекта")

    args = parser.parse_args()

    tracker = ProgressTracker(args.project_root)

    # Обновить основной файл прогресса
    success = tracker.update_progress_file()

    # Создать ежедневный отчет если запрошено
    if args.daily:
        tracker.create_daily_report()

    if success:
        print("🎉 Прогресс успешно обновлен!")
    else:
        print("❌ Произошла ошибка при обновлении прогресса")
        exit(1)

if __name__ == "__main__":
    main()
