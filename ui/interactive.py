"""Интерактивные «Правила» и «Об игре и народе»: не читать, а трогать.

Карточки переворачиваются, кости бросаются, клавиши загораются, ёхор танцует.
"""
from __future__ import annotations

import math
import random

from PySide6.QtCore import QElapsedTimer, QPointF, QRectF, Qt, QTimer, QVariantAnimation, Signal
from PySide6.QtGui import QColor, QKeySequence, QPainter, QPen, QShortcut
from PySide6.QtWidgets import (QButtonGroup, QGridLayout, QHBoxLayout, QLabel, QPushButton, QSizePolicy,
                               QSlider, QStackedWidget, QVBoxLayout, QWidget)

from core.shagai import QUICK_LENGTH, Race, Rider, Side, TRACK_LENGTH, calc_score, throw
from . import texts
from . import theme as T
from .art import draw_horse_token, draw_ornament_band, draw_shagai, ui_font
from .effects import draw_badge
from .screens import Screen, button, label
from .widgets import DiceWidget, TrackWidget, horses_word, plural, points_txt, throws_txt


# ====================== карточка-перевёртыш ======================
def fit_text(p: QPainter, rect: QRectF, text: str, flags, start: float, smallest: float = 11,
             title: bool = False) -> None:
    """Рисует текст самым крупным шрифтом, при котором он целиком влезает в прямоугольник."""
    size = start
    while size > smallest:
        p.setFont(ui_font(size, title=title))
        br = p.boundingRect(rect, flags, text)
        if br.height() <= rect.height() and br.width() <= rect.width() + 1:
            break
        size -= 1
    p.setFont(ui_font(size, title=title))
    p.drawText(rect, flags, text)


class FlipCard(QWidget):
    """Лицо: значок и название. Нажали — карточка переворачивается и показывает рассказ.
    Размер тянется под окно (w, h — «удобный» размер), шрифты подбираются под карточку."""
    flipped = Signal(bool)

    def __init__(self, title: str, sub: str, back_title: str, back_text: str, icon=None,
                 back_color: str = T.BLUE, w: int = 184, h: int = 236, wide: bool = False):
        super().__init__()
        self.wide = wide  # значок слева, текст справа — для низких карточек
        self.title, self.sub, self.back_title, self.back_text = title, sub, back_title, back_text
        self.icon, self.back_color = icon, back_color
        self.setMinimumSize(int(w * 0.7), int(h * 0.62))
        self.setMaximumSize(int(w * 1.7), int(h * 1.55))
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip("Нажмите, чтобы перевернуть")
        self.v = 0.0          # 0 — лицом, 1 — оборотом
        self.seen = False
        self._hover = False
        self._a = QVariantAnimation(self)
        self._a.setDuration(420)
        self._a.valueChanged.connect(self._set)

    def _set(self, v):
        self.v = float(v)
        self.update()

    def mousePressEvent(self, e):
        if e.button() != Qt.LeftButton:
            return
        to_back = self.v < 0.5
        self._a.stop()
        self._a.setStartValue(self.v)
        self._a.setEndValue(1.0 if to_back else 0.0)
        self._a.start()
        if to_back:
            self.seen = True
        self.flipped.emit(to_back)

    def enterEvent(self, _):
        self._hover = True
        self.update()

    def leaveEvent(self, _):
        self._hover = False
        self.update()

    def _hint(self, p: QPainter, r: QRectF):
        p.setPen(QColor(T.RED if not self.seen else T.INK_SOFT))
        p.setFont(ui_font(13, title=True))
        p.drawText(QRectF(r.left(), r.bottom() - 24, r.width() - 12, 18), Qt.AlignRight,
                   "НАЖМИ  ↻" if not self.seen else "↻")

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        lift = 3 if self._hover else 0
        r = QRectF(2, 2 + (3 - lift), self.width() - 10, self.height() - 12)
        sx = max(0.03, abs(math.cos(math.pi * self.v)))
        back = self.v > 0.5
        p.translate(r.center())
        p.scale(sx, 1)
        p.translate(-r.center())
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(T.INK))
        p.drawRoundedRect(r.translated(5 + lift, 5 + lift), 8, 8)
        p.setPen(QPen(QColor(T.INK), 2))
        p.setBrush(QColor(self.back_color if back else T.PAPER_LIGHT))
        p.drawRoundedRect(r, 8, 8)
        W, H = r.width(), r.height()
        if not back and self.wide:
            ic = min(H * 0.3, W * 0.16)
            if self.icon:
                self.icon(p, QPointF(r.left() + 18 + ic, r.center().y()), ic)
            tx = r.left() + 34 + ic * 2
            p.setPen(QColor(T.INK))
            fit_text(p, QRectF(tx, r.center().y() - H * 0.26, r.right() - tx - 10, H * 0.26),
                     self.title, Qt.AlignLeft | Qt.AlignBottom, min(30, H * 0.2), 14, title=True)
            p.setPen(QColor(T.INK_SOFT))
            fit_text(p, QRectF(tx, r.center().y() + 4, r.right() - tx - 10, H * 0.2), self.sub,
                     Qt.AlignLeft | Qt.AlignTop, min(17, H * 0.13), 11)
            self._hint(p, r)
        elif not back:
            if self.icon:
                self.icon(p, QPointF(r.center().x(), r.top() + H * 0.33), min(W, H) * 0.24)
                ty = r.top() + H * 0.6
            th, sh = H * 0.17, H * 0.14
            if not self.icon:  # карточка без значка — крупная подпись по центру
                th, sh = H * 0.36, H * 0.18
                ty = r.center().y() - th * 0.75
            p.setPen(QColor(T.INK))
            fit_text(p, QRectF(r.left() + 8, ty, W - 16, th), self.title, Qt.AlignCenter,
                     min(36, th * 0.85), 14, title=True)
            p.setPen(QColor(T.INK_SOFT))
            fit_text(p, QRectF(r.left() + 8, ty + th, W - 16, sh), self.sub,
                     Qt.AlignHCenter | Qt.AlignTop, min(17, sh * 0.7), 11)
            self._hint(p, r)
        else:
            light = self.back_color in (T.BLUE, T.RED, T.FELT, T.GREEN)
            p.setPen(QColor(T.PAPER_LIGHT if light else T.INK))
            head = min(H * 0.22, 40)
            fit_text(p, QRectF(r.left() + 14, r.top() + 10, W - 28, head), self.back_title,
                     Qt.AlignLeft | Qt.AlignVCenter, min(28, head * 0.8), 14, title=True)
            fit_text(p, QRectF(r.left() + 14, r.top() + 14 + head, W - 28, H - head - 26), self.back_text,
                     Qt.AlignLeft | Qt.AlignTop | Qt.TextWordWrap, 18, 11)


def bone_icon(side: Side):
    return lambda p, c, r: draw_shagai(p, c, r * 1.9, side, -10, glow=side is Side.MORIN)


def badge_icon(icon: str):
    return lambda p, c, r: draw_badge(p, c, r * 0.95, icon)


def letter_icon(letter: str, color: str = T.BLUE):
    def paint(p: QPainter, c: QPointF, r: float):
        p.setPen(QPen(QColor(T.INK), 2))
        p.setBrush(QColor(color))
        p.drawEllipse(c, r, r)
        p.setPen(QColor(T.PAPER_LIGHT))
        p.setFont(ui_font(r * 1.1, title=True))
        p.drawText(QRectF(c.x() - r, c.y() - r, 2 * r, 2 * r), Qt.AlignCenter, letter)
    return paint


def horse_icon(color: str = T.RED):
    return lambda p, c, r: draw_horse_token(p, QPointF(c.x(), c.y() + r * 0.15), r * 0.8, color, "")


class Progress(QLabel):
    """«Открыто 2 из 4» — маленькая цель на странице. done — цель выполнена."""
    done = Signal()

    def __init__(self, total: int, what: str, done_text: str):
        super().__init__()
        self.total, self.what, self.done_text = total, what, done_text
        self.n = 0
        self.setObjectName("status")
        self._show()

    def bump(self):
        if self.n >= self.total:
            return
        self.n += 1
        self._show()
        if self.n >= self.total:
            self.done.emit()

    def _show(self):
        if self.n >= self.total:
            self.setText(f'<span style="color:{T.GREEN}">✓</span> {self.done_text}')
        else:
            dots = "".join(f'<span style="color:{T.RED if k < self.n else "#CFC4B0"}">●</span>'
                           for k in range(self.total))
            self.setText(f"{dots}  {self.what}: {self.n} из {self.total}")


def card_row(cards: list[FlipCard], prog: Progress | None = None, cols: int | None = None) -> QWidget:
    w = QWidget()
    w.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
    g = QGridLayout(w)
    g.setContentsMargins(0, 0, 0, 0)
    g.setHorizontalSpacing(14)
    g.setVerticalSpacing(14)
    cols = cols or len(cards)
    for k, c in enumerate(cards):
        g.addWidget(c, k // cols, k % cols)
        if prog:
            c.flipped.connect(lambda back, c=c: back and not getattr(c, "_counted", False)
                              and (setattr(c, "_counted", True), prog.bump()))
    for k in range(cols):
        g.setColumnStretch(k, 1)
    return w


# ====================== книга с шагами ======================
class Page(QWidget):
    def __init__(self, over: str, title: str, lead: str):
        super().__init__()
        self.progress: Progress | None = None
        self.lay = QVBoxLayout(self)
        self.lay.setContentsMargins(0, 0, 0, 0)
        self.lay.setSpacing(12)
        o = label(over, "over")
        o.setStyleSheet("font-size: 16px;")
        self.lay.addWidget(o)
        h = label(title, "h1", wrap=True)
        h.setStyleSheet("font-size: 42px;")
        self.lay.addWidget(h)
        if lead:
            ld = label(lead, wrap=True)
            ld.setStyleSheet(f"font-family: '{T.BODY_FONT}'; font-size: 18px; color: {T.INK};")
            self.lay.addWidget(ld)
        self.lay.addSpacing(4)

    def goal(self, prog: Progress) -> Progress:
        self.progress = prog
        return prog

    def on_enter(self):
        pass

    def on_key(self, e) -> bool:
        return False


class Sidebar(QWidget):
    """Синяя полоса слева: название раздела, шаги, внизу — рисунок с шагаями и кайма."""

    def __init__(self):
        super().__init__()
        self.setFixedWidth(330)
        self.setAttribute(Qt.WA_StyledBackground, False)
        self.art_top = 0

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect()).adjusted(0, 0, -10, -10)
        p.fillRect(r.translated(8, 8), QColor(T.INK))
        p.fillRect(r, QColor(T.BLUE))
        p.setPen(QPen(QColor(T.INK), 2))
        p.drawLine(r.topRight(), r.bottomRight())
        p.drawLine(r.bottomLeft(), r.bottomRight())
        band = QRectF(r.left(), r.bottom() - 34, r.width(), 22)
        draw_ornament_band(p, band, T.PAPER_LIGHT, lines=False)
        room = band.top() - self.art_top
        if room > 150:  # рисунок, если осталось место: четыре стороны шагая
            size = min(64.0, room * 0.3, r.width() * 0.2)
            cy = self.art_top + room * 0.5
            for k, side in enumerate((Side.HONIN, Side.YAMAAN, Side.MORIN, Side.TEMEEN)):
                x = r.left() + r.width() * (0.16 + 0.225 * k)
                y = cy + (k % 2) * size * 0.55 - size * 0.25
                draw_shagai(p, QPointF(x, y), size, side, (-1) ** k * 14, glow=side is Side.MORIN,
                            shadow=QColor(0, 0, 0, 90))


NAV_QSS = f"""
QPushButton#nav {{ background: transparent; border: none; border-left: 5px solid transparent;
    border-radius: 0; color: {T.PAPER_LIGHT}; font-size: 19px; padding: 11px 16px; text-align: left; }}
QPushButton#nav:hover {{ background: rgba(248,243,232,30); }}
QPushButton#nav:checked {{ background: {T.PAPER_LIGHT}; color: {T.INK}; border-left: 5px solid {T.RED}; }}
QPushButton#side {{ background: transparent; border: none; color: rgba(248,243,232,200);
    font-size: 16px; padding: 4px 0; text-align: left; }}
QPushButton#side:hover {{ color: {T.PAPER_LIGHT}; text-decoration: underline; }}
"""


class StepBook(Screen):
    """Экран-книга: синяя панель с шагами слева, интерактивная страница справа."""

    def __init__(self, title: str, subtitle: str, pages: list[tuple[str, Page]], final_text: str, final_target):
        super().__init__()  # без стандартной шапки — заголовок живёт в боковой панели
        self.esc = QShortcut(QKeySequence(Qt.Key_Escape), self, activated=self.go_back)
        self.pages = pages
        self.final_target = final_target
        self.final_text = final_text
        self.outer.setContentsMargins(0, 26, 0, 0)
        body = QHBoxLayout()
        body.setSpacing(40)

        side = Sidebar()
        side.setStyleSheet(NAV_QSS)
        sl = QVBoxLayout(side)
        sl.setContentsMargins(26, 22, 34, 50)
        sl.setSpacing(4)
        back = QPushButton("←  В меню")
        back.setObjectName("side")
        back.setCursor(Qt.PointingHandCursor)
        back.setFocusPolicy(Qt.NoFocus)
        back.clicked.connect(self.go_back)
        sl.addWidget(back, 0, Qt.AlignLeft)
        sl.addSpacing(8)
        t = label(title, wrap=True)
        t.setStyleSheet(f"font-family: '{T.TITLE_FONT}'; font-size: 44px; color: {T.PAPER_LIGHT};")
        sl.addWidget(t)
        st = label(subtitle, wrap=True)
        st.setStyleSheet("font-size: 16px; color: rgba(248,243,232,200);")
        sl.addWidget(st)
        sl.addSpacing(18)
        self.nav = QButtonGroup(self)
        self.nav_btns = []
        for k, (name, pg) in enumerate(pages):
            b = QPushButton(f"{k + 1:02d}    {name}")
            b.setObjectName("nav")
            b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
            b.setFocusPolicy(Qt.NoFocus)
            self.nav.addButton(b, k)
            self.nav_btns.append(b)
            sl.addWidget(b)
            if pg.progress is not None:
                pg.progress.done.connect(lambda k=k: self._mark_done(k))
        self.nav.idClicked.connect(self.show_page)
        sl.addStretch()
        self.sidebar = side
        body.addWidget(side)

        right = QVBoxLayout()
        right.setContentsMargins(0, 26, 44, 28)
        self.stack = QStackedWidget()
        for _, pg in pages:
            self.stack.addWidget(pg)
        right.addWidget(self.stack, 1)
        right.addSpacing(10)
        foot = QHBoxLayout()
        self.prev = button("←  Назад", "", "Предыдущий шаг")
        self.prev.setFocusPolicy(Qt.NoFocus)
        self.prev.clicked.connect(lambda: self.show_page(self.k - 1))
        self.dots = label("", "hint")
        self.dots.setStyleSheet("font-size: 16px;")
        self.next = button("Дальше  →", "primary")
        self.next.setMinimumWidth(170)
        self.next.setFocusPolicy(Qt.NoFocus)
        self.next.clicked.connect(self._forward)
        foot.addWidget(self.prev)
        foot.addStretch()
        foot.addWidget(self.dots)
        foot.addStretch()
        foot.addWidget(self.next)
        right.addLayout(foot)
        body.addLayout(right, 1)
        self.outer.addLayout(body, 1)
        self.setFocusPolicy(Qt.StrongFocus)
        self.k = 0

    def resizeEvent(self, e):
        super().resizeEvent(e)
        QTimer.singleShot(0, self._art)

    def _mark_done(self, k: int):
        name = self.pages[k][0]
        self.nav_btns[k].setText(f"{k + 1:02d}    {name}   ✓")

    def on_show(self, page: int = 0, **_):
        self.show_page(page)
        QTimer.singleShot(0, self._art)

    def _art(self):
        self.sidebar.art_top = self.nav_btns[-1].geometry().bottom() + 20
        self.sidebar.update()

    def show_page(self, k: int):
        k = max(0, min(len(self.pages) - 1, k))
        self.k = k
        self.stack.setCurrentIndex(k)
        self.nav.button(k).setChecked(True)
        self.prev.setVisible(k > 0)
        last = k == len(self.pages) - 1
        self.next.setText(self.final_text if last else "Дальше  →")
        self.dots.setText("   ".join("●" if i == k else "○" for i in range(len(self.pages))))
        pg = self.pages[k][1]
        self.esc.setEnabled(not getattr(pg, "grabs_esc", False))
        pg.on_enter()
        self.setFocus()

    def _forward(self):
        if self.k < len(self.pages) - 1:
            self.show_page(self.k + 1)
        else:
            self.final_target()

    def keyPressEvent(self, e):
        if not self.pages[self.k][1].on_key(e):
            super().keyPressEvent(e)


# ====================== ПРАВИЛА ======================
class SidesPage(Page):
    def __init__(self):
        super().__init__("ШАГ 1", "Четыре стороны шагая",
                         "Шагай — косточка из ноги барана. Она может упасть четырьмя сторонами, и у каждой "
                         "есть имя. Переверните все карточки и найдите ту, что ведёт коня вперёд.")
        prog = self.goal(Progress(4, "Открыто карточек", "Запомните: шаг вперёд даёт только «морин» — конь!"))
        cards = [
            FlipCard("Хонин", "овца", "Хонин — овца", "Кость лежит выпуклой стороной вверх.\n\n"
                     "Выпадает чаще всего: примерно 38 из 100 бросков.\n\nВ скачках: коня не двигает.",
                     bone_icon(Side.HONIN)),
            FlipCard("Ямаан", "коза", "Ямаан — коза", "Кость лежит вогнутой стороной вверх.\n\n"
                     "Тоже частая: около 38 из 100.\n\nВ скачках: коня не двигает.", bone_icon(Side.YAMAAN)),
            FlipCard("Морин", "конь", "Морин — конь!", "Кость встала на бок.\n\nРедкая удача: примерно "
                     "12 из 100 бросков.\n\nВ скачках: +1 шаг за каждого коня в броске!",
                     bone_icon(Side.MORIN), back_color=T.OCHRE),
            FlipCard("Тэмээн", "верблюд", "Тэмээн — верблюд", "Кость стоит на узком торце.\n\n"
                     "Около 12 из 100.\n\nВ скачках: коня не двигает.", bone_icon(Side.TEMEEN)),
        ]
        self.lay.addWidget(card_row(cards, prog), 4)
        self.lay.addSpacing(8)
        self.lay.addWidget(prog)
        self.lay.addStretch()


class PracticePage(Page):
    """Учебный заезд: тот же бросок, что в игре, и один конь на ипподроме."""

    def __init__(self, sounds):
        super().__init__("ШАГ 2", "Попробуйте бросить",
                         "Зажмите кнопку — кости затрясутся в горсти. Отпустите — полетят по войлоку. "
                         "Сколько костей встало боком («морин»), на столько костей скачет ваш конь. "
                         "Доведите его до финиша!")
        self.sounds = sounds
        self.track = TrackWidget()
        self.track.setMinimumHeight(118)
        self.track.moved.connect(self._moved)
        self.track.hop.connect(lambda: self.sounds.play("hoof"))
        self.lay.addWidget(self.track, 2)
        self.dice = DiceWidget()
        self.dice.setMinimumHeight(140)
        self.dice.rolled.connect(self._rolled)
        self.lay.addWidget(self.dice, 3)
        row = QHBoxLayout()
        self.info = label("", "status", wrap=True)
        row.addWidget(self.info, 1)
        self.btn = button("Зажмите и отпустите  →", "primary")
        self.btn.setMinimumWidth(280)
        self.btn.pressed.connect(self._press)
        self.btn.released.connect(self._release)
        row.addWidget(self.btn)
        self.lay.addLayout(row)
        self.reset()

    def reset(self):
        self.track.stop()
        self.dice.reset()
        self.rider = Rider("Вы", is_human=True)
        self.race = Race([self.rider], length=QUICK_LENGTH)  # учебный — короткий ипподром
        self.track.set_riders([self.rider], QUICK_LENGTH)
        self.busy = self.holding = False
        self.info.setText("Ваш конь у первой кости. Бросайте!")
        self.btn.setText("Зажмите и отпустите  →")

    def _press(self):
        if self.race.over:
            self.reset()
            return
        if not self.busy and self.dice.start_shake():
            self.busy = self.holding = True
            self.btn.setText("Трясём… отпустите!")

    def _release(self):
        if not self.holding:
            return
        self.holding = False
        self.btn.setText("Летят!")
        self._dice = throw()
        self.sounds.play("throw")
        self.dice.release(self._dice)

    def _rolled(self):
        t = self.race.play_turn(self._dice)
        n = t.steps
        if n:
            self.info.setText(f"{n} {horses_word(n)}! Конь скачет на {n} "
                              f"{plural(n, 'кость', 'кости', 'костей')} вперёд.")
        else:
            self.info.setText("Ни одного коня — ни шагу. Так бывает часто, пробуйте ещё!")
        self.track.animate(0, t.new_position)

    def _moved(self):
        self.busy = False
        if self.race.over:
            self.track.celebrate(0)
            self.sounds.play("win")
            self.info.setText(f"Учебный заезд пройден за {throws_txt(self.rider.throws)}! "
                              f"В настоящей игре соперники бросают по очереди с вами.")
            self.btn.setText("Ещё раз  ↻")
        else:
            left = self.race.finish - self.rider.position
            self.btn.setText("Зажмите и отпустите  →")
            if left <= 2:
                self.info.setText(self.info.text() + f" До финиша {left}!")


class ScorePage(Page):
    """Калькулятор очков: двигайте ползунки — очки пересчитываются сразу."""

    def __init__(self):
        super().__init__("ШАГ 3", "Откуда берутся очки",
                         "Подвигайте ползунки и посмотрите, как меняется результат в таблице рекордов.")
        row = QHBoxLayout()
        row.setSpacing(30)
        form = QGridLayout()
        form.setVerticalSpacing(14)
        form.setHorizontalSpacing(14)

        def seg(values, default, fmt=str):
            box = QHBoxLayout()
            g = QButtonGroup(self)
            for v in values:
                b = button(fmt(v), "seg")
                b.setCheckable(True)
                b.setFocusPolicy(Qt.NoFocus)
                g.addButton(b, int(v))
                box.addWidget(b)
            g.button(int(default)).setChecked(True)
            g.idClicked.connect(lambda _: self._calc())
            return box, g

        def slider(lo, hi, val):
            s = QSlider(Qt.Horizontal)
            s.setRange(lo, hi)
            s.setValue(val)
            s.setMinimumWidth(240)
            s.valueChanged.connect(lambda _: self._calc())
            return s

        wl, self.won = seg((1, 0), 1, lambda v: "Победа" if v else "Не первый")
        self.prog = slider(0, TRACK_LENGTH, TRACK_LENGTH)
        self.thr = slider(5, 40, 16)
        ol, self.opp = seg((1, 2, 3), 2)
        ql, self.quiz = seg((0, 1, 2, 3), 2)
        self.prog_l, self.thr_l = label("", "hint"), label("", "hint")
        rows = [("Итог заезда", wl), ("Пройдено костей", self.prog, self.prog_l),
                ("Бросков", self.thr, self.thr_l), ("Соперников", ol), ("Верных ответов", ql)]
        for k, r in enumerate(rows):
            form.addWidget(label(r[0], "status"), k, 0)
            if isinstance(r[1], QHBoxLayout):
                form.addLayout(r[1], k, 1)
            else:
                form.addWidget(r[1], k, 1)
                form.addWidget(r[2], k, 2)
        row.addLayout(form, 3)
        res = QVBoxLayout()
        res.addWidget(label("ИТОГ", "over"))
        self.total = label("")
        self.total.setStyleSheet(f"font-family: '{T.TITLE_FONT}'; font-size: 72px; color: {T.RED};")
        res.addWidget(self.total)
        self.parts = label("", wrap=True)
        self.parts.setStyleSheet(f"font-family: '{T.BODY_FONT}'; font-size: 15px;")
        res.addWidget(self.parts)
        res.addStretch()
        row.addLayout(res, 2)
        self.lay.addLayout(row)
        self.lay.addStretch()
        self._calc()

    def _calc(self):
        won = self.won.checkedId() == 1
        if won:
            self.prog.setValue(TRACK_LENGTH)
        self.prog.setEnabled(not won)
        prog, thr = self.prog.value(), self.thr.value()
        opp, q = self.opp.checkedId(), self.quiz.checkedId()
        self.prog_l.setText(f"{prog} из {TRACK_LENGTH}")
        self.thr_l.setText(str(thr))
        total = calc_score(won, prog, thr, opp, q)
        self.total.setText(points_txt(total))
        lines = [f"• кости: {prog} × 50 = <b>{prog * 50}</b>"]
        if won:
            lines.append("• победа: <b>+400</b>")
            lines.append(f"• скорость: 300 − 10 × {thr} = <b>+{max(0, 300 - 10 * thr)}</b>")
        if q:
            lines.append(f"• знания: {q} × 50 = <b>+{q * 50}</b>")
        lines.append(f"• соперники: всё × <b>{1 + 0.1 * opp:.1f}</b>")
        self.parts.setText("<br>".join(lines))


class MomentsPage(Page):
    def __init__(self):
        super().__init__("ШАГ 4", "Что ещё бывает в заезде",
                         "В игре вас ждут сюрпризы. Переверните карточки — узнайте, какие.")
        prog = self.goal(Progress(6, "Открыто сюрпризов", "Теперь вы знаете все секреты!"))
        cards = [
            FlipCard("Знаете ли вы?", "факты", "Знаете ли вы?", "Рядом с ковриком на каждом вашем ходу — "
                     "новый факт о бурятах. Читайте: пригодится для вопросов!", letter_icon("?", T.BLUE),
                     w=255, h=150, wide=True),
            FlipCard("Вопрос знатока", "+50 очков", "Вопрос знатока", "После 2-го, 5-го и 8-го броска — "
                     "вопрос о народе с тремя ответами. Верно — +50 очков. На скачки не влияет.",
                     badge_icon("book"), w=255, h=150, wide=True),
            FlipCard("Решающий бросок", "за шаг до финиша", "Решающий бросок!", "Когда коню остаётся 1–2 "
                     "кости, камера наезжает на него, а ход идёт в замедлении.", badge_icon("wind"),
                     back_color=T.RED, w=255, h=150, wide=True),
            FlipCard("Игра вместе", "2–4 наездника", "Вместе веселее", "«Играть вместе» в меню: "
                     "каждый вписывает имя, и вы ходите по очереди, передавая устройство.",
                     badge_icon("people"), w=255, h=150, wide=True),
            FlipCard("Достижения", "9 значков", "Достижения", "«Табун», «Быстрее ветра», «Знаток культуры»… "
                     "Значки выезжают со звоном и хранятся в карточке игрока.", badge_icon("crown"),
                     back_color=T.OCHRE, w=255, h=150, wide=True),
            FlipCard("Сертификат", "для победителя", "Сертификат", "Победитель получает именной сертификат "
                     "A4 — сохраните в PNG или PDF и распечатайте!", badge_icon("clean"), back_color=T.GREEN,
                     w=255, h=150, wide=True),
        ]
        self.lay.addWidget(card_row(cards, prog, cols=3), 4)
        self.lay.addWidget(prog)
        self.lay.addStretch()


class KeyCap(QWidget):
    def __init__(self, text: str, caption: str, w: int = 110):
        super().__init__()
        self.text, self.caption = text, caption
        self.setFixedSize(max(w, 150), 112)
        self.kw = w
        self.lit = 0.0
        self.tried = False
        self._a = QVariantAnimation(self)
        self._a.setDuration(650)
        self._a.setStartValue(1.0)
        self._a.setEndValue(0.0)
        self._a.valueChanged.connect(lambda v: (setattr(self, "lit", float(v)), self.update()))

    def hit(self):
        self.tried = True
        self._a.stop()
        self._a.start()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        x = (self.width() - self.kw) / 2
        down = 4 * self.lit
        r = QRectF(x, 4 + down, self.kw - 6, 50)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(T.INK))
        p.drawRoundedRect(QRectF(x, 10, self.kw - 6, 50), 7, 7)
        col = QColor(T.OCHRE) if self.tried else QColor(T.PAPER_LIGHT)
        if self.lit > 0:
            col = QColor(T.RED)
        p.setPen(QPen(QColor(T.INK), 2))
        p.setBrush(col)
        p.drawRoundedRect(r, 7, 7)
        p.setPen(QColor(T.PAPER_LIGHT if self.lit > 0 else T.INK))
        p.setFont(ui_font(19, title=True))
        p.drawText(r, Qt.AlignCenter, self.text)
        p.setPen(QColor(T.INK_SOFT))
        p.setFont(ui_font(15))
        p.drawText(QRectF(0, 66, self.width(), 46), Qt.AlignHCenter | Qt.AlignTop | Qt.TextWordWrap,
                   self.caption)


class KeysPage(Page):
    grabs_esc = True  # здесь Esc только загорается, а не уводит со страницы

    def __init__(self):
        super().__init__("ШАГ 5", "Управление", "Нажимайте клавиши прямо сейчас — они загорятся. "
                         "Попробуйте все!")
        self.caps = {
            "space": KeyCap("Пробел", "зажать — потрясти,\nотпустить — бросок", 230),
            "enter": KeyCap("Enter", "бросить сразу"),
            "esc": KeyCap("Esc", "назад, в меню"),
            "ctrlf": KeyCap("Ctrl + F", "поиск в рекордах", 130),
            "del": KeyCap("Delete", "удалить запись"),
            "dbl": KeyCap("2× клик", "здесь — по странице;\nв рекордах — переименовать", 130),
        }
        g = QGridLayout()
        g.setHorizontalSpacing(10)
        for k, c in enumerate(self.caps.values()):
            g.addWidget(c, k // 3, k % 3, Qt.AlignCenter)
        self.lay.addLayout(g)
        self.prog = self.goal(Progress(len(self.caps), "Попробовано", "Отлично! Вы готовы к скачкам."))
        self.lay.addWidget(self.prog)
        self.lay.addStretch()

    def _hit(self, key: str):
        c = self.caps[key]
        if not c.tried:
            self.prog.bump()
        c.hit()

    def on_key(self, e) -> bool:
        k = e.key()
        if e.isAutoRepeat():
            return True
        if k == Qt.Key_Space:
            self._hit("space")
        elif k in (Qt.Key_Return, Qt.Key_Enter):
            self._hit("enter")
        elif k == Qt.Key_Escape:
            self._hit("esc")
        elif k == Qt.Key_F and e.modifiers() & Qt.ControlModifier:
            self._hit("ctrlf")
        elif k == Qt.Key_Delete:
            self._hit("del")
        else:
            return False
        return True

    def mouseDoubleClickEvent(self, _):
        self._hit("dbl")


class RulesScreen(StepBook):
    def __init__(self, sounds):
        pages = [("Стороны шагая", SidesPage()), ("Пробный бросок", PracticePage(sounds)),
                 ("Очки", ScorePage()), ("Сюрпризы", MomentsPage()), ("Управление", KeysPage())]
        super().__init__("Как играть", "Мори урилдаан — скачки на шагаях. Пять шагов, и вы готовы!",
                         pages, "Играть  →", lambda: self.navigate.emit("setup", {"mode": 0}))


# ====================== ОБ ИГРЕ И НАРОДЕ ======================
class GamesPage(Page):
    def __init__(self, go):
        super().__init__("ЧАСТЬ 1", "Шагай наадан — «игра в косточки»",
                         "Игры с шагаем — одна из самых древних забав бурят, монголов, калмыков и тувинцев. "
                         "Играют и дети, и взрослые, особенно в Сагаалган. Одними косточками — десятки игр:")
        prog = self.goal(Progress(4, "Открыто игр", "Две из этих игр есть в нашем приложении — попробуйте!"))
        cards = [
            FlipCard("Мори урилдаан", "скачки", "Скачки", "Двенадцать шагай — ипподром. Бросаешь пять "
                     "костей: сколько встало «конём», на столько шагов скачет твой конь.", horse_icon(),
                     back_color=T.RED),
            FlipCard("Шагай няһалалга", "щелчки", "Щелчки", "Щелчком пальца надо попасть одной костью "
                     "в другую, лежащую той же стороной. Сбил — забираешь себе.", bone_icon(Side.YAMAAN)),
            FlipCard("Шагай шүүрэлгэ", "ловкость рук", "Ловкость рук", "Подбросить чётки, успеть "
                     "сгрести горсть костей и поймать чётки той же рукой.", bone_icon(Side.HONIN),
                     back_color=T.GREEN),
            FlipCard("Гадание", "на удачу", "Гадание", "Бросали четыре шагая и по сочетанию сторон "
                     "гадали об удаче. Кость «овцой» дарили уходящему в дальний путь.",
                     bone_icon(Side.TEMEEN), back_color=T.OCHRE),
        ]
        self.lay.addWidget(card_row(cards, prog), 4)
        self.lay.addWidget(prog)
        row = QHBoxLayout()
        b1 = button("Сыграть в скачки  →", "primary")
        b1.clicked.connect(lambda: go("setup", {"mode": 0}))
        b2 = button("Сыграть в щелчки  →")
        b2.clicked.connect(lambda: go("harbaha", {}))
        row.addWidget(b1)
        row.addWidget(b2)
        row.addStretch()
        self.lay.addLayout(row)
        self.lay.addStretch()


class HerdPage(Page):
    def __init__(self):
        super().__init__("ЧАСТЬ 2", "Пять видов скота — «табан хушуун мал»",
                         "Стороны косточки названы в честь скота, которым жили кочевники. Поэтому шагай — "
                         "символ достатка. Откройте всех пятерых.")
        prog = self.goal(Progress(5, "Открыто", "Все пять «драгоценностей степи» открыты!"))
        cards = [
            FlipCard("Хонин", "овца", "Овца", "Главное богатство кочевника: мясо, шерсть для войлока "
                     "и, конечно, косточки-шагай.", bone_icon(Side.HONIN), w=150),
            FlipCard("Ямаан", "коза", "Коза", "Даёт тёплый пух и молоко. Неприхотлива и пасётся даже "
                     "на каменистых склонах.", bone_icon(Side.YAMAAN), w=150),
            FlipCard("Морин", "конь", "Конь", "Друг и гордость семьи. Скачки — главное состязание "
                     "летнего праздника Сурхарбан.", horse_icon(), back_color=T.RED, w=150),
            FlipCard("Тэмээн", "верблюд", "Верблюд", "Выносливый «корабль степи»: возил юрты и грузы "
                     "при перекочёвках.", bone_icon(Side.TEMEEN), w=150),
            FlipCard("Үхэр", "корова", "Корова", "Кормилица семьи: молоко, сливки, творог — «белая "
                     "пища», которой встречают Белый месяц.", letter_icon("Ү", T.GREEN), back_color=T.GREEN,
                     w=150),
        ]
        self.lay.addWidget(card_row(cards, prog), 4)
        self.lay.addWidget(prog)
        self.lay.addStretch()


class Yokhor(QWidget):
    """Хоровод ёхор: танцоры держатся за руки и идут по ходу солнца. Нажмите — быстрее!"""

    def __init__(self):
        super().__init__()
        self.setMinimumHeight(150)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setCursor(Qt.PointingHandCursor)
        self.angle = 0.0
        self.speed = 0.5
        self.t = 0.0
        self._clock = QElapsedTimer()
        self._clock.start()
        self._timer = QTimer(self)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._tick)
        self._timer.start()
        self.colors = [T.RED, T.BLUE, T.OCHRE, T.GREEN, "#6A4AA8", T.RED, T.BLUE, T.OCHRE, T.GREEN, "#D98324"]

    def mousePressEvent(self, _):
        self.speed = min(5.0, self.speed + 0.9)

    def _tick(self):
        dt = min(0.04, self._clock.restart() / 1000)
        self.t += dt
        self.speed = max(0.5, self.speed - dt * 0.6)
        self.angle += self.speed * dt
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect()).adjusted(2, 2, -8, -8)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(T.INK))
        p.drawRoundedRect(r.translated(6, 6), 8, 8)
        p.setPen(QPen(QColor(T.INK), 2))
        p.setBrush(QColor("#CFE0C0"))  # степная трава
        p.drawRoundedRect(r, 8, 8)
        c = QPointF(r.center().x(), r.center().y() + 4)
        rx, ry = r.width() * 0.3, r.height() * 0.24
        # костёр в центре
        for k, (col, s) in enumerate(((T.RED, 1.0), (T.OCHRE, 0.6))):
            fl = 1 + 0.15 * math.sin(self.t * 9 + k)
            p.setPen(QPen(QColor(T.INK), 2) if k == 0 else Qt.NoPen)
            p.setBrush(QColor(col))
            p.drawEllipse(QPointF(c.x(), c.y() - 8 * s * fl), 16 * s, 22 * s * fl)
        n = len(self.colors)
        pts = []
        for i in range(n):
            a = self.angle + i * 2 * math.pi / n
            pts.append((math.sin(a) * ry, QPointF(c.x() + math.cos(a) * rx, c.y() + math.sin(a) * ry), i))
        pts.sort(key=lambda x: x[0])
        # «руки»: цепочка между соседями
        p.setPen(QPen(QColor(T.INK), 3, Qt.SolidLine, Qt.RoundCap))
        pos = {i: q for _, q, i in pts}
        for i in range(n):
            a, b = pos[i], pos[(i + 1) % n]
            p.drawLine(QPointF(a.x(), a.y() - 26), QPointF(b.x(), b.y() - 26))
        for depth, q, i in pts:
            sc = 0.8 + 0.25 * (depth / ry + 1) / 2
            bob = abs(math.sin(self.angle * 6 + i)) * 6 * min(1.6, self.speed)
            x, y = q.x(), q.y() - bob
            p.setPen(QPen(QColor(T.INK), 2))
            p.setBrush(QColor(self.colors[i]))
            body = QRectF(x - 12 * sc, y - 34 * sc, 24 * sc, 40 * sc)
            p.drawRoundedRect(body, 6, 6)
            p.setBrush(QColor("#E8C9A0"))
            p.drawEllipse(QPointF(x, y - 44 * sc), 9 * sc, 9 * sc)
            p.setBrush(QColor(T.INK))
            p.drawRect(QRectF(x - 9 * sc, y - 56 * sc, 18 * sc, 6 * sc))  # шапочка
        p.setPen(QColor(T.INK))
        p.setFont(ui_font(15, title=True))
        tempo = "медленно" if self.speed < 1.2 else "весело!" if self.speed < 3 else "ВИХРЕМ!"
        p.drawText(r.adjusted(14, 0, -14, -10), Qt.AlignLeft | Qt.AlignBottom,
                   f"Нажимайте на хоровод — он закружится быстрее   ·   темп: {tempo}")


class HolidaysPage(Page):
    def __init__(self):
        super().__init__("ЧАСТЬ 3", "Праздники и ёхор",
                         "Шагай достают на больших праздниках. А в конце праздника все встают в круг — танцевать ёхор.")
        prog = self.goal(Progress(3, "Открыто праздников", "Отлично! А теперь — потанцуйте ёхор ниже."))
        cards = [
            FlipCard("Сагаалган", "Белый месяц", "Сагаалган", "Новый год по лунному календарю. Встречают "
                     "«белой пищей», ходят в гости и всей семьёй играют в шагай.", letter_icon("С", T.BLUE),
                     w=255, h=140, wide=True),
            FlipCard("Сурхарбан", "летний праздник", "Сурхарбан", "Праздник «трёх игр мужей»: борьба, "
                     "стрельба из лука и конные скачки.", horse_icon(), back_color=T.RED, w=255, h=140, wide=True),
            FlipCard("Ёхор", "танец в кругу", "Ёхор", "Танцующие держатся за руки и идут по кругу — по "
                     "ходу солнца. Поют и танцуют иногда до утра.", letter_icon("Ё", T.OCHRE),
                     back_color=T.OCHRE, w=255, h=140, wide=True),
        ]
        self.lay.addWidget(card_row(cards, prog), 4)
        self.lay.addWidget(prog)
        self.lay.addWidget(Yokhor(), 1)


WORDS = [("Шагай", "косточка для игры"), ("Наадан", "игра"), ("Морин", "конь"), ("Хонин", "овца"),
         ("Ямаан", "коза"), ("Тэмээн", "верблюд"), ("Үхэр", "корова"), ("Сайн байна!", "Здравствуйте!"),
         ("Баярлаа", "Спасибо"), ("Баяртай", "До свидания"), ("Байгал далай", "озеро Байкал"),
         ("Хадаг", "шарф уважения")]


class WordsPage(Page):
    def __init__(self):
        super().__init__("ЧАСТЬ 4", "Словарик", "Несколько бурятских слов. Угадайте перевод, а потом "
                         "переверните карточку — проверьте себя.")
        prog = self.goal(Progress(len(WORDS), "Выучено слов", "Баярлаа! Все слова открыты."))
        cards = [FlipCard(w, "бурятское слово", w, f"«{tr}»", None, back_color=T.BLUE if k % 3 else T.RED,
                          w=190, h=120) for k, (w, tr) in enumerate(WORDS)]
        for c in cards:  # у маленьких карточек значка нет — поднимаем подпись
            c.icon = None
        self.lay.addWidget(card_row(cards, prog, cols=4), 4)
        self.lay.addWidget(prog)
        note = label("Буряты говорят на бурятском языке монгольской группы. Раньше писали старомонгольским "
                     "вертикальным письмом, сейчас — кириллицей с буквами Ү, Ө и Һ.", "hint", wrap=True)
        self.lay.addWidget(note)
        self.lay.addStretch()


class QuizPage(Page):
    """Мини-викторина: пять вопросов подряд, итог со звёздами."""

    def __init__(self):
        super().__init__("ЧАСТЬ 5", "Проверь себя", "Пять вопросов обо всём, что вы узнали. Сколько угадаете?")
        self.dots = label("", "status")
        self.lay.addWidget(self.dots)
        self.q = label("", "h1", wrap=True)
        self.q.setStyleSheet("font-size: 32px;")
        self.lay.addWidget(self.q)
        self.opts = []
        for k in range(3):
            b = button("")
            b.setFocusPolicy(Qt.NoFocus)
            b.setProperty("big", True)
            b.setMinimumHeight(50)
            b.clicked.connect(lambda _=False, k=k: self._answer(k))
            self.lay.addWidget(b)
            self.opts.append(b)
        self.note = label("", wrap=True)
        self.note.setStyleSheet(f"font-family: '{T.BODY_FONT}'; font-size: 16px;")
        self.lay.addWidget(self.note)
        self.go = button("Следующий вопрос  →", "primary")
        self.go.setFocusPolicy(Qt.NoFocus)
        self.go.clicked.connect(self._next)
        self.lay.addWidget(self.go, 0, Qt.AlignLeft)
        self.lay.addStretch()
        self.start()

    def on_enter(self):
        if self.k >= len(self.items):
            self.start()

    def start(self):
        self.items = random.sample(texts.QUIZ, 5)
        self.k, self.right, self.marks = 0, 0, []
        self._show()

    def _show(self):
        self.dots.setText("  ".join(
            f'<span style="color:{T.GREEN if m else T.RED}">●</span>' for m in self.marks)
            + "  " + "  ".join("○" for _ in range(len(self.items) - len(self.marks))))
        if self.k >= len(self.items):
            stars = "★" * self.right + "☆" * (len(self.items) - self.right)
            verdict = ("Настоящий знаток бурятской культуры!" if self.right == 5 else
                       "Очень хорошо!" if self.right >= 3 else "Загляните в карточки ещё раз — и попробуйте снова.")
            self.q.setText(f'<span style="color:{T.OCHRE}">{stars}</span><br>{self.right} из 5. {verdict}')
            for b in self.opts:
                b.hide()
            self.note.setText("")
            self.go.setText("Ещё раз  ↻")
            return
        q, options, right, expl = self.items[self.k]
        self.q.setText(q)
        for b, t in zip(self.opts, options):
            b.setText(t)
            b.setStyleSheet("font-size: 19px;")
            b.setEnabled(True)
            b.show()
        self.ans = right
        self.expl = expl
        self.note.setText("")
        self.go.hide()

    def _answer(self, k):
        ok = k == self.ans
        self.right += ok
        self.marks.append(ok)
        self.opts[self.ans].setStyleSheet(f"font-size: 19px; background: {T.GREEN}; color: {T.PAPER_LIGHT};")
        if not ok:
            self.opts[k].setStyleSheet(f"font-size: 19px; background: {T.RED}; color: {T.PAPER_LIGHT};")
        for b in self.opts:
            b.setEnabled(False)
        self.note.setText(("Верно! " if ok else "Не угадали. ") + self.expl)
        self.k += 1
        self.go.setText("Следующий вопрос  →" if self.k < len(self.items) else "Узнать итог  →")
        self.go.show()

    def _next(self):
        if self.k >= len(self.items) and not self.opts[0].isVisible():
            self.start()
        else:
            self._show()


class AboutScreen(StepBook):
    def __init__(self):
        go = lambda t, kw: self.navigate.emit(t, kw)
        pages = [("Игры с шагаем", GamesPage(go)), ("Пять видов скота", HerdPage()),
                 ("Праздники и ёхор", HolidaysPage()), ("Словарик", WordsPage()), ("Проверь себя", QuizPage())]
        super().__init__("Об игре и народе", "Буряты, их праздники и косточки-шагай — нажимайте на всё!",
                         pages, "Играть  →", lambda: self.navigate.emit("setup", {"mode": 0}))
