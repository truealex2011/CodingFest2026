from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (QDialog, QGridLayout, QHBoxLayout, QLabel, QPushButton, QVBoxLayout,
                               QWidget)

from core import achievements as A
from . import theme as T
from .art import ui_font
from .effects import draw_badge


class ScoreChart(QWidget):

    def __init__(self, scores: list[int]):
        super().__init__()
        self.scores = scores[-20:]
        self.setMinimumHeight(170)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect()).adjusted(36, 14, -8, -24)
        p.setPen(QPen(QColor(T.INK), 2))
        p.drawLine(r.bottomLeft(), r.bottomRight())
        if not self.scores:
            p.setPen(QColor(T.INK_SOFT))
            p.setFont(ui_font(14))
            p.drawText(r, Qt.AlignCenter, "Заездов ещё не было")
            return
        top = max(self.scores) or 1
        n = len(self.scores)
        w = r.width() / n
        best = self.scores.index(max(self.scores))
        p.setFont(ui_font(11))
        for i, s in enumerate(self.scores):
            h = r.height() * s / top
            bar = QRectF(r.left() + i * w + w * 0.18, r.bottom() - h, w * 0.64, h)
            p.setPen(QPen(QColor(T.INK), 1.5))
            p.setBrush(QColor(T.RED if i == best else T.BLUE))
            p.drawRect(bar)
            p.setPen(QColor(T.INK_SOFT))
            p.drawText(QRectF(bar.left() - 10, r.bottom() + 4, bar.width() + 20, 16), Qt.AlignCenter, str(i + 1))
        avg = sum(self.scores) / n
        y = r.bottom() - r.height() * avg / top
        p.setPen(QPen(QColor(T.OCHRE), 2, Qt.DashLine))
        p.drawLine(QPointF(r.left(), y), QPointF(r.right(), y))
        p.setPen(QColor(T.INK_SOFT))
        p.drawText(QRectF(0, y - 8, 34, 16), Qt.AlignRight | Qt.AlignVCenter, f"{avg:.0f}")
        p.drawText(QRectF(0, r.top() - 8, 34, 16), Qt.AlignRight | Qt.AlignVCenter, str(top))


class BadgeTile(QWidget):
    def __init__(self, ach: A.Achievement, date: str | None):
        super().__init__()
        self.ach, self.date = ach, date
        self.setFixedSize(150, 150)
        self.setToolTip(f"{ach.title}\n{ach.text}" + (f"\nОткрыто: {date}" if date else "\nЕщё не открыто"))

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        draw_badge(p, QPointF(75, 46), 38, self.ach.icon, self.date is not None)
        p.setPen(QColor(T.INK if self.date else T.INK_SOFT))
        p.setFont(ui_font(15, title=True))
        p.drawText(QRectF(0, 92, 150, 22), Qt.AlignCenter, self.ach.title)
        p.setPen(QColor(T.INK_SOFT))
        p.setFont(ui_font(11))
        p.drawText(QRectF(4, 114, 142, 34), Qt.AlignHCenter | Qt.AlignTop | Qt.TextWordWrap, self.ach.text)


class PlayerCard(QDialog):
    def __init__(self, parent, db, name: str):
        super().__init__(parent)
        self.setWindowTitle(f"Карточка игрока — {name}")
        self.setMinimumWidth(820)
        recs = db.player_records(name)
        got = db.achievements(name)
        harb = db.harbaha_best(name)
        o = QVBoxLayout(self)
        o.setContentsMargins(30, 24, 30, 22)
        o.setSpacing(10)
        over = QLabel("КАРТОЧКА НАЕЗДНИКА")
        over.setObjectName("over")
        o.addWidget(over)
        h = QLabel(name)
        h.setObjectName("h1")
        h.setStyleSheet("font-size: 48px;")
        o.addWidget(h)

        wins = sum(1 for r in recs if r.place == 1)
        stats = [("Заездов", len(recs)), ("Побед", wins),
                 ("Лучший результат", max((r.score for r in recs), default=0)),
                 ("Меньше всего бросков", min((r.throws for r in recs if r.place == 1), default="—")),
                 ("Рекорд в харбаха", harb or "—")]
        row = QHBoxLayout()
        row.setSpacing(12)
        for cap, val in stats:
            box = QVBoxLayout()
            v = QLabel(str(val))
            v.setStyleSheet(f"font-family: '{T.TITLE_FONT}'; font-size: 36px; color: {T.RED};")
            c = QLabel(cap)
            c.setObjectName("hint")
            box.addWidget(v)
            box.addWidget(c)
            row.addLayout(box)
            row.addStretch()
        o.addLayout(row)

        o.addWidget(self._over("ОЧКИ ПО ЗАЕЗДАМ"))
        o.addWidget(ScoreChart([r.score for r in recs]))
        o.addWidget(self._over(f"ДОСТИЖЕНИЯ  ·  {len(got)} ИЗ {len(A.ALL)}"))
        grid = QGridLayout()
        grid.setSpacing(4)
        for k, ach in enumerate(A.ALL):
            grid.addWidget(BadgeTile(ach, got.get(ach.code)), k // 5, k % 5)
        o.addLayout(grid)
        close = QPushButton("Закрыть")
        close.setObjectName("primary")
        close.setStyleSheet("text-align: center;")
        close.clicked.connect(self.accept)
        o.addWidget(close, 0, Qt.AlignRight)

    @staticmethod
    def _over(text):
        lb = QLabel(text)
        lb.setObjectName("over")
        return lb
