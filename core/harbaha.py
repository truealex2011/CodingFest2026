"""«Шагай харбаха» — щелчки по шагаям. Правила (без интерфейса, покрыты тестами).

* На войлоке рассыпаны шагай. Игрок выбирает кость и щелчком отправляет её в другую.
* Попадание засчитывается, если первой задета кость ТОЙ ЖЕ стороны
  (хонин в хонин, морин в морин...). Сбитую кость игрок забирает себе.
* Задел кость другой стороны — «промах рукой», не задел ничего — просто промах.
  Каждый промах отнимает одну из трёх попыток.
* Игра заканчивается, когда пар одинаковых сторон не осталось («чистый войлок»)
  или закончились попытки.
"""
from __future__ import annotations

import random
from collections import Counter

from .shagai import SIDES, WEIGHTS, Side

BONES = 10
LIVES = 3
HIT_POINTS = 100
MAX_COMBO = 5
CLEAN_BONUS = 300
LIFE_BONUS = 100

HIT, FOUL, MISS = "hit", "foul", "miss"


def scatter(rng: random.Random | None = None, count: int = BONES) -> list[Side]:
    """Случайные стороны костей; гарантируем хотя бы две пары, чтобы было во что целиться."""
    rng = rng or random
    while True:
        sides = rng.choices(SIDES, weights=WEIGHTS, k=count)
        if sum(n // 2 for n in Counter(sides).values()) >= 2:
            return sides


def judge(shooter: Side, first_contact: Side | None) -> str:
    if first_contact is None:
        return MISS
    return HIT if first_contact is shooter else FOUL


def has_pairs(sides: list[Side]) -> bool:
    return any(n >= 2 for n in Counter(sides).values())


def hit_points(combo: int) -> int:
    """combo — номер попадания подряд (1, 2, 3...)."""
    return HIT_POINTS * min(max(combo, 1), MAX_COMBO)


def final_bonus(cleared: bool, lives_left: int) -> int:
    return CLEAN_BONUS + LIFE_BONUS * lives_left if cleared else 0
