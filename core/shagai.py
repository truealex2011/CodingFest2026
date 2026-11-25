from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum

TRACK_LENGTH = 12
QUICK_LENGTH = 6
DICE_COUNT = 5
START = 1
FINISH = TRACK_LENGTH + 1


class Side(Enum):
    HONIN = ("Хонин", "Овца", 0.38)
    YAMAAN = ("Ямаан", "Коза", 0.38)
    MORIN = ("Морин", "Конь", 0.12)
    TEMEEN = ("Тэмээн", "Верблюд", 0.12)

    @property
    def buryat(self) -> str:
        return self.value[0]

    @property
    def russian(self) -> str:
        return self.value[1]

    @property
    def weight(self) -> float:
        return self.value[2]


SIDES = list(Side)
WEIGHTS = [s.weight for s in SIDES]


def throw(rng: random.Random | None = None, count: int = DICE_COUNT) -> list[Side]:
    rng = rng or random
    return rng.choices(SIDES, weights=WEIGHTS, k=count)


def horses_in(result: list[Side]) -> int:
    return sum(1 for s in result if s is Side.MORIN)


@dataclass
class Rider:
    name: str
    is_human: bool = False
    position: int = START
    throws: int = 0
    finish: int = FINISH

    @property
    def finished(self) -> bool:
        return self.position >= self.finish

    @property
    def progress(self) -> int:
        return min(self.position, self.finish) - START


@dataclass
class TurnResult:
    rider: Rider
    dice: list[Side]
    steps: int
    old_position: int
    new_position: int
    winner: Rider | None


@dataclass
class Race:
    riders: list[Rider]
    rng: random.Random = field(default_factory=random.Random)
    current: int = 0
    winner: Rider | None = None
    length: int = TRACK_LENGTH

    def __post_init__(self) -> None:
        if not self.riders:
            raise ValueError("В скачках должен быть хотя бы один участник")
        if self.length < 1:
            raise ValueError("В ряду должна быть хотя бы одна кость")
        for r in self.riders:
            r.finish = self.finish

    @property
    def finish(self) -> int:
        return self.length + START

    @property
    def current_rider(self) -> Rider:
        return self.riders[self.current]

    @property
    def over(self) -> bool:
        return self.winner is not None

    def play_turn(self, dice: list[Side] | None = None) -> TurnResult:
        if self.over:
            raise RuntimeError("Скачки уже закончились")
        rider = self.current_rider
        dice = dice if dice is not None else throw(self.rng)
        if len(dice) != DICE_COUNT:
            raise ValueError(f"Нужно бросить ровно {DICE_COUNT} шагай")
        steps = horses_in(dice)
        old = rider.position
        rider.position = min(old + steps, self.finish)
        rider.throws += 1
        if rider.finished:
            self.winner = rider
        else:
            self.current = (self.current + 1) % len(self.riders)
        return TurnResult(rider, dice, steps, old, rider.position, self.winner)

    def standings(self) -> list[Rider]:
        return sorted(self.riders, key=lambda r: (r is not self.winner, -r.position, r.throws))

    def place_of(self, rider: Rider) -> int:
        return self.standings().index(rider) + 1


QUIZ_BONUS = 50


def calc_score(won: bool, progress: int, throws: int, opponents: int, quiz_correct: int = 0,
               length: int = TRACK_LENGTH) -> int:
    score = progress * 50 + quiz_correct * QUIZ_BONUS
    if won:
        score += 400 + max(0, 300 - 10 * throws)
    return round(score * (1 + 0.1 * opponents) * length / TRACK_LENGTH)
