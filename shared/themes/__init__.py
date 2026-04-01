"""Centralized theme system for both Matcher and Knowledge Base apps."""

from __future__ import annotations

import logging
from pathlib import Path

from shared.themes.generator import generate_chaos_palette

logger = logging.getLogger(__name__)

_TEMPLATE_PATH = Path(__file__).parent / "base.qss"

THEME_NAMES = ["Светлая", "Тёмная", "Хаос"]

_LIGHT_PURPLE: dict[str, str] = {
    "primary": "#5b6abf",
    "primary_hover": "#4a59ae",
    "primary_pressed": "#3d4c9e",
    "primary_disabled": "#b0b0c8",
    "disabled_text": "#e0e0e8",
    "bg": "#f5f5fa",
    "bg_card": "#ffffff",
    "bg_log": "#fafafe",
    "bg_readonly": "#f0f0f8",
    "text": "#1e1e2e",
    "text_secondary": "#7a7a9a",
    "text_label": "#2e2e4e",
    "text_title": "#1a1a3e",
    "text_group": "#4a4a6a",
    "text_readonly": "#6a6a8a",
    "border": "#d0d0e0",
    "border_input": "#c8c8e0",
    "header_bg": "#eaecf4",
    "header_text": "#3e3e5e",
    "selection_bg": "#e0e4f8",
    "alt_row": "#f8f8fc",
    "gridline": "#e8e8f0",
    "scrollbar": "#c0c0d8",
    "scrollbar_hover": "#a0a0c0",
    "splitter": "#d8d8e8",
    "btn_secondary": "#eceff4",
    "btn_secondary_hover": "#dde1ea",
    "checkbox_border": "#b0b0c8",
}

_LIGHT_TEAL: dict[str, str] = {
    **_LIGHT_PURPLE,
    "primary": "#2a9d8f",
    "primary_hover": "#238b80",
    "primary_pressed": "#1d7a70",
    "primary_disabled": "#b0c8c4",
    "disabled_text": "#e0e8e6",
    "text_title": "#1a3a3e",
    "text_group": "#3a6a6a",
    "header_bg": "#e2ecea",
    "header_text": "#2e4e4e",
    "selection_bg": "#d0ece8",
    "alt_row": "#f8faf9",
    "scrollbar": "#b8d0cc",
    "scrollbar_hover": "#90b8b0",
    "splitter": "#d0dcd8",
}

_DARK_PURPLE: dict[str, str] = {
    "primary": "#7b8acf",
    "primary_hover": "#8a99de",
    "primary_pressed": "#6a79be",
    "primary_disabled": "#404060",
    "disabled_text": "#606080",
    "bg": "#1a1a2e",
    "bg_card": "#252540",
    "bg_log": "#202038",
    "bg_readonly": "#2a2a44",
    "text": "#e0e0f0",
    "text_secondary": "#8a8aa0",
    "text_label": "#c0c0d8",
    "text_title": "#e8e8ff",
    "text_group": "#9a9abe",
    "text_readonly": "#707090",
    "border": "#3a3a55",
    "border_input": "#44446a",
    "header_bg": "#2a2a44",
    "header_text": "#b0b0cc",
    "selection_bg": "#3a3a60",
    "alt_row": "#222238",
    "gridline": "#303050",
    "scrollbar": "#404068",
    "scrollbar_hover": "#505080",
    "splitter": "#353555",
    "btn_secondary": "#2e2e4a",
    "btn_secondary_hover": "#383860",
    "checkbox_border": "#505070",
}

_DARK_TEAL: dict[str, str] = {
    **_DARK_PURPLE,
    "primary": "#3cb8a8",
    "primary_hover": "#4cc8b8",
    "primary_pressed": "#2ea898",
    "primary_disabled": "#304848",
    "disabled_text": "#506060",
    "text_title": "#d0f0ea",
    "text_group": "#6aaa9a",
    "header_bg": "#2a3844",
    "header_text": "#a0c0b8",
    "selection_bg": "#2a4a44",
    "scrollbar": "#3a5858",
    "scrollbar_hover": "#4a7070",
    "splitter": "#354545",
}

_PALETTE_MAP: dict[str, dict[str, str]] = {
    "matcher": {"Светлая": _LIGHT_PURPLE, "Тёмная": _DARK_PURPLE},
    "knowledge_base": {"Светлая": _LIGHT_TEAL, "Тёмная": _DARK_TEAL},
}


def _load_template() -> str:
    return _TEMPLATE_PATH.read_text(encoding="utf-8")


def _apply_palette(template: str, palette: dict[str, str]) -> str:
    result = template
    for key, value in palette.items():
        result = result.replace(f"@{key}@", value)
    return result


class ThemeManager:
    """Load and switch themes for a given app."""

    def __init__(self, app_name: str = "matcher") -> None:
        self._app_name = app_name
        self._template = _load_template()

    def get_stylesheet(self, theme_name: str) -> str:
        palette = self._resolve_palette(theme_name)
        return _apply_palette(self._template, palette)

    def _resolve_palette(self, theme_name: str) -> dict[str, str]:
        if theme_name == "Хаос":
            return generate_chaos_palette()
        app_palettes = _PALETTE_MAP.get(self._app_name, _PALETTE_MAP["matcher"])
        return app_palettes.get(theme_name, _LIGHT_PURPLE)
