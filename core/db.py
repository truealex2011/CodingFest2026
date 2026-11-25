"""Таблица рекордов в SQLite (встроена в Python, сервер не нужен)."""
from __future__ import annotations

import csv
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .validation import validate_name

SCHEMA = """
CREATE TABLE IF NOT EXISTS records (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT    NOT NULL CHECK(length(trim(name)) > 0),
    score      INTEGER NOT NULL CHECK(score >= 0),
    throws     INTEGER NOT NULL CHECK(throws >= 0),
    place      INTEGER NOT NULL CHECK(place >= 1),
    riders     INTEGER NOT NULL CHECK(riders >= 1),
    created_at TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_records_name  ON records(name COLLATE NOCASE);
CREATE INDEX IF NOT EXISTS idx_records_score ON records(score DESC);

-- достижения игроков: одно достижение на игрока один раз
CREATE TABLE IF NOT EXISTS achievements (
    player     TEXT NOT NULL,      -- имя в нижнем регистре
    code       TEXT NOT NULL,
    unlocked_at TEXT NOT NULL,
    PRIMARY KEY (player, code)
);

-- результаты мини-игры «Шагай харбаха» (щелчки)
CREATE TABLE IF NOT EXISTS harbaha (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT    NOT NULL,
    score      INTEGER NOT NULL CHECK(score >= 0),
    hits       INTEGER NOT NULL CHECK(hits >= 0),
    created_at TEXT    NOT NULL
);
"""


@dataclass
class Record:
    id: int
    name: str
    score: int
    throws: int
    place: int
    riders: int
    created_at: str


class RecordsDB:
    def __init__(self, path: str | Path = ":memory:") -> None:
        self.path = str(path)
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self.conn.create_function("PYLOWER", 1, lambda s: s.lower() if s else s)
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    # --- CRUD ---
    def add(self, name: str, score: int, throws: int, place: int, riders: int) -> int:
        name = validate_name(name)
        with self.conn:
            cur = self.conn.execute(
                "INSERT INTO records(name, score, throws, place, riders, created_at)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (name, int(score), int(throws), int(place), int(riders),
                 datetime.now().strftime("%Y-%m-%d %H:%M")),
            )
        return int(cur.lastrowid)

    def rename(self, record_id: int, new_name: str) -> None:
        new_name = validate_name(new_name)
        with self.conn:
            cur = self.conn.execute("UPDATE records SET name=? WHERE id=?", (new_name, record_id))
        if cur.rowcount == 0:
            raise KeyError(f"Запись #{record_id} не найдена")

    def delete(self, record_id: int) -> None:
        with self.conn:
            cur = self.conn.execute("DELETE FROM records WHERE id=?", (record_id,))
        if cur.rowcount == 0:
            raise KeyError(f"Запись #{record_id} не найдена")

    def clear(self) -> None:
        with self.conn:
            self.conn.execute("DELETE FROM records")

    def list(self, name_filter: str = "") -> list[Record]:
        """Все записи по убыванию очков; фильтр — подстрока имени без учёта регистра
        (работает и для кириллицы, в отличие от LIKE в SQLite)."""
        sql = "SELECT * FROM records"
        args: tuple = ()
        f = " ".join(name_filter.split()).lower()
        if f:
            sql += " WHERE instr(PYLOWER(name), ?) > 0"
            args = (f,)
        sql += " ORDER BY score DESC, throws ASC, id ASC"
        return [Record(**dict(r)) for r in self.conn.execute(sql, args)]

    def rank_of(self, record_id: int) -> int | None:
        for i, r in enumerate(self.list(), 1):
            if r.id == record_id:
                return i
        return None

    # --- карточка игрока ---
    def player_records(self, name: str) -> list[Record]:
        """Все заезды игрока (имя целиком, без учёта регистра) в порядке времени."""
        key = " ".join(name.split()).lower()
        rows = self.conn.execute("SELECT * FROM records WHERE PYLOWER(name) = ? ORDER BY id", (key,))
        return [Record(**dict(r)) for r in rows]

    # --- достижения ---
    def unlock(self, name: str, code: str) -> bool:
        """Открывает достижение. True — если оно новое."""
        key = " ".join(name.split()).lower()
        with self.conn:
            cur = self.conn.execute(
                "INSERT OR IGNORE INTO achievements(player, code, unlocked_at) VALUES (?, ?, ?)",
                (key, code, datetime.now().strftime("%Y-%m-%d %H:%M")))
        return cur.rowcount == 1

    def achievements(self, name: str) -> dict[str, str]:
        """{код: дата открытия} для игрока."""
        key = " ".join(name.split()).lower()
        rows = self.conn.execute("SELECT code, unlocked_at FROM achievements WHERE player = ?", (key,))
        return {r["code"]: r["unlocked_at"] for r in rows}

    # --- «Шагай харбаха» ---
    def add_harbaha(self, name: str, score: int, hits: int) -> int:
        name = validate_name(name)
        with self.conn:
            cur = self.conn.execute(
                "INSERT INTO harbaha(name, score, hits, created_at) VALUES (?, ?, ?, ?)",
                (name, int(score), int(hits), datetime.now().strftime("%Y-%m-%d %H:%M")))
        return int(cur.lastrowid)

    def harbaha_top(self, limit: int = 5) -> list[tuple[str, int, int]]:
        rows = self.conn.execute("SELECT name, score, hits FROM harbaha ORDER BY score DESC, id ASC LIMIT ?",
                                 (limit,))
        return [(r["name"], r["score"], r["hits"]) for r in rows]

    def harbaha_best(self, name: str) -> int:
        key = " ".join(name.split()).lower()
        r = self.conn.execute("SELECT MAX(score) AS m FROM harbaha WHERE PYLOWER(name) = ?", (key,)).fetchone()
        return int(r["m"] or 0)

    def export_csv(self, path: str | Path, name_filter: str = "") -> int:
        rows = self.list(name_filter)
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f, delimiter=";")
            w.writerow(["Место", "Имя", "Очки", "Бросков", "Место в заезде", "Всадников", "Дата"])
            for i, r in enumerate(rows, 1):
                w.writerow([i, r.name, r.score, r.throws, r.place, r.riders, r.created_at])
        return len(rows)
