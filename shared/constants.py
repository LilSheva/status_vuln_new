"""Shared constants for the vulnerability analyzer."""

# --- Vulnerability statuses ---
STATUS_YES = "ДА"
STATUS_NO = "НЕТ"
STATUS_LINUX = "ЛИНУКС"
STATUS_CONDITIONAL = "УСЛОВНО"
STATUS_EMPTY = ""

ALL_STATUSES = (STATUS_YES, STATUS_NO, STATUS_LINUX, STATUS_CONDITIONAL)

# --- Status sources ---
SOURCE_JOURNAL = "journal"
SOURCE_KNOWLEDGE_BASE = "knowledge_base"
SOURCE_AUTO_NO_MATCH = "auto_no_match"
SOURCE_MANUAL = "manual"

# --- Match types (knowledge base rules) ---
MATCH_EXACT = "exact"
MATCH_CONTAINS = "contains"
MATCH_REGEX = "regex"
MATCH_VECTOR = "vector"

ALL_MATCH_TYPES = (MATCH_EXACT, MATCH_CONTAINS, MATCH_REGEX, MATCH_VECTOR)

# --- Software sources ---
SOURCE_LOCAL_PPTS = "local_ppts"
SOURCE_GENERAL_PPTS = "general_ppts"

# --- Default pipeline thresholds ---
DEFAULT_TOP_N = 10
DEFAULT_VECTOR_THRESHOLD = 0.5
DEFAULT_FUZZY_THRESHOLD = 75
DEFAULT_TRANSLITERATION_DIRECTION = "to_en"
DEFAULT_MIN_WORD_LENGTH = 3

# --- Database ---
DB_DEFAULT_FILENAME = "knowledge.db"

# --- Embedding model ---
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
