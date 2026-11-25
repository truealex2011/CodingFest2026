"""Звуки. Если QtMultimedia недоступен или нет аудиоустройства — игра идёт молча."""
from pathlib import Path

from PySide6.QtCore import QUrl

ASSETS = Path(__file__).resolve().parent.parent / "assets"

import os

try:
    if os.environ.get("SHAGAI_NO_SOUND"):
        raise ImportError
    from PySide6.QtMultimedia import QSoundEffect
except Exception:  # pragma: no cover — нет модуля мультимедиа
    QSoundEffect = None


class Sounds:
    def __init__(self) -> None:
        self.enabled = True
        self._fx = {}
        self.music = None
        self.music_on = False
        if QSoundEffect is None:
            return
        f = ASSETS / "music.wav"
        if f.exists():
            try:
                self.music = QSoundEffect()
                self.music.setSource(QUrl.fromLocalFile(str(f)))
                self.music.setLoopCount(QSoundEffect.Infinite)
                self.music.setVolume(0.35)
            except Exception:
                self.music = None
        for name in ("throw", "hoof", "win", "lose", "fanfare", "knock", "achieve"):
            f = ASSETS / f"{name}.wav"
            if f.exists():
                try:
                    e = QSoundEffect()
                    e.setSource(QUrl.fromLocalFile(str(f)))
                    e.setVolume(0.6)
                    self._fx[name] = e
                except Exception:
                    pass

    def set_music(self, on: bool) -> None:
        """Фоновая мелодия по кругу. Если музыки нет — тихо ничего не делаем."""
        self.music_on = on
        if self.music is None:
            return
        try:
            self.music.play() if on else self.music.stop()
        except Exception:
            pass

    def play(self, name: str) -> None:
        if self.enabled and name in self._fx:
            try:
                self._fx[name].play()
            except Exception:
                pass
