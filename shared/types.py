"""Shared data types for the vulnerability analyzer."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Vulnerability:
    """A single vulnerability entry from TSU (ТСУ) file."""

    cve_id: str
    vendor: str
    product: str
    version: str
    raw_text: str
    cvss: str = ""
    source_url: str = ""


@dataclass
class Software:
    """A software entry from PPTS (ППТС) file."""

    id: str
    name: str
    vendor: str
    source: str  # "local_ppts" | "general_ppts"


@dataclass
class JournalEntry:
    """A row from a historical vulnerability journal."""

    cve_id: str
    status: str
    ppts_id: str
    responsible: str
    product: str = ""


@dataclass
class MatchCandidate:
    """A candidate match between a vulnerability and a software entry."""

    software: Software
    vector_score: float = 0.0
    fuzzy_score: float = 0.0
    exact_score: float = 0.0
    combined_score: float = 0.0


@dataclass
class AnalysisResult:
    """Final analysis result for a single vulnerability."""

    vulnerability: Vulnerability
    status: str  # ДА | НЕТ | ЛИНУКС | УСЛОВНО | ""
    status_source: str  # "journal" | "knowledge_base" | "auto_no_match" | "manual"
    candidates: list[MatchCandidate] = field(default_factory=list)
    ppts_id: str | None = None
    responsible: str | None = None


@dataclass
class KnowledgeBaseRule:
    """A rule from the knowledge base with vendor/product pattern matching."""

    id: int | None = None
    pattern: str = ""                           # legacy / product pattern
    match_type: str = "exact"                   # legacy / product match type
    vendor_pattern: str = ""                    # vendor pattern (empty = any vendor)
    vendor_match_type: str = "contains"         # vendor match type
    status: str = ""                            # ДА | НЕТ | ЛИНУКС | УСЛОВНО
    ppts_id: str | None = None
    vector_threshold: float | None = None
    comment: str | None = None
    created_at: str | None = None
    last_matched_at: str | None = None
    match_count: int = 0


@dataclass
class PptsColumnMapping:
    """Column mapping for a PPTS file — which columns hold ID, name, vendor."""

    file_path: str = ""
    col_id: int | None = None        # column index for PPTS ID
    col_name: int | None = None      # column index for product name
    col_vendor: int | None = None    # column index for vendor
    headers: list[str] = field(default_factory=list)  # raw headers for display


@dataclass
class ScriptConfig:
    """Configuration for a preprocessing script plugin."""

    id: int | None = None
    script_path: str = ""
    condition: str = ""
    priority: int = 0
    enabled: bool = True


@dataclass
class PipelineSettings:
    """User-configurable pipeline parameters."""

    top_n: int = 10
    vector_threshold: float = 0.5
    fuzzy_threshold: int = 75
    transliteration_direction: str = "to_en"
    min_word_length: int = 3
    use_knowledge_base: bool = False
    kb_path: str = ""
    journal_paths: list[str] = field(default_factory=list)
    theme: str = "Светлая"
    detail_primary_limit: int = 0    # 0 = show all from primary tier
    detail_secondary_limit: int = 3  # top N from secondary tier
    use_preprocessing: bool = True
    scripts_dir: str = "scripts"
