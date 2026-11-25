from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QMarginsF, QPointF, QRectF, Qt, QUrl
from PySide6.QtGui import (QColor, QDesktopServices, QImage, QPageLayout, QPageSize, QPainter,
                           QPainterPath, QPdfWriter, QPen)
from PySide6.QtWidgets import QFileDialog, QMessageBox, QWidget

from core.shagai import Side, TRACK_LENGTH
from . import theme as T
from .widgets import plural, points_txt, throws_txt
from .art import draw_horse_token, draw_ornament_band, draw_shagai, grain_tile, ui_font

W, H = 1754, 1240


@dataclass
class CertData:
    name: str
    score: int
    throws: int
    riders: int
    hotseat: bool = False
    date: str = ""
    length: int = TRACK_LENGTH

    def __post_init__(self):
        if not self.date:
            self.date = datetime.now().strftime("%d.%m.%Y")


def _corner(p: QPainter, c: QPointF, s: float) -> None:
    path = QPainterPath(QPointF(c.x(), c.y() - s))
    for dx, dy in ((s, 0), (0, s), (-s, 0)):
        path.lineTo(c.x() + dx, c.y() + dy)
    path.closeSubpath()
    p.setPen(QPen(QColor(T.INK), 3))
    p.setBrush(QColor(T.RED))
    p.drawPath(path)
    p.setBrush(QColor(T.OCHRE))
    p.drawEllipse(c, s * 0.35, s * 0.35)


def _seal(p: QPainter, c: QPointF, r: float) -> None:
    path = QPainterPath()
    n = 36
    for k in range(n * 2 + 1):
        a = k * math.pi / n
        rr = r if k % 2 == 0 else r * 0.92
        pt = QPointF(c.x() + math.cos(a) * rr, c.y() + math.sin(a) * rr)
        path.moveTo(pt) if k == 0 else path.lineTo(pt)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(30, 27, 24, 70))
    p.drawPath(path.translated(8, 10))
    p.setPen(QPen(QColor(T.INK), 3))
    p.setBrush(QColor(T.OCHRE))
    p.drawPath(path)
    p.setBrush(QColor(T.BLUE))
    p.drawEllipse(c, r * 0.74, r * 0.74)
    p.setBrush(Qt.NoBrush)
    p.setPen(QPen(QColor(T.PAPER_LIGHT), 2))
    p.drawEllipse(c, r * 0.66, r * 0.66)
    draw_horse_token(p, QPointF(c.x(), c.y() - r * 0.05), r * 0.38, T.RED, "")
    p.setPen(QColor(T.PAPER_LIGHT))
    p.setFont(ui_font(r * 0.15, title=True))
    p.drawText(QRectF(c.x() - r, c.y() + r * 0.34, 2 * r, r * 0.2), Qt.AlignCenter, "1 МЕСТО")


def paint_certificate(p: QPainter, d: CertData) -> None:
    p.setRenderHint(QPainter.Antialiasing)
    full = QRectF(0, 0, W, H)
    p.fillRect(full, QColor(T.PAPER_LIGHT))
    p.drawTiledPixmap(full, grain_tile())

    m = 46
    band = 44
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(T.BLUE))
    outer = full.adjusted(m, m, -m, -m)
    p.drawRect(outer)
    p.setBrush(QColor(T.PAPER_LIGHT))
    inner = outer.adjusted(band, band, -band, -band)
    p.drawRect(inner)
    p.drawTiledPixmap(inner, grain_tile())
    for rect in (QRectF(outer.left(), outer.top(), outer.width(), band),
                 QRectF(outer.left(), outer.bottom() - band, outer.width(), band)):
        draw_ornament_band(p, rect.adjusted(0, 8, 0, -8), T.PAPER_LIGHT, lines=False)
    p.setPen(QPen(QColor(T.RED), 6))
    p.setBrush(Qt.NoBrush)
    p.drawRect(inner.adjusted(-3, -3, 3, 3))
    p.setPen(QPen(QColor(T.INK), 2))
    p.drawRect(inner.adjusted(18, 18, -18, -18))
    for c in (inner.topLeft(), inner.topRight(), inner.bottomLeft(), inner.bottomRight()):
        _corner(p, c, 26)

    cx = W / 2
    y = inner.top() + 80
    p.setPen(QColor(T.RED))
    f = ui_font(30, title=True)
    f.setLetterSpacing(f.SpacingType.AbsoluteSpacing, 8)
    p.setFont(f)
    p.drawText(QRectF(0, y, W, 40), Qt.AlignCenter, "ШАГАЙ НААДАН  ·  МОРИ УРИЛДААН")
    y += 50
    p.setPen(QColor(T.INK))
    p.setFont(ui_font(150, title=True))
    p.drawText(QRectF(0, y, W, 170), Qt.AlignCenter, "СЕРТИФИКАТ")
    y += 168
    p.setFont(ui_font(36))
    p.setPen(QColor(T.INK_SOFT))
    p.drawText(QRectF(0, y, W, 50), Qt.AlignCenter, "победителя бурятских скачек на бараньих косточках")

    y += 92
    p.setPen(QColor(T.INK))
    p.setFont(ui_font(30))
    p.drawText(QRectF(0, y, W, 40), Qt.AlignCenter, "Настоящим подтверждается, что")
    y += 50
    p.setPen(QColor(T.RED))
    p.setFont(ui_font(118, title=True))
    p.drawText(QRectF(0, y, W, 140), Qt.AlignCenter, d.name)
    p.setPen(QPen(QColor(T.INK), 3))
    p.drawLine(QPointF(cx - 470, y + 146), QPointF(cx + 470, y + 146))
    y += 172
    opp = d.riders - 1
    rivals = (f"среди {d.riders} наездников за одним устройством" if d.hotseat
              else f"в борьбе с {opp} {'соперником' if opp == 1 else 'соперниками'}")
    text = (f"— победитель скачек «Мори урилдаан». Конь наездника первым пришёл к финишу, "
            f"пройдя все {d.length} {plural(d.length, 'кость', 'кости', 'костей')} ипподрома за {throws_txt(d.throws)} {rivals}. "
            f"Итог заезда — {points_txt(d.score)}.")
    p.setPen(QColor(T.INK))
    p.setFont(ui_font(32))
    p.drawText(QRectF(cx - 660, y, 1320, 140), Qt.AlignHCenter | Qt.AlignTop | Qt.TextWordWrap, text)

    by = inner.bottom() - 150
    for k, side in enumerate((Side.HONIN, Side.YAMAAN, Side.MORIN, Side.TEMEEN)):
        draw_shagai(p, QPointF(inner.left() + 120 + k * 92, by + 10), 74, side, (-1) ** k * 12,
                    glow=side is Side.MORIN)
    for k, (cap, val) in enumerate((("Дата", d.date), ("Главный судья скачек", ""))):
        x = cx - 330 + k * 400
        p.setPen(QPen(QColor(T.INK), 2))
        p.drawLine(QPointF(x, by + 30), QPointF(x + 260, by + 30))
        p.setPen(QColor(T.INK_SOFT))
        p.setFont(ui_font(22))
        p.drawText(QRectF(x, by + 38, 260, 30), Qt.AlignCenter, cap)
        p.setPen(QColor(T.INK))
        if val:
            p.setFont(ui_font(34, title=True))
            p.drawText(QRectF(x, by - 20, 260, 46), Qt.AlignCenter, val)
        else:
            sig = QPainterPath(QPointF(x + 40, by + 18))
            sig.cubicTo(x + 80, by - 40, x + 110, by + 40, x + 140, by - 6)
            sig.cubicTo(x + 160, by - 30, x + 180, by + 26, x + 225, by - 10)
            p.setPen(QPen(QColor(T.BLUE), 4, Qt.SolidLine, Qt.RoundCap))
            p.setBrush(Qt.NoBrush)
            p.drawPath(sig)
    _seal(p, QPointF(inner.right() - 190, by - 10), 120)


def render(d: CertData) -> QImage:
    img = QImage(W, H, QImage.Format_ARGB32)
    img.fill(QColor(T.PAPER_LIGHT))
    p = QPainter(img)
    paint_certificate(p, d)
    p.end()
    return img


def save(d: CertData, path: str) -> None:
    img = render(d)
    if path.lower().endswith(".pdf"):
        pdf = QPdfWriter(path)
        pdf.setPageLayout(QPageLayout(QPageSize(QPageSize.A4), QPageLayout.Landscape, QMarginsF(0, 0, 0, 0)))
        pdf.setResolution(150)
        pdf.setTitle(f"Сертификат — {d.name}")
        p = QPainter(pdf)
        p.drawImage(QRectF(0, 0, pdf.width(), pdf.height()), img)
        p.end()
    elif not img.save(path):
        raise OSError("не удалось записать файл")


def ask_and_save(parent: QWidget, d: CertData) -> None:
    default = str(Path.home() / f"Сертификат_{d.name.replace(' ', '_')}.png")
    path, _ = QFileDialog.getSaveFileName(parent, "Сохранить сертификат", default,
                                          "Картинка PNG (*.png);;Документ PDF (*.pdf)")
    if not path:
        return
    if not path.lower().endswith((".png", ".pdf")):
        path += ".png"
    try:
        save(d, path)
    except OSError as e:
        QMessageBox.critical(parent, "Сертификат", f"Не удалось сохранить сертификат:\n{e}")
        return
    QDesktopServices.openUrl(QUrl.fromLocalFile(path))
