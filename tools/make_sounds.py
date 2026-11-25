"""Генерирует звуки игры (WAV) — без сторонних файлов и лицензий.
Запуск: python tools/make_sounds.py"""
import math
import random
import struct
import wave
from pathlib import Path

RATE = 22050
OUT = Path(__file__).resolve().parent.parent / "assets"


def save(name, samples):
    OUT.mkdir(exist_ok=True)
    with wave.open(str(OUT / name), "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(b"".join(struct.pack("<h", int(max(-1, min(1, s)) * 30000)) for s in samples))


def click(t0, dur=0.035, freq=1800, amp=0.8, rnd=random.Random(3)):
    n = int(dur * RATE)
    return t0, [amp * math.exp(-i / (n / 5)) * (0.6 * math.sin(2 * math.pi * freq * i / RATE)
                                                + 0.4 * (rnd.random() * 2 - 1)) for i in range(n)]


def mix(length, parts):
    buf = [0.0] * int(length * RATE)
    for t0, s in parts:
        o = int(t0 * RATE)
        for i, v in enumerate(s):
            if o + i < len(buf):
                buf[o + i] += v
    return buf


def throw_sound():
    rnd = random.Random(5)
    parts = [click(0.02 + k * 0.045 + rnd.random() * 0.03, freq=1200 + rnd.random() * 1400,
                   amp=0.5 + rnd.random() * 0.4) for k in range(11)]
    return mix(0.65, parts)


def hoof_sound():
    parts = []
    for t0 in (0.0, 0.09, 0.22, 0.31):
        n = int(0.05 * RATE)
        parts.append((t0, [0.9 * math.exp(-i / (n / 6)) * math.sin(2 * math.pi * (260 - i * 0.6) * i / RATE)
                           for i in range(n)]))
    return mix(0.42, parts)


def win_sound():
    notes = [392, 494, 587, 784, 587, 784]
    parts = []
    for k, f in enumerate(notes):
        dur = 0.18 if k < 5 else 0.6
        n = int(dur * RATE)
        parts.append((k * 0.16, [0.35 * math.sin(2 * math.pi * f * i / RATE)
                                 * min(1, i / 400) * math.exp(-i / (n * 0.7))
                                 + 0.12 * math.sin(2 * math.pi * 2 * f * i / RATE) * math.exp(-i / (n * 0.4))
                                 for i in range(n)]))
    return mix(1.5, parts)


def lose_sound():
    parts = []
    for k, f in enumerate([392, 349, 311]):
        n = int(0.3 * RATE)
        parts.append((k * 0.25, [0.3 * math.sin(2 * math.pi * f * i / RATE) * math.exp(-i / (n * 0.6))
                                 for i in range(n)]))
    return mix(1.1, parts)


def tone(f, dur, amp=0.3, harm=(1.0, 0.5, 0.3, 0.15), attack=300, decay=0.8):
    n = int(dur * RATE)
    return [amp * sum(h * math.sin(2 * math.pi * f * (k + 1) * i / RATE) for k, h in enumerate(harm))
            * min(1, i / attack) * math.exp(-i / (n * decay)) for i in range(n)]


def fanfare_sound():
    """Победная фанфара: «медные» ноты с обертонами, финальный аккорд."""
    seq = [(392, 0.0, 0.16), (392, 0.17, 0.16), (392, 0.34, 0.16), (523, 0.52, 0.5),
           (466, 1.05, 0.22), (523, 1.3, 0.22), (659, 1.55, 0.9)]
    parts = [(t0, tone(f, d, 0.16)) for f, t0, d in seq]
    parts += [(1.55, tone(f, 0.9, 0.09)) for f in (523, 784)]  # аккорд в конце
    return mix(2.6, parts)


def knock_sound():
    """Кость ударилась о кость — короткий сухой щелчок."""
    return mix(0.12, [click(0.0, dur=0.06, freq=2400, amp=0.9)])


def achieve_sound():
    parts = [(k * 0.09, tone(f, 0.5, 0.12, harm=(1.0, 0.0, 0.25), attack=80, decay=0.5))
             for k, f in enumerate((784, 988, 1175, 1568))]
    return mix(1.0, parts)


NOTE = {"D4": 293.66, "E4": 329.63, "F#4": 369.99, "A4": 440.0, "B4": 493.88,
        "D5": 587.33, "E5": 659.26}
MELODY = [  # D-мажорная пентатоника — звукоряд монгольских и бурятских протяжных песен
    ("A4", 1), ("B4", .5), ("A4", .5), ("F#4", 1), ("E4", 1), ("D4", 2), ("E4", 1), ("F#4", 1),
    ("A4", 2), ("B4", 1), ("A4", 1), ("F#4", 2), (None, 2),
    ("D5", 1), ("B4", 1), ("A4", 1), ("B4", 1), ("D5", 2), ("E5", 1), ("D5", 1), ("B4", 2),
    ("A4", 1), ("F#4", 1), ("A4", 2), (None, 2),
    ("A4", 1), ("F#4", 1), ("E4", 1), ("F#4", 1), ("A4", 2), ("B4", 1), ("A4", 1), ("F#4", 1),
    ("E4", 1), ("D4", 4), (None, 6),
]
BEAT = 0.6


def bowed(f, dur, amp):
    """«Смычковый» звук в духе морин хуура: мягкая атака, обертоны, вибрато к концу ноты."""
    n = int(dur * RATE)
    out = []
    ph = 0.0
    for i in range(n):
        t = i / RATE
        vib = 1 + 0.006 * min(1, t / 0.35) * math.sin(2 * math.pi * 5.5 * t)
        ph += 2 * math.pi * f * vib / RATE
        env = min(1, t / 0.09) * min(1, (dur - t) / 0.12)
        s = (math.sin(ph) + 0.55 * math.sin(2 * ph) + 0.33 * math.sin(3 * ph)
             + 0.18 * math.sin(4 * ph) + 0.1 * math.sin(5 * ph))
        out.append(amp * env * s)
    return out


def music_loop():
    """Фоновая мелодия ~31 с, зациклена без шва: бурдон звучит ровно, мелодия молчит на стыке."""
    total = sum(b for _, b in MELODY) * BEAT
    n = int(total * RATE)
    buf = [0.0] * n
    # бурдон D2 + A2 — ровный, с медленным «дыханием», период целиком укладывается в петлю
    breath = 2 * math.pi * 4 / total
    for i in range(n):
        t = i / RATE
        b = 0.85 + 0.15 * math.sin(breath * t)
        buf[i] = b * (0.07 * math.sin(2 * math.pi * 73.42 * t) + 0.035 * math.sin(2 * math.pi * 146.83 * t)
                      + 0.03 * math.sin(2 * math.pi * 110.0 * t))
    t0 = 0.0
    for note, beats in MELODY:
        if note:
            for k, v in enumerate(bowed(NOTE[note], beats * BEAT * 0.98, 0.075)):
                buf[int(t0 * RATE) + k] += v
        t0 += beats * BEAT
    # топот копыт «та-та-там» во второй фразе
    rnd = random.Random(9)
    start, end = 16 * BEAT, 32 * BEAT
    beat = start
    while beat < end - 0.01:
        for off, a in ((0.0, 0.10), (BEAT / 4, 0.07), (BEAT / 2, 0.12)):
            m = int(0.06 * RATE)
            o = int((beat + off) * RATE)
            for k in range(m):
                if o + k < n:
                    buf[o + k] += a * math.exp(-k / (m / 6)) * math.sin(2 * math.pi * (170 - k * 0.8) * k / RATE)
        beat += BEAT
    peak = max(abs(v) for v in buf) or 1
    return [v * 0.55 / peak for v in buf]


if __name__ == "__main__":
    save("music.wav", music_loop())
    save("fanfare.wav", fanfare_sound())
    save("knock.wav", knock_sound())
    save("achieve.wav", achieve_sound())
    save("throw.wav", throw_sound())
    save("hoof.wav", hoof_sound())
    save("win.wav", win_sound())
    save("lose.wav", lose_sound())
    print("OK:", sorted(p.name for p in OUT.glob("*.wav")))
