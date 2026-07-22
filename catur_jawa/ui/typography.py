from __future__ import annotations

from PySide6.QtGui import QFont, QFontDatabase

FONT_CANDIDATES = ("Nunito Sans", "Inter", "Noto Sans", "DejaVu Sans")


def family() -> str:
    installed = set(QFontDatabase.families())
    for candidate in FONT_CANDIDATES:
        if candidate in installed:
            return candidate
    return "sans-serif"


def font(size: int, weight: QFont.Weight = QFont.Weight.DemiBold) -> QFont:
    return QFont(family(), size, weight)


def title(size: int = 40) -> QFont:
    return font(size, QFont.Weight.ExtraBold)


def page_title(size: int = 31) -> QFont:
    return font(size, QFont.Weight.ExtraBold)


def body(size: int = 16) -> QFont:
    return font(size, QFont.Weight.Medium)


def label(size: int = 14) -> QFont:
    return font(size, QFont.Weight.Bold)
