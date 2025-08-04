# 🛠️ СКРИПТЫ УПРАВЛЕНИЯ РЕФАКТОРИНГОМ

Этот каталог содержит автоматизированные скрипты для управления процессом рефакторинга проекта.

---

## 📋 СПИСОК СКРИПТОВ

### 🎯 Главный скрипт
- **`refactoring_manager.py`** - Основной скрипт управления всем процессом рефакторинга

### 🔧 Специализированные скрипты
- **`update_progress.py`** - Автоматическое отслеживание и обновление прогресса
- **`git_strategy.py`** - Управление Git стратегией и ветками
- **`generate_report.py`** - Генерация различных отчетов

---

## 🚀 БЫСТРЫЙ СТАРТ

### 1. Первоначальная настройка
```bash
# Полная настройка проекта рефакторинга
python scripts/refactoring_manager.py --setup
```

### 2. Ежедневное использование
```bash
# Показать текущий статус
python scripts/refactoring_manager.py --status

# Ежедневное обновление прогресса
python scripts/refactoring_manager.py --daily

# Обновить только прогресс
python scripts/refactoring_manager.py --update-progress
```

### 3. Управление этапами
```bash
# Начать этап 0 (Подготовка)
python scripts/refactoring_manager.py --start-stage 0

# Завершить текущий этап
python scripts/refactoring_manager.py --complete-stage 0
```

### 4. Отчеты
```bash
# Еженедельные отчеты
python scripts/refactoring_manager.py --weekly

# Создать все отчеты
python scripts/refactoring_manager.py --generate-reports
```

---

## 📖 ДЕТАЛЬНОЕ ОПИСАНИЕ СКРИПТОВ

## 🎯 refactoring_manager.py

**Назначение**: Главный скрипт для управления всем процессом рефакторинга

### Основные команды:
```bash
# Показать статус проекта
python scripts/refactoring_manager.py --status

# Полная настройка проекта
python scripts/refactoring_manager.py --setup

# Начать этап рефакторинга (0-5)
python scripts/refactoring_manager.py --start-stage 1

# Завершить этап рефакторинга (0-5)
python scripts/refactoring_manager.py --complete-stage 1

# Ежедневная рутина (обновление прогресса + отчет)
python scripts/refactoring_manager.py --daily

# Еженедельная рутина (все отчеты)
python scripts/refactoring_manager.py --weekly

# Обновить только прогресс
python scripts/refactoring_manager.py --update-progress

# Создать все отчеты
python scripts/refactoring_manager.py --generate-reports

# Настроить Git стратегию
python scripts/refactoring_manager.py --setup-git
```

### Что делает:
- Объединяет все инструменты в единый интерфейс
- Управляет этапами рефакторинга
- Автоматизирует рутинные задачи
- Создает отчеты о начале/завершении этапов

---

## 📊 update_progress.py

**Назначение**: Автоматическое отслеживание прогресса рефакторинга

### Команды:
```bash
# Обновить прогресс
python scripts/update_progress.py

# Создать ежедневный отчет
python scripts/update_progress.py --daily

# Указать корневую папку проекта
python scripts/update_progress.py --project-root /path/to/project
```

### Что анализирует:
- **Git коммиты и ветки** - отслеживает изменения в репозитории
- **Структуру файлов** - анализирует созданные модули и файлы
- **Размер кодовой базы** - подсчитывает строки кода в ключевых файлах
- **Дублирование кода** - ищет повторяющиеся паттерны
- **Покрытие тестами** - анализирует результаты pytest

### Создает:
- **PROGRESS_TRACKER.md** - основной файл отслеживания прогресса
- **reports/daily_report_YYYY-MM-DD.md** - ежедневные отчеты

---

## 🔄 git_strategy.py

**Назначение**: Управление Git стратегией для рефакторинга

### Команды:
```bash
# Полная настройка Git стратегии
python scripts/git_strategy.py --setup

# Создать только ветки
python scripts/git_strategy.py --branches

# Показать статус веток
python scripts/git_strategy.py --status

# Создать GitHub workflow
python scripts/git_strategy.py --workflow
```

### Что создает:
- **Ветки рефакторинга**:
  - `refactoring/master-plan`
  - `refactoring/stage-0-preparation`
  - `refactoring/stage-1-critical-fixes`
  - `refactoring/stage-2-architecture`
  - `refactoring/stage-3-optimization`
  - `refactoring/stage-4-testing`
  - `refactoring/stage-5-documentation`

- **GitHub Actions workflow** (`.github/workflows/refactoring.yml`)
- **PR шаблоны** (`.github/pull_request_template/`)
- **Pre-commit hooks** (`.pre-commit-config.yaml`)
- **Обновления .gitignore**

---

## 📈 generate_report.py

**Назначение**: Генерация различных отчетов по рефакторингу

### Команды:
```bash
# Еженедельный отчет (автоопределение недели)
python scripts/generate_report.py --weekly

# Еженедельный отчет для конкретной недели
python scripts/generate_report.py --weekly 2

# Отчет по метрикам качества кода
python scripts/generate_report.py --metrics

# Создать все отчеты
python scripts/generate_report.py --all
```

### Типы отчетов:

#### 📅 Еженедельные отчеты
- Прогресс за неделю
- Выполненные задачи
- Изменения в коде
- Ключевые коммиты
- Планы на следующую неделю

#### 📊 Отчеты по метрикам
- Размер кодовой базы
- Качество кода
- Прогресс к целям
- Рекомендации по улучшению

---

## 🔧 НАСТРОЙКА И ТРЕБОВАНИЯ

### Системные требования:
- Python 3.8+
- Git
- Доступ к репозиторию проекта

### Python зависимости:
```bash
# Основные зависимости уже в requirements.txt
pip install -r requirements.txt

# Дополнительные инструменты для анализа кода
pip install pre-commit black flake8 mypy pytest-cov
```

### Настройка pre-commit hooks:
```bash
# После запуска git_strategy.py --setup
pre-commit install
```

---

## 📁 СТРУКТУРА СОЗДАВАЕМЫХ ФАЙЛОВ

```
project/
├── PROGRESS_TRACKER.md          # Основной трекер прогресса
├── reports/                     # Папка с отчетами
│   ├── daily_report_YYYY-MM-DD.md
│   ├── weekly_report_week_N_YYYYMMDD.md
│   ├── metrics_report_YYYYMMDD_HHMM.md
│   └── stage_N_start_YYYYMMDD_HHMM.md
├── .github/
│   ├── workflows/
│   │   └── refactoring.yml      # GitHub Actions
│   └── pull_request_template/
│       ├── refactoring.md       # Шаблон PR
│       └── critical.md          # Шаблон для критических PR
├── .pre-commit-config.yaml      # Конфигурация pre-commit
└── scripts/
    ├── refactoring_manager.py   # Главный скрипт
    ├── update_progress.py       # Отслеживание прогресса
    ├── git_strategy.py          # Git стратегия
    └── generate_report.py       # Генерация отчетов
```

---

## 🔄 РАБОЧИЙ ПРОЦЕСС

### Ежедневная рутина:
1. **Утром**: `python scripts/refactoring_manager.py --status`
2. **В процессе работы**: Обычная разработка с коммитами
3. **Вечером**: `python scripts/refactoring_manager.py --daily`

### Еженедельная рутина:
1. **В конце недели**: `python scripts/refactoring_manager.py --weekly`
2. **Анализ отчетов** в папке `reports/`
3. **Планирование** следующей недели

### При переходе между этапами:
1. **Завершение**: `python scripts/refactoring_manager.py --complete-stage N`
2. **Начало нового**: `python scripts/refactoring_manager.py --start-stage N+1`

---

## 🚨 УСТРАНЕНИЕ ПРОБЛЕМ

### Проблема: "Команда не найдена"
```bash
# Убедитесь что находитесь в корне проекта
cd /path/to/pizdec__bot-master

# Проверьте Python
python --version  # Должен быть 3.8+

# Проверьте путь к скрипту
ls scripts/refactoring_manager.py
```

### Проблема: "Git ошибки"
```bash
# Проверьте Git репозиторий
git status

# Убедитесь что есть коммиты
git log --oneline -5

# Проверьте права доступа
git remote -v
```

### Проблема: "Ошибки импорта"
```bash
# Установите зависимости
pip install -r requirements.txt

# Проверьте PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

### Проблема: "Нет прав на запись"
```bash
# Проверьте права на папки
ls -la reports/
ls -la scripts/

# Создайте папки если нужно
mkdir -p reports logs
```

---

## 📞 ПОДДЕРЖКА

### Логи и отладка:
- Все скрипты выводят подробную информацию о выполнении
- Ошибки сохраняются в `logs/` (если папка существует)
- Используйте `--help` для любого скрипта

### Полезные команды для отладки:
```bash
# Проверить статус Git
python scripts/git_strategy.py --status

# Проверить метрики без сохранения
python scripts/generate_report.py --metrics

# Обновить прогресс с отладкой
python scripts/update_progress.py --daily
```

---

## 🎯 ПРИМЕРЫ ИСПОЛЬЗОВАНИЯ

### Сценарий 1: Первый запуск
```bash
# 1. Полная настройка
python scripts/refactoring_manager.py --setup

# 2. Проверить что все создалось
python scripts/refactoring_manager.py --status

# 3. Начать первый этап
python scripts/refactoring_manager.py --start-stage 0
```

### Сценарий 2: Ежедневная работа
```bash
# Утром - проверить статус
python scripts/refactoring_manager.py --status

# В течение дня - обычная работа с Git
git add .
git commit -m "Исправление дублирования в handlers"

# Вечером - обновить прогресс
python scripts/refactoring_manager.py --daily
```

### Сценарий 3: Завершение этапа
```bash
# Проверить готовность
python scripts/refactoring_manager.py --status

# Завершить этап
python scripts/refactoring_manager.py --complete-stage 1

# Начать следующий этап
python scripts/refactoring_manager.py --start-stage 2
```

---

**Последнее обновление**: 2025-01-27
**Версия скриптов**: 1.0
