from __future__ import annotations

import sqlite3

from PySide6.QtCore import QEasingCurve, QPropertyAnimation
from PySide6.QtWidgets import (QGraphicsOpacityEffect, QMainWindow, QMessageBox, QStackedWidget)

from core import achievements as ACH
from core.db import RecordsDB
from core.validation import NameError_
from . import texts
from .art import app_icon
from .effects import AchievementToast
from .harbaha import HarbahaScreen
from .interactive import AboutScreen, RulesScreen
from .screens import GameScreen, MenuScreen, RecordsScreen, SetupScreen, TextScreen
from .sound import Sounds


class MainWindow(QMainWindow):
    def __init__(self, db: RecordsDB):
        super().__init__()
        self.db = db
        self.setWindowTitle("Шагай наадан — Мори урилдаан")
        self.setWindowIcon(app_icon())
        self.setMinimumSize(1000, 700)
        self.sounds = Sounds()

        self.stack = QStackedWidget()
        self.stack.setObjectName("root")
        self.setCentralWidget(self.stack)
        self.game = GameScreen(self.sounds)
        self.game.finished.connect(self.save_result)
        self.game.achieve.connect(self.grant)
        self.harbaha = HarbahaScreen(db, self.sounds)
        self.harbaha.achieve.connect(self.grant)
        self.last_name = ""
        self.screens = {
            "menu": MenuScreen(self.sounds),
            "rules": RulesScreen(self.sounds),
            "about": AboutScreen(),
            "setup": SetupScreen(),
            "game": self.game,
            "records": RecordsScreen(db),
            "harbaha": self.harbaha,
        }
        for s in self.screens.values():
            s.navigate.connect(self.go)
            self.stack.addWidget(s)
        self.toast = AchievementToast(self)
        self.toast.on_show = lambda: self.sounds.play("achieve")
        self.go("menu", {})

    def go(self, name: str, kw: dict):
        w = self.screens[name]
        if name == "harbaha":
            kw = {"name": self.last_name, **kw}
        self.stack.setCurrentWidget(w)
        w.on_show(**kw)
        eff = QGraphicsOpacityEffect(w)
        w.setGraphicsEffect(eff)
        a = QPropertyAnimation(eff, b"opacity", w)
        a.setStartValue(0.0)
        a.setEndValue(1.0)
        a.setDuration(280)
        a.setEasingCurve(QEasingCurve.OutCubic)
        a.finished.connect(lambda: w.setGraphicsEffect(None))  # не тормозим отрисовку после перехода
        a.start()
        self._anim = a

    def save_result(self, r: dict):
        try:
            rid = self.db.add(r["name"], r["score"], r["throws"], r["place"], r["riders"])
        except (NameError_, sqlite3.Error) as e:
            QMessageBox.critical(self, "Ошибка сохранения", f"Не удалось сохранить результат:\n{e}")
            self.game.last_record_id = None
            return
        self.game.last_record_id = rid
        rank = self.db.rank_of(rid)
        self.game.last_rank_text = f"Результат сохранён: {rank}-е место в таблице рекордов из {len(self.db.list())}."
        self.last_name = r["name"]
        self.grant(r["name"], ACH.for_race(r.get("won", False), r["throws"], r.get("quiz_ok", 0),
                                           r.get("quiz_asked", 0), r.get("hotseat", False),
                                           len(self.db.player_records(r["name"])),
                                           classic=r.get("track", 12) == 12))

    def grant(self, name: str, codes: list):
        """Открывает достижения; новые показываются всплывающей карточкой со звоном."""
        for code in codes:
            try:
                fresh = self.db.unlock(name, code)
            except sqlite3.Error:
                return
            if fresh:
                self.toast.push(ACH.BY_CODE[code], name)

    def closeEvent(self, e):
        self.db.close()
        super().closeEvent(e)
