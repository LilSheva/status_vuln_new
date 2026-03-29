# Текущее состояние
Обновлено: 2026-03-29

## Фаза: ПРОЕКТ ЗАВЕРШЁН + УЛУЧШЕНИЯ UX

Все 5 этапов реализованы. Поверх базовой версии добавлена серия улучшений
по результатам реального использования (сессия 2026-03-29).

## Изменения 2026-03-29

### Исправления
- **matcher/main.py** — `sentence_transformers` импортируется до PySide6, что
  устраняет `MemoryError` в shiboken при загрузке `transformers` в runtime.

### GUI — таблица результатов (`matcher/gui/results_view.py`)
- **Статус** (двойной клик) — выпадающий список (ДА / НЕТ / ЛИНУКС / УСЛОВНО / пусто).
  Список открывается автоматически. В ячейке видна стрелка `▾`.
  При смене: цвет текста обновляется, источник → "Ручной".
- **ППТС ID** (двойной клик) — прямое редактирование текста.
- Редактирование работает корректно после сортировки таблицы (каждая ячейка
  хранит оригинальный индекс результата через `UserRole+100`).

### GUI — главное окно (`matcher/gui/main_window.py`)
- Поле **Ответственный** — редактируемый ComboBox. Введённые имена
  сохраняются в `~/.vuln-analyzer/responsible_persons.json` и подтягиваются
  при следующем запуске.
- Поле **Публикация** — выбор «БДУ ФСТЕК» / «RSS». Последний выбор сохраняется.
- Оба поля сохраняются при экспорте и при закрытии окна.
- После экспорта диалог содержит кнопку **«Открыть файл»**
  (`QDesktopServices.openUrl`).
- Экспорт берёт данные из `results_view.get_results()` (с ручными правками).

### Конфиг (`matcher/config.py`)
- `load_responsible_data()` / `save_responsible_data()` — хранение списка
  ответственных и последнего выбора публикации.

### Пайплайн (`matcher/core/pipeline.py`)
- Векторный поиск теперь выполняется с `threshold=0` (top-N без фильтра).
  Порог конфигурации применяется отдельно: если ни один кандидат его не
  прошёл — статус НЕТ, иначе все top-N передаются дальше. Благодаря этому
  детальный анализ получает полный список кандидатов, а не 0–1.

### Отчёт (`matcher/io/report_writer.py`)

**Основная таблица (лист 1) — новый порядок столбцов:**

| № | Столбец | Логика |
|---|---------|--------|
| 1 | № | Порядковый номер |
| 2 | Дата | Вчера если 00:00–08:00, иначе сегодня |
| 3 | Ответственный | Из поля в UI |
| 4 | Публикация | БДУ ФСТЕК / RSS |
| 5 | Статус | Цветной текст; пустой статус = пустая ячейка |
| 6 | ID ППТС | `----------` для НЕТ/УСЛОВНО/ЛИНУКС; ID для ДА |
| 7 | CVE | Из ТСУ |
| 8 | CVSS | Из ТСУ |
| 9 | Продукт | `Вендор - Продукт` из ТСУ |
| 10 | Источник | Ссылка из ТСУ |

- Цвет текста статуса: НЕТ=зелёный, ДА=красный, ЛИНУКС=синий, УСЛОВНО=оранжевый.
- Рамки таблицы: толстая внешняя (medium, тёмно-синяя) + тонкие внутренние.

**Детальный анализ (лист 2):**
- Добавлен столбец **№** — совпадает с номером в основной таблице.
- Продукт ТСУ и кандидат ППТС: `Вендор - Наименование`.
- Столбец **Ранг** — тир по combined_score: 1 (≥0.7) / 2 (≥0.4) / 3 (<0.4).
- Фильтрация кандидатов для отображения:
  - Есть тир-1 → все тир-1 + топ-3 тир-2
  - Нет тир-1, есть тир-2 → все тир-2 + топ-3 тир-3
  - Нет тир-1 и тир-2 → все тир-3

**Справка (лист 3):** добавлена таблица описания рангов.

---

## Порядок разработки

### Этап 1: Фундамент (shared + core без GUI) ✅
- [x] shared/types.py — все dataclasses
- [x] shared/constants.py — статусы, дефолты
- [x] shared/db/models.py — SQLite схема (rules, scripts_config)
- [x] shared/db/repository.py — CRUD для правил
- [x] matcher/io/readers.py — чтение Excel/CSV (ТСУ, ППТС)
- [x] Тесты для readers и repository
- [x] pyproject.toml — конфигурация проекта

### Этап 2: Пайплайн Сопоставителя (core) ✅
- [x] matcher/core/preprocessor.py — загрузка и запуск плагинов
- [x] matcher/core/vectorizer.py — sentence-transformers + cosine search
- [x] matcher/core/normalizer.py — транслитерация
- [x] matcher/core/fuzzy_matcher.py — RapidFuzz
- [x] matcher/core/exact_matcher.py — прямое сопоставление
- [x] matcher/core/scorer.py — комбинированный скоринг (50% vector + 30% fuzzy + 20% exact)
- [x] matcher/core/status_assigner.py — логика статусов + проверка по БЗ
- [x] matcher/core/pipeline.py — оркестратор всех этапов

### Этап 3: GUI Сопоставителя ✅
- [x] matcher/gui/styles/theme.qss — modern flat тема
- [x] matcher/gui/main_window.py — главное окно + QThread
- [x] matcher/gui/file_loader.py — загрузка файлов
- [x] matcher/gui/settings_panel.py — настройки
- [x] matcher/gui/progress_view.py — прогресс-бар + лог
- [x] matcher/gui/results_view.py — таблица результатов
- [x] matcher/io/report_writer.py — XLSX отчёт (3 листа)
- [x] matcher/config.py + matcher/main.py

### Этап 4: База Знаний (отдельное приложение) ✅
- [x] knowledge_base/gui/main_window.py — главное окно
- [x] knowledge_base/gui/rules_table.py — таблица с поиском/фильтрацией
- [x] knowledge_base/gui/rule_editor.py — редактор правил
- [x] knowledge_base/gui/rule_tester.py — тестирование правил
- [x] knowledge_base/gui/styles/theme.qss — teal-accent тема
- [x] knowledge_base/config.py + knowledge_base/main.py

### Этап 5: Плагины + Полировка ✅
- [x] scripts/_template.py — шаблон плагина
- [x] scripts/split_multiproduct.py — разбивка мультипродуктовых строк
- [x] scripts/clean_microsoft.py — очистка Microsoft-мусора
- [x] scripts/clean_versions.py — удаление версий/годов
- [x] matcher.spec + knowledge_base.spec — PyInstaller сборка
- [x] requirements.txt
- [x] README.md
- [x] tests/test_scripts.py — 22 теста для плагинов

## Запуск

```bash
python -m matcher.main          # Сопоставитель
python -m knowledge_base.main   # База Знаний
pytest tests/ -v                # тесты
pyinstaller matcher.spec        # Сборка EXE
pyinstaller knowledge_base.spec # Сборка EXE
```

## Читать перед работой
- CLAUDE.md — полная спецификация
- shared/types.py — все dataclasses
- matcher/core/pipeline.py — оркестратор
