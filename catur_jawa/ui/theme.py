from __future__ import annotations

WINDOW_BG = "#2A160C"
BACKGROUND_OVERLAY = "rgba(24, 14, 8, 0.20)"
TOP_BAR_SURFACE = "rgba(24, 13, 7, 0.42)"
GLASS_SURFACE = "rgba(45, 24, 13, 0.76)"
GLASS_HOVER = "rgba(58, 32, 18, 0.82)"
GLASS_OUTLINE = "rgba(238, 194, 136, 0.20)"
TEXT = "#F6EBDD"
MUTED = "#C9B29A"
TEXT_MUTED = "#9D8875"
PIECE_A_FILL = "#F0D9B5"
PIECE_A_TEXT = "#2E2118"
PIECE_B_FILL = "#33383D"
PIECE_B_TEXT = "#F7F3EC"
BOARD_LINE = "#D4A66D"
BOARD_NODE = "#DDB47E"
BOARD_LINE_INACTIVE = "rgba(212, 166, 109, 0.64)"
ACCENT = "#F0B94F"
ACCENT_HOVER = "#FFD06A"
SUCCESS = "#55C65A"
WARNING = "#E0A63A"
DANGER = "#D85E58"
CAPTURE = "#D98942"

DISPLAY_FONT = "Nunito Sans, Inter, Noto Sans, DejaVu Sans, sans-serif"
UI_FONT = DISPLAY_FONT


def stylesheet() -> str:
    return f"""
    QWidget {{
        background: transparent;
        color: {TEXT};
        font-family: Nunito Sans, Inter, Noto Sans, DejaVu Sans, sans-serif;
        font-size: 13px;
    }}
    QMainWindow {{
        background: {WINDOW_BG};
    }}
    QLabel#Title {{
        font-size: 30px;
        font-weight: 800;
    }}
    QLabel#MenuTitle {{
        color: {TEXT};
        font-size: 42px;
        font-weight: 900;
    }}
    QLabel#MenuEmblem {{
        color: {ACCENT};
        font-size: 34px;
        font-weight: 900;
    }}
    QLabel#Subtitle, QLabel#Muted, QCheckBox {{
        color: {MUTED};
    }}
    QLabel#Badge {{
        background: {GLASS_SURFACE};
        border: 1px solid {GLASS_OUTLINE};
        border-radius: 18px;
        padding: 8px 14px;
        font-weight: 700;
    }}
    QLabel#TurnPill {{
        background: rgba(45, 24, 13, 0.56);
        border: 1px solid {GLASS_OUTLINE};
        border-radius: 24px;
        padding: 12px 34px;
        font-size: 19px;
        font-weight: 800;
    }}
    QLabel#TokenA, QLabel#TokenB {{
        border-radius: 22px;
        min-width: 44px;
        min-height: 44px;
        max-width: 44px;
        max-height: 44px;
        font-size: 19px;
        font-weight: 800;
    }}
    QLabel#TokenA {{
        background: {PIECE_A_FILL};
        color: {PIECE_A_TEXT};
    }}
    QLabel#TokenB {{
        background: {PIECE_B_FILL};
        color: {PIECE_B_TEXT};
    }}
    QPushButton {{
        background: {GLASS_SURFACE};
        border: 1px solid {GLASS_OUTLINE};
        border-radius: 16px;
        padding: 10px 14px;
        font-weight: 700;
    }}
    QPushButton:hover {{
        background: {GLASS_HOVER};
    }}
    QPushButton:pressed {{
        background: rgba(32, 16, 8, 0.84);
    }}
    QPushButton:disabled {{
        color: #B29C85;
        background: rgba(63, 39, 24, 0.56);
    }}
    QPushButton#Primary {{
        background: {ACCENT};
        color: #2B190A;
    }}
    QPushButton#Primary:hover {{
        background: {ACCENT_HOVER};
    }}
    QPushButton#Primary:disabled {{
        background: #3A4A2D;
        color: #8E9A83;
    }}
    QPushButton#Danger:disabled {{
        background: #4A302E;
        color: #9A807D;
    }}
    QPushButton#Danger {{
        background: {DANGER};
        color: #160807;
    }}
    QPushButton#RailButton {{
        min-width: 82px;
        min-height: 72px;
        border-radius: 22px;
        font-size: 14px;
        padding: 8px 6px;
    }}
    QPushButton#MenuButton {{
        min-width: 52px;
        min-height: 52px;
        max-width: 52px;
        max-height: 52px;
        border-radius: 26px;
        font-size: 24px;
    }}
    QFrame#GlassRail, QFrame#Drawer, QFrame#BottomStatus {{
        background: {GLASS_SURFACE};
        border: 1px solid {GLASS_OUTLINE};
        border-radius: 26px;
    }}
    QListWidget {{
        background: transparent;
        border: none;
        outline: 0;
    }}
    QListWidget::item {{
        padding: 7px 4px;
        border-bottom: 1px solid rgba(244, 244, 244, 0.06);
    }}
    QTextEdit {{
        background: rgba(31, 17, 9, 0.45);
        border: 1px solid {GLASS_OUTLINE};
        border-radius: 16px;
        padding: 8px;
    }}
    QCheckBox::indicator {{
        width: 22px;
        height: 22px;
        border-radius: 7px;
        border: 1px solid {GLASS_OUTLINE};
        background: rgba(45, 24, 13, 0.72);
    }}
    QCheckBox::indicator:checked {{
        background: {ACCENT};
        border: 1px solid {ACCENT_HOVER};
    }}
    QLineEdit, QSpinBox {{
        background: rgba(45, 24, 13, 0.72);
        color: {TEXT};
        border: 1px solid {GLASS_OUTLINE};
        border-radius: 15px;
        padding: 10px 15px;
        min-height: 30px;
        font-size: 16px;
        font-weight: 700;
        selection-background-color: {ACCENT};
        selection-color: #2B190A;
    }}
    QLineEdit:focus, QSpinBox:focus {{
        border: 2px solid {ACCENT};
    }}
    QLabel#PageTitle {{
        color: {TEXT};
        font-size: 32px;
        font-weight: 800;
    }}
    QLabel#PageDescription {{
        color: {MUTED};
        font-size: 16px;
        font-weight: 600;
    }}
    QLabel#FieldLabel {{
        color: {TEXT};
        font-size: 14px;
        font-weight: 800;
    }}
    QLabel#HelperText {{
        color: {TEXT_MUTED};
        font-size: 13px;
        font-weight: 600;
    }}
    QLabel#ErrorText {{
        color: {DANGER};
        font-size: 13px;
        font-weight: 800;
    }}
    QPushButton#LinkButton {{
        background: transparent;
        border: 1px solid transparent;
        color: {MUTED};
        padding: 8px 12px;
    }}
    QPushButton#LinkButton:hover {{
        color: {TEXT};
        border-color: {GLASS_OUTLINE};
        background: rgba(45, 24, 13, 0.42);
    }}
    """
