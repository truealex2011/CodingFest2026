import math
import os
import sys
from pathlib import Path

os.environ["SHAGAI_NO_SOUND"] = "1"
os.environ["SHAGAI_NO_TOUR"] = "1"
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
DOCS = ROOT / "docs"

from PySide6.QtCore import QEvent, QPointF, Qt, QTimer
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication

import ui.screens as S
from core.db import RecordsDB
from core.shagai import Side
from ui.certificate import CertData, render
from ui.interactive import FlipCard
from ui.main_window import MainWindow
from ui.profile import PlayerCard
from ui.theme import QSS

app = QApplication(sys.argv)
app.setStyleSheet(QSS)
db = RecordsDB(":memory:")
for name, score, throws, place in (("Баир", 1180, 17, 1), ("Сэсэг", 940, 19, 1), ("Аюна", 610, 22, 2),
                                   ("Николай", 520, 18, 2), ("Николай", 760, 21, 1), ("Жаргал", 380, 24, 3)):
    db.add(name, score, throws, place, 3)
for code in ("first_horse", "herd", "winner", "scholar"):
    db.unlock("Николай", code)
db.add_harbaha("Аюна", 1450, 5)
w = MainWindow(db)
w.resize(1180, 780)
w.show()
g = w.game
DOCS.mkdir(exist_ok=True)


def snap(name, widget=None):
    (widget or w).grab().save(str(DOCS / f"{name}.png"))
    print("docs/" + name + ".png")


def click(card):
    e = QMouseEvent(QEvent.MouseButtonPress, QPointF(10, 10), QPointF(10, 10), Qt.LeftButton, Qt.LeftButton,
                    Qt.NoModifier)
    card.mousePressEvent(e)


def flip(screen, idx):
    cards = screen.stack.currentWidget().findChildren(FlipCard)
    for k in idx:
        click(cards[k])


steps = []


def at(delay, fn):
    steps.append((delay, fn))


def when(cond, delay, fn):
    steps.append((delay, fn, cond))


def run(i=0):
    if i >= len(steps):
        return
    delay, fn, *cond = steps[i]
    if cond and not cond[0]():
        QTimer.singleShot(50, lambda: run(i))
        return
    QTimer.singleShot(delay, lambda: (fn(), run(i + 1)))


rigged = [Side.MORIN, Side.MORIN, Side.HONIN, Side.YAMAAN, Side.TEMEEN]
S.throw = lambda rng=None: list(rigged)

at(500, lambda: snap("shot_menu"))
at(100, lambda: w.go("setup", {"mode": 1}))
at(200, lambda: [r.edit.setText(n) for r, n in zip(w.screens["setup"].rows, ("Баир", "Сэсэг"))])
at(200, lambda: snap("shot_setup"))
at(100, lambda: w.go("game", {"names": ["Николай"], "opponents": 2}))
at(500, lambda: g.start_tour())
at(300, lambda: (g.tour._advance(), g.tour._advance()))
at(400, lambda: (snap("shot_tour"), g.tour.hide()))
at(200, lambda: (g._press(), QTimer.singleShot(450, g._release)))
at(3900, lambda: snap("shot_game"))


def to_finish():
    w.go("game", {"names": ["Николай"], "opponents": 2})
    g.fast_btn.setChecked(True)
    g.human.position = g.race.finish - 2
    g.track.pos[0] = float(g.human.position)
    g._next()


at(4200, to_finish)
at(900, lambda: snap("shot_drama"))
at(100, lambda: (g._press(), QTimer.singleShot(300, g._release)))
when(lambda: g.track.winner >= 0, 1300, lambda: snap("shot_finish"))
at(2500, lambda: db.delete(g.last_record_id) if g.last_record_id else None)
at(100, lambda: render(CertData("Николай", 1320, 15, 3)).scaledToWidth(1100, Qt.SmoothTransformation)
   .save(str(DOCS / "shot_certificate.png")))


def harb():
    w.go("harbaha", {"name": "Аюна"})
    b = w.harbaha.board

    def aim():
        bs = b.bones
        for i, x in enumerate(bs):
            for j, y in enumerate(bs):
                if i != j and x.side is y.side:
                    d = math.hypot(y.x - x.x, y.y - x.y)
                    b.shooter, b.state = i, b.DRAG
                    b._mouse = QPointF(x.x - (y.x - x.x) / d * 110, x.y - (y.y - x.y) / d * 110)
                    b.update()
                    return
    QTimer.singleShot(500, aim)
    QTimer.singleShot(900, lambda: (snap("shot_harbaha"), setattr(b, "state", b.AIM)))


at(800, lambda: (setattr(g, "aborted", True), g.rain.stop(), harb()))
at(1500, lambda: (w.go("rules", {}), QTimer.singleShot(200, lambda: flip(w.screens["rules"], (0, 2)))))
at(1100, lambda: snap("shot_rules"))
at(100, lambda: (w.go("about", {}), w.screens["about"].show_page(2)))
at(300, lambda: flip(w.screens["about"], (1,)))
at(900, lambda: snap("shot_about"))
at(100, lambda: w.go("records", {}))
at(400, lambda: snap("shot_records"))


def card():
    c = PlayerCard(w, db, "Николай")
    c.show()
    QTimer.singleShot(500, lambda: (snap("shot_card", c), c.close()))


at(100, card)
at(1200, app.quit)
run()
app.exec()
