from __future__ import annotations

import random

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QSettings, Qt, QTimer, Signal
from PySide6.QtGui import (QColor, QFont, QFontMetricsF, QKeySequence, QPainter, QPainterPath,
                           QShortcut)
from PySide6.QtWidgets import (QAbstractItemView, QButtonGroup, QFileDialog, QFrame,
                               QGraphicsOpacityEffect, QHBoxLayout, QHeaderView, QInputDialog,
                               QLabel, QLineEdit, QMenu, QMessageBox, QPushButton, QTableWidget,
                               QTableWidgetItem, QTextBrowser, QVBoxLayout, QWidget)

from core.db import RecordsDB
from core.shagai import (DICE_COUNT, QUICK_LENGTH, QUIZ_BONUS, TRACK_LENGTH, Race, Rider, calc_score,
                         horses_in, throw)
from core.validation import MAX_NAME_LEN, NameError_, validate_name
from . import texts
from . import theme as T
from .art import OrnamentBackground, ui_font
from core import achievements as ACH
from . import certificate
from .effects import HadakRain
from .profile import PlayerCard
from .tour import Tour, tour_done
from .widgets import DiceWidget, FloatingBones, TrackWidget, horses_word, points_txt, throws_txt

AI_NAMES = ["Баатар", "Сэсэг", "Жаргал"]


def label(text: str, name: str = "", wrap: bool = False, align=None) -> QLabel:
    lb = QLabel(text)
    if name:
        lb.setObjectName(name)
    lb.setWordWrap(wrap)
    if align is not None:
        lb.setAlignment(align)
    return lb


def ask(parent, title: str, text: str, yes: str, no: str, danger: bool = False) -> bool:
    box = QMessageBox(QMessageBox.Warning if danger else QMessageBox.Question, title, text, parent=parent)
    y = box.addButton(yes, QMessageBox.AcceptRole)
    n = box.addButton(no, QMessageBox.RejectRole)
    if danger:
        y.setObjectName("primary")
    box.setDefaultButton(n)
    box.setEscapeButton(n)
    box.exec()
    return box.clickedButton() is y


def button(text: str, name: str = "", tip: str = "") -> QPushButton:
    b = QPushButton(text)
    if name:
        b.setObjectName(name)
    if tip:
        b.setToolTip(tip)
    b.setCursor(Qt.PointingHandCursor)
    return b


class Screen(OrnamentBackground):
    navigate = Signal(str, dict)

    def __init__(self, title: str = "", subtitle: str = "", back: bool = True):
        super().__init__()
        self.outer = QVBoxLayout(self)
        self.outer.setContentsMargins(48, 40, 48, 36)
        self.outer.setSpacing(14)
        if title:
            if back:
                b = button("←  В меню", "flat", "Вернуться в главное меню (Esc)")
                b.clicked.connect(self.go_back)
                self.outer.addWidget(b, 0, Qt.AlignLeft)
            head = QVBoxLayout()
            head.setSpacing(2)
            head.addWidget(label(title, "h1"))
            if subtitle:
                head.addWidget(label(subtitle, "h2"))
            self.outer.addLayout(head)
            self.outer.addSpacing(4)
        if back:
            self.esc = QShortcut(QKeySequence(Qt.Key_Escape), self, activated=self.go_back)

    def go_back(self):
        self.navigate.emit("menu", {})

    def on_show(self, **kw):
        pass


class PosterTitle(QWidget):

    def __init__(self, lines, px: int):
        super().__init__()
        self.lines = lines
        self.font_ = ui_font(px, title=True)
        fm = QFontMetricsF(self.font_)
        self.step = fm.capHeight() * 1.22
        self.top = fm.capHeight() * 0.3
        self.setFixedSize(int(max(fm.horizontalAdvance(s) for s in lines)) + 4,
                          int(self.top + self.step * (len(lines) - 1) + fm.capHeight() + fm.descent()))

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        path = QPainterPath()
        cap = QFontMetricsF(self.font_).capHeight()
        for i, s in enumerate(self.lines):
            path.addText(0, self.top + cap + self.step * i, self.font_, s)
        p.fillPath(path, QColor(T.INK))


class MenuScreen(Screen):
    def __init__(self, sounds):
        super().__init__(back=False)
        self.sounds = sounds
        o = self.outer
        o.setContentsMargins(64, 48, 56, 44)
        split = QHBoxLayout()
        split.setSpacing(56)
        col = QVBoxLayout()
        col.setSpacing(0)
        col.addStretch(1)
        col.addWidget(label("БУРЯТСКАЯ НАРОДНАЯ ИГРА", "over"))
        col.addSpacing(6)
        col.addWidget(PosterTitle(("ШАГАЙ", "НААДАН"), 96))
        col.addSpacing(8)
        col.addWidget(label("Мори урилдаан — скачки на бараньих\nкосточках. Бросай пять шагай,\n"
                            "каждый «конь» — шаг к финишу.", "h2"))
        col.addSpacing(30)
        for num, text, target, kw, name, tip in (
            ("", "Играть  →", "setup", {"mode": SetupScreen.SOLO}, "primary", "Против компьютера (Enter)"),
            ("01", "Играть вместе", "setup", {"mode": SetupScreen.HOT}, "",
             "2–4 наездника на одном устройстве"),
            ("02", "Шагай харбаха — щелчки", "harbaha", {}, "", "Мини-игра: сбейте кость той же стороны"),
            ("03", "Правила", "rules", {}, "", "Как играть"),
            ("04", "Таблица рекордов", "records", {}, "", "Лучшие наездники и их достижения"),
            ("05", "Об игре и народе", "about", {}, "", "История Шагай наадан"),
        ):
            b = button(f"{num}   {text}" if num else text, name, tip)
            b.setFixedWidth(340)
            b.clicked.connect(lambda _=False, t=target, k=kw: self.navigate.emit(t, dict(k)))
            col.addWidget(b)
            col.addSpacing(16 if name else 10)
        row = QHBoxLayout()
        self.sound_btn = button("Звук: вкл", "flat", "Включить / выключить звук")
        self.sound_btn.clicked.connect(self.toggle_sound)
        self.music_btn = button("", "flat", "Фоновая мелодия в духе морин хуура")
        self.music_btn.clicked.connect(self.toggle_music)
        try:
            music = QSettings("ShagaiNaadan", "game").value("music", True, type=bool)
        except Exception:
            music = True
        self.sounds.set_music(music)
        self._music_text()
        quit_b = button("Выход", "flat")
        quit_b.clicked.connect(lambda: self.window().close())
        row.addWidget(self.sound_btn)
        row.addSpacing(24)
        row.addWidget(self.music_btn)
        row.addSpacing(24)
        row.addWidget(quit_b)
        row.addStretch()
        col.addSpacing(6)
        col.addLayout(row)
        col.addStretch(1)
        split.addLayout(col)
        split.addWidget(FloatingBones(), 1)
        o.addLayout(split)
        QShortcut(QKeySequence(Qt.Key_Return), self,
                  activated=lambda: self.navigate.emit("setup", {"mode": SetupScreen.SOLO}))

    def _music_text(self):
        self.music_btn.setText("Музыка: вкл" if self.sounds.music_on else "Музыка: выкл")

    def toggle_music(self):
        self.sounds.set_music(not self.sounds.music_on)
        try:
            QSettings("ShagaiNaadan", "game").setValue("music", self.sounds.music_on)
        except Exception:
            pass
        self._music_text()

    def toggle_sound(self):
        self.sounds.enabled = not self.sounds.enabled
        self.sound_btn.setText("Звук: вкл" if self.sounds.enabled else "Звук: выкл")


class TextScreen(Screen):
    def __init__(self, title, subtitle, html, with_play=True):
        super().__init__(title, subtitle)
        tb = QTextBrowser()
        tb.setOpenExternalLinks(True)
        tb.setHtml(html)
        self.outer.addWidget(tb, 1)
        if with_play:
            b = button("Понятно, играть  →", "primary")
            b.clicked.connect(lambda: self.navigate.emit("setup", {}))
            self.outer.addWidget(b, 0, Qt.AlignHCenter)


MAX_PLAYERS = 4


class NameRow(QWidget):

    def __init__(self, idx: int, on_remove, on_enter, on_change):
        super().__init__()
        h = QHBoxLayout(self)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(10)
        self.chip = QLabel()
        self.chip.setFixedSize(14, 40)
        h.addWidget(self.chip)
        self.edit = QLineEdit()
        self.edit.setMaxLength(MAX_NAME_LEN + 10)
        self.edit.returnPressed.connect(on_enter)
        self.edit.textChanged.connect(on_change)
        h.addWidget(self.edit, 1)
        self.remove = button("✕", "flat", "Убрать наездника")
        self.remove.setFixedWidth(32)
        self.remove.clicked.connect(lambda: on_remove(self))
        h.addWidget(self.remove)
        self.set_index(idx)

    def set_index(self, idx: int):
        self.chip.setStyleSheet(f"background: {T.RIDER_COLORS[idx]}; border: 2px solid {T.INK};"
                                " border-radius: 3px;")
        self.edit.setPlaceholderText(("Например: Баир", "Например: Сэсэг", "Например: Жаргал",
                                      "Например: Аюна")[idx])

    def set_invalid(self, bad: bool):
        self.edit.setProperty("invalid", bad)
        self.edit.style().unpolish(self.edit)
        self.edit.style().polish(self.edit)


class SetupScreen(Screen):
    SOLO, HOT = 0, 1

    def __init__(self):
        super().__init__("Новый заезд", "Играйте против компьютера или вместе на одном устройстве")
        o = self.outer
        o.addStretch(1)
        card = QFrame()
        card.setObjectName("card")
        card.setMaximumWidth(580)
        c = QVBoxLayout(card)
        c.setContentsMargins(34, 26, 34, 26)
        c.setSpacing(10)

        mode = QHBoxLayout()
        self.mode = QButtonGroup(self)
        for k, text, tip in ((self.SOLO, "Против компьютера", "Один наездник и соперники-компьютеры"),
                             (self.HOT, "Вместе на одном устройстве",
                              "2–4 наездника ходят по очереди, передавая устройство")):
            b = button(text, "seg", tip)
            b.setCheckable(True)
            self.mode.addButton(b, k)
            mode.addWidget(b)
        self.mode.button(self.SOLO).setChecked(True)
        self.mode.idToggled.connect(lambda k, on: on and self._set_mode(k))
        c.addLayout(mode)
        c.addSpacing(6)

        self.names_title = label("Имя наездника", "status")
        c.addWidget(self.names_title)
        self.rows_box = QVBoxLayout()
        self.rows_box.setSpacing(8)
        c.addLayout(self.rows_box)
        self.rows: list[NameRow] = []
        self.add_btn = button("+  Добавить наездника", "flat")
        self.add_btn.clicked.connect(lambda: self._add_row(focus=True))
        c.addWidget(self.add_btn, 0, Qt.AlignLeft)
        self.error = label(" ", "error", wrap=True)
        c.addWidget(self.error)
        self.counter = label(f"0 / {MAX_NAME_LEN}", "hint", align=Qt.AlignRight)
        c.addWidget(self.counter)

        self.opp_box = QWidget()
        ob = QVBoxLayout(self.opp_box)
        ob.setContentsMargins(0, 0, 0, 0)
        ob.setSpacing(10)
        ob.addWidget(label("Соперники-компьютеры", "status"))
        seg = QHBoxLayout()
        self.group = QButtonGroup(self)
        for n in (1, 2, 3):
            b = button(f"{n}", "seg", f"{n} соперник(а), +{n * 10}% к очкам")
            b.setCheckable(True)
            self.group.addButton(b, n)
            seg.addWidget(b)
        self.group.button(2).setChecked(True)
        ob.addLayout(seg)
        ob.addWidget(label("Чем больше соперников, тем сложнее победить и тем больше очков.", "hint", wrap=True))
        c.addWidget(self.opp_box)
        c.addWidget(label("Заезд", "status"))
        lenrow = QHBoxLayout()
        self.length = QButtonGroup(self)
        for n, text, tip in ((TRACK_LENGTH, f"Классический · {TRACK_LENGTH} костей",
                              "Настоящие скачки: пройдите все 12 костей"),
                             (QUICK_LENGTH, f"Быстрый · {QUICK_LENGTH} костей",
                              "Короткий заезд на пару минут (очков вдвое меньше)")):
            b = button(text, "seg", tip)
            b.setCheckable(True)
            self.length.addButton(b, n)
            lenrow.addWidget(b)
        self.length.button(TRACK_LENGTH).setChecked(True)
        c.addLayout(lenrow)
        self.hot_hint = label("Ходите по очереди: игра подскажет, кому передать устройство. "
                              "Результат каждого попадёт в таблицу рекордов.", "hint", wrap=True)
        c.addWidget(self.hot_hint)
        c.addSpacing(8)
        self.go = button("На старт  →", "primary")
        self.go.clicked.connect(self.start)
        c.addWidget(self.go)
        row = QHBoxLayout()
        row.addStretch()
        row.addWidget(card, 1)
        row.addStretch()
        o.addLayout(row)
        o.addStretch(2)
        self._add_row()
        self._set_mode(self.SOLO)

    def _add_row(self, focus=False):
        if len(self.rows) >= MAX_PLAYERS:
            return
        r = NameRow(len(self.rows), self._remove_row, self.start, self._live_check)
        self.rows.append(r)
        self.rows_box.addWidget(r)
        self._refresh_rows()
        if focus:
            r.edit.setFocus()

    def _remove_row(self, r: NameRow):
        if len(self.rows) <= 2:
            return
        self.rows.remove(r)
        r.setParent(None)
        r.deleteLater()
        for i, x in enumerate(self.rows):
            x.set_index(i)
        self._refresh_rows()
        self._live_check()

    def _refresh_rows(self):
        hot = self.mode.checkedId() == self.HOT
        for r in self.rows:
            r.remove.setVisible(hot and len(self.rows) > 2)
            r.chip.setVisible(hot)
        self.add_btn.setVisible(hot and len(self.rows) < MAX_PLAYERS)

    def _set_mode(self, k: int):
        hot = k == self.HOT
        if hot:
            while len(self.rows) < 2:
                self._add_row()
        else:
            for r in self.rows[1:]:
                r.setParent(None)
                r.deleteLater()
            self.rows = self.rows[:1]
        self.names_title.setText(f"Наездники (2–{MAX_PLAYERS})" if hot else "Имя наездника")
        self.opp_box.setVisible(not hot)
        self.hot_hint.setVisible(hot)
        self.counter.setVisible(not hot)
        self.go.setText("Все на старт  →" if hot else "На старт  →")
        self.error.setText(" ")
        for r in self.rows:
            r.set_invalid(False)
        self._refresh_rows()
        self.rows[0].edit.setFocus()

    def on_show(self, mode: int | None = None, **kw):
        if mode is not None:
            self.mode.button(mode).setChecked(True)
        self.error.setText(" ")
        for r in self.rows:
            r.set_invalid(False)
        self.rows[0].edit.setFocus()
        self.rows[0].edit.selectAll()

    def _check(self) -> tuple[list[str], int, str]:
        names: list[str] = []
        multi = len(self.rows) > 1
        for i, r in enumerate(self.rows):
            who = f"Наездник {i + 1}: " if multi else ""
            try:
                name = validate_name(r.edit.text())
            except NameError_ as e:
                return names, i, who + str(e)
            if name.casefold() in (n.casefold() for n in names):
                return names, i, who + "такое имя уже есть — придумайте другое, чтобы не перепутать коней."
            names.append(name)
        return names, -1, ""

    def _live_check(self, *_):
        n = len(" ".join(self.rows[0].edit.text().split())) if self.rows else 0
        self.counter.setText(f"{n} / {MAX_NAME_LEN}")
        self.counter.setStyleSheet(f"color: {T.RED};" if n > MAX_NAME_LEN else "")
        if self.error.text().strip():
            _, bad, msg = self._check()
            self.error.setText(msg or " ")
            for i, r in enumerate(self.rows):
                r.set_invalid(i == bad)

    def start(self):
        names, bad, msg = self._check()
        for i, r in enumerate(self.rows):
            r.set_invalid(i == bad)
        if bad >= 0:
            self.error.setText(msg)
            self._shake(self.rows[bad].edit)
            self.rows[bad].edit.setFocus()
            return
        for r, n in zip(self.rows, names):
            r.edit.setText(n)
        hot = self.mode.checkedId() == self.HOT
        self.navigate.emit("game", {"names": names, "opponents": 0 if hot else self.group.checkedId(),
                                    "track": self.length.checkedId()})

    def _shake(self, w):
        a = QPropertyAnimation(w, b"pos", self)
        p = w.pos()
        a.setDuration(320)
        for i, dx in enumerate((0, -10, 10, -7, 7, -3, 0)):
            a.setKeyValueAt(i / 6, p + type(p)(dx, 0))
        lay = w.parentWidget().layout()
        a.finished.connect(lambda: (lay.invalidate(), lay.activate()))
        a.start()
        self._shake_anim = a


class ResultOverlay(QWidget):
    action = Signal(str)

    def __init__(self, parent):
        super().__init__(parent)
        self.hide()
        lay = QVBoxLayout(self)
        lay.addStretch()
        self.card = QFrame()
        self.card.setObjectName("card")
        self.card.setFixedWidth(560)
        c = QVBoxLayout(self.card)
        c.setContentsMargins(30, 26, 30, 26)
        c.setSpacing(10)
        self.title = label("", "h1", align=Qt.AlignCenter)
        self.title.setStyleSheet("font-size: 44px;")
        self.body = label("", wrap=True, align=Qt.AlignCenter)
        self.body.setStyleSheet("font-size: 17px;")
        self.score = label("", align=Qt.AlignCenter)
        self.score.setStyleSheet(f"font-family: '{T.TITLE_FONT}'; font-size: 64px; color: {T.RED};")
        for w in (self.title, self.score, self.body):
            c.addWidget(w)
        self.cert_btn = button("Получить сертификат победителя", "", "Сохранить именной сертификат (PNG или PDF)")
        self.cert_btn.setStyleSheet(f"text-align: center; background: {T.OCHRE};")
        self.cert_btn.clicked.connect(lambda: self.cert and certificate.ask_and_save(self, self.cert))
        c.addWidget(self.cert_btn)
        self.cert = None
        row = QHBoxLayout()
        for text, act, name in (("Ещё заезд", "again", "primary"), ("Рекорды", "records", ""),
                                ("Меню", "menu", "")):
            b = button(text, name)
            b.setStyleSheet("text-align: center;")
            b.clicked.connect(lambda _=False, a=act: self.action.emit(a))
            row.addWidget(b)
        c.addLayout(row)
        h = QHBoxLayout()
        h.addStretch()
        h.addWidget(self.card)
        h.addStretch()
        lay.addLayout(h)
        lay.addStretch()

    def paintEvent(self, _):
        QPainter(self).fillRect(self.rect(), QColor(30, 27, 24, 170))

    def show_result(self, title, score, body, cert=None):
        self.cert = cert
        self.cert_btn.setVisible(cert is not None)
        if cert is not None:
            self.cert_btn.setText(f"Получить сертификат: {cert.name}")
        self.title.setText(title)
        self.score.setVisible(score is not None)
        self.score.setText(points_txt(score))
        self.body.setText(body)
        self.setGeometry(self.parentWidget().rect())
        eff = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(eff)
        self.show()
        self.raise_()
        a = QPropertyAnimation(eff, b"opacity", self)
        a.setStartValue(0.0)
        a.setEndValue(1.0)
        a.setDuration(450)
        a.start()
        self._a = a


class QuizOverlay(QWidget):
    done = Signal(bool)

    def __init__(self, parent):
        super().__init__(parent)
        self.hide()
        self.correct = False
        lay = QVBoxLayout(self)
        lay.addStretch()
        card = QFrame()
        card.setObjectName("card")
        card.setFixedWidth(600)
        c = QVBoxLayout(card)
        c.setContentsMargins(32, 26, 32, 26)
        c.setSpacing(10)
        self.head = label("", "over")
        c.addWidget(self.head)
        self.question = label("", "status", wrap=True)
        self.question.setStyleSheet("font-size: 26px;")
        c.addWidget(self.question)
        c.addSpacing(4)
        self.opts: list[QPushButton] = []
        for k in range(3):
            b = button("")
            b.clicked.connect(lambda _=False, k=k: self._answer(k))
            c.addWidget(b)
            self.opts.append(b)
        self.note = label("", wrap=True)
        self.note.setStyleSheet("font-size: 16px;")
        c.addWidget(self.note)
        self.next_btn = button("Дальше  →", "primary")
        self.next_btn.clicked.connect(self._close)
        c.addWidget(self.next_btn)
        h = QHBoxLayout()
        h.addStretch()
        h.addWidget(card)
        h.addStretch()
        lay.addLayout(h)
        lay.addStretch()

    def paintEvent(self, _):
        QPainter(self).fillRect(self.rect(), QColor(30, 27, 24, 150))

    def ask(self, q, title="ВОПРОС ЗНАТОКА"):
        self.q, self.options, self.right, self.expl = q
        self.head.setText(f"{title}  ·  +{QUIZ_BONUS} ОЧКОВ")
        self.question.setText(self.q)
        for b, text in zip(self.opts, self.options):
            b.setText(text)
            b.setStyleSheet("")
            b.setEnabled(True)
        self.note.setText("")
        self.next_btn.hide()
        self.setGeometry(self.parentWidget().rect())
        self.show()
        self.raise_()
        self.opts[0].setFocus()

    def _answer(self, k):
        self.correct = k == self.right
        ok = f"background: {T.GREEN}; color: {T.PAPER_LIGHT};"
        self.opts[self.right].setStyleSheet(ok)
        if not self.correct:
            self.opts[k].setStyleSheet(f"background: {T.RED}; color: {T.PAPER_LIGHT};")
        for b in self.opts:
            b.setEnabled(b is self.opts[k] or b is self.opts[self.right])
            b.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.note.setText(("Верно! " if self.correct else "Не угадали. ") + self.expl)
        self.next_btn.show()
        self.next_btn.setFocus()

    def _close(self):
        for b in self.opts:
            b.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        self.hide()
        self.done.emit(self.correct)


class FactCard(QFrame):

    def __init__(self):
        super().__init__()
        self.setObjectName("card")
        self.setFixedWidth(290)
        c = QVBoxLayout(self)
        c.setContentsMargins(20, 18, 20, 16)
        c.setSpacing(8)
        c.addWidget(label("ЗНАЕТЕ ЛИ ВЫ?", "over"))
        self.text = label("", wrap=True, align=Qt.AlignTop | Qt.AlignLeft)
        self.text.setStyleSheet(f"font-family: '{T.BODY_FONT}'; font-size: 15px;")
        c.addWidget(self.text, 1)
        self.counter = label("", "hint")
        c.addWidget(self.counter)
        self.order = list(range(len(texts.FACTS)))
        random.shuffle(self.order)
        self.k = -1

    def show_next(self):
        self.k = (self.k + 1) % len(self.order)
        self.text.setText(texts.FACTS[self.order[self.k]])
        self.counter.setText(f"Факт {self.k + 1} из {len(self.order)}")
        eff = QGraphicsOpacityEffect(self.text)
        self.text.setGraphicsEffect(eff)
        a = QPropertyAnimation(eff, b"opacity", self)
        a.setStartValue(0.0)
        a.setEndValue(1.0)
        a.setDuration(400)
        a.finished.connect(lambda: self.text.setGraphicsEffect(None))
        a.start()
        self._a = a


THROW_TEXT = "Бросить шагай  →"
QUIZ_AT = (2, 5, 8)


class GameScreen(Screen):
    finished = Signal(dict)
    achieve = Signal(str, list)

    def __init__(self, sounds):
        super().__init__("Мори урилдаан", "Каждый «конь» в броске — шаг вперёд. Пройдите 12 костей первым!",
                         back=False)
        self.sounds = sounds
        self.race: Race | None = None
        self.human: Rider | None = None
        self.busy = False
        self.aborted = False
        self._holding = False
        self.rng = random.Random()

        top = QHBoxLayout()
        quit_b = button("←  Сдаться", "flat", "Выйти в меню (результат не сохранится)")
        quit_b.setFocusPolicy(Qt.NoFocus)
        quit_b.clicked.connect(self.give_up)
        top.addWidget(quit_b)
        top.addStretch()
        help_b = button("?  Подсказки", "flat", "Показать, что где на экране")
        help_b.setFocusPolicy(Qt.NoFocus)
        help_b.clicked.connect(self.start_tour)
        top.addWidget(help_b)
        top.addSpacing(18)
        self.fast_btn = button("Быстро: выкл", "flat", "Ускорить анимацию")
        self.fast_btn.setFocusPolicy(Qt.NoFocus)
        self.fast_btn.setCheckable(True)
        self.fast_btn.toggled.connect(self._fast)
        top.addWidget(self.fast_btn)
        self.outer.insertLayout(0, top)

        self.track = TrackWidget()
        self.track.moved.connect(self._after_move)
        self.track.hop.connect(lambda: self.sounds.play("hoof"))
        self.outer.addWidget(self.track, 3)
        mid = QHBoxLayout()
        mid.setSpacing(18)
        self.dice = DiceWidget()
        self.dice.rolled.connect(self._after_roll)
        mid.addWidget(self.dice, 1)
        self.facts = FactCard()
        mid.addWidget(self.facts)
        self.outer.addLayout(mid, 2)

        bottom = QHBoxLayout()
        info = QVBoxLayout()
        self.status = label("", "status")
        self.log = label("", "hint", wrap=True)
        self.log.setStyleSheet("font-size: 15px;")
        info.addWidget(self.status)
        info.addWidget(self.log)
        bottom.addLayout(info, 1)
        self.stats = label("", "h2", align=Qt.AlignRight | Qt.AlignVCenter)
        bottom.addWidget(self.stats)
        bottom.addSpacing(12)
        self.throw_btn = button(THROW_TEXT, "primary",
                                "Зажмите (мышью или пробелом), потрясите кости и отпустите. Enter — сразу бросок")
        self.throw_btn.setMinimumWidth(270)
        self.throw_btn.pressed.connect(self._press)
        self.throw_btn.released.connect(self._release)
        bottom.addWidget(self.throw_btn)
        self.outer.addLayout(bottom)

        QShortcut(QKeySequence(Qt.Key_Return), self, activated=self._quick_throw)
        QShortcut(QKeySequence(Qt.Key_Escape), self, activated=self.give_up)

        self.quiz_box = QuizOverlay(self)
        self.quiz_box.done.connect(self._after_quiz)
        self.overlay = ResultOverlay(self)
        self.overlay.action.connect(self._overlay_action)
        self.rain = HadakRain(self)
        self.tour = Tour(self)
        self.tour.finished.connect(lambda: self.throw_btn.setFocus())
        self.last_setup: dict = {}

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self.overlay.setGeometry(self.rect())
        self.quiz_box.setGeometry(self.rect())
        self.rain.setGeometry(self.rect())
        self.tour.setGeometry(self.rect())

    def _fast(self, on):
        self.track.fast = self.dice.fast = on
        self.fast_btn.setText("Быстро: вкл" if on else "Быстро: выкл")

    def on_show(self, names: list[str] | None = None, opponents: int = 2, name: str = "",
                track: int = TRACK_LENGTH, **_):
        names = list(names or [name])
        self.last_setup = {"names": names, "opponents": opponents, "track": track}
        self.overlay.hide()
        self.quiz_box.hide()
        self.rain.stop()
        self.dice.reset()
        self.track.stop()
        self.humans = [Rider(n, is_human=True) for n in names]
        self.human = self.humans[0]
        self.hot = len(self.humans) > 1
        riders = self.humans + [Rider(n) for n in AI_NAMES[:opponents]]
        self.race = Race(riders, rng=self.rng, length=track)
        self.track.set_riders(riders, track)
        self.busy = False
        self.aborted = False
        self._holding = False
        self.quiz = {id(h): [0, 0] for h in self.humans}
        self._questions = self.rng.sample(texts.QUIZ, min(len(texts.QUIZ), len(QUIZ_AT) * len(self.humans)))
        self.log.setText("Зажмите кнопку или пробел — кости затрясутся в горсти. Отпустите, чтобы бросить!")
        self.tour.hide()
        self._next()
        if not tour_done():
            QTimer.singleShot(450, self.start_tour)

    def start_tour(self):
        if self.overlay.isVisible() or self.quiz_box.isVisible() or self.race is None:
            return
        n = self.race.length
        self.tour.start([
            (self.track, "Это ипподром",
             f"Ряд из {n} шагай — дорожка для скачек. Ваш конь стоит у первой кости, "
             f"его дорожка подсвечена. Пройдите все {n} костей первым!"),
            (self.dice, "Войлок для броска",
             "Сюда падают пять шагай. Кость, вставшая боком, — «морин», конь. "
             "Сколько коней выпало, на столько костей скачет ваш конь."),
            (self.throw_btn, "Как бросать",
             "Зажмите кнопку или пробел — кости затрясутся в горсти. Отпустите — полетят! "
             "Enter бросает сразу, без тряски."),
            (self.facts, "Знаете ли вы?",
             "На каждом ходу здесь новый факт о бурятах. После 2-го, 5-го и 8-го броска будет "
             "вопрос знатока — за верный ответ +50 очков."),
        ])

    def _can_throw(self) -> bool:
        return (not self.busy and self.race is not None and not self.race.over
                and self.race.current_rider.is_human and not self.quiz_box.isVisible()
                and not self.tour.isVisible()
                and not self.overlay.isVisible())

    def _press(self):
        if self._can_throw() and self.dice.start_shake():
            self.busy = self._holding = True
            self.throw_btn.setText("Трясём… отпустите!")

    def _release(self):
        if not self._holding:
            return
        self._holding = False
        self.throw_btn.setText(THROW_TEXT)
        self.throw_btn.setEnabled(False)
        self._dice = throw(self.rng)
        self.sounds.play("throw")
        self.dice.release(self._dice)

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Space and not e.isAutoRepeat():
            self._press()
        else:
            super().keyPressEvent(e)

    def keyReleaseEvent(self, e):
        if e.key() == Qt.Key_Space and not e.isAutoRepeat():
            self._release()
        else:
            super().keyReleaseEvent(e)

    def _quick_throw(self):
        if self._can_throw():
            self._throw()

    def _throw(self):
        self.busy = True
        self.throw_btn.setEnabled(False)
        self._dice = throw(self.rng)
        self.sounds.play("throw")
        self.dice.roll(self._dice, quick=not self.race.current_rider.is_human)

    @staticmethod
    def _leader(riders):
        top = sorted(riders, key=lambda r: -r.position)
        return top[0] if len(top) == 1 or top[0].position > top[1].position else None

    def _after_roll(self):
        if self.aborted or self.race.over:
            return
        rider = self.race.current_rider
        idx = self.race.riders.index(rider)
        was_leader = self._leader(self.race.riders)
        t = self.race.play_turn(self._dice)
        n = t.steps
        if rider.is_human:
            codes = ACH.for_throw(n)
            if codes:
                self.achieve.emit(rider.name, codes)
        if n == 0:
            self.log.setText(self.rng.choice((
                f"{rider.name}: ни одного коня — стоит на месте.",
                f"{rider.name}: конь заупрямился и не двигается.",
                f"{rider.name}: кони отдыхают — ни шагу вперёд.",
            )))
        else:
            head = f"{rider.name}: {n} {horses_word(n)} — вперёд на {n}!"
            if rider.finished:
                tail = "Финиш!"
            elif self._leader(self.race.riders) is rider and was_leader is not rider:
                tail = f"{rider.name} выходит вперёд!"
            elif n >= 3:
                tail = "Вот это бросок!"
            elif self.race.finish - rider.position <= 2:
                tail = "До финиша рукой подать!"
            else:
                tail = ""
            self.log.setText(f"{head} {tail}".strip())
        self.track.animate(idx, t.new_position)
        self._update_stats()

    def _after_move(self):
        if self.aborted:
            return
        self.busy = False
        if self.race.over:
            self._finish()
            return
        mover = self.race.riders[self.race.current - 1]
        if mover.is_human and mover.throws in QUIZ_AT and self._questions:
            self.busy = True
            q = self._questions.pop()
            self.quiz[id(mover)][1] += 1
            self._quiz_for = mover
            title = f"ВОПРОС ДЛЯ: {mover.name.upper()}" if self.hot else "ВОПРОС ЗНАТОКА"
            QTimer.singleShot(350, lambda: (not self.aborted) and self.quiz_box.ask(q, title))
            return
        self._next()

    def _after_quiz(self, correct: bool):
        if correct:
            self.quiz[id(self._quiz_for)][0] += 1
        self.busy = False
        self._next()

    def _next(self):
        r = self.race.current_rider
        self.track.active = self.race.riders.index(r)
        near = self.race.finish - r.position <= 2
        self.track.set_drama(self.track.active if near else -1)
        if near:
            self.log.setText(f"{r.name} в шаге от финиша — решающий бросок!")
        self.track.update()
        self._update_stats()
        if r.is_human:
            self.human = r
            self._update_stats()
            if self.hot:
                col = T.RIDER_COLORS[self.race.riders.index(r)]
                self.status.setText(f'<span style="color:{col}">■</span> Ходит {r.name}! '
                                    f'<span style="font-size:15px; color:{T.INK_SOFT}">Передайте устройство</span>')
            else:
                self.status.setText(f"Ваш ход, {r.name}!")
            self.throw_btn.setEnabled(True)
            self.throw_btn.setFocus()
            self.facts.show_next()
        else:
            self.status.setText(f"Бросает {r.name}…")
            self.throw_btn.setEnabled(False)
            self.busy = True
            QTimer.singleShot(200 if self.track.fast else 450, self._ai_throw)

    def _ai_throw(self):
        if self.race and not self.race.over and not self.aborted:
            self._throw()

    def _update_stats(self):
        h = self.human
        ok, asked = self.quiz[id(h)]
        who = f"{h.name}:   " if self.hot else ""
        self.stats.setText(f"{who}Бросков: {h.throws}   ·   Пройдено: {h.progress} / {self.race.length}   ·   "
                           f"Знания: {ok} / {asked}")

    def _save(self, h: Rider) -> tuple[int, int | None, str]:
        race = self.race
        ok, _ = self.quiz[id(h)]
        score = calc_score(race.winner is h, h.progress, h.throws, len(race.riders) - 1, ok, race.length)
        self.last_record_id, self.last_rank_text = None, ""
        self.finished.emit({"name": h.name, "score": score, "throws": h.throws,
                            "place": race.place_of(h), "riders": len(race.riders),
                            "won": race.winner is h, "quiz_ok": ok, "quiz_asked": self.quiz[id(h)][1],
                            "hotseat": self.hot, "track": race.length})
        return score, self.last_record_id, self.last_rank_text

    def _celebrate(self, then) -> None:
        race = self.race
        human_won = race.winner.is_human
        self.track.set_drama(-1)
        self.track.celebrate(race.riders.index(race.winner))
        self.throw_btn.setEnabled(False)
        self.status.setText(f"Финиш! Первым пришёл {race.winner.name}!")
        if human_won:
            self.sounds.play("fanfare")
            self.rain.start()
        else:
            self.sounds.play("lose")

        def show():
            if self.aborted or self.race is not race:
                return
            then()
            self.rain.raise_()
        QTimer.singleShot(2200 if human_won else 1300, show)

    def _finish(self):
        race = self.race
        win = race.winner
        if not self.hot:
            h = self.human = self.humans[0]
            won = win is h
            score, _, extra = self._save(h)
            if won:
                title = "Победа!"
                body = f"Ваш конь первым пришёл к финишу за {throws_txt(h.throws)}."
            else:
                title = f"{race.place_of(h)}-е место"
                body = (f"Первым пришёл {win.name}. Вы прошли {h.progress} из {race.length} костей "
                        f"за {throws_txt(h.throws)}.")
            ok, asked = self.quiz[id(h)]
            if asked:
                body += f"\nВопросы знатока: {ok} из {asked} (+{ok * QUIZ_BONUS} очков)."
            cert = certificate.CertData(h.name, score, h.throws, len(race.riders), length=race.length) if won else None
            full = body + ("\n" + extra if extra else "")
            self._celebrate(lambda: self.overlay.show_result(title, score, full, cert))
            return

        results = {id(h): self._save(h) for h in self.humans}
        best = results.get(id(win)) or max(results.values(), key=lambda r: r[0])
        self.last_record_id = best[1]
        lines = []
        for place, r in enumerate(race.standings(), 1):
            if id(r) in results:
                ok, asked = self.quiz[id(r)]
                lines.append(f"{place}. {r.name} — {points_txt(results[id(r)][0])} · {throws_txt(r.throws)} · "
                             f"знания {ok}/{asked}")
            else:
                lines.append(f"{place}. {r.name} — {r.progress} из {race.length} костей")
        body = "\n".join(lines) + "\nВсе результаты сохранены в таблице рекордов."
        score = results[id(win)][0] if id(win) in results else None
        cert = (certificate.CertData(win.name, score, win.throws, len(race.riders), hotseat=True, length=race.length)
                if score is not None else None)
        self._celebrate(lambda: self.overlay.show_result(f"Победил {win.name}!", score, body, cert))

    def give_up(self):
        if self.tour.isVisible():
            self.tour.close_tour()
            return
        if self.overlay.isVisible():
            self.navigate.emit("menu", {})
            return
        if self.race and not self.race.over and any(h.throws for h in self.humans):
            if not ask(self, "Сдаться?", "Выйти в меню? Результат этого заезда не сохранится.",
                       "Сдаться и выйти", "Продолжить скачки"):
                return
        self.aborted = True
        self.quiz_box.hide()
        self.rain.stop()
        self.dice.reset()
        self.track.stop()
        self.navigate.emit("menu", {})

    def _overlay_action(self, act):
        if act == "again":
            self.on_show(**self.last_setup)
        elif act == "records":
            self.navigate.emit("records", {"highlight": self.last_record_id})
        else:
            self.navigate.emit("menu", {})

    last_record_id = None
    last_rank_text = ""
    quiz: dict = {}
    hot = False


class NumItem(QTableWidgetItem):

    def __init__(self, value: int, text: str | None = None):
        super().__init__(text if text is not None else str(value))
        self.value = value
        self.setTextAlignment(Qt.AlignCenter)

    def __lt__(self, other):
        return self.value < getattr(other, "value", 0)


class RecordsScreen(Screen):
    COLS = ["Место", "Наездник", "Очки", "Бросков", "Место в заезде", "Дата"]
    PODIUM = {1: T.RED, 2: T.BLUE, 3: T.INK}

    def __init__(self, db: RecordsDB):
        super().__init__("Таблица рекордов", "Лучшие наездники Шагай наадан")
        self.db = db
        self.highlight = None
        o = self.outer

        bar = QHBoxLayout()
        self.filter = QLineEdit()
        self.filter.setPlaceholderText("Фильтр по имени игрока…")
        self.filter.setClearButtonEnabled(True)
        self.filter.textChanged.connect(lambda: self._debounce.start())
        bar.addWidget(self.filter, 1)
        self.count = label("", "hint")
        bar.addWidget(self.count)
        o.addLayout(bar)
        self.filter_err = label("", "error")
        self.filter_err.hide()
        o.addWidget(self.filter_err)

        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(120)
        self._debounce.timeout.connect(self.refresh)

        self.table = QTableWidget(0, len(self.COLS))
        self.table.setHorizontalHeaderLabels(self.COLS)
        self.table.verticalHeader().hide()
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSortingEnabled(True)
        self.table.setShowGrid(False)
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(1, QHeaderView.Stretch)
        hh.setToolTip("Нажмите на заголовок, чтобы отсортировать")
        self.table.verticalHeader().setDefaultSectionSize(40)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._menu)
        self.table.doubleClicked.connect(lambda _: self.rename())
        self.table.itemSelectionChanged.connect(self._sel_changed)
        o.addWidget(self.table, 1)

        self.empty = label("", "h2", align=Qt.AlignCenter)
        self.empty.hide()
        o.addWidget(self.empty, 1)

        row = QHBoxLayout()
        self.ren_btn = button("Переименовать", tip="Изменить имя в записи (двойной щелчок)")
        self.ren_btn.clicked.connect(self.rename)
        self.del_btn = button("Удалить", tip="Удалить выбранную запись (Delete)")
        self.del_btn.clicked.connect(self.delete)
        self.card_btn = button("Карточка игрока", tip="Статистика, график очков и достижения игрока")
        self.card_btn.clicked.connect(self.show_card)
        exp = button("Экспорт CSV", tip="Сохранить таблицу (с учётом фильтра) в файл для Excel")
        exp.clicked.connect(self.export)
        clr = button("Очистить всё", "flat")
        clr.clicked.connect(self.clear_all)
        play = button("Играть  →", "primary")
        play.clicked.connect(lambda: self.navigate.emit("setup", {}))
        for w in (self.card_btn, self.ren_btn, self.del_btn, exp):
            row.addWidget(w)
        row.addWidget(clr)
        row.addStretch()
        row.addWidget(play)
        o.addLayout(row)
        QShortcut(QKeySequence(Qt.Key_Delete), self.table, activated=self.delete)
        QShortcut(QKeySequence("Ctrl+F"), self, activated=self.filter.setFocus)

    def on_show(self, highlight=None, **_):
        self.highlight = highlight
        self.refresh()
        if highlight is None:
            self.filter.setFocus()

    def _sel_changed(self):
        has = self._selected_id() is not None
        self.card_btn.setEnabled(has)
        self.ren_btn.setEnabled(has)
        self.del_btn.setEnabled(has)

    def refresh(self):
        text = self.filter.text()
        if len(text) > 40:
            self.filter_err.setText("Слишком длинный запрос для поиска (максимум 40 символов).")
            self.filter_err.show()
            return
        self.filter_err.hide()
        try:
            ranks = {r.id: i for i, r in enumerate(self.db.list(), 1)}
            rows = self.db.list(text)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка базы данных", f"Не удалось прочитать рекорды:\n{e}")
            return
        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(rows))
        hl_item = None
        for i, r in enumerate(rows):
            rank = ranks[r.id]
            items = [
                NumItem(rank),
                QTableWidgetItem(r.name),
                NumItem(r.score),
                NumItem(r.throws),
                NumItem(r.place, f"{r.place} из {r.riders}"),
                QTableWidgetItem(r.created_at),
            ]
            items[0].setData(Qt.UserRole, r.id)
            items[5].setTextAlignment(Qt.AlignCenter)
            f = QFont()
            f.setBold(True)
            items[2].setFont(f)
            items[2].setForeground(QColor(T.RED))
            if rank in self.PODIUM:
                items[0].setFont(f)
                items[0].setForeground(QColor(self.PODIUM[rank]))
            if r.id == self.highlight:
                hl_item = items[0]
                for it in items:
                    it.setBackground(QColor(T.RED))
                    it.setForeground(QColor(T.PAPER_LIGHT))
                items[1].setText(r.name + "   ← вы")
            for c, it in enumerate(items):
                self.table.setItem(i, c, it)
        self.table.setSortingEnabled(True)
        self.table.sortItems(0, Qt.AscendingOrder)
        total = len(ranks)
        self.count.setText(f"Показано: {len(rows)} из {total}")
        if not rows:
            self.empty.setText("Пока нет ни одного заезда — сыграйте первым!" if total == 0
                               else f"Игроков с именем «{text.strip()}» не найдено")
        self.empty.setVisible(not rows)
        self.table.setVisible(bool(rows))
        if hl_item is not None:
            self.table.selectRow(hl_item.row())
            self.table.scrollToItem(hl_item)
        self._sel_changed()

    def _selected_id(self):
        rows = self.table.selectionModel().selectedRows() if self.table.selectionModel() else []
        if not rows:
            return None
        return self.table.item(rows[0].row(), 0).data(Qt.UserRole)

    def _menu(self, pos):
        if self.table.itemAt(pos) is None:
            return
        self.table.selectRow(self.table.itemAt(pos).row())
        m = QMenu(self)
        m.addAction("Карточка игрока", self.show_card)
        m.addAction("Переименовать", self.rename)
        m.addAction("Показать все заезды игрока", self._filter_by_selected)
        m.addSeparator()
        m.addAction("Удалить", self.delete)
        m.exec(self.table.viewport().mapToGlobal(pos))

    def show_card(self):
        if self._selected_id() is None:
            QMessageBox.information(self, "Карточка игрока", "Сначала выберите запись в таблице.")
            return
        name = self.table.item(self.table.currentRow(), 1).text().replace("   ← вы", "")
        PlayerCard(self, self.db, name).exec()

    def _filter_by_selected(self):
        row = self.table.currentRow()
        if row >= 0:
            self.filter.setText(self.table.item(row, 1).text().replace("   ← вы", ""))

    def rename(self):
        rid = self._selected_id()
        if rid is None:
            QMessageBox.information(self, "Переименовать", "Сначала выберите запись в таблице.")
            return
        cur = self.table.item(self.table.currentRow(), 1).text().replace("   ← вы", "")
        while True:
            new, ok = QInputDialog.getText(self, "Переименовать", "Новое имя наездника:", text=cur)
            if not ok:
                return
            try:
                self.db.rename(rid, new)
                break
            except NameError_ as e:
                QMessageBox.warning(self, "Некорректное имя", str(e))
                cur = new
            except KeyError as e:
                QMessageBox.warning(self, "Ошибка", str(e))
                return
        self.refresh()

    def delete(self):
        rid = self._selected_id()
        if rid is None:
            QMessageBox.information(self, "Удалить", "Сначала выберите запись в таблице.")
            return
        name = self.table.item(self.table.currentRow(), 1).text().replace("   ← вы", "")
        if not ask(self, "Удалить запись", f"Удалить результат игрока «{name}»?", "Удалить", "Оставить",
                   danger=True):
            return
        try:
            self.db.delete(rid)
        except KeyError as e:
            QMessageBox.warning(self, "Ошибка", str(e))
        self.refresh()

    def clear_all(self):
        if not self.db.list():
            return
        if ask(self, "Очистить таблицу", "Удалить ВСЕ рекорды? Это нельзя отменить.",
               "Удалить всё", "Отмена", danger=True):
            self.db.clear()
            self.refresh()

    def export(self):
        path, _ = QFileDialog.getSaveFileName(self, "Экспорт рекордов", "рекорды_шагай.csv", "CSV (*.csv)")
        if not path:
            return
        try:
            n = self.db.export_csv(path, self.filter.text())
            QMessageBox.information(self, "Готово", f"Сохранено записей: {n}\n{path}")
        except OSError as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить файл:\n{e}")
