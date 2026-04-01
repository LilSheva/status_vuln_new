"""Chaos theme generator — random but readable color palettes via HSL."""

from __future__ import annotations

import colorsys
import random


def _hsl_to_hex(h: float, s: float, l: float) -> str:
    r, g, b = colorsys.hls_to_rgb(h, l, s)
    return f"#{int(r * 255):02x}{int(g * 255):02x}{int(b * 255):02x}"


def generate_chaos_palette() -> dict[str, str]:
    """Generate a random palette with consistent readability."""
    hue = random.random()

    primary = _hsl_to_hex(hue, 0.60, 0.52)
    primary_hover = _hsl_to_hex(hue, 0.60, 0.45)
    primary_pressed = _hsl_to_hex(hue, 0.60, 0.38)
    primary_disabled = _hsl_to_hex(hue, 0.15, 0.70)
    disabled_text = _hsl_to_hex(hue, 0.08, 0.82)

    bg_hue = (hue + 0.5) % 1.0
    bg = _hsl_to_hex(bg_hue, 0.06, 0.96)
    bg_card = _hsl_to_hex(bg_hue, 0.04, 0.99)
    bg_log = _hsl_to_hex(bg_hue, 0.05, 0.98)
    bg_readonly = _hsl_to_hex(bg_hue, 0.05, 0.95)

    text = _hsl_to_hex(hue, 0.20, 0.15)
    text_secondary = _hsl_to_hex(hue, 0.10, 0.52)
    text_label = _hsl_to_hex(hue, 0.15, 0.22)
    text_title = _hsl_to_hex(hue, 0.30, 0.12)
    text_group = _hsl_to_hex(hue, 0.25, 0.38)
    text_readonly = _hsl_to_hex(hue, 0.10, 0.45)

    border = _hsl_to_hex(bg_hue, 0.10, 0.84)
    border_input = _hsl_to_hex(bg_hue, 0.12, 0.80)
    header_bg = _hsl_to_hex(hue, 0.12, 0.92)
    header_text = _hsl_to_hex(hue, 0.15, 0.32)
    selection_bg = _hsl_to_hex(hue, 0.25, 0.90)
    alt_row = _hsl_to_hex(bg_hue, 0.04, 0.97)
    gridline = _hsl_to_hex(bg_hue, 0.08, 0.91)
    scrollbar = _hsl_to_hex(hue, 0.12, 0.78)
    scrollbar_hover = _hsl_to_hex(hue, 0.15, 0.68)
    splitter = _hsl_to_hex(bg_hue, 0.08, 0.86)
    btn_secondary = _hsl_to_hex(bg_hue, 0.06, 0.93)
    btn_secondary_hover = _hsl_to_hex(bg_hue, 0.08, 0.88)
    checkbox_border = _hsl_to_hex(hue, 0.10, 0.72)

    return {
        "primary": primary,
        "primary_hover": primary_hover,
        "primary_pressed": primary_pressed,
        "primary_disabled": primary_disabled,
        "disabled_text": disabled_text,
        "bg": bg,
        "bg_card": bg_card,
        "bg_log": bg_log,
        "bg_readonly": bg_readonly,
        "text": text,
        "text_secondary": text_secondary,
        "text_label": text_label,
        "text_title": text_title,
        "text_group": text_group,
        "text_readonly": text_readonly,
        "border": border,
        "border_input": border_input,
        "header_bg": header_bg,
        "header_text": header_text,
        "selection_bg": selection_bg,
        "alt_row": alt_row,
        "gridline": gridline,
        "scrollbar": scrollbar,
        "scrollbar_hover": scrollbar_hover,
        "splitter": splitter,
        "btn_secondary": btn_secondary,
        "btn_secondary_hover": btn_secondary_hover,
        "checkbox_border": checkbox_border,
    }
