#!/usr/bin/env python3
"""
Скрипт для автоматического создания Git стратегии рефакторинга
Создает ветки, настраивает workflow, создает шаблоны PR
"""

import os
import subprocess
import json
from pathlib import Path
from typing import List, Dict

class GitStrategyManager:
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.branches = [
            "refactoring/master-plan",
            "refactoring/stage-0-preparation",
            "refactoring/stage-1-critical-fixes",
            "refactoring/stage-2-architecture",
            "refactoring/stage-3-optimization",
            "refactoring/stage-4-testing",
            "refactoring/stage-5-documentation"
        ]

    def run_git_command(self, command: List[str]) -> tuple:
        """Выполнить Git команду"""
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

    def get_current_branch(self) -> str:
        """Получить текущую ветку"""
        success, output = self.run_git_command(["git", "branch", "--show-current"])
        return output if success else "unknown"

    def branch_exists(self, branch_name: str) -> bool:
        """Проверить существование ветки"""
        success, output = self.run_git_command(["git", "branch", "-a"])
        if success:
            return branch_name in output
        return False

    def create_branch(self, branch_name: str, from_branch: str = "main") -> bool:
        """Создать новую ветку"""
        if self.branch_exists(branch_name):
            print(f"✅ Ветка {branch_name} уже существует")
            return True

        # Переключиться на базовую ветку
        success, _ = self.run_git_command(["git", "checkout", from_branch])
        if not success:
            print(f"❌ Не удалось переключиться на ветку {from_branch}")
            return False

        # Создать новую ветку
        success, _ = self.run_git_command(["git", "checkout", "-b", branch_name])
        if success:
            print(f"✅ Создана ветка {branch_name}")
            return True
        else:
            print(f"❌ Не удалось создать ветку {branch_name}")
            return False

    def create_all_branches(self):
        """Создать все ветки для рефакторинга"""
        print("🚀 Создание веток для рефакторинга...")

        current_branch = self.get_current_branch()
        print(f"Текущая ветка: {current_branch}")

        # Убедиться что мы на main или develop
        if current_branch not in ["main", "develop"]:
            print("⚠️ Рекомендуется создавать ветки от main или develop")
            response = input("Продолжить? (y/N): ")
            if response.lower() != 'y':
                return

        base_branch = current_branch
        created_count = 0

        for branch in self.branches:
            if self.create_branch(branch, base_branch):
                created_count += 1

        print(f"✅ Создано {created_count} веток из {len(self.branches)}")

        # Вернуться на исходную ветку
        self.run_git_command(["git", "checkout", current_branch])
        print(f"🔄 Возвращены на ветку {current_branch}")

    def create_github_workflow(self):
        """Создать GitHub Actions workflow"""
        workflow_dir = self.project_root / ".github" / "workflows"
        workflow_dir.mkdir(parents=True, exist_ok=True)

        workflow_content = """name: Refactoring Progress Tracker

on:
  push:
    branches: [ main, develop, 'refactoring/**' ]
  pull_request:
    branches: [ main, develop ]

jobs:
  track-progress:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v3
      with:
        fetch-depth: 0

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.9'

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt

    - name: Update progress tracker
      run: |
        python scripts/update_progress.py

    - name: Run code quality checks
      run: |
        python -m flake8 --max-line-length=100 --ignore=E203,W503
        python -m black --check .

    - name: Run tests
      run: |
        python -m pytest --cov=. --cov-report=json

    - name: Commit progress updates
      if: github.ref == 'refs/heads/main' || startsWith(github.ref, 'refs/heads/refactoring/')
      run: |
        git config --local user.email "action@github.com"
        git config --local user.name "GitHub Action"
        git add PROGRESS_TRACKER.md reports/
        git diff --staged --quiet || git commit -m "🤖 Автообновление прогресса рефакторинга"
        git push

  code-metrics:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.9'

    - name: Install analysis tools
      run: |
        pip install radon complexity-report

    - name: Calculate code metrics
      run: |
        echo "## Code Metrics" >> $GITHUB_STEP_SUMMARY
        echo "### Cyclomatic Complexity" >> $GITHUB_STEP_SUMMARY
        radon cc . --average --show-complexity >> $GITHUB_STEP_SUMMARY
        echo "### Maintainability Index" >> $GITHUB_STEP_SUMMARY
        radon mi . >> $GITHUB_STEP_SUMMARY
"""

        workflow_file = workflow_dir / "refactoring.yml"
        try:
            with open(workflow_file, 'w', encoding='utf-8') as f:
                f.write(workflow_content)
            print(f"✅ Создан GitHub workflow: {workflow_file}")
        except Exception as e:
            print(f"❌ Ошибка создания workflow: {e}")

    def create_pr_templates(self):
        """Создать шаблоны для Pull Request"""
        pr_template_dir = self.project_root / ".github" / "pull_request_template"
        pr_template_dir.mkdir(parents=True, exist_ok=True)

        # Основной шаблон
        main_template = """# 🔄 Рефакторинг: [Название изменения]

## 📋 Описание
Краткое описание изменений в рамках рефакторинга.

## 🎯 Этап рефакторинга
- [ ] Этап 0: Подготовка
- [ ] Этап 1: Критические исправления
- [ ] Этап 2: Архитектурные улучшения
- [ ] Этап 3: Оптимизация
- [ ] Этап 4: Тестирование
- [ ] Этап 5: Документация

## ✅ Чеклист изменений
- [ ] Код соответствует новой архитектуре
- [ ] Добавлены/обновлены тесты
- [ ] Обновлена документация
- [ ] Проверена обратная совместимость
- [ ] Нет нарушения существующей функциональности

## 🧪 Тестирование
- [ ] Unit тесты пройдены
- [ ] Integration тесты пройдены
- [ ] Ручное тестирование выполнено
- [ ] Проверена производительность

## 📊 Метрики
- Уменьшение дублирования кода: X мест
- Улучшение покрытия тестами: +X%
- Уменьшение сложности: -X единиц

## 🔗 Связанные задачи
Closes #[номер issue]
Related to #[номер issue]

## 📸 Скриншоты (если применимо)
[Добавить скриншоты изменений в UI]

## 🚨 Риски
- [ ] Нет рисков
- [ ] Низкий риск: [описание]
- [ ] Средний риск: [описание]
- [ ] Высокий риск: [описание]

## 📝 Дополнительные заметки
[Любая дополнительная информация для ревьюеров]
"""

        # Шаблон для критических исправлений
        critical_template = """# 🔴 Критические исправления: [Название]

## 🚨 Критичность
Это PR содержит критические исправления, которые должны быть проверены особенно тщательно.

## 🎯 Цель
- [ ] Устранение дублирования кода
- [ ] Исправление архитектурных проблем
- [ ] Улучшение производительности
- [ ] Исправление багов

## 📋 Изменения
### Удаленный код
- [Список удаленных файлов/функций]

### Новый код
- [Список новых файлов/функций]

### Измененный код
- [Список измененных файлов/функций]

## ⚠️ Потенциальные проблемы
- [Список потенциальных проблем]

## 🔄 План отката
В случае проблем:
1. [Шаг 1 отката]
2. [Шаг 2 отката]

## ✅ Обязательные проверки
- [ ] Все тесты проходят
- [ ] Нет регрессии функциональности
- [ ] Производительность не ухудшилась
- [ ] Код ревью от 2+ разработчиков
"""

        try:
            with open(pr_template_dir / "refactoring.md", 'w', encoding='utf-8') as f:
                f.write(main_template)

            with open(pr_template_dir / "critical.md", 'w', encoding='utf-8') as f:
                f.write(critical_template)

            print(f"✅ Созданы шаблоны PR: {pr_template_dir}")
        except Exception as e:
            print(f"❌ Ошибка создания шаблонов PR: {e}")

    def create_pre_commit_config(self):
        """Создать конфигурацию pre-commit hooks"""
        pre_commit_config = """repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.4.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
      - id: check-merge-conflict
      - id: debug-statements

  - repo: https://github.com/psf/black
    rev: 23.1.0
    hooks:
      - id: black
        language_version: python3
        args: [--line-length=100]

  - repo: https://github.com/pycqa/flake8
    rev: 6.0.0
    hooks:
      - id: flake8
        args: [--max-line-length=100, --ignore=E203,W503]

  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort
        args: [--profile=black, --line-length=100]

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.0.1
    hooks:
      - id: mypy
        additional_dependencies: [types-all]
        args: [--ignore-missing-imports]

  - repo: local
    hooks:
      - id: update-progress
        name: Update refactoring progress
        entry: python scripts/update_progress.py
        language: system
        always_run: true
        pass_filenames: false
"""

        config_file = self.project_root / ".pre-commit-config.yaml"
        try:
            with open(config_file, 'w', encoding='utf-8') as f:
                f.write(pre_commit_config)
            print(f"✅ Создана конфигурация pre-commit: {config_file}")

            # Установить pre-commit hooks
            success, _ = self.run_git_command(["pre-commit", "install"])
            if success:
                print("✅ Pre-commit hooks установлены")
            else:
                print("⚠️ Не удалось установить pre-commit hooks (возможно, не установлен pre-commit)")

        except Exception as e:
            print(f"❌ Ошибка создания pre-commit конфигурации: {e}")

    def create_gitignore_updates(self):
        """Обновить .gitignore для рефакторинга"""
        gitignore_additions = """
# Refactoring specific
reports/
*.coverage
coverage.json
.coverage
htmlcov/
.pytest_cache/
.mypy_cache/
.ruff_cache/

# Temporary refactoring files
*.tmp
*.backup
refactoring_*.log
"""

        gitignore_file = self.project_root / ".gitignore"
        try:
            # Проверить, есть ли уже эти записи
            existing_content = ""
            if gitignore_file.exists():
                with open(gitignore_file, 'r', encoding='utf-8') as f:
                    existing_content = f.read()

            if "# Refactoring specific" not in existing_content:
                with open(gitignore_file, 'a', encoding='utf-8') as f:
                    f.write(gitignore_additions)
                print("✅ Обновлен .gitignore для рефакторинга")
            else:
                print("✅ .gitignore уже содержит настройки для рефакторинга")

        except Exception as e:
            print(f"❌ Ошибка обновления .gitignore: {e}")

    def setup_git_strategy(self):
        """Полная настройка Git стратегии"""
        print("🚀 Настройка Git стратегии для рефакторинга...")

        # 1. Создать все ветки
        self.create_all_branches()

        # 2. Создать GitHub workflow
        self.create_github_workflow()

        # 3. Создать шаблоны PR
        self.create_pr_templates()

        # 4. Настроить pre-commit hooks
        self.create_pre_commit_config()

        # 5. Обновить .gitignore
        self.create_gitignore_updates()

        print("✅ Git стратегия настроена!")
        print("\n📋 Следующие шаги:")
        print("1. Установите pre-commit: pip install pre-commit")
        print("2. Запустите: pre-commit install")
        print("3. Создайте первый коммит в ветке refactoring/master-plan")
        print("4. Настройте GitHub репозиторий для автоматических действий")

    def show_branch_status(self):
        """Показать статус всех веток рефакторинга"""
        print("📊 Статус веток рефакторинга:")
        print("-" * 60)

        for branch in self.branches:
            exists = "✅" if self.branch_exists(branch) else "❌"
            print(f"{exists} {branch}")

        current = self.get_current_branch()
        print(f"\n🔄 Текущая ветка: {current}")

def main():
    """Главная функция"""
    import argparse

    parser = argparse.ArgumentParser(description="Настройка Git стратегии для рефакторинга")
    parser.add_argument("--setup", action="store_true", help="Полная настройка Git стратегии")
    parser.add_argument("--branches", action="store_true", help="Создать только ветки")
    parser.add_argument("--status", action="store_true", help="Показать статус веток")
    parser.add_argument("--workflow", action="store_true", help="Создать только GitHub workflow")
    parser.add_argument("--project-root", default=".", help="Корневая папка проекта")

    args = parser.parse_args()

    manager = GitStrategyManager(args.project_root)

    if args.setup:
        manager.setup_git_strategy()
    elif args.branches:
        manager.create_all_branches()
    elif args.status:
        manager.show_branch_status()
    elif args.workflow:
        manager.create_github_workflow()
    else:
        print("Используйте --help для просмотра доступных команд")
        manager.show_branch_status()

if __name__ == "__main__":
    main()
