# Текущее состояние
Обновлено: 2026-03-18

## Фаза: ПРОЕКТ ЗАВЕРШЁН

Все 5 этапов реализованы. 137 тестов проходят.
Адаптировано под реальные форматы файлов (ТСУ, ППТС, Журнал).

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
pytest tests/ -v                # 130 тестов
pyinstaller matcher.spec        # Сборка EXE
pyinstaller knowledge_base.spec # Сборка EXE
```

## Читать перед работой
- CLAUDE.md — полная спецификация
- shared/types.py — все dataclasses
- matcher/core/pipeline.py — оркестратор
