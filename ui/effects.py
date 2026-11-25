from __future__ import annotations

import math
import random

from PySide6.QtCore import QEasingCurve, QPointF, QRectF, Qt, QTimer, QVariantAnimation
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen, QPolygonF
from PySide6.QtWidgets import QWidget

from core.achievements import Achievement
from core.shagai import Side
from . import theme as T
from .art import draw_horse_token, draw_shagai, ui_font

HADAK_COLORS = ["#5B9BD5", "#7FB3E0", "#F8F3E8", "#4A86C5", "#F8F3E8"]


class _Hadak:
    __slots__ = ("x", "y", "vy", "a", "spin", "length", "width", "phase", "sway", "color")


class HadakRain(QWidget):

    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WA_NoSystemBackground)
        self.hide()
        self._rnd = random.Random()
        self.items: list[_Hadak] = []
        self._left = 0
        self._t = 0.0
        self._timer = QTimer(self)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._tick)

    def start(self, count: int = 46) -> None:
        self.setGeometry(self.parentWidget().rect())
        self.items.clear()
        self._left = count
        self._t = 0.0
        self.show()
        self.raise_()
        self._timer.start()

    def stop(self) -> None:
        self._timer.stop()
        self.items.clear()
        self.hide()

    def _spawn(self) -> None:
        h = _Hadak()
        h.x = self._rnd.uniform(0, self.width())
        h.y = -self._rnd.uniform(40, 140)
        h.vy = self._rnd.uniform(110, 210)
        h.a = self._rnd.uniform(-40, 40)
        h.spin = self._rnd.uniform(-70, 70)
        h.length = self._rnd.uniform(70, 120)
        h.width = self._rnd.uniform(16, 24)
        h.phase = self._rnd.uniform(0, 6.3)
        h.sway = self._rnd.uniform(30, 70)
        h.color = self._rnd.choice(HADAK_COLORS)
        self.items.append(h)

    def _tick(self) -> None:
        dt = 0.016
        self._t += dt
        burst = 6 if self._t < 0.5 else 1
        for _ in range(burst):
            if self._left > 0 and self._rnd.random() < 0.5:
                self._spawn()
                self._left -= 1
        for h in self.items:
            h.y += h.vy * dt
            h.phase += dt * 2.2
            h.a += h.spin * dt
        self.items = [h for h in self.items if h.y < self.height() + 160]
        if not self.items and self._left <= 0:
            self.stop()
            return
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        for h in self.items:
            p.save()
            p.translate(h.x + math.sin(h.phase) * h.sway, h.y)
            p.rotate(h.a)
            n = 14
            left, right = [], []
            for i in range(n + 1):
                s = i / n
                y = (s - 0.5) * h.length
                off = math.sin(h.phase * 2.3 + s * 5.5) * h.width * 0.55
                left.append(QPointF(off - h.width / 2, y))
                right.append(QPointF(off + h.width / 2, y))
            poly = QPolygonF(left + right[::-1])
            p.setPen(QPen(QColor(T.INK), 1.6))
            p.setBrush(QColor(h.color))
            p.drawPolygon(poly)
            p.setPen(QPen(QColor(T.INK), 1))
            for a, b, sign in ((left[0], right[0], -1), (left[-1], right[-1], 1)):
                for k in range(5):
                    t = (k + 0.5) / 5
                    x = a.x() + (b.x() - a.x()) * t
                    p.drawLine(QPointF(x, a.y()), QPointF(x, a.y() + sign * 9))
            p.restore()


def _icon(p: QPainter, c: QPointF, r: float, icon: str) -> None:
    ink = QPen(QColor(T.INK), max(2.0, r / 9), Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
    if icon == "horse":
        draw_horse_token(p, QPointF(c.x(), c.y() + r * 0.1), r * 0.55, T.RED, "")
    elif icon == "bone":
        draw_shagai(p, c, r * 1.1, Side.MORIN, -15)
    elif icon == "crown":
        path = QPainterPath(QPointF(c.x() - r * 0.6, c.y() + r * 0.35))
        for dx, dy in ((-0.6, -0.4), (-0.3, 0.0), (0, -0.55), (0.3, 0.0), (0.6, -0.4), (0.6, 0.35)):
            path.lineTo(c.x() + r * dx, c.y() + r * dy)
        path.closeSubpath()
        p.setPen(ink)
        p.setBrush(QColor(T.RED))
        p.drawPath(path)
    elif icon == "wind":
        p.setPen(ink)
        p.setBrush(Qt.NoBrush)
        for k, w in enumerate((0.9, 0.65, 0.8)):
            y = c.y() + (k - 1) * r * 0.32
            path = QPainterPath(QPointF(c.x() - r * 0.6, y))
            path.cubicTo(c.x(), y - r * 0.12, c.x() + r * 0.2 * w, y + r * 0.12, c.x() + r * 0.6 * w, y)
            p.drawPath(path)
    elif icon == "book":
        p.setPen(ink)
        p.setBrush(QColor(T.PAPER_LIGHT))
        for sign in (-1, 1):
            path = QPainterPath(QPointF(c.x(), c.y() - r * 0.3))
            path.lineTo(c.x() + sign * r * 0.6, c.y() - r * 0.42)
            path.lineTo(c.x() + sign * r * 0.6, c.y() + r * 0.38)
            path.lineTo(c.x(), c.y() + r * 0.5)
            path.closeSubpath()
            p.drawPath(path)
    elif icon == "people":
        p.setPen(ink)
        for dx, col in ((-0.28, T.BLUE), (0.28, T.RED)):
            p.setBrush(QColor(col))
            p.drawEllipse(QPointF(c.x() + r * dx, c.y() - r * 0.25), r * 0.17, r * 0.17)
            p.drawRoundedRect(QRectF(c.x() + r * (dx - 0.22), c.y(), r * 0.44, r * 0.45), 4, 4)
    elif icon == "target":
        p.setPen(ink)
        for k, col in enumerate((T.PAPER_LIGHT, T.RED, T.PAPER_LIGHT)):
            p.setBrush(QColor(col))
            rr = r * (0.6 - k * 0.2)
            p.drawEllipse(c, rr, rr)
    elif icon == "clean":
        p.setPen(QPen(QColor(T.GREEN), max(3.0, r / 5), Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        path = QPainterPath(QPointF(c.x() - r * 0.4, c.y()))
        path.lineTo(c.x() - r * 0.1, c.y() + r * 0.3)
        path.lineTo(c.x() + r * 0.45, c.y() - r * 0.35)
        p.drawPath(path)
    else:
        p.setPen(QColor(T.INK))
        p.setFont(ui_font(r * 0.9, title=True))
        p.drawText(QRectF(c.x() - r, c.y() - r, 2 * r, 2 * r), Qt.AlignCenter, "10")


def draw_badge(p: QPainter, c: QPointF, r: float, icon: str, unlocked: bool = True) -> None:
    p.save()
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(30, 27, 24, 70))
    p.drawEllipse(QPointF(c.x() + r * 0.08, c.y() + r * 0.1), r, r)
    p.setPen(QPen(QColor(T.INK), max(1.5, r / 16)))
    p.setBrush(QColor(T.OCHRE if unlocked else "#D9CFBE"))
    p.drawEllipse(c, r, r)
    p.setBrush(Qt.NoBrush)
    p.drawEllipse(c, r * 0.8, r * 0.8)
    for k in range(16):
        a = k * math.pi / 8
        p.drawLine(QPointF(c.x() + math.cos(a) * r * 0.84, c.y() + math.sin(a) * r * 0.84),
                   QPointF(c.x() + math.cos(a) * r * 0.94, c.y() + math.sin(a) * r * 0.94))
    _icon(p, c, r * 0.72, icon)
    if not unlocked:
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(239, 230, 211, 175))
        p.drawEllipse(c, r * 0.8, r * 0.8)
        p.setPen(QColor(T.INK_SOFT))
        p.setFont(ui_font(r * 0.8, title=True))
        p.drawText(QRectF(c.x() - r, c.y() - r, 2 * r, 2 * r), Qt.AlignCenter, "?")
    p.restore()


class AchievementToast(QWidget):
    W, H = 360, 96

    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setFixedSize(self.W, self.H)
        self.hide()
        self.queue: list[tuple[Achievement, str]] = []
        self.current: tuple[Achievement, str] | None = None
        self._anim = QVariantAnimation(self)
        self._anim.valueChanged.connect(self._place)
        self._anim.finished.connect(self._step)
        self._phase = ""
        self.on_show = None

    def push(self, ach: Achievement, who: str) -> None:
        self.queue.append((ach, who))
        if self.current is None:
            self._next()

    def _next(self) -> None:
        if not self.queue:
            self.current = None
            self.hide()
            return
        self.current = self.queue.pop(0)
        if self.on_show:
            self.on_show()
        self.show()
        self.raise_()
        self._run("in", 0.0, 1.0, 420, QEasingCurve.OutBack)

    def _run(self, phase, a, b, ms, curve):
        self._phase = phase
        self._anim.stop()
        self._anim.setStartValue(a)
        self._anim.setEndValue(b)
        self._anim.setDuration(ms)
        self._anim.setEasingCurve(curve)
        self._anim.start()

    def _step(self):
        if self._phase == "in":
            self._phase = "stay"
            QTimer.singleShot(2600, lambda: self._run("out", 1.0, 0.0, 320, QEasingCurve.InCubic))
        elif self._phase == "out":
            self._next()

    def _place(self, k):
        pw = self.parentWidget().width()
        self.move(int(pw - 24 - self.W * float(k)), 60)

    def paintEvent(self, _):
        if not self.current:
            return
        ach, who = self.current
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(0, 0, self.W - 6, self.H - 6)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(T.INK))
        p.drawRoundedRect(r.translated(5, 5), 6, 6)
        p.setPen(QPen(QColor(T.INK), 2))
        p.setBrush(QColor(T.PAPER_LIGHT))
        p.drawRoundedRect(r, 6, 6)
        draw_badge(p, QPointF(46, r.center().y()), 30, ach.icon)
        p.setPen(QColor(T.RED))
        p.setFont(ui_font(12, title=True))
        p.drawText(QRectF(90, 12, r.width() - 100, 16), Qt.AlignLeft,
                   f"ДОСТИЖЕНИЕ  ·  {who.upper()}")
        p.setPen(QColor(T.INK))
        p.setFont(ui_font(22, title=True))
        p.drawText(QRectF(90, 28, r.width() - 100, 28), Qt.AlignLeft, ach.title)
        p.setPen(QColor(T.INK_SOFT))
        p.setFont(ui_font(13))
        p.drawText(QRectF(90, 58, r.width() - 100, 30), Qt.AlignLeft | Qt.TextWordWrap, ach.text)
