from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import cast


class RatingRepository:
    def __init__(self, path: str | Path = "ratings.sqlite3"):
        self.path = Path(path)
        self.connection = sqlite3.connect(self.path)
        self.connection.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        with self.connection:
            self.connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS players (
                    name TEXT PRIMARY KEY,
                    rating REAL NOT NULL DEFAULT 1500,
                    games_played INTEGER NOT NULL DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS match_results (
                    game_id TEXT PRIMARY KEY,
                    player_a TEXT NOT NULL,
                    player_b TEXT NOT NULL,
                    score_a REAL NOT NULL,
                    score_b REAL NOT NULL,
                    rating_a_before REAL NOT NULL,
                    rating_b_before REAL NOT NULL,
                    rating_a_after REAL NOT NULL,
                    rating_b_after REAL NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                """
            )

    def ensure_player(self, name: str) -> sqlite3.Row:
        with self.connection:
            self.connection.execute("INSERT OR IGNORE INTO players(name) VALUES (?)", (name,))
        row = self.connection.execute("SELECT * FROM players WHERE name = ?", (name,)).fetchone()
        if row is None:
            raise RuntimeError(f"Unable to load player {name}")
        return cast(sqlite3.Row, row)

    def close(self) -> None:
        self.connection.close()
