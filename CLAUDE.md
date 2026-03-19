# Анализатор Статусов Уязвимостей v2.0

Два независимых десктопных приложения для автоматизации анализа уязвимостей: **Сопоставитель** (основной анализ ТСУ vs ППТС) и **База Знаний** (менеджер правил). Связь — через общий SQLite-файл.

## Стек

- Python 3.11+
- PySide6 (GUI — modern, красивый, с кастомными QSS-стилями)
- sentence-transformers (локальные embeddings, офлайн)
- scikit-learn (cosine similarity)
- rapidfuzz (нечёткое сравнение строк)
- transliterate (транслитерация кириллица ↔ латиница)
- openpyxl (генерация xlsx-отчётов)
- SQLite3 (хранение базы знаний)
- PyInstaller (сборка в exe)

## Команды

```bash
# Запуск Сопоставителя
python -m matcher.main

# Запуск Базы Знаний
python -m knowledge_base.main

# Тесты
pytest tests/ -v

# Линтинг
ruff check .

# Сборка exe
pyinstaller matcher.spec
pyinstaller knowledge_base.spec
```

## Структура проекта

```
vuln-analyzer/
├── CLAUDE.md
├── CURRENT_STAGE.md
├── README.md
├── requirements.txt
├── pyproject.toml
│
├── shared/                     # Общий код для обоих приложений
│   ├── __init__.py
│   ├── db/
│   │   ├── __init__.py
│   │   ├── models.py           # SQLite схема, миграции
│   │   └── repository.py       # CRUD операции с базой знаний
│   ├── types.py                # Общие dataclasses/TypedDict
│   └── constants.py            # Статусы, дефолтные пороги
│
├── matcher/                    # Приложение 1: Сопоставитель
│   ├── __init__.py
│   ├── main.py                 # Точка входа
│   ├── gui/
│   │   ├── __init__.py
│   │   ├── main_window.py      # Главное окно
│   │   ├── settings_panel.py   # Панель настроек (пороги, top-n, транслит)
│   │   ├── file_loader.py      # Виджеты загрузки файлов
│   │   ├── progress_view.py    # Прогресс-бар + лог
│   │   ├── results_view.py     # Предпросмотр результатов
│   │   └── styles/
│   │       └── theme.qss       # QSS-стили
│   ├── core/
│   │   ├── __init__.py
│   │   ├── pipeline.py         # Оркестратор всего пайплайна
│   │   ├── preprocessor.py     # Загрузчик и запуск плагинов-скриптов
│   │   ├── vectorizer.py       # sentence-transformers + cosine search
│   │   ├── normalizer.py       # Транслитерация / приведение к одному языку
│   │   ├── fuzzy_matcher.py    # RapidFuzz сравнение
│   │   ├── exact_matcher.py    # Прямое/подстроковое сопоставление
│   │   ├── scorer.py           # Комбинированный скоринг (vector+fuzzy+exact)
│   │   └── status_assigner.py  # Логика присвоения статусов
│   ├── io/
│   │   ├── __init__.py
│   │   ├── readers.py          # Чтение ТСУ, ППТС (Excel/CSV)
│   │   └── report_writer.py    # Генерация xlsx-отчёта (3 листа)
│   └── config.py               # Настройки приложения (defaults, пути)
│
├── knowledge_base/             # Приложение 2: База Знаний
│   ├── __init__.py
│   ├── main.py                 # Точка входа
│   ├── gui/
│   │   ├── __init__.py
│   │   ├── main_window.py      # Главное окно
│   │   ├── rules_table.py      # Таблица правил с поиском/фильтрацией
│   │   ├── rule_editor.py      # Диалог создания/редактирования правила
│   │   ├── rule_tester.py      # Тест правила на данных
│   │   └── styles/
│   │       └── theme.qss       # QSS-стили
│   └── config.py
│
├── scripts/                    # Плагины препроцессинга (НЕ в exe, рядом)
│   ├── _template.py            # Шаблон для новых скриптов
│   ├── split_multiproduct.py   # Разбивка мультипродуктовых строк
│   ├── clean_microsoft.py      # Очистка Microsoft-специфичного мусора
│   └── clean_versions.py       # Удаление версий/годов
│
├── tests/
│   ├── __init__.py
│   ├── test_pipeline.py
│   ├── test_vectorizer.py
│   ├── test_fuzzy_matcher.py
│   ├── test_preprocessor.py
│   └── test_knowledge_base.py
│
└── .claude/
    └── commands/
        ├── review.md
        └── test-pipeline.md
```

## Архитектура

### Два приложения, общая база

```
[Сопоставитель.exe]  ←──→  [knowledge.db (SQLite)]  ←──→  [База Знаний.exe]
                                    │
                              rules table
                              scripts_config table
                              processing_log table
```

- Приложения НИКОГДА не общаются напрямую — только через SQLite
- Сопоставитель ЧИТАЕТ базу знаний (не пишет)
- База Знаний УПРАВЛЯЕТ правилами (полный CRUD)

### Пайплайн Сопоставителя

```
Загрузка ТСУ + ППТС
        │
        ▼
[Препроцессинг] — плагины из scripts/ разделяют/очищают строки
        │
        ▼
[Проверка по БЗ] — если включена, exact→contains→regex→vector по правилам
        │  (совпало → статус мгновенно, дальше не идёт)
        ▼
[Векторный поиск] — embeddings + cosine similarity → Top-N кандидатов
        │
        ▼
[Нормализация] — транслитерация к одному языку
        │
        ▼
[Fuzzy-сравнение] — RapidFuzz на нормализованных строках
        │
        ▼
[Прямое сопоставление] — exact/substring match для финального ранга
        │
        ▼
[Скоринг + статус] — комбинированный балл → статус (НЕТ / пустой)
        │
        ▼
[XLSX-отчёт] — 3 листа: основная таблица, детальный анализ, справка
```

### Система плагинов (Препроцессинг)

Папка `scripts/` содержит .py файлы. Каждый скрипт реализует контракт:

```python
def process(entries: list[dict]) -> list[dict]:
    """
    entry = {
        "vendor": str,
        "product": str, 
        "version": str,
        "raw_text": str  # исходная строка из ТСУ
    }
    Может вернуть больше записей чем получил (разбивка мультипродукта).
    """
```

Правила запуска скриптов хранятся в SQLite (таблица scripts_config):
- condition: когда запускать (vendor contains X, product matches regex Y)
- script_path: какой .py файл
- priority: порядок выполнения
- enabled: вкл/выкл

### База Знаний — структура правила (SQLite)

```sql
CREATE TABLE rules (
    id INTEGER PRIMARY KEY,
    pattern TEXT NOT NULL,           -- что матчим
    match_type TEXT NOT NULL,        -- exact | contains | regex | vector
    status TEXT NOT NULL,            -- ДА | НЕТ | ЛИНУКС | УСЛОВНО
    ppts_id TEXT,                    -- ID из ППТС (опционально)
    vector_threshold REAL,           -- порог для vector-типа (опционально)
    comment TEXT,                    -- заметка аналитика
    created_at TIMESTAMP,
    last_matched_at TIMESTAMP,       -- когда последний раз сработало
    match_count INTEGER DEFAULT 0    -- сколько раз сработало
);
```

### Статусы уязвимостей

- **ДА** — ПО есть в инфраструктуре (только через базу знаний, НИКОГДА автоматически)
- **НЕТ** — ПО нет в инфраструктуре (автоматически, если 0 кандидатов после воронки)
- **ЛИНУКС** — Linux-специфичное ПО
- **УСЛОВНО** — требует дополнительной проверки
- **Пустой** — есть кандидаты, но уверенности недостаточно → ручной разбор

### XLSX-отчёт (3 листа)

1. **Основная таблица** — все уязвимости + финальный статус + ID ППТС + источник решения (БЗ/авто)
2. **Детальный анализ** — для строк с пустым статусом: список кандидатов с vector_score, fuzzy_score, exact_score, итоговый ранг. Цветовое кодирование.
3. **Справка** — документация к метрикам и порогам, использованным в этом запуске

## Ключевые сущности

```python
@dataclass
class Vulnerability:
    cve_id: str
    vendor: str
    product: str
    version: str
    raw_text: str

@dataclass 
class Software:
    id: str
    name: str
    source: str  # "local_ppts" | "general_ppts"

@dataclass
class MatchCandidate:
    software: Software
    vector_score: float
    fuzzy_score: float
    exact_score: float
    combined_score: float

@dataclass
class AnalysisResult:
    vulnerability: Vulnerability
    status: str  # ДА | НЕТ | ЛИНУКС | УСЛОВНО | ""
    status_source: str  # "knowledge_base" | "auto_no_match" | "manual"
    candidates: list[MatchCandidate]
    ppts_id: str | None
```

## GUI — настраиваемые параметры (Сопоставитель)

| Параметр | Тип | Дефолт | Описание |
|----------|-----|--------|----------|
| top_n | int | 10 | Кол-во кандидатов из векторного поиска |
| vector_threshold | float | 0.5 | Минимальный cosine similarity |
| fuzzy_threshold | int | 75 | Минимальный fuzzy score (0-100) |
| transliteration_direction | str | "to_en" | Направление: to_en / to_ru |
| min_word_length | int | 3 | Минимальная длина слова для сравнения |
| use_knowledge_base | bool | False | Подключить базу знаний |
| kb_path | str | "" | Путь к SQLite-файлу базы знаний |

## Правила кода

- Типизация ВЕЗДЕ: параметры функций, возвращаемые значения, dataclasses
- Никаких print() — только logging (модуль logging, уровни DEBUG/INFO/WARNING/ERROR)
- Docstrings для всех публичных функций и классов
- Бизнес-логика ТОЛЬКО в core/ — GUI не содержит логику
- GUI общается с core/ через сигналы PySide6 (Signal/Slot)
- Все пороги и дефолты — в shared/constants.py, НЕ магические числа в коде
- Ошибки чтения файлов — перехватывать и показывать пользователю через GUI, не крашить
- Каждый этап пайплайна — отдельный класс с методом process() 
- Плагины из scripts/ загружаются через importlib, изолированы try/except
- SQLite — WAL mode для безопасного параллельного чтения
- QSS-стили ТОЛЬКО в .qss файлах, не инлайн в Python-коде
- Язык интерфейса: русский
- Язык кода (переменные, комментарии, docstrings): английский
