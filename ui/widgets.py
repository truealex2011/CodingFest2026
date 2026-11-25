from __future__ import annotations

import math
import random

from PySide6.QtCore import (QEasingCurve, QElapsedTimer, QPointF, QRectF, Qt, QTimer,
                            QVariantAnimation, Signal)
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QSizePolicy, QWidget

from core.shagai import DICE_COUNT, SIDES, START, TRACK_LENGTH, WEIGHTS, Side
from . import theme as T
from .art import draw_horse_token, draw_ornament_band, draw_shagai, ui_font


def plural(n: int, one: str, few: str, many: str) -> str:
    n = abs(int(n))
    if n % 10 == 1 and n % 100 != 11:
        return one
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return few
    return many


def throws_txt(n: int) -> str:
    return f"{n} {plural(n, 'бросок', 'броска', 'бросков')}"


def points_txt(n: int) -> str:
    return f"{n} {plural(n, 'очко', 'очка', 'очков')}"


def horses_word(n: int) -> str:
    if n % 10 == 1 and n % 100 != 11:
        return "конь"
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return "коня"
    return "коней"


class _Bone:
    __slots__ = ("x", "y", "z", "vx", "vy", "vz", "a", "spin", "side", "landed", "pop")

    def __init__(self):
        self.x = self.y = self.z = self.vx = self.vy = self.vz = self.a = self.spin = 0.0
        self.side = Side.HONIN
        self.landed = True
        self.pop = 0.0


class DiceWidget(QWidget):
    rolled = Signal()
    popped = Signal()

    IDLE, SHAKE, FLY, REVEAL, HOLD = range(5)
    G = 1500.0
    HOLD_TIME = 1.35
    POP_EVERY = 0.32
    LIFT_VIEW = 0.5

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(220)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.fast = False
        self._rnd = random.Random()
        self.bones = [_Bone() for _ in range(DICE_COUNT)]
        for b, s in zip(self.bones, (Side.HONIN, Side.YAMAAN, Side.MORIN, Side.TEMEEN, Side.HONIN)):
            b.side = s
        self._fresh = True
        self.state = self.IDLE
        self.power = 0.0
        self._final: list[Side] = []
        self._t = 0.0
        self._morin: list[int] = []
        self._n_popped = 0
        self.banner = ""
        self._banner_t = 0.0
        self._cluster = QPointF()
        self._token = 0
        self._clock = QElapsedTimer()
        self._timer = QTimer(self)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._tick)

    def _mat(self) -> QRectF:
        return QRectF(self.rect()).adjusted(2, 2, -8, -8)

    def _area(self) -> QRectF:
        return self._mat().adjusted(22, 36, -22, -12)

    def _size(self) -> float:
        a = self._area()
        return max(30.0, min(a.height() * 0.40, a.width() / 8.5))

    def _lay_row(self) -> None:
        a, size = self._area(), self._size()
        for i, b in enumerate(self.bones):
            b.x = a.left() + a.width() * (i + 1) / (DICE_COUNT + 1)
            b.y = a.center().y() - size * 0.1
            b.z, b.a = 0.0, self._rnd.uniform(-10, 10)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if self._fresh:
            self._lay_row()
        else:
            a, size = self._area(), self._size()
            for b in self.bones:
                b.x = min(max(b.x, a.left() + size * 0.45), a.right() - size * 0.45)
                b.y = min(max(b.y, a.top() + size * 0.4), a.bottom() - size * 0.55 - 20)

    @property
    def busy(self) -> bool:
        return self.state != self.IDLE

    def start_shake(self) -> bool:
        if self.state != self.IDLE:
            return False
        if self._fresh:
            self._lay_row()
        self._fresh = False
        a, size = self._area(), self._size()
        self._cluster = QPointF(a.left() + size * 1.25, a.center().y())
        self.state, self.power, self._t = self.SHAKE, 0.0, 0.0
        self._hold = self.HOLD_TIME
        self.banner = ""
        for b in self.bones:
            b.pop, b.landed = 0.0, False
        self._clock.start()
        self._timer.start()
        return True

    def release(self, final: list[Side]) -> None:
        if self.state != self.SHAKE:
            return
        self._final = list(final)
        size, k = self._size(), self._area().width() / 900
        p = max(0.25, self.power)
        c = self._cluster
        for b in self.bones:
            b.x = c.x() + self._rnd.uniform(-0.3, 0.3) * size
            b.y = c.y() + self._rnd.uniform(-0.5, 0.5) * size
            b.z = 30.0
            b.vx = (250 + 430 * p) * k * self._rnd.uniform(0.65, 1.25)
            b.vy = self._rnd.uniform(-1, 1) * 420 * k
            b.vz = self._rnd.uniform(260, 380) + 200 * p
            b.spin = self._rnd.uniform(500, 1000) * self._rnd.choice((-1, 1))
            b.landed = False
        self.state, self._t = self.FLY, 0.0

    def reset(self) -> None:
        self._timer.stop()
        self._token += 1
        self.state, self.banner = self.IDLE, ""
        for b in self.bones:
            b.z, b.pop, b.landed = 0.0, 0.0, True
        self.update()

    def roll(self, final: list[Side], quick: bool = False) -> None:
        if self.start_shake():
            self._hold = self.HOLD_TIME * (0.6 if quick else 1)
            hold = self._rnd.randint(250, 450) if not self.fast else 150
            token = self._token
            QTimer.singleShot(hold, lambda: token == self._token and self.release(final))

    def _tick(self) -> None:
        dt = min(0.04, self._clock.restart() / 1000)
        if self.fast:
            dt *= 1.8
        self._t += dt
        if self.state == self.SHAKE:
            self._shake(dt)
        elif self.state == self.FLY:
            self._fly(dt)
        elif self.state == self.REVEAL:
            self._reveal(dt)
        elif self.state == self.HOLD:
            self._banner_t += dt
            if self._t >= self._hold:
                self.state = self.IDLE
                self._timer.stop()
                self.update()
                self.rolled.emit()
                return
        self.update()

    def _shake(self, dt: float) -> None:
        self.power = min(1.0, self.power + dt / 1.1)
        size, c = self._size(), self._cluster
        amp = 2 + self.power * 8
        for i, b in enumerate(self.bones):
            ang = i * 2 * math.pi / DICE_COUNT + self._t * 4
            b.x = c.x() + math.cos(ang) * size * 0.3 + self._rnd.uniform(-amp, amp)
            b.y = c.y() + math.sin(ang) * size * 0.42 + self._rnd.uniform(-amp, amp)
            b.z = 8 + abs(math.sin(self._t * 17 + i)) * (6 + self.power * 14)
            b.a += self._rnd.uniform(-30, 30)
            if self._rnd.random() < 0.12:
                b.side = self._rnd.choice(SIDES)

    def _fly(self, dt: float) -> None:
        a, size = self._area(), self._size()
        lo_x, hi_x = a.left() + size * 0.45, a.right() - size * 0.45
        lo_y, hi_y = a.top() + size * 0.5 + 10, a.bottom() - size * 0.55 - 20
        for i, b in enumerate(self.bones):
            b.x += b.vx * dt
            b.y += b.vy * dt
            b.a += b.spin * dt
            if not b.landed:
                b.vz -= self.G * dt
                b.z += b.vz * dt
                if b.z <= 0 and b.vz < 0:
                    b.z = 0.0
                    if -b.vz < 110:
                        b.vz, b.landed, b.side = 0.0, True, self._final[i]
                    else:
                        b.vz = -b.vz * 0.45
                        b.side = self._rnd.choices(SIDES, weights=WEIGHTS)[0]
                    b.vx *= 0.7
                    b.vy *= 0.7
                    b.spin *= 0.55
            else:
                f = max(0.0, 1 - 5 * dt)
                b.vx *= f
                b.vy *= f
                b.spin *= max(0.0, 1 - 6 * dt)
            if b.x < lo_x:
                b.x, b.vx = lo_x, abs(b.vx) * 0.5
            elif b.x > hi_x:
                b.x, b.vx = hi_x, -abs(b.vx) * 0.5
            if b.y < lo_y:
                b.y, b.vy = lo_y, abs(b.vy) * 0.5
            elif b.y > hi_y:
                b.y, b.vy = hi_y, -abs(b.vy) * 0.5
        self._collide(size)
        settled = all(b.landed and math.hypot(b.vx, b.vy) < 10 and abs(b.spin) < 25 for b in self.bones)
        if settled or self._t > 3.5:
            for i, b in enumerate(self.bones):
                b.z = b.vz = b.vx = b.vy = b.spin = 0.0
                b.landed, b.side = True, self._final[i]
            for _ in range(12):
                self._collide(size)
            self._morin = [i for i, s in enumerate(self._final) if s is Side.MORIN]
            self._n_popped = 0
            self.state, self._t = self.REVEAL, 0.0

    def _collide(self, size: float) -> None:
        md = size * 0.82
        bs = self.bones
        for i in range(len(bs)):
            for j in range(i + 1, len(bs)):
                p, q = bs[i], bs[j]
                if p.z > size * 0.5 or q.z > size * 0.5:
                    continue
                dx, dy = q.x - p.x, q.y - p.y
                d = math.hypot(dx, dy)
                if d >= md:
                    continue
                if d < 0.01:
                    dx, dy, d = self._rnd.uniform(-1, 1), self._rnd.uniform(-1, 1), 1.0
                ux, uy = dx / d, dy / d
                push = (md - d) / 2
                p.x -= ux * push
                p.y -= uy * push
                q.x += ux * push
                q.y += uy * push
                rel = (p.vx - q.vx) * ux + (p.vy - q.vy) * uy
                if rel > 0:
                    imp = rel * 0.9
                    p.vx -= imp * ux
                    p.vy -= imp * uy
                    q.vx += imp * ux
                    q.vy += imp * uy
                    p.spin, q.spin = q.spin * 0.8, p.spin * 0.8

    def _reveal(self, dt: float) -> None:
        due = min(len(self._morin), int(self._t / self.POP_EVERY) + 1) if self._morin else 0
        while self._n_popped < due:
            self.bones[self._morin[self._n_popped]].pop = 0.001
            self._n_popped += 1
            self.popped.emit()
        for b in self.bones:
            if 0 < b.pop < 1:
                b.pop = min(1.0, b.pop + dt / 0.3)
        done_at = self.POP_EVERY * len(self._morin) + 0.2
        if self._t >= done_at:
            n = len(self._morin)
            self.banner = f"+{n} {horses_word(n).upper()}!" if n else "НИ ОДНОГО КОНЯ"
            self._banner_t = 0.0
            self.state, self._t = self.HOLD, 0.0

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
        size = self._size()

        if self.state == self.SHAKE:
            rad = size * 1.05
            box = QRectF(self._cluster.x() - rad, self._cluster.y() - rad, rad * 2, rad * 2)
            p.setBrush(Qt.NoBrush)
            p.setPen(QPen(QColor(248, 243, 232, 50), 6))
            p.drawEllipse(box)
            p.setPen(QPen(QColor(T.OCHRE), 6, Qt.SolidLine, Qt.FlatCap))
            p.drawArc(box, 90 * 16, int(-self.power * 360 * 16))

        p.save()
        p.setClipRect(r.adjusted(2, 2, -2, -2))
        show_labels = self.state in (self.HOLD, self.IDLE) and bool(self.banner)
        for b in sorted(self.bones, key=lambda b: b.y):
            sc = 1 + 0.32 * math.sin(math.pi * b.pop) if 0 < b.pop < 1 else 1.0
            lift = b.z * self.LIFT_VIEW
            draw_shagai(p, QPointF(b.x, b.y - lift), size, b.side, b.a, glow=b.pop > 0,
                        shadow=QColor(0, 0, 0, 90), lift=lift, scale=sc)
            if show_labels:
                morin = b.side is Side.MORIN
                p.setFont(ui_font(14, bold=morin))
                p.setPen(QColor(T.OCHRE if morin else T.PAPER_LIGHT))
                p.drawText(QRectF(b.x - 60, b.y + size * 0.6, 120, 20), Qt.AlignCenter, b.side.buryat)

        p.restore()

        if self.banner:
            k = min(1.0, self._banner_t / 0.22) if self.state == self.HOLD else 1.0
            sc = 1 + 0.35 * (1 - k) * math.cos(k * math.pi * 1.5)
            p.save()
            p.translate(r.center().x(), r.top() + 22)
            p.scale(sc, sc)
            f = ui_font(30, title=True)
            p.setFont(f)
            tw = p.fontMetrics().horizontalAdvance(self.banner) + 40
            pill = QRectF(-tw / 2, -22, tw, 44)
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(T.INK))
            p.drawRoundedRect(pill.translated(4, 4), 6, 6)
            got = bool(self._morin)
            p.setBrush(QColor(T.OCHRE if got else T.PAPER_LIGHT))
            p.setPen(QPen(QColor(T.INK), 2))
            p.drawRoundedRect(pill, 6, 6)
            p.setPen(QColor(T.INK))
            p.drawText(pill, Qt.AlignCenter, self.banner)
            p.restore()


class TrackWidget(QWidget):
    moved = Signal()
    hop = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(230)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.riders = []
        self.colors: list[str] = []
        self.pos: list[float] = []
        self.length = TRACK_LENGTH
        self.finish = TRACK_LENGTH + START
        self.active = -1
        self.moving = -1
        self._phase = 0.0
        self._anim: QVariantAnimation | None = None
        self.fast = False
        self.drama = -1
        self.zoom = 1.0
        self._zoom_anim = QVariantAnimation(self)
        self._zoom_anim.valueChanged.connect(self._set_zoom)
        self.winner = -1
        self._cel_t = 0.0
        self._cel = QTimer(self)
        self._cel.setInterval(16)
        self._cel.timeout.connect(self._cel_tick)

    def stop(self) -> None:
        if self._anim is not None:
            self._anim.stop()
        self.moving = -1
        self._cel.stop()
        self.winner = -1
        self._zoom_anim.stop()
        self.drama, self.zoom = -1, 1.0
        self.update()

    def _set_zoom(self, v):
        self.zoom = float(v)
        self.update()

    def set_drama(self, idx: int) -> None:
        if idx == self.drama:
            return
        if idx >= 0:
            self.drama = idx
        self._zoom_anim.stop()
        self._zoom_anim.setStartValue(self.zoom)
        self._zoom_anim.setEndValue(1.28 if idx >= 0 else 1.0)
        self._zoom_anim.setDuration(550)
        self._zoom_anim.setEasingCurve(QEasingCurve.InOutCubic)
        if idx < 0:
            self._zoom_anim.finished.connect(self._drama_off)
        self._zoom_anim.start()

    def _drama_off(self):
        self._zoom_anim.finished.disconnect(self._drama_off)
        if self.zoom <= 1.001:
            self.drama = -1
            self.update()

    def celebrate(self, idx: int) -> None:
        self.winner = idx
        self._cel_t = 0.0
        self._cel.start()

    def _cel_tick(self):
        self._cel_t += 0.016
        self.update()

    def set_riders(self, riders, length: int = TRACK_LENGTH) -> None:
        self.length, self.finish = length, length + START
        self.riders = riders
        self.colors = T.RIDER_COLORS[: len(riders)]
        self.pos = [float(r.position) for r in riders]
        self.active = 0
        self.update()

    def animate(self, idx: int, new_pos: int) -> None:
        start = self.pos[idx]
        if new_pos == start:
            QTimer.singleShot(150, self.moved.emit)
            return
        self.moving = idx
        a = QVariantAnimation(self)
        a.setStartValue(start)
        a.setEndValue(float(new_pos))
        slow = 1.7 if self.drama == idx else 1.0
        a.setDuration(int((240 if self.fast else 460) * slow * (new_pos - start) + 150))
        a.setEasingCurve(QEasingCurve.Linear)

        hops = [0]

        def step(v):
            self.pos[idx] = float(v)
            done = float(v) - start
            self._phase = done * math.pi
            if int(done + 0.5) > hops[0]:
                hops[0] = int(done + 0.5)
                self.hop.emit()
            self.update()

        def done():
            self.moving = -1
            self.update()
            self.moved.emit()

        a.valueChanged.connect(step)
        a.finished.connect(done)
        self._anim = a
        a.start()

    def _x(self, r: QRectF, pos: float) -> float:
        left, right = r.left() + 70, r.right() - 70
        return left + (pos - START) * (right - left) / (self.finish - START)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect()).adjusted(2, 2, -8, -8)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(T.INK))
        p.drawRoundedRect(r.translated(6, 6), 6, 6)
        p.setPen(QPen(QColor(T.INK), 2))
        p.setBrush(QColor(T.PAPER_LIGHT))
        p.drawRoundedRect(r, 6, 6)

        n = max(1, len(self.riders))
        bone_y = r.top() + 40
        lane_top = bone_y + 38
        lane_h = (r.bottom() - 2 - lane_top) / n

        p.save()
        p.setClipRect(r.adjusted(1, 1, -1, -1))
        if self.zoom > 1.001 and 0 <= self.drama < len(self.riders):
            fx_ = min(self._x(r, self.pos[self.drama]), self._x(r, self.finish) - 40)
            focus = QPointF(fx_, lane_top + lane_h * (self.drama + 0.5))
            p.translate(focus)
            p.scale(self.zoom, self.zoom)
            p.translate(-focus)

        p.setFont(ui_font(13, title=True))
        p.setPen(QColor(T.INK_SOFT))
        p.drawText(QRectF(r.left() + 14, r.top() + 8, 120, 18), Qt.AlignLeft, "СТАРТ")
        p.drawText(QRectF(r.right() - 134, r.top() + 8, 120, 18), Qt.AlignRight, "ФИНИШ")

        num_font = ui_font(11, bold=True)
        for k in range(1, self.length + 1):
            x = self._x(r, k)
            draw_shagai(p, QPointF(x, bone_y), 28, Side.HONIN if k % 2 else Side.YAMAAN, 0)
            p.setPen(QColor(T.INK_SOFT))
            p.setFont(num_font)
            p.drawText(QRectF(x - 12, bone_y + 13, 24, 14), Qt.AlignCenter, str(k))

        p.setPen(QPen(QColor(T.INK), 2))
        p.drawLine(QPointF(r.left(), lane_top), QPointF(r.right(), lane_top))
        fx = self._x(r, self.finish)
        for i in range(len(self.riders)):
            lane = QRectF(r.left() + 1, lane_top + lane_h * i + 1, r.width() - 2, lane_h - 1)
            if i == self.active:
                c = QColor(T.OCHRE)
                c.setAlpha(110)
            else:
                c = QColor(0, 0, 0, 14 if i % 2 else 0)
            p.fillRect(lane, c)
            p.fillRect(QRectF(lane.left(), lane.top(), 6, lane.height()), QColor(self.colors[i]))
            if i:
                p.setPen(QPen(QColor(T.INK), 1))
                p.drawLine(QPointF(r.left(), lane.top() - 1), QPointF(r.right(), lane.top() - 1))
            p.setPen(QPen(QColor(30, 27, 24, 60), 1, Qt.DashLine))
            p.drawLine(QPointF(self._x(r, START), lane.center().y()), QPointF(fx, lane.center().y()))

        cell = 7
        y = lane_top + 1
        i = 0
        while y < r.bottom() - 1:
            hgt = min(cell, r.bottom() - 1 - y)
            p.fillRect(QRectF(fx - cell, y, cell, hgt), QColor(T.PAPER_LIGHT if i % 2 else T.INK))
            p.fillRect(QRectF(fx, y, cell, hgt), QColor(T.INK if i % 2 else T.PAPER_LIGHT))
            y += cell
            i += 1

        if self.drama >= 0:
            k = min(1.0, (self.zoom - 1) / 0.28)
            for i in range(len(self.riders)):
                if i != self.drama:
                    p.fillRect(QRectF(r.left(), lane_top + lane_h * i, r.width(), lane_h),
                               QColor(30, 27, 24, int(45 * k)))

        for i, rider in enumerate(self.riders):
            lane = QRectF(r.left(), lane_top + lane_h * i, r.width(), lane_h)
            rad = min(lane_h * 0.3, 24)
            c = QPointF(self._x(r, self.pos[i]), lane.center().y() - rad * 0.25)
            bob = -abs(math.sin(self._phase)) * rad * 0.8 if i == self.moving else 0
            if i == self.winner:
                self._paint_rays(p, c, rad)
                bob = -abs(math.sin(self._cel_t * 7)) * rad * 0.7
            label = rider.name if len(rider.name) <= 10 else rider.name[:9] + "…"
            draw_horse_token(p, c, rad, self.colors[i], label, bob,
                             highlight=(i == self.active and self.winner < 0))
        p.restore()

        p.setPen(QPen(QColor(T.INK), 2))
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(r, 6, 6)
        if self.drama >= 0 and self.winner < 0:
            k = min(1.0, (self.zoom - 1) / 0.28)
            self._ribbon(p, QPointF(r.center().x(), r.top() + 4), "РЕШАЮЩИЙ БРОСОК!", T.RED, k)
        if self.winner >= 0:
            name = self.riders[self.winner].name
            self._ribbon(p, QPointF(r.center().x(), r.top() + 4), f"ФИНИШ! ПОБЕДИЛ {name.upper()}",
                         T.OCHRE, min(1.0, self._cel_t / 0.3))

    def _paint_rays(self, p: QPainter, c: QPointF, rad: float) -> None:
        p.save()
        p.translate(c)
        p.rotate(self._cel_t * 40)
        p.setPen(Qt.NoPen)
        col = QColor(T.OCHRE)
        col.setAlpha(200)
        p.setBrush(col)
        R = rad * 2.6 * min(1.0, self._cel_t / 0.4)
        for k in range(12):
            p.rotate(30)
            path = QPainterPath(QPointF(0, 0))
            path.lineTo(R, -R * 0.13)
            path.lineTo(R, R * 0.13)
            path.closeSubpath()
            p.drawPath(path)
        p.restore()

    def _ribbon(self, p: QPainter, top: QPointF, text: str, color: str, k: float) -> None:
        if k <= 0:
            return
        p.save()
        f = ui_font(22, title=True)
        p.setFont(f)
        w = p.fontMetrics().horizontalAdvance(text) + 36
        p.translate(top.x(), top.y() + 18)
        sc = 0.6 + 0.4 * k + 0.12 * math.sin(k * math.pi)
        p.scale(sc, sc)
        box = QRectF(-w / 2, -16, w, 34)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(T.INK))
        p.drawRoundedRect(box.translated(4, 4), 5, 5)
        p.setPen(QPen(QColor(T.INK), 2))
        p.setBrush(QColor(color))
        p.drawRoundedRect(box, 5, 5)
        p.setPen(QColor(T.PAPER_LIGHT if color == T.RED else T.INK))
        p.drawText(box, Qt.AlignCenter, text)
        p.restore()


class FloatingBones(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(380, 420)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.t = 0.0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(33)

    def _tick(self):
        self.t += 0.03
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect()).adjusted(2, 2, -10, -10)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(T.INK))
        p.drawRect(r.translated(8, 8))
        p.setPen(QPen(QColor(T.INK), 2))
        p.setBrush(QColor(T.BLUE))
        p.drawRect(r)
        draw_ornament_band(p, QRectF(r.left() + 1, r.bottom() - 30, r.width() - 2, 18), T.PAPER_LIGHT)
        inner = r.adjusted(16, 16, -16, -46)
        p.setPen(QPen(QColor(248, 243, 232, 90), 1))
        p.setBrush(Qt.NoBrush)
        p.drawRect(inner)
        p.drawLine(QPointF(inner.center().x(), inner.top()), QPointF(inner.center().x(), inner.bottom()))
        p.drawLine(QPointF(inner.left(), inner.center().y()), QPointF(inner.right(), inner.center().y()))

        cw, ch = inner.width() / 2, inner.height() / 2
        size = min(cw, ch) * 0.46
        for i, side in enumerate(SIDES):
            cx = inner.left() + cw * (i % 2 + 0.5)
            top = inner.top() + ch * (i // 2)
            y = top + ch * 0.42 + math.sin(self.t + i * 1.3) * 4
            draw_shagai(p, QPointF(cx, y), size, side, math.sin(self.t * 0.8 + i) * 8,
                        glow=side is Side.MORIN, shadow=QColor(0, 0, 0, 80))
            p.setFont(ui_font(20, title=True))
            p.setPen(QColor(T.OCHRE if side is Side.MORIN else T.PAPER_LIGHT))
            p.drawText(QRectF(cx - cw / 2, top + ch * 0.72, cw, 24), Qt.AlignCenter, side.buryat.upper())
            p.setFont(ui_font(13))
            p.setPen(QColor(248, 243, 232, 190))
            p.drawText(QRectF(cx - cw / 2, top + ch * 0.72 + 24, cw, 18), Qt.AlignCenter,
                       side.russian.lower() + (" — шаг вперёд" if side is Side.MORIN else ""))
