"""Chaos theme generator — random but readable color palettes via HSL."""

from __future__ import annotations

import colorsys
import random


def _hsl_to_hex(h: float, s: float, l: float) -> str:
    r, g, b = colorsys.hls_to_rgb(h, l, s)
    return f"#{int(r * 255):02x}{int(g * 255):02x}{int(b * 255):02x}"


def _hex_to_rgb(hex_color: str) -> tuple[float, float, float]:
    """Convert hex color to (r, g, b) in [0, 1]."""
    h = hex_color.lstrip("#")
    return (int(h[0:2], 16) / 255.0, int(h[2:4], 16) / 255.0, int(h[4:6], 16) / 255.0)


def _relative_luminance(hex_color: str) -> float:
    """Compute relative luminance per WCAG 2.0."""
    r, g, b = _hex_to_rgb(hex_color)
    components = []
    for c in (r, g, b):
        if c <= 0.03928:
            components.append(c / 12.92)
        else:
            components.append(((c + 0.055) / 1.055) ** 2.4)
    return 0.2126 * components[0] + 0.7152 * components[1] + 0.0722 * components[2]


def _contrast_ratio(hex1: str, hex2: str) -> float:
    """Compute WCAG contrast ratio between two colors."""
    l1 = _relative_luminance(hex1)
    l2 = _relative_luminance(hex2)
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def generate_chaos_palette() -> dict[str, str]:
    """Generate a random palette with consistent readability."""
    hue = random.random()
    bg_hue = random.random()  # fully independent
    is_dark = random.choice([True, False])

    if is_dark:
        bg_l = random.uniform(0.10, 0.20)
        text_l = random.uniform(0.85, 0.95)
        card_l = bg_l + 0.05
        log_l = bg_l + 0.03
        readonly_l = bg_l + 0.02
        border_l = bg_l + 0.15
        border_input_l = bg_l + 0.18
        header_bg_l = bg_l + 0.08
        header_text_l = text_l - 0.10
        selection_bg_l = bg_l + 0.12
        alt_row_l = bg_l + 0.04
        gridline_l = bg_l + 0.10
        scrollbar_l = bg_l + 0.20
        scrollbar_hover_l = bg_l + 0.30
        splitter_l = bg_l + 0.12
        btn_secondary_l = bg_l + 0.08
        btn_secondary_hover_l = bg_l + 0.12
        checkbox_border_l = text_l - 0.20
        text_secondary_l = text_l - 0.20
        text_label_l = text_l - 0.10
        text_title_l = text_l
        text_group_l = text_l - 0.15
        text_readonly_l = text_l - 0.25
        disabled_text_l = bg_l + 0.25
        primary_disabled_l = bg_l + 0.15
    else:
        bg_l = random.uniform(0.90, 0.97)
        text_l = random.uniform(0.08, 0.20)
        card_l = bg_l - 0.03
        log_l = bg_l - 0.02
        readonly_l = bg_l - 0.01
        border_l = bg_l - 0.12
        border_input_l = bg_l - 0.16
        header_bg_l = bg_l - 0.04
        header_text_l = text_l + 0.15
        selection_bg_l = bg_l - 0.06
        alt_row_l = bg_l - 0.02
        gridline_l = bg_l - 0.06
        scrollbar_l = bg_l - 0.18
        scrollbar_hover_l = bg_l - 0.28
        splitter_l = bg_l - 0.10
        btn_secondary_l = bg_l - 0.04
        btn_secondary_hover_l = bg_l - 0.08
        checkbox_border_l = text_l + 0.50
        text_secondary_l = text_l + 0.35
        text_label_l = text_l + 0.08
        text_title_l = text_l
        text_group_l = text_l + 0.22
        text_readonly_l = text_l + 0.30
        disabled_text_l = bg_l - 0.14
        primary_disabled_l = bg_l - 0.26

    # Clamp all lightness values to [0, 1]
    def _clamp(v: float) -> float:
        return max(0.0, min(1.0, v))

    primary = _hsl_to_hex(hue, 0.60, 0.52)
    primary_hover = _hsl_to_hex(hue, 0.60, 0.45)
    primary_pressed = _hsl_to_hex(hue, 0.60, 0.38)
    primary_disabled = _hsl_to_hex(hue, 0.15, _clamp(primary_disabled_l))
    disabled_text = _hsl_to_hex(hue, 0.08, _clamp(disabled_text_l))

    bg = _hsl_to_hex(bg_hue, 0.06, _clamp(bg_l))
    bg_card = _hsl_to_hex(bg_hue, 0.04, _clamp(card_l))
    bg_log = _hsl_to_hex(bg_hue, 0.05, _clamp(log_l))
    bg_readonly = _hsl_to_hex(bg_hue, 0.05, _clamp(readonly_l))

    text = _hsl_to_hex(hue, 0.20, _clamp(text_l))
    text_secondary = _hsl_to_hex(hue, 0.10, _clamp(text_secondary_l))
    text_label = _hsl_to_hex(hue, 0.15, _clamp(text_label_l))
    text_title = _hsl_to_hex(hue, 0.30, _clamp(text_title_l))
    text_group = _hsl_to_hex(hue, 0.25, _clamp(text_group_l))
    text_readonly = _hsl_to_hex(hue, 0.10, _clamp(text_readonly_l))

    border = _hsl_to_hex(bg_hue, 0.10, _clamp(border_l))
    border_input = _hsl_to_hex(bg_hue, 0.12, _clamp(border_input_l))
    header_bg = _hsl_to_hex(hue, 0.12, _clamp(header_bg_l))
    header_text = _hsl_to_hex(hue, 0.15, _clamp(header_text_l))
    selection_bg = _hsl_to_hex(hue, 0.25, _clamp(selection_bg_l))
    alt_row = _hsl_to_hex(bg_hue, 0.04, _clamp(alt_row_l))
    gridline = _hsl_to_hex(bg_hue, 0.08, _clamp(gridline_l))
    scrollbar = _hsl_to_hex(hue, 0.12, _clamp(scrollbar_l))
    scrollbar_hover = _hsl_to_hex(hue, 0.15, _clamp(scrollbar_hover_l))
    splitter = _hsl_to_hex(bg_hue, 0.08, _clamp(splitter_l))
    btn_secondary = _hsl_to_hex(bg_hue, 0.06, _clamp(btn_secondary_l))
    btn_secondary_hover = _hsl_to_hex(bg_hue, 0.08, _clamp(btn_secondary_hover_l))
    checkbox_border = _hsl_to_hex(hue, 0.10, _clamp(checkbox_border_l))

    # Contrast check: ensure text vs bg has at least 4.5:1 ratio
    ratio = _contrast_ratio(text, bg)
    if ratio < 4.5:
        # Force text to be much darker/lighter to achieve contrast
        if is_dark:
            text = _hsl_to_hex(hue, 0.20, 0.95)
        else:
            text = _hsl_to_hex(hue, 0.20, 0.05)

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
