# 🎹 Модульная структура клавиатур

## 📁 Структура проекта

```
keyboards/
├── __init__.py          # Главный файл с импортами
├── base.py              # Базовые клавиатуры
├── main_menu.py         # Главное меню и навигация
├── generation.py        # Генерация контента
├── user_profile.py      # Профиль пользователя
├── admin.py            # Админ-панель
├── payments.py         # Платежи и подписки
├── support.py          # Поддержка и FAQ
├── broadcast.py        # Рассылки
├── utils.py           # Утилитарные клавиатуры
└── README.md          # Этот файл
```

## 🎯 Преимущества новой структуры

### ✅ **Организация кода**
- **Логическое разделение** по функциональности
- **Легкий поиск** нужных клавиатур
- **Простое добавление** новых функций

### ✅ **Читаемость**
- **Короткие файлы** (50-200 строк вместо 1000+)
- **Понятные названия** функций
- **Документация** для каждой клавиатуры

### ✅ **Поддерживаемость**
- **Изолированные изменения** - правки в одном модуле не влияют на другие
- **Простое тестирование** отдельных компонентов
- **Легкий рефакторинг**

## 📋 Описание модулей

### 🔧 `base.py` - Базовые клавиатуры
```python
create_back_keyboard()           # Кнопка "Назад"
create_confirmation_keyboard()   # Подтверждение действий
create_error_keyboard()         # Обработка ошибок
```

### 🏠 `main_menu.py` - Главное меню
```python
create_main_menu_keyboard()              # Главное меню
create_photo_generate_menu_keyboard()    # Меню фотогенерации
create_video_generate_menu_keyboard()    # Меню видеогенерации
```

### 🎨 `generation.py` - Генерация контента
```python
create_style_selection_keyboard()        # Выбор стиля
create_aspect_ratio_keyboard()           # Соотношения сторон
create_avatar_style_choice_keyboard()    # Выбор пола аватара
create_new_male_avatar_styles_keyboard() # Стили мужских аватаров
create_new_female_avatar_styles_keyboard() # Стили женских аватаров
create_video_styles_keyboard()           # Стили видео
create_prompt_selection_keyboard()       # Выбор промптов
create_generation_in_progress_keyboard() # Процесс генерации
```

### 👤 `user_profile.py` - Профиль пользователя
```python
create_user_profile_keyboard()      # Личный кабинет
create_avatar_selection_keyboard()  # Выбор аватара
create_training_keyboard()          # Обучение аватара
create_rating_keyboard()           # Оценка контента
create_payment_success_keyboard()   # Успешная оплата
```

### 🔐 `admin.py` - Админ-панель
```python
create_admin_keyboard()                    # Главная админ-панель
create_admin_user_actions_keyboard()       # Действия с пользователем
```

### 💳 `payments.py` - Платежи
```python
create_subscription_keyboard()      # Тарифы подписки
create_payment_only_keyboard()      # Клавиатура для неоплативших
```

### 🆘 `support.py` - Поддержка
```python
create_faq_keyboard()              # Частые вопросы
create_support_keyboard()          # Поддержка
create_referral_keyboard()         # Реферальная программа
```

### 📢 `broadcast.py` - Рассылки
```python
create_broadcast_keyboard()                        # Рассылка
create_broadcast_with_payment_audience_keyboard()  # Выбор аудитории
create_dynamic_broadcast_keyboard()                # Динамические кнопки
```

### 🛠 `utils.py` - Утилиты
```python
create_photo_upload_keyboard()     # Загрузка фото
create_video_status_keyboard()     # Статус видео
send_avatar_training_message()     # Сообщение с аватаром
```

## 🔄 Миграция со старого кода

### Старый импорт:
```python
from keyboards import create_main_menu_keyboard
```

### Новый импорт (тот же самый):
```python
from keyboards import create_main_menu_keyboard
```

**✅ Обратная совместимость сохранена!**

## 🚀 Использование

### Простое использование:
```python
from keyboards import create_main_menu_keyboard

keyboard = await create_main_menu_keyboard(user_id)
```

### Прямой импорт из модуля:
```python
from keyboards.main_menu import create_main_menu_keyboard

keyboard = await create_main_menu_keyboard(user_id)
```

## 📊 Сравнение размеров

| Файл | Старый размер | Новый размер | Улучшение |
|------|---------------|--------------|-----------|
| keyboards.py | 1067 строк | - | ❌ Слишком большой |
| base.py | - | 50 строк | ✅ Компактный |
| main_menu.py | - | 80 строк | ✅ Читаемый |
| generation.py | - | 300 строк | ✅ Логичный |
| user_profile.py | - | 150 строк | ✅ Организованный |

## 🎯 Рекомендации по использованию

1. **Используйте основной импорт** для большинства случаев
2. **Прямой импорт из модуля** для специфичных случаев
3. **Добавляйте новые клавиатуры** в соответствующие модули
4. **Следуйте документации** в каждом файле

## 🔧 Добавление новых клавиатур

1. Выберите подходящий модуль
2. Добавьте функцию с префиксом `create_`
3. Добавьте импорт в `__init__.py`
4. Обновите `__all__` список

Пример:
```python
# keyboards/generation.py
async def create_new_style_keyboard() -> InlineKeyboardMarkup:
    """Создаёт клавиатуру нового стиля."""
    # Ваш код здесь
    pass
```

## 📈 Результаты рефакторинга

- ✅ **Уменьшение размера файлов** с 1067 до 50-300 строк
- ✅ **Улучшение читаемости** кода
- ✅ **Логическая организация** по функциональности
- ✅ **Простота поддержки** и расширения
- ✅ **Сохранение совместимости** со старым кодом 