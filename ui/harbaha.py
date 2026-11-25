"""Мини-игра «Шагай харбаха» — щелчки по шагаям. Правила — в core/harbaha.py."""
from __future__ import annotations

import math
import random

from PySide6.QtCore import QElapsedTimer, QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QKeySequence, QPainter, QPen, QShortcut
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QLineEdit, QPushButton, QSizePolicy,
                               QVBoxLayout, QWidget)

from core import harbaha as HB
from core.shagai import Side
from core.validation import MAX_NAME_LEN, NameError_, validate_name
from . import theme as T
from .art import OrnamentBackground, draw_ornament_band, draw_shagai, ui_font


class _B:
    __slots__ = ("x", "y", "vx", "vy", "a", "spin", "side", "alive", "gone")

    def __init__(self, x, y, side, a):
        self.x, self.y, self.side, self.a = x, y, side, a
        self.vx = self.vy = self.spin = 0.0
        self.alive = True
        self.gone = 0.0  # 0..1 — анимация «забрали кость»


class HarbahaBoard(QWidget):
    """Войлок с рассыпанными шагаями. Кость тянут мышью, как рогатку, и отпускают."""
    changed = Signal()               # очки / попытки / комбо изменились
    knock = Signal()                 # кости стукнулись
    over = Signal(int, int, bool, int)  # очки, попаданий, чистый войлок, лучшая серия

    AIM, DRAG, ROLL, OVER = range(4)
    MAX_PULL = 170.0
    SPEED = 9.0        # пикс/с на пиксель натяжения

    def __init__(self):
        super().__init__()
        self.setMinimumSize(560, 420)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMouseTracking(True)
        self.setCursor(Qt.OpenHandCursor)
        self.rng = random.Random()
        self.bones: list[_B] = []
        self._timer = QTimer(self)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._tick)
        self._clock = QElapsedTimer()
        self.floats: list[list] = []  # [x, y, текст, цвет, t]
        self.new_game()

    # ---------- геометрия ----------
    def _mat(self) -> QRectF:
        return QRectF(self.rect()).adjusted(2, 2, -8, -8)

    def _area(self) -> QRectF:
        return self._mat().adjusted(26, 44, -26, -22)

    def size_(self) -> float:
        a = self._area()
        return max(40.0, min(a.width(), a.height()) / 6.2)

    def _rad(self) -> float:
        return self.size_() * 0.4

    # ---------- партия ----------
    def new_game(self):
        self.score = 0
        self.hits = 0
        self.lives = HB.LIVES
        self.combo = 0
        self.best_streak = 0
        self.collected: list[Side] = []
        self.state = self.AIM
        self.shooter = -1
        self.hover = -1
        self.result_text = ""
        self.floats.clear()
        self._sides = HB.scatter(self.rng)
        self._placed = False
        self._place()
        self._timer.start()
        self._clock.start()
        self.changed.emit()
        self.update()

    def _place(self):
        """Рассыпать кости, не допуская наложений."""
        if self.width() < 100:
            return
        a, rad = self._area(), self._rad()
        self.bones = []
        for side in self._sides:
            for _ in range(400):
                x = self.rng.uniform(a.left() + rad, a.right() - rad)
                y = self.rng.uniform(a.top() + rad, a.bottom() - rad)
                if all(math.hypot(x - b.x, y - b.y) > rad * 3.0 for b in self.bones):
                    break
            self.bones.append(_B(x, y, side, self.rng.uniform(-30, 30)))
        self._placed = True

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if not self._placed:
            self._place()
        else:
            a, rad = self._area(), self._rad()
            for b in self.bones:
                b.x = min(max(b.x, a.left() + rad), a.right() - rad)
                b.y = min(max(b.y, a.top() + rad), a.bottom() - rad)

    def _alive_sides(self):
        return [b.side for b in self.bones if b.alive]

    # ---------- мышь ----------
    def _bone_at(self, pt: QPointF) -> int:
        rad = self._rad() * 1.25
        for i in reversed(range(len(self.bones))):
            b = self.bones[i]
            if b.alive and math.hypot(pt.x() - b.x, pt.y() - b.y) <= rad:
                return i
        return -1

    def mousePressEvent(self, e):
        if self.state == self.OVER:
            self.new_game()
            return
        if self.state != self.AIM or e.button() != Qt.LeftButton:
            return
        i = self._bone_at(e.position())
        if i >= 0:
            self.shooter = i
            self.state = self.DRAG
            self._mouse = e.position()
            self.setCursor(Qt.ClosedHandCursor)
            self.update()

    def mouseMoveEvent(self, e):
        self._mouse = e.position()
        if self.state == self.AIM:
            h = self._bone_at(e.position())
            if h != self.hover:
                self.hover = h
                self.update()
        elif self.state == self.DRAG:
            self.update()

    def _pull(self) -> tuple[float, float, float]:
        b = self.bones[self.shooter]
        dx, dy = b.x - self._mouse.x(), b.y - self._mouse.y()
        d = math.hypot(dx, dy)
        if d > self.MAX_PULL:
            dx, dy, d = dx / d * self.MAX_PULL, dy / d * self.MAX_PULL, self.MAX_PULL
        return dx, dy, d

    def mouseReleaseEvent(self, e):
        if self.state != self.DRAG:
            return
        self.setCursor(Qt.OpenHandCursor)
        dx, dy, d = self._pull()
        if d < 12:  # просто щёлкнули — не стреляем
            self.state, self.shooter = self.AIM, -1
            self.update()
            return
        b = self.bones[self.shooter]
        k = self.SPEED * (self._area().width() / 900 + 0.35)
        b.vx, b.vy = dx * k, dy * k
        b.spin = self.rng.uniform(300, 700) * self.rng.choice((-1, 1))
        self.first = -1
        self.state = self.ROLL
        self._roll_t = 0.0

    # ---------- физика ----------
    def _tick(self):
        dt = min(0.04, self._clock.restart() / 1000)
        for f in self.floats:
            f[4] += dt
        self.floats = [f for f in self.floats if f[4] < 1.4]
        for b in self.bones:
            if not b.alive and b.gone < 1:
                b.gone = min(1.0, b.gone + dt / 0.45)
        if self.state == self.ROLL:
            self._roll_t += dt
            self._physics(dt)
        self.update()

    def _physics(self, dt: float):
        a, rad = self._area(), self._rad()
        live = [b for b in self.bones if b.alive]
        steps = 3  # несколько мелких шагов — кость не «проскочит» сквозь другую
        h = dt / steps
        for _ in range(steps):
            for b in live:
                b.x += b.vx * h
                b.y += b.vy * h
                b.a += b.spin * h
                f = max(0.0, 1 - 1.9 * h)
                b.vx *= f
                b.vy *= f
                b.spin *= max(0.0, 1 - 3 * h)
                sp = math.hypot(b.vx, b.vy)  # сухое трение войлока
                if sp > 0:
                    dec = min(sp, 120 * h)
                    b.vx -= b.vx / sp * dec
                    b.vy -= b.vy / sp * dec
                if b.x < a.left() + rad:
                    b.x, b.vx = a.left() + rad, abs(b.vx) * 0.6
                elif b.x > a.right() - rad:
                    b.x, b.vx = a.right() - rad, -abs(b.vx) * 0.6
                if b.y < a.top() + rad:
                    b.y, b.vy = a.top() + rad, abs(b.vy) * 0.6
                elif b.y > a.bottom() - rad:
                    b.y, b.vy = a.bottom() - rad, -abs(b.vy) * 0.6
            for i in range(len(self.bones)):
                p = self.bones[i]
                if not p.alive:
                    continue
                for j in range(i + 1, len(self.bones)):
                    q = self.bones[j]
                    if not q.alive:
                        continue
                    dx, dy = q.x - p.x, q.y - p.y
                    d = math.hypot(dx, dy)
                    md = rad * 2
                    if d >= md or d < 0.01:
                        continue
                    ux, uy = dx / d, dy / d
                    push = (md - d) / 2
                    p.x -= ux * push
                    p.y -= uy * push
                    q.x += ux * push
                    q.y += uy * push
                    rel = (p.vx - q.vx) * ux + (p.vy - q.vy) * uy
                    if rel > 0:
                        imp = rel * 0.92
                        p.vx -= imp * ux
                        p.vy -= imp * uy
                        q.vx += imp * ux
                        q.vy += imp * uy
                        q.spin += self.rng.uniform(-300, 300)
                        if rel > 40:
                            self.knock.emit()
                        if self.first < 0 and self.shooter in (i, j):
                            self.first = j if i == self.shooter else i
        if all(math.hypot(b.vx, b.vy) < 4 for b in live) or self._roll_t > 6:
            for b in live:
                b.vx = b.vy = b.spin = 0.0
            self._judge()

    def _judge(self):
        sh = self.bones[self.shooter]
        target = self.bones[self.first] if self.first >= 0 else None
        verdict = HB.judge(sh.side, target.side if target else None)
        if verdict == HB.HIT:
            self.combo += 1
            self.hits += 1
            self.best_streak = max(self.best_streak, self.combo)
            pts = HB.hit_points(self.combo)
            self.score += pts
            target.alive = False
            self.collected.append(target.side)
            txt = f"+{pts}" + (f"  ×{min(self.combo, HB.MAX_COMBO)}!" if self.combo > 1 else "")
            self.floats.append([target.x, target.y, txt, T.OCHRE, 0.0])
        else:
            self.combo = 0
            self.lives -= 1
            txt = "Мимо!" if verdict == HB.MISS else f"Задели «{target.side.buryat}» — чужая сторона!"
            self.floats.append([sh.x, sh.y, txt, T.PAPER_LIGHT, 0.0])
        self.state, self.shooter = self.AIM, -1
        cleared = not HB.has_pairs(self._alive_sides())
        if cleared or self.lives <= 0:
            bonus = HB.final_bonus(cleared, self.lives)
            self.score += bonus
            self.result_text = (f"ЧИСТЫЙ ВОЙЛОК!  +{bonus}" if cleared else "ПОПЫТКИ КОНЧИЛИСЬ")
            self.state = self.OVER
            self.over.emit(self.score, self.hits, cleared, self.best_streak)
        self.changed.emit()

    # ---------- рисование ----------
    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = self._mat()
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(T.INK))
        p.drawRoundedRect(r.translated(6, 6), 6, 6)
        p.setPen(QPen(QColor(T.INK), 2))
        p.setBrush(QColor(T.FELT))
        p.drawRoundedRect(r, 6, 6)
        draw_ornament_band(p, QRectF(r.left() + 2, r.top() + 10, r.width() - 4, 14), T.OCHRE, lines=False)
        size = self.size_()
        rad = self._rad()

        # подсказка «во что можно бить»: кости той же стороны в пунктирных кольцах
        focus = self.shooter if self.state == self.DRAG else self.hover if self.state == self.AIM else -1
        if focus >= 0:
            side = self.bones[focus].side
            pen = QPen(QColor(T.OCHRE), 3, Qt.DashLine)
            p.setBrush(Qt.NoBrush)
            for i, b in enumerate(self.bones):
                if b.alive and i != focus and b.side is side:
                    p.setPen(pen)
                    p.drawEllipse(QPointF(b.x, b.y), rad * 1.45, rad * 1.45)

        if self.state == self.DRAG:  # рогатка и линия прицела
            b = self.bones[self.shooter]
            dx, dy, d = self._pull()
            p.setPen(QPen(QColor(T.PAPER_LIGHT), 3, Qt.SolidLine, Qt.RoundCap))
            p.drawLine(QPointF(b.x, b.y), QPointF(b.x - dx, b.y - dy))
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(T.PAPER_LIGHT))
            n = int(4 + d / 14)
            for k in range(1, n + 1):
                t = k / n
                p.drawEllipse(QPointF(b.x + dx * t * 2.2, b.y + dy * t * 2.2), 3.2 * (1 - t * 0.6),
                              3.2 * (1 - t * 0.6))
            # шкала силы
            p.setPen(QPen(QColor(T.OCHRE), 5, Qt.SolidLine, Qt.FlatCap))
            p.setBrush(Qt.NoBrush)
            box = QRectF(b.x - rad * 1.8, b.y - rad * 1.8, rad * 3.6, rad * 3.6)
            p.drawArc(box, 90 * 16, int(-d / self.MAX_PULL * 360 * 16))

        for i, b in enumerate(self.bones):
            if not b.alive:
                if b.gone >= 1:
                    continue
                # забранная кость взлетает и тает
                g = b.gone
                p.setOpacity(1 - g)
                draw_shagai(p, QPointF(b.x, b.y - g * 60), size * (1 + g * 0.4), b.side, b.a,
                            shadow=QColor(0, 0, 0, 90), lift=g * 40)
                p.setOpacity(1)
                continue
            selected = i == self.shooter or (i == self.hover and self.state == self.AIM)
            if selected:
                p.setPen(QPen(QColor(T.PAPER_LIGHT), 3))
                p.setBrush(Qt.NoBrush)
                p.drawEllipse(QPointF(b.x, b.y), rad * 1.3, rad * 1.3)
            draw_shagai(p, QPointF(b.x, b.y), size, b.side, b.a, shadow=QColor(0, 0, 0, 90))

        for x, y, text, color, t in self.floats:  # всплывающие «+200 ×2!»
            p.setOpacity(max(0.0, 1 - t / 1.4))
            p.setFont(ui_font(24, title=True))
            rect = QRectF(x - 220, y - 60 - t * 50, 440, 30)
            p.setPen(QColor(T.INK))
            p.drawText(rect.translated(2, 2), Qt.AlignCenter, text)
            p.setPen(QColor(color))
            p.drawText(rect, Qt.AlignCenter, text)
            p.setOpacity(1)

        if self.state == self.OVER:
            p.fillRect(r, QColor(30, 27, 24, 110))
            p.setFont(ui_font(44, title=True))
            box = QRectF(r.center().x() - 300, r.center().y() - 70, 600, 140)
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(T.INK))
            p.drawRoundedRect(box.translated(6, 6), 6, 6)
            p.setPen(QPen(QColor(T.INK), 2))
            p.setBrush(QColor(T.OCHRE))
            p.drawRoundedRect(box, 6, 6)
            p.setPen(QColor(T.INK))
            p.drawText(box.adjusted(0, 14, 0, -50), Qt.AlignCenter, self.result_text)
            p.setFont(ui_font(18))
            p.drawText(box.adjusted(0, 80, 0, -12), Qt.AlignCenter,
                       f"{self.score} очков · щёлкните, чтобы сыграть ещё")


class TrayWidget(QWidget):
    """Собранные кости — маленьким рядом."""

    def __init__(self):
        super().__init__()
        self.sides: list[Side] = []
        self.setFixedHeight(44)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        if not self.sides:
            p.setPen(QColor(T.INK_SOFT))
            p.setFont(ui_font(13))
            p.drawText(self.rect(), Qt.AlignVCenter | Qt.AlignLeft, "пока пусто")
            return
        step = min(34.0, (self.width() - 30) / max(1, len(self.sides) - 1)) if len(self.sides) > 1 else 0
        for k, s in enumerate(self.sides):
            draw_shagai(p, QPointF(18 + k * step, 22), 30, s, (-1) ** k * 10)


class HarbahaScreen(OrnamentBackground):
    navigate = Signal(str, dict)
    achieve = Signal(str, list)   # имя, коды достижений

    def __init__(self, db, sounds):
        super().__init__()
        self.db = db
        self.sounds = sounds
        o = QVBoxLayout(self)
        o.setContentsMargins(48, 40, 48, 36)
        o.setSpacing(10)
        back = QPushButton("←  В меню")
        back.setObjectName("flat")
        back.setCursor(Qt.PointingHandCursor)
        back.clicked.connect(lambda: self.navigate.emit("menu", {}))
        o.addWidget(back, 0, Qt.AlignLeft)
        t = QLabel("Шагай харбаха")
        t.setObjectName("h1")
        o.addWidget(t)
        st = QLabel("Щелчки: сбейте кость той же стороны и заберите её себе")
        st.setObjectName("h2")
        o.addWidget(st)
        row = QHBoxLayout()
        row.setSpacing(18)
        self.board = HarbahaBoard()
        self.board.changed.connect(self._refresh)
        self.board.knock.connect(lambda: self.sounds.play("knock"))
        self.board.over.connect(self._over)
        row.addWidget(self.board, 1)

        side = QFrame()
        side.setObjectName("card")
        side.setFixedWidth(300)
        c = QVBoxLayout(side)
        c.setContentsMargins(20, 18, 20, 18)
        c.setSpacing(6)
        c.addWidget(self._lab("ИГРОК", "over"))
        self.name = QLineEdit()
        self.name.setPlaceholderText("Ваше имя")
        self.name.setMaxLength(MAX_NAME_LEN + 10)
        self.name.textChanged.connect(lambda: self.err.setText(""))
        c.addWidget(self.name)
        self.err = self._lab("", "error")
        self.err.setWordWrap(True)
        c.addWidget(self.err)
        self.score = self._lab("0")
        self.score.setStyleSheet(f"font-family: '{T.TITLE_FONT}'; font-size: 54px; color: {T.RED};")
        c.addWidget(self.score)
        self.info = self._lab("", "status")
        c.addWidget(self.info)
        c.addWidget(self._lab("СОБРАНО", "over"))
        self.tray = TrayWidget()
        c.addWidget(self.tray)
        self.save_btn = QPushButton("Сохранить результат")
        self.save_btn.setCursor(Qt.PointingHandCursor)
        self.save_btn.clicked.connect(self._save)
        self.save_btn.hide()
        c.addWidget(self.save_btn)
        c.addSpacing(6)
        c.addWidget(self._lab("ЛУЧШИЕ ЩЕЛЧКИ", "over"))
        self.top = self._lab("", "hint")
        self.top.setStyleSheet("font-size: 14px;")
        c.addWidget(self.top)
        c.addStretch()
        help_ = self._lab("Нажмите на кость и тяните назад, как рогатку. Отпустите — кость полетит. "
                          "Первой нужно задеть кость той же стороны. Три промаха — конец игры.", "hint")
        help_.setWordWrap(True)
        c.addWidget(help_)
        again = QPushButton("Новая раскладка")
        again.setObjectName("primary")
        again.setCursor(Qt.PointingHandCursor)
        again.clicked.connect(self.board.new_game)
        c.addWidget(again)
        row.addWidget(side)
        o.addLayout(row, 1)
        QShortcut(QKeySequence(Qt.Key_Escape), self, activated=lambda: self.navigate.emit("menu", {}))
        self._pending: tuple | None = None

    @staticmethod
    def _lab(text, name=""):
        lb = QLabel(text)
        if name:
            lb.setObjectName(name)
        return lb

    def on_show(self, name: str = "", **_):
        if name and not self.name.text():
            self.name.setText(name)
        self.board.new_game()
        self._refresh_top()

    def _refresh(self):
        b = self.board
        self.score.setText(f"{b.score}")
        lives = "●" * b.lives + "○" * (HB.LIVES - b.lives)
        combo = f"   ·   серия ×{min(b.combo, HB.MAX_COMBO)}" if b.combo > 1 else ""
        self.info.setText(f"Попытки: {lives}{combo}")
        self.tray.sides = list(b.collected)
        self.tray.update()
        if b.state != b.OVER:
            self.save_btn.hide()

    def _refresh_top(self):
        try:
            top = self.db.harbaha_top(5)
        except Exception:
            top = []
        self.top.setText("\n".join(f"{i}. {n} — {s}" for i, (n, s, _) in enumerate(top, 1))
                         or "Пока никто не играл — будьте первым!")

    def _over(self, score, hits, cleared, streak):
        self.sounds.play("win" if cleared else "lose")
        self._pending = (score, hits, cleared, streak)
        self._save()

    def _save(self):
        if not self._pending:
            return
        score, hits, cleared, streak = self._pending
        try:
            name = validate_name(self.name.text())
        except NameError_ as e:
            self.err.setText(f"{e} Без имени результат не сохранится.")
            self.save_btn.show()
            self.name.setFocus()
            return
        try:
            self.db.add_harbaha(name, score, hits)
        except Exception as e:
            self.err.setText(f"Не удалось сохранить: {e}")
            self.save_btn.show()
            return
        self.name.setText(name)
        self._pending = None
        self.save_btn.hide()
        self._refresh_top()
        from core.achievements import for_harbaha
        self.achieve.emit(name, for_harbaha(streak, cleared))
