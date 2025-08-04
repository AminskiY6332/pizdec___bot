#!/usr/bin/env python3
"""
Главный скрипт управления процессом рефакторинга
Объединяет все инструменты и предоставляет единый интерфейс
"""

import os
import sys
import subprocess
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# Добавить путь к скриптам
sys.path.append(str(Path(__file__).parent))

from update_progress import ProgressTracker
from git_strategy import GitStrategyManager
from generate_report import ReportGenerator

class RefactoringManager:
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.progress_tracker = ProgressTracker(project_root)
        self.git_manager = GitStrategyManager(project_root)
        self.report_generator = ReportGenerator(project_root)

        # Создать необходимые папки
        (self.project_root / "scripts").mkdir(exist_ok=True)
        (self.project_root / "reports").mkdir(exist_ok=True)
        (self.project_root / "logs").mkdir(exist_ok=True)

    def show_status(self):
        """Показать текущий статус проекта рефакторинга"""
        print("🚀 СТАТУС ПРОЕКТА РЕФАКТОРИНГА")
        print("=" * 50)

        # Git статус
        print("\n📊 Git статус:")
        self.git_manager.show_branch_status()

        # Прогресс
        print("\n📈 Прогресс:")
        git_info = self.progress_tracker.get_git_info()
        codebase_stats = self.progress_tracker.analyze_codebase()
        stage_progress = self.progress_tracker.calculate_stage_progress()

        total_completed = sum(stage["completed"] for stage in stage_progress.values())
        total_tasks = sum(stage["total"] for stage in stage_progress.values())
        overall_progress = (total_completed / total_tasks * 100) if total_tasks > 0 else 0

        print(f"Общий прогресс: {overall_progress:.1f}% ({total_completed}/{total_tasks} задач)")

        # Метрики
        print(f"\n📊 Ключевые метрики:")
        print(f"- main.py: {codebase_stats['main_py_lines']} строк (цель: <300)")
        print(f"- database.py: {codebase_stats['database_py_lines']} строк (цель: <500)")
        print(f"- Дублирования: {codebase_stats['duplications_found']} (цель: 0)")
        print(f"- Покрытие тестами: {codebase_stats['test_coverage']:.1f}% (цель: 80%)")

        # Текущая ветка
        current_branch = git_info.get('current_branch', 'unknown')
        print(f"\n🔄 Текущая ветка: {current_branch}")

        # Рекомендации
        print(f"\n💡 Рекомендации:")
        if overall_progress < 5:
            print("- Начните с настройки Git стратегии: --setup-git")
            print("- Создайте первые отчеты: --generate-reports")
        elif overall_progress < 25:
            print("- Продолжите работу над Этапом 1")
            print("- Обновляйте прогресс регулярно: --update-progress")
        else:
            print("- Продолжайте следовать плану")
            print("- Регулярно создавайте отчеты")

    def setup_project(self):
        """Полная настройка проекта для рефакторинга"""
        print("🚀 НАСТРОЙКА ПРОЕКТА РЕФАКТОРИНГА")
        print("=" * 50)

        steps = [
            ("Настройка Git стратегии", self.git_manager.setup_git_strategy),
            ("Обновление прогресса", self.progress_tracker.update_progress_file),
            ("Создание первого отчета", lambda: self.report_generator.save_report(
                self.report_generator.generate_weekly_report(1),
                f"weekly_report_week_1_{datetime.now().strftime('%Y%m%d')}.md"
            )),
            ("Создание отчета по метрикам", lambda: self.report_generator.save_report(
                self.report_generator.generate_metrics_report(),
                f"metrics_report_{datetime.now().strftime('%Y%m%d_%H%M')}.md"
            ))
        ]

        for step_name, step_func in steps:
            print(f"\n🔄 {step_name}...")
            try:
                step_func()
                print(f"✅ {step_name} завершен")
            except Exception as e:
                print(f"❌ Ошибка в {step_name}: {e}")

        print("\n🎉 Настройка проекта завершена!")
        print("\n📋 Следующие шаги:")
        print("1. Переключитесь на ветку refactoring/stage-0-preparation")
        print("2. Начните работу над задачами Этапа 0")
        print("3. Регулярно обновляйте прогресс: python scripts/refactoring_manager.py --update-progress")

    def start_stage(self, stage_number: int):
        """Начать новый этап рефакторинга"""
        stage_names = {
            0: "Подготовка",
            1: "Критические исправления",
            2: "Архитектурные улучшения",
            3: "Оптимизация",
            4: "Тестирование",
            5: "Документация"
        }

        stage_name = stage_names.get(stage_number, f"Этап {stage_number}")
        branch_name = f"refactoring/stage-{stage_number}-{stage_name.lower().replace(' ', '-')}"

        print(f"🚀 НАЧАЛО ЭТАПА {stage_number}: {stage_name}")
        print("=" * 50)

        # Создать ветку если не существует
        if not self.git_manager.branch_exists(branch_name):
            success = self.git_manager.create_branch(branch_name)
            if not success:
                print(f"❌ Не удалось создать ветку {branch_name}")
                return

        # Переключиться на ветку
        success, _ = self.git_manager.run_git_command(["git", "checkout", branch_name])
        if not success:
            print(f"❌ Не удалось переключиться на ветку {branch_name}")
            return

        print(f"✅ Переключились на ветку {branch_name}")

        # Обновить прогресс
        self.progress_tracker.update_progress_file()

        # Создать отчет о начале этапа
        report_content = f"""# 🚀 НАЧАЛО ЭТАПА {stage_number}: {stage_name}

**Дата начала**: {datetime.now().strftime('%d.%m.%Y %H:%M')}
**Ветка**: `{branch_name}`

## 🎯 Цели этапа:
"""

        stage_goals = {
            0: [
                "Создать полную документацию проекта",
                "Настроить инфраструктуру разработки",
                "Провести детальный анализ кода",
                "Подготовить план миграции"
            ],
            1: [
                "Устранить дублирование кода",
                "Создать систему обработки ошибок",
                "Рефакторинг main.py",
                "Создать базовые core модули"
            ],
            2: [
                "Создать слой сервисов",
                "Рефакторинг database.py",
                "Добавить валидацию данных",
                "Обновить handlers"
            ],
            3: [
                "Оптимизировать производительность",
                "Добавить кэширование",
                "Улучшить логирование",
                "Настроить мониторинг"
            ],
            4: [
                "Написать unit тесты",
                "Создать integration тесты",
                "Достичь 80% покрытия",
                "Провести нагрузочное тестирование"
            ],
            5: [
                "Создать техническую документацию",
                "Обновить пользовательскую документацию",
                "Создать руководства",
                "Провести финальную ретроспективу"
            ]
        }

        goals = stage_goals.get(stage_number, ["Выполнить задачи согласно плану"])
        for goal in goals:
            report_content += f"- {goal}\n"

        report_content += f"""

## 📋 План работы:
1. Изучить детальный план в REFACTORING_MASTER_PLAN.md
2. Выполнять задачи поэтапно
3. Регулярно коммитить изменения
4. Обновлять прогресс ежедневно
5. Создавать отчеты еженедельно

## 🚨 Важные напоминания:
- Тестировать каждое изменение
- Делать резервные копии
- Следить за метриками качества
- Документировать все изменения

---

*Отчет создан автоматически при начале этапа*
"""

        report_filename = f"stage_{stage_number}_start_{datetime.now().strftime('%Y%m%d_%H%M')}.md"
        self.report_generator.save_report(report_content, report_filename)

        print(f"📊 Создан отчет о начале этапа: reports/{report_filename}")
        print(f"\n📋 Следующие шаги:")
        print(f"1. Изучите план этапа в REFACTORING_MASTER_PLAN.md")
        print(f"2. Начните выполнение задач")
        print(f"3. Регулярно коммитьте изменения")
        print(f"4. Обновляйте прогресс: python scripts/refactoring_manager.py --update-progress")

    def complete_stage(self, stage_number: int):
        """Завершить этап рефакторинга"""
        stage_names = {
            0: "Подготовка",
            1: "Критические исправления",
            2: "Архитектурные улучшения",
            3: "Оптимизация",
            4: "Тестирование",
            5: "Документация"
        }

        stage_name = stage_names.get(stage_number, f"Этап {stage_number}")

        print(f"🎉 ЗАВЕРШЕНИЕ ЭТАПА {stage_number}: {stage_name}")
        print("=" * 50)

        # Обновить прогресс
        self.progress_tracker.update_progress_file()

        # Получить метрики
        codebase_stats = self.progress_tracker.analyze_codebase()
        stage_progress = self.progress_tracker.calculate_stage_progress()

        # Создать отчет о завершении
        report_content = f"""# 🎉 ЗАВЕРШЕНИЕ ЭТАПА {stage_number}: {stage_name}

**Дата завершения**: {datetime.now().strftime('%d.%m.%Y %H:%M')}

## ✅ Достижения этапа:
"""

        # Анализ достижений на основе изменений в коде
        achievements = []

        if stage_number == 0:
            if (self.project_root / "REFACTORING_MASTER_PLAN.md").exists():
                achievements.append("Создан мастер-план рефакторинга")
            if (self.project_root / "CODEBASE_ANALYSIS.md").exists():
                achievements.append("Проведен анализ кодовой базы")
            if (self.project_root / "DEPENDENCY_MAP.md").exists():
                achievements.append("Создана карта зависимостей")

        elif stage_number == 1:
            if codebase_stats['duplications_found'] < 50:
                achievements.append("Сокращено дублирование кода")
            if (self.project_root / "core").exists():
                achievements.append("Созданы базовые core модули")
            if codebase_stats['main_py_lines'] < 1362:
                achievements.append("Начат рефакторинг main.py")

        if not achievements:
            achievements = ["Выполнены задачи согласно плану"]

        for achievement in achievements:
            report_content += f"- {achievement}\n"

        report_content += f"""

## 📊 Метрики на момент завершения:
- main.py: {codebase_stats['main_py_lines']} строк
- database.py: {codebase_stats['database_py_lines']} строк
- Дублирования: {codebase_stats['duplications_found']} мест
- Покрытие тестами: {codebase_stats['test_coverage']:.1f}%

## 🎯 Готовность к следующему этапу:
"""

        # Проверка готовности к следующему этапу
        next_stage_ready = True
        readiness_checks = []

        if stage_number == 0:
            if not (self.project_root / "REFACTORING_MASTER_PLAN.md").exists():
                readiness_checks.append("❌ Отсутствует мастер-план")
                next_stage_ready = False
            else:
                readiness_checks.append("✅ Мастер-план создан")

        elif stage_number == 1:
            if codebase_stats['duplications_found'] > 10:
                readiness_checks.append("⚠️ Много дублирований кода")
            else:
                readiness_checks.append("✅ Дублирования устранены")

        if not readiness_checks:
            readiness_checks = ["✅ Готов к следующему этапу"]

        for check in readiness_checks:
            report_content += f"- {check}\n"

        if next_stage_ready:
            report_content += f"\n🚀 **Можно переходить к Этапу {stage_number + 1}**\n"
        else:
            report_content += f"\n⚠️ **Необходимо завершить текущие задачи перед переходом**\n"

        report_content += f"""

## 📋 Рекомендации:
1. Провести ретроспективу этапа
2. Обновить планы при необходимости
3. Подготовиться к следующему этапу
4. Создать резервную копию текущего состояния

---

*Отчет создан автоматически при завершении этапа*
"""

        report_filename = f"stage_{stage_number}_complete_{datetime.now().strftime('%Y%m%d_%H%M')}.md"
        self.report_generator.save_report(report_content, report_filename)

        print(f"📊 Создан отчет о завершении: reports/{report_filename}")

        if next_stage_ready and stage_number < 5:
            print(f"\n🚀 Готов к переходу на Этап {stage_number + 1}")
            response = input(f"Начать Этап {stage_number + 1}? (y/N): ")
            if response.lower() == 'y':
                self.start_stage(stage_number + 1)
        else:
            print(f"\n📋 Завершите текущие задачи перед переходом к следующему этапу")

    def daily_routine(self):
        """Ежедневная рутина обновления прогресса"""
        print("📅 ЕЖЕДНЕВНОЕ ОБНОВЛЕНИЕ")
        print("=" * 30)

        # Обновить прогресс
        print("🔄 Обновление прогресса...")
        self.progress_tracker.update_progress_file()

        # Создать ежедневный отчет
        print("📊 Создание ежедневного отчета...")
        self.progress_tracker.create_daily_report()

        # Показать краткий статус
        print("\n📈 Краткий статус:")
        codebase_stats = self.progress_tracker.analyze_codebase()
        print(f"- Дублирования: {codebase_stats['duplications_found']}")
        print(f"- Покрытие тестами: {codebase_stats['test_coverage']:.1f}%")

        git_info = self.progress_tracker.get_git_info()
        print(f"- Текущая ветка: {git_info.get('current_branch', 'unknown')}")

        print("\n✅ Ежедневное обновление завершено!")

    def weekly_routine(self):
        """Еженедельная рутина создания отчетов"""
        print("📅 ЕЖЕНЕДЕЛЬНОЕ ОБНОВЛЕНИЕ")
        print("=" * 30)

        # Определить номер недели
        start_date = datetime(2025, 1, 27)
        current_date = datetime.now()
        week_number = ((current_date - start_date).days // 7) + 1

        print(f"📊 Создание отчета за неделю {week_number}...")

        # Создать еженедельный отчет
        weekly_report = self.report_generator.generate_weekly_report(week_number)
        weekly_filename = f"weekly_report_week_{week_number}_{datetime.now().strftime('%Y%m%d')}.md"
        self.report_generator.save_report(weekly_report, weekly_filename)

        # Создать отчет по метрикам
        print("📊 Создание отчета по метрикам...")
        metrics_report = self.report_generator.generate_metrics_report()
        metrics_filename = f"metrics_report_{datetime.now().strftime('%Y%m%d_%H%M')}.md"
        self.report_generator.save_report(metrics_report, metrics_filename)

        # Обновить прогресс
        print("🔄 Обновление прогресса...")
        self.progress_tracker.update_progress_file()

        print(f"\n✅ Еженедельное обновление завершено!")
        print(f"📊 Отчеты сохранены в папке reports/")

def main():
    """Главная функция"""
    import argparse

    parser = argparse.ArgumentParser(description="Управление процессом рефакторинга")
    parser.add_argument("--status", action="store_true", help="Показать статус проекта")
    parser.add_argument("--setup", action="store_true", help="Полная настройка проекта")
    parser.add_argument("--start-stage", type=int, help="Начать этап (0-5)")
    parser.add_argument("--complete-stage", type=int, help="Завершить этап (0-5)")
    parser.add_argument("--daily", action="store_true", help="Ежедневная рутина")
    parser.add_argument("--weekly", action="store_true", help="Еженедельная рутина")
    parser.add_argument("--update-progress", action="store_true", help="Обновить прогресс")
    parser.add_argument("--generate-reports", action="store_true", help="Создать все отчеты")
    parser.add_argument("--setup-git", action="store_true", help="Настроить Git стратегию")
    parser.add_argument("--project-root", default=".", help="Корневая папка проекта")

    args = parser.parse_args()

    manager = RefactoringManager(args.project_root)

    if args.status:
        manager.show_status()
    elif args.setup:
        manager.setup_project()
    elif args.start_stage is not None:
        manager.start_stage(args.start_stage)
    elif args.complete_stage is not None:
        manager.complete_stage(args.complete_stage)
    elif args.daily:
        manager.daily_routine()
    elif args.weekly:
        manager.weekly_routine()
    elif args.update_progress:
        manager.progress_tracker.update_progress_file()
    elif args.generate_reports:
        manager.weekly_routine()
    elif args.setup_git:
        manager.git_manager.setup_git_strategy()
    else:
        print("🚀 МЕНЕДЖЕР РЕФАКТОРИНГА")
        print("=" * 30)
        print("Используйте --help для просмотра команд")
        print("\nОсновные команды:")
        print("  --status          Показать статус")
        print("  --setup           Настроить проект")
        print("  --start-stage N   Начать этап N")
        print("  --daily           Ежедневное обновление")
        print("  --weekly          Еженедельные отчеты")
        print("\nПример: python scripts/refactoring_manager.py --status")

        # Показать краткий статус
        print("\n" + "=" * 30)
        manager.show_status()

if __name__ == "__main__":
    main()
