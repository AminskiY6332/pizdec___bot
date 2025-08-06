# Руководство по миграции на smart_message_send

## Что изменилось

Вместо отправки новых сообщений при каждом нажатии на кнопку, теперь бот будет редактировать текущее сообщение. Это создает более плавный пользовательский опыт.

## Новые функции

### `smart_message_send()`
Автоматически пытается отредактировать существующее сообщение, а если не получается - отправляет новое.

### `smart_message_send_with_photo()`
То же самое, но для сообщений с фотографиями.

## Примеры миграции

### До (старый способ):
```python
try:
    await query.message.edit_text(
        text="Новый текст",
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN_V2
    )
    await query.answer()
except TelegramBadRequest:
    await query.message.answer(
        text="Новый текст", 
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN_V2
    )
    await query.answer()
```

### После (новый способ):
```python
await smart_message_send(
    query,
    text="Новый текст",
    reply_markup=keyboard,
    parse_mode=ParseMode.MARKDOWN_V2
)
```

## Что нужно обновить

1. **Импорты** - добавить в обработчики:
```python
from handlers.utils import smart_message_send, smart_message_send_with_photo
```

2. **Заменить паттерны**:
   - `query.message.answer(...)` → `smart_message_send(query, ...)`
   - `query.message.edit_text(...)` + fallback → `smart_message_send(query, ...)`

3. **Убрать ручные `query.answer()`** - они теперь вызываются автоматически

## Преимущества

- ✅ Весь интерфейс в одном сообщении
- ✅ Меньше "мусорных" сообщений
- ✅ Более быстрая навигация
- ✅ Автоматическая обработка ошибок
- ✅ Меньше кода

## Статус миграции

- ✅ Утилиты созданы в `handlers/utils.py`
- ✅ Импорты добавлены в ключевые файлы
- 🟡 Частично обновлены обработчики
- ⏳ Требуется полная замена во всех файлах

## Файлы для обновления

- `handlers/user/callbacks.py` - основные callback'и пользователей
- `handlers/user/messages.py` - обработчики сообщений
- `handlers/user/onboarding.py` - онбординг
- `handlers/user/photo_transform.py` - трансформация фото
- `handlers/admin/callbacks.py` - админ callback'и
- `handlers/admin/commands.py` - админ команды
- `handlers/admin/generation.py` - админ генерация
- `handlers/admin/panels.py` - админ панели