"""
Anvil Theme - warm light theme "Sand & Terracotta" (chosen 2026-10-20).

Warm paper backgrounds, one terracotta accent, colour kept for meaning. Warnings always carry an
icon and a word as well as colour, because terracotta and warning red are close.
Font: IBM Plex Sans JP (Latin, French accents and Japanese in one family), bundled in ui/assets/fonts.
Type scale: 32 / 22 / 18 / 16 (body) / 14 / 13 (smallest). Spacing 4-8-12-16-24-32. Radius 12 cards, 20 pills.
The old token names are kept so every view picks the new colours up.
"""

import re

import flet as ft


class Colors:
    # Surfaces
    BG_PRIMARY = "#F5F2EC"      # page
    BG_SECONDARY = "#FFFFFF"    # cards, panels
    BG_TERTIARY = "#ECE7DF"     # rail, chips, quiet fills
    BORDER = "#D9D2C7"

    # Text (all pass WCAG AA on the page and on cards)
    TEXT_PRIMARY = "#262321"
    TEXT_SECONDARY = "#56504A"
    TEXT_MUTED = "#736C64"

    # Accent
    ACCENT = "#A84B24"          # terracotta
    ACCENT_HOVER = "#8E3E1D"
    ACCENT_SOFT = "#F8E6DC"     # selected nav item, soft buttons

    # Meaning
    SUCCESS = "#2B7656"
    WARNING = "#94630A"
    ERROR = "#A8332B"
    SUCCESS_SOFT = "#E3F0E9"
    WARNING_SOFT = "#F6EBD6"
    ERROR_SOFT = "#F7E2DE"

    # Severity (fraud-check warnings)
    SEVERITY_HIGH = ERROR
    SEVERITY_MEDIUM = WARNING
    SEVERITY_LOW = "#7A6A2E"


class Fonts:
    BODY = "Plex"
    MEDIUM = "Plex"                 # two files only: fewer bytes to load at start
    SEMIBOLD = "Plex SemiBold"
    FILES = {
        "Plex": "fonts/IBMPlexSansJP-Regular.ttf",
        "Plex SemiBold": "fonts/IBMPlexSansJP-SemiBold.ttf",
    }


# name: (size, font)
TYPE = {
    "display": (32, Fonts.SEMIBOLD),
    "title": (22, Fonts.SEMIBOLD),
    "section": (18, Fonts.MEDIUM),
    "strong": (16, Fonts.SEMIBOLD),
    "body": (16, Fonts.BODY),
    "secondary": (14, Fonts.BODY),
    "caption": (13, Fonts.BODY),
}


_LINK = re.compile(r"(https?://[^\s<>\"'（）]+|www\.[^\s<>\"'（）]+|[\w.+-]+@[\w-]+(?:\.[\w-]+)+"
                   r"|\b(?:[a-z0-9-]+\.)+(?:com|net|org|io|jp|fr|eu|de|be|ch|lu|ie|nl|es|it|co\.jp)\b(?:/[^\s<>\"'（）]*)?)",
                   re.IGNORECASE)


def _spans(value: str):
    """Plain text split into spans; web addresses and e-mail addresses become clickable links."""
    spans, pos = [], 0
    for m in _LINK.finditer(value):
        raw = m.group(0).rstrip(".,;:)」、。")
        start, end = m.start(), m.start() + len(raw)
        if start > pos:
            spans.append(ft.TextSpan(value[pos:start]))
        url = raw if raw.lower().startswith("http") else ("mailto:" + raw if "@" in raw else "https://" + raw)
        spans.append(ft.TextSpan(raw, url=url, style=ft.TextStyle(color=Colors.ACCENT,
                                                                  decoration=ft.TextDecoration.UNDERLINE)))
        pos = end
    if pos < len(value):
        spans.append(ft.TextSpan(value[pos:]))
    return spans


def text(value, kind: str = "body", color: str = None, **kw) -> ft.Text:
    """A Text in the type scale: display, title, section, strong, body, secondary, caption.
    Links and e-mail addresses inside the text are clickable."""
    size, font = TYPE[kind]
    if color is None:
        color = Colors.TEXT_SECONDARY if kind in ("secondary", "caption") else Colors.TEXT_PRIMARY
    if isinstance(value, str) and _LINK.search(value):
        return ft.Text(spans=_spans(value), size=size, font_family=font, color=color, **kw)
    return ft.Text(value, size=size, font_family=font, color=color, **kw)


def get_theme() -> ft.Theme:
    return ft.Theme(
        font_family=Fonts.BODY,
        color_scheme_seed=Colors.ACCENT,
        color_scheme=ft.ColorScheme(
            primary=Colors.ACCENT,
            on_primary="#FFFFFF",
            primary_container=Colors.ACCENT_SOFT,
            on_primary_container=Colors.ACCENT_HOVER,
            secondary=Colors.TEXT_SECONDARY,
            on_secondary="#FFFFFF",
            secondary_container=Colors.BG_TERTIARY,
            on_secondary_container=Colors.TEXT_PRIMARY,
            surface=Colors.BG_SECONDARY,
            on_surface=Colors.TEXT_PRIMARY,
            on_surface_variant=Colors.TEXT_SECONDARY,
            surface_container_lowest="#FFFFFF",
            surface_container_low="#FBF9F5",
            surface_container=Colors.BG_PRIMARY,
            surface_container_high=Colors.BG_TERTIARY,
            surface_container_highest="#E4DED4",
            outline=Colors.BORDER,
            outline_variant=Colors.BORDER,
            error=Colors.ERROR,
            on_error="#FFFFFF",
        ),
    )


def style_page(page: ft.Page):
    """Apply the theme to a page."""
    page.fonts = Fonts.FILES
    page.theme = get_theme()
    page.theme_mode = ft.ThemeMode.LIGHT
    page.bgcolor = Colors.BG_PRIMARY
    page.padding = 0
