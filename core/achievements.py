"""Достижения игрока. Чистая логика без интерфейса — проверяется тестами.

Каждое событие игры (бросок, заезд, щелчок) превращается в список кодов,
которые игрок заработал. Хранит открытые достижения база (RecordsDB.unlock).
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Achievement:
    code: str
    title: str
    text: str
    icon: str  # horse / bone / crown / wind / book / people / target / clean / ten


ALL = [
    Achievement("first_horse", "Первый конь", "Выбросить первого «морин»", "horse"),
    Achievement("herd", "Табун", "Выбросить 3 коня или больше за один бросок", "bone"),
    Achievement("winner", "Победитель скачек", "Первым прийти к финишу", "crown"),
    Achievement("fast", "Быстрее ветра", "Победить в классическом заезде за 14 бросков или быстрее", "wind"),
    Achievement("scholar", "Знаток культуры", "Верно ответить на все вопросы знатока в заезде", "book"),
    Achievement("friends", "Вместе веселее", "Сыграть заезд на одном устройстве", "people"),
    Achievement("sniper", "Меткий щелчок", "Три попадания подряд в «Шагай харбаха»", "target"),
    Achievement("clean", "Чистый войлок", "Собрать все пары в «Шагай харбаха»", "clean"),
    Achievement("veteran", "Бывалый наездник", "Сыграть 10 заездов", "ten"),
]
BY_CODE = {a.code: a for a in ALL}

HERD = 3          # коней за бросок для «Табуна»
FAST_THROWS = 14  # бросков для «Быстрее ветра»
VETERAN = 10      # заездов для «Бывалого наездника»
SNIPER = 3        # попаданий подряд для «Меткого щелчка»


def for_throw(horses: int) -> list[str]:
    out = []
    if horses >= 1:
        out.append("first_horse")
    if horses >= HERD:
        out.append("herd")
    return out


def for_race(won: bool, throws: int, quiz_ok: int, quiz_asked: int, hotseat: bool,
             races_played: int, classic: bool = True) -> list[str]:
    """classic=False — быстрый заезд: «Быстрее ветра» в нём не даётся, иначе слишком легко."""
    out = []
    if won:
        out.append("winner")
        if classic and throws <= FAST_THROWS:
            out.append("fast")
    if quiz_asked and quiz_ok == quiz_asked:
        out.append("scholar")
    if hotseat:
        out.append("friends")
    if races_played >= VETERAN:
        out.append("veteran")
    return out


def for_harbaha(best_streak: int, cleared: bool) -> list[str]:
    out = []
    if best_streak >= SNIPER:
        out.append("sniper")
    if cleared:
        out.append("clean")
    return out
