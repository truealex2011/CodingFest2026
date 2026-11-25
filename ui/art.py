"""Вся графика рисуется кодом (QPainter): орнамент, шагай, кони, ипподром.
Никаких внешних картинок — приложение не сломается из-за потерянного файла.
Стиль — плоская печать: заливка, чёткая обводка, жёсткая тень без размытия."""
from __future__ import annotations

import random

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import QWidget

from core.shagai import Side
from . import theme as T


def ui_font(size: float, bold: bool = False, title: bool = False) -> QFont:
    f = QFont(T.TITLE_FONT if title else T.UI_FONT)
    f.setPixelSize(max(8, int(size)))
    f.setBold(bold)
    return f


# ---------- фактура войлока ----------
_grain: QPixmap | None = None


def grain_tile() -> QPixmap:
    """Тайл с мелкими «ворсинками» — фон перестаёт быть стерильно-гладким."""
    global _grain
    if _grain is None:
        rnd = random.Random(7)
        _grain = QPixmap(160, 160)
        _grain.fill(Qt.transparent)
        p = QPainter(_grain)
        for _ in range(900):
            dark = rnd.random() < 0.6
            c = QColor(60, 45, 30, rnd.randint(10, 26)) if dark else QColor(255, 255, 255, rnd.randint(20, 45))
            p.fillRect(QRectF(rnd.uniform(0, 160), rnd.uniform(0, 160), rnd.choice((1, 1, 2)), 1), c)
        p.end()
    return _grain


# ---------- орнамент «алхан хээ» (молоточковый узор) ----------
def draw_ornament_band(p: QPainter, rect: QRectF, color: str = T.PAPER_LIGHT, step: float | None = None,
                       lines: bool = True) -> None:
    """Повторяющийся меандр — классическая бурятско-монгольская кайма."""
    h = rect.height()
    s = step or h
    pen = QPen(QColor(color), max(1.5, h / 8), Qt.SolidLine, Qt.SquareCap, Qt.MiterJoin)
    p.save()
    p.setClipRect(rect)
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)
    m = h * 0.2
    top, bot = rect.top() + m, rect.bottom() - m
    x = rect.left() - s
    while x < rect.right() + s:
        u = s / 6
        path = QPainterPath(QPointF(x, bot))
        for dx, y in ((0, top), (4 * u, top), (4 * u, bot - 2 * u), (2 * u, bot - 2 * u),
                      (2 * u, bot - 3.4 * u)):
            path.lineTo(x + dx, y)
        path.moveTo(x + 4 * u, bot)
        path.lineTo(x + 6 * u, bot)
        p.drawPath(path)
        x += s
    if lines:
        p.drawLine(QPointF(rect.left(), rect.top() + 1), QPointF(rect.right(), rect.top() + 1))
        p.drawLine(QPointF(rect.left(), rect.bottom() - 1), QPointF(rect.right(), rect.bottom() - 1))
    p.restore()


def paint_background(p: QPainter, rect: QRectF, band: bool = True) -> None:
    p.fillRect(rect, QColor(T.PAPER))
    p.drawTiledPixmap(rect, grain_tile())
    if band:
        strip = QRectF(rect.left(), rect.top(), rect.width(), 22)
        p.fillRect(strip, QColor(T.BLUE))
        draw_ornament_band(p, strip.adjusted(0, 2, 0, -2), T.PAPER_LIGHT, lines=False)
        p.fillRect(QRectF(rect.left(), strip.bottom(), rect.width(), 4), QColor(T.RED))


class OrnamentBackground(QWidget):
    """Базовый экран: войлок с синей каймой сверху."""
    band = True

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_StyledBackground, False)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        paint_background(p, QRectF(self.rect()), self.band)


# ---------- шагай ----------
def _bone_path(w: float, h: float) -> QPainterPath:
    """Силуэт бараньей лодыжки: тело с двумя «перетяжками» по бокам."""
    path = QPainterPath()
    path.moveTo(-w * 0.42, -h * 0.5)
    path.cubicTo(-w * 0.1, -h * 0.62, w * 0.1, -h * 0.38, w * 0.42, -h * 0.5)
    path.cubicTo(w * 0.62, -h * 0.42, w * 0.38, -h * 0.05, w * 0.5, h * 0.05)
    path.cubicTo(w * 0.6, h * 0.4, w * 0.5, h * 0.55, w * 0.35, h * 0.5)
    path.cubicTo(w * 0.1, h * 0.62, -w * 0.1, h * 0.38, -w * 0.35, h * 0.5)
    path.cubicTo(-w * 0.55, h * 0.55, -w * 0.6, h * 0.35, -w * 0.5, h * 0.05)
    path.cubicTo(-w * 0.4, -h * 0.1, -w * 0.62, -h * 0.4, -w * 0.42, -h * 0.5)
    return path


def draw_shagai(p: QPainter, center: QPointF, size: float, side: Side,
                angle: float = 0.0, glow: bool = False, shadow: QColor | None = None,
                lift: float = 0.0, scale: float = 1.0) -> None:
    """glow — выделить кость плоской охристой «наклейкой» под ней (для «коня»).
    lift — высота кости над войлоком в полёте: тень остаётся на земле и бледнеет."""
    if side in (Side.HONIN, Side.YAMAAN):
        w, h = size, size * 0.78
    elif side is Side.MORIN:
        w, h = size * 0.62, size * 0.9
    else:  # TEMEEN
        w, h = size * 0.55, size * 0.62
    path = _bone_path(w, h)
    lw = max(1.3, size / 30)

    if glow:
        p.save()
        p.translate(center)
        p.setPen(QPen(QColor(T.INK), max(1.5, size / 34)))
        p.setBrush(QColor(T.OCHRE))
        r = size * 0.56 * scale
        p.drawEllipse(QPointF(0, 0), r, r)
        p.restore()

    # жёсткая тень — та же форма со сдвигом, без размытия
    sc = QColor(shadow if shadow is not None else QColor(30, 27, 24, 55))
    if lift > 0:
        sc.setAlpha(int(sc.alpha() * max(0.35, 1 - lift / 220)))
    p.save()
    p.translate(center.x() + size * 0.05 + lift * 0.12, center.y() + size * 0.07 + lift)
    p.rotate(angle)
    k = 1 / (1 + lift / 300)
    p.scale(k, k)
    p.setPen(Qt.NoPen)
    p.setBrush(sc)
    p.drawPath(path)
    p.restore()

    p.save()
    p.translate(center)
    p.rotate(angle)
    s = scale * (1 + lift / 500)
    if s != 1:
        p.scale(s, s)

    # тело: тёмный «полутон» снизу-справа, светлая кость поверх со сдвигом
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(T.BONE_SHADE))
    p.drawPath(path)
    p.save()
    p.setClipPath(path)
    p.setBrush(QColor(T.BONE))
    p.drawPath(path.translated(-w * 0.05, -h * 0.07))
    p.restore()
    p.setBrush(Qt.NoBrush)
    p.setPen(QPen(QColor(T.BONE_LINE), lw))
    p.drawPath(path)

    detail = QPen(QColor(T.BONE_LINE), lw, Qt.SolidLine, Qt.RoundCap)
    p.setPen(detail)
    if side is Side.HONIN:      # выпуклая — гладкий бугор
        p.drawArc(QRectF(-w * 0.3, -h * 0.25, w * 0.6, h * 0.5), 200 * 16, 140 * 16)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(255, 255, 255, 170))
        p.drawEllipse(QPointF(-w * 0.14, -h * 0.14), w * 0.13, h * 0.08)
    elif side is Side.YAMAAN:   # вогнутая — углубление
        p.setBrush(QColor(T.BONE_SHADE))
        p.drawEllipse(QPointF(0, 0), w * 0.22, h * 0.2)
    elif side is Side.MORIN:    # боком — S-образный гребень
        sp = QPainterPath(QPointF(0, -h * 0.38))
        sp.cubicTo(w * 0.3, -h * 0.15, -w * 0.3, h * 0.15, 0, h * 0.38)
        p.drawPath(sp)
    else:                       # на торце — маленькая площадка
        p.setBrush(QColor(T.BONE_SHADE))
        p.drawRect(QRectF(-w * 0.2, -h * 0.18, w * 0.4, h * 0.36))
    p.restore()


# ---------- конь-фишка ----------
def draw_horse_token(p: QPainter, center: QPointF, r: float, color: str, label: str,
                     bob: float = 0.0, highlight: bool = False) -> None:
    p.save()
    p.translate(center.x(), center.y() + bob)
    lw = max(1.5, r / 10)
    if highlight:
        p.setPen(QPen(QColor(T.INK), lw))
        p.setBrush(QColor(T.OCHRE))
        p.drawEllipse(QPointF(0, -r * 0.1), r * 1.25, r * 1.25)
    # голова коня — стилизованный силуэт
    head = QPainterPath()
    head.moveTo(-r * 0.55, r * 0.8)
    head.cubicTo(-r * 0.7, 0, -r * 0.4, -r * 0.75, r * 0.05, -r * 0.9)
    head.lineTo(r * 0.2, -r * 1.15)
    head.lineTo(r * 0.3, -r * 0.82)
    head.cubicTo(r * 0.7, -r * 0.6, r * 0.95, -r * 0.1, r * 0.85, r * 0.12)
    head.cubicTo(r * 0.7, r * 0.3, r * 0.4, r * 0.15, r * 0.25, r * 0.05)
    head.cubicTo(r * 0.3, r * 0.45, r * 0.45, r * 0.65, r * 0.5, r * 0.8)
    head.closeSubpath()
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(30, 27, 24, 70))
    p.drawPath(head.translated(r * 0.12, r * 0.12))
    p.setBrush(QColor(color))
    p.setPen(QPen(QColor(T.INK), lw, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    p.drawPath(head)
    # грива
    p.setPen(QPen(QColor(T.INK), lw, Qt.SolidLine, Qt.RoundCap))
    for k in range(4):
        y = -r * 0.7 + k * r * 0.3
        p.drawLine(QPointF(-r * 0.25 - k * r * 0.06, y), QPointF(-r * 0.5 - k * r * 0.06, y + r * 0.12))
    p.setBrush(QColor(T.INK))
    p.setPen(Qt.NoPen)
    p.drawEllipse(QPointF(r * 0.35, -r * 0.45), r * 0.09, r * 0.09)
    # подпись
    p.setFont(ui_font(max(11, r * 0.55), bold=True))
    p.setPen(QColor(T.INK))
    p.drawText(QRectF(-r * 3, r * 0.95, r * 6, r * 0.9), Qt.AlignCenter, label)
    p.restore()


def app_icon() -> QIcon:
    pm = QPixmap(128, 128)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.setBrush(QColor(T.BLUE))
    p.setPen(QPen(QColor(T.INK), 5))
    p.drawRoundedRect(QRectF(4, 4, 120, 120), 18, 18)
    draw_shagai(p, QPointF(62, 60), 82, Side.HONIN, -15, shadow=QColor(0, 0, 0, 90))
    p.end()
    return QIcon(pm)
