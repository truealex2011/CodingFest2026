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
    return HIT_POINTS * min(max(combo, 1), MAX_COMBO)


def final_bonus(cleared: bool, lives_left: int) -> int:
    return CLEAN_BONUS + LIFE_BONUS * lives_left if cleared else 0
