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
    "primary": "#4aba7a",
    "primary_hover": "#5ccc8c",
    "primary_pressed": "#3aaa6a",
    "primary_disabled": "#3a4a40",
    "disabled_text": "#586858",
    "bg": "#1e1e1e",
    "bg_card": "#2a2a2a",
    "bg_log": "#242424",
    "bg_readonly": "#2e2e2e",
    "text": "#e0e0e0",
    "text_secondary": "#8a8a8a",
    "text_label": "#c0c0c0",
    "text_title": "#f0f0f0",
    "text_group": "#9aba9a",
    "text_readonly": "#707070",
    "border": "#404040",
    "border_input": "#484848",
    "header_bg": "#2e2e2e",
    "header_text": "#b0b0b0",
    "selection_bg": "#2a3a2e",
    "alt_row": "#232323",
    "gridline": "#353535",
    "scrollbar": "#484848",
    "scrollbar_hover": "#585858",
    "splitter": "#383838",
    "btn_secondary": "#333333",
    "btn_secondary_hover": "#3e3e3e",
    "checkbox_border": "#555555",
}

_DARK_TEAL: dict[str, str] = {
    **_DARK_PURPLE,
    "primary": "#2abba8",
    "primary_hover": "#3accb8",
    "primary_pressed": "#1aaa98",
    "primary_disabled": "#304848",
    "disabled_text": "#506060",
    "text_group": "#6aaa9a",
    "header_bg": "#2a3232",
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
