"""Палитра и стили. Стиль «войлок и кость»: плоская печать по бумаге, как у настольной игры.
Цвета — из монгольского флага и бурятского орнамента: синий — Вечное Небо,
красный — огонь очага, охра — солнце, кремовый — войлок и кость шагая."""

PAPER = "#EFE6D3"       # фон — некрашеный войлок
PAPER_LIGHT = "#F8F3E8"  # карточки, поля ввода
INK = "#1E1B18"         # текст и все обводки
INK_SOFT = "#6B6156"    # второстепенный текст
BLUE = "#1F4E8C"
BLUE_DARK = "#173B6B"
RED = "#C0392B"
RED_DARK = "#962D21"
OCHRE = "#E0A526"
FELT = "#9E2F22"        # коврик для броска
BONE = "#EADCC0"
BONE_SHADE = "#C9B48D"
BONE_LINE = "#5A4630"
GREEN = "#3E8E5A"

RIDER_COLORS = [RED, "#2F8F5B", "#6A4AA8", "#D98324"]

TITLE_FONT = "Bahnschrift SemiBold Condensed"
UI_FONT = "Bahnschrift"
BODY_FONT = "Segoe UI Variable Text"

QSS = f"""
* {{ font-family: "{UI_FONT}", "Segoe UI"; color: {INK}; }}
QWidget#root {{ background: {PAPER}; }}
QLabel {{ background: transparent; }}
QLabel#h1 {{ font-family: "{TITLE_FONT}"; font-size: 40px; color: {INK}; }}
QLabel#h2 {{ font-size: 15px; color: {INK_SOFT}; }}
QLabel#over {{ font-family: "{TITLE_FONT}"; font-size: 14px; letter-spacing: 3px; color: {RED}; }}
QLabel#error {{ color: {RED}; font-size: 14px; font-weight: 600; }}
QLabel#hint {{ color: {INK_SOFT}; font-size: 13px; }}
QLabel#status {{ font-family: "{TITLE_FONT}"; font-size: 21px; color: {INK}; }}

QPushButton {{
    background: {PAPER_LIGHT}; border: 2px solid {INK}; border-bottom-width: 5px;
    border-radius: 4px; padding: 9px 22px 8px 22px; font-size: 16px; font-weight: 600;
    text-align: left;
}}
QPushButton:hover {{ background: #FFFFFF; }}
QPushButton:pressed {{ border-bottom-width: 2px; padding-top: 12px; }}
QPushButton:disabled {{ background: {PAPER}; border-color: #A79D90; color: #A79D90; }}
QPushButton#primary {{ background: {RED}; color: {PAPER_LIGHT}; font-size: 19px; }}
QPushButton#primary:hover {{ background: #D2412F; }}
QPushButton#primary:disabled {{ background: #D8B9A9; color: {PAPER_LIGHT}; border-color: #A79D90; }}
QPushButton#flat {{ background: transparent; border: none; color: {INK_SOFT}; font-size: 15px;
                    padding: 6px 4px; }}
QPushButton#flat:hover {{ color: {INK}; text-decoration: underline; }}
QPushButton#flat:pressed {{ padding-top: 6px; }}
QPushButton#seg {{ text-align: center; padding: 8px 18px; }}
QPushButton#seg:checked {{ background: {BLUE}; color: {PAPER_LIGHT}; }}

QFrame#card {{ background: {PAPER_LIGHT}; border: 2px solid {INK}; border-radius: 6px; }}
QFrame#card QLabel {{ border: none; }}

QLineEdit {{
    background: #FFFFFF; color: {INK}; border: 2px solid {INK};
    border-radius: 4px; padding: 9px 12px; font-size: 18px;
    selection-background-color: {OCHRE}; selection-color: {INK};
}}
QLineEdit:focus {{ border-color: {BLUE}; }}
QLineEdit[invalid="true"] {{ border-color: {RED}; background: #FBE6E1; }}

QTableWidget {{
    background: {PAPER_LIGHT}; alternate-background-color: #EFE7D6;
    border: 2px solid {INK}; border-radius: 4px; gridline-color: transparent;
    font-size: 15px; selection-background-color: {OCHRE}; selection-color: {INK};
}}
QTableWidget::item {{ padding: 6px; }}
QTableWidget::item:selected {{ background: {OCHRE}; color: {INK}; }}
QHeaderView::section {{
    background: {INK}; color: {PAPER_LIGHT}; font-weight: bold; font-size: 14px;
    border: none; padding: 8px;
}}
QTextBrowser {{
    background: {PAPER_LIGHT}; border: 2px solid {INK}; border-radius: 4px;
    padding: 18px 22px; font-family: "{BODY_FONT}", "Segoe UI"; font-size: 16px;
}}
QScrollBar:vertical {{ background: transparent; width: 10px; }}
QScrollBar::handle:vertical {{ background: {INK}; border-radius: 3px; min-height: 30px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}
QMenu {{ background: {PAPER_LIGHT}; border: 2px solid {INK}; }}
QMenu::item {{ padding: 6px 20px; }}
QMenu::item:selected {{ background: {OCHRE}; color: {INK}; }}
QMessageBox, QInputDialog, QDialog {{ background: {PAPER}; }}
QMessageBox QLabel {{ font-size: 15px; }}
QMessageBox QPushButton, QInputDialog QPushButton {{ text-align: center; min-width: 80px; }}
QSlider::groove:horizontal {{ height: 6px; background: #D6CBB6; border-radius: 3px; }}
QSlider::sub-page:horizontal {{ background: {RED}; border-radius: 3px; }}
QSlider {{ min-height: 26px; }}
QSlider::handle:horizontal {{ background: {PAPER_LIGHT}; border: 2px solid {INK}; width: 16px; height: 16px;
                              margin: -7px 0; border-radius: 10px; }}
QToolTip {{ background: {INK}; color: {PAPER_LIGHT}; border: none; padding: 4px 8px; }}
"""
