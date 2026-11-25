from __future__ import annotations

import math
import os

from PySide6.QtCore import QPointF, QRectF, QSettings, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from . import theme as T

SETTINGS = ("ShagaiNaadan", "game")


def tour_done() -> bool:
    if os.environ.get("SHAGAI_NO_TOUR"):
        return True
    try:
        return QSettings(*SETTINGS).value("tour_done", False, type=bool)
    except Exception:
        return False


def mark_tour_done() -> None:
    try:
        QSettings(*SETTINGS).setValue("tour_done", True)
    except Exception:
        pass


class Tour(QWidget):
    finished = Signal()

    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.hide()
        self.steps: list[tuple[QWidget, str, str]] = []
        self.k = 0
        self._t = 0.0
        self._timer = QTimer(self)
        self._timer.setInterval(33)
        self._timer.timeout.connect(self._pulse)

        self.bubble = QFrame(self)
        self.bubble.setObjectName("card")
        self.bubble.setFixedWidth(380)
        b = QVBoxLayout(self.bubble)
        b.setContentsMargins(22, 18, 22, 16)
        b.setSpacing(8)
        self.step_l = QLabel()
        self.step_l.setObjectName("over")
        b.addWidget(self.step_l)
        self.title = QLabel()
        self.title.setObjectName("status")
        self.title.setStyleSheet("font-size: 26px;")
        b.addWidget(self.title)
        self.text = QLabel()
        self.text.setWordWrap(True)
        self.text.setStyleSheet(f"font-family: '{T.BODY_FONT}'; font-size: 16px;")
        b.addWidget(self.text)
        row = QHBoxLayout()
        self.skip = QPushButton("Пропустить")
        self.skip.setObjectName("flat")
        self.skip.setCursor(Qt.PointingHandCursor)
        self.skip.clicked.connect(self.close_tour)
        self.next = QPushButton("Дальше  →")
        self.next.setObjectName("primary")
        self.next.setCursor(Qt.PointingHandCursor)
        self.next.clicked.connect(self._advance)
        row.addWidget(self.skip)
        row.addStretch()
        row.addWidget(self.next)
        b.addLayout(row)

    def start(self, steps):
        self.steps = steps
        self.k = 0
        self.setGeometry(self.parentWidget().rect())
        self.show()
        self.raise_()
        self._timer.start()
        self._show_step()

    def _target(self) -> QRectF:
        w = self.steps[self.k][0]
        tl = w.mapTo(self.parentWidget(), w.rect().topLeft())
        return QRectF(tl.x(), tl.y(), w.width(), w.height()).adjusted(-10, -10, 10, 10)

    def _show_step(self):
        _, title, text = self.steps[self.k]
        last = self.k == len(self.steps) - 1
        self.step_l.setText(f"ПОДСКАЗКА {self.k + 1} ИЗ {len(self.steps)}")
        self.title.setText(title)
        self.text.setText(text)
        self.next.setText("Понятно, поехали!" if last else "Дальше  →")
        self.skip.setVisible(not last)
        self.bubble.adjustSize()
        self._place()
        self.next.setFocus()
        self.update()

    def _place(self):
        r = self._target()
        bw, bh = self.bubble.width(), self.bubble.height()
        W, H = self.width(), self.height()
        if r.top() - bh - 24 > 0:
            x, y = r.center().x() - bw / 2, r.top() - bh - 24
        elif r.bottom() + bh + 24 < H:
            x, y = r.center().x() - bw / 2, r.bottom() + 24
        else:
            x, y = r.left() - bw - 24, r.center().y() - bh / 2
            if x < 10:
                x = r.right() + 24
        self.bubble.move(int(min(max(x, 12), W - bw - 12)), int(min(max(y, 12), H - bh - 12)))

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if self.steps and self.isVisible():
            self._place()

    def _pulse(self):
        self._t += 0.033
        self.update()

    def _advance(self):
        if self.k < len(self.steps) - 1:
            self.k += 1
            self._show_step()
        else:
            self.close_tour()

    def close_tour(self):
        self._timer.stop()
        self.hide()
        mark_tour_done()
        self.finished.emit()

    def keyPressEvent(self, e):
        if e.key() in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Space):
            self._advance()
        elif e.key() == Qt.Key_Escape:
            self.close_tour()

    def mousePressEvent(self, e):
        self._advance()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        hole = self._target()
        shade = QPainterPath()
        shade.addRect(QRectF(self.rect()))
        cut = QPainterPath()
        cut.addRoundedRect(hole, 10, 10)
        p.fillPath(shade.subtracted(cut), QColor(30, 27, 24, 175))
        grow = 3 + 3 * math.sin(self._t * 5)
        p.setPen(QPen(QColor(T.OCHRE), 4))
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(hole.adjusted(-grow, -grow, grow, grow), 12, 12)
        b = self.bubble.geometry()
        bc = QPointF(b.center().x(), b.bottom() if b.bottom() < hole.top() else b.top())
        if b.right() < hole.left():
            bc = QPointF(b.right(), b.center().y())
        elif b.left() > hole.right():
            bc = QPointF(b.left(), b.center().y())
        tgt = QPointF(min(max(bc.x(), hole.left() + 20), hole.right() - 20),
                      hole.top() if bc.y() < hole.top() else hole.bottom() if bc.y() > hole.bottom()
                      else hole.center().y())
        if b.right() < hole.left():
            tgt = QPointF(hole.left(), min(max(bc.y(), hole.top() + 10), hole.bottom() - 10))
        elif b.left() > hole.right():
            tgt = QPointF(hole.right(), min(max(bc.y(), hole.top() + 10), hole.bottom() - 10))
        p.setPen(QPen(QColor(T.OCHRE), 3, Qt.DashLine, Qt.RoundCap))
        p.drawLine(bc, tgt)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(T.OCHRE))
        p.drawEllipse(tgt, 6, 6)
