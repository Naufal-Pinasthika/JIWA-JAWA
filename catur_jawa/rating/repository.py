from __future__ import annotations

import sqlite3
from threading import RLock
from pathlib import Path
from typing import cast


class RatingRepository:
    def __init__(self, path: str | Path = "ratings.sqlite3"):
        self.path = Path(path)
        self.lock = RLock()
        self.connection = sqlite3.connect(self.path, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        with self.connection:
            self._migrate_legacy_players()
            self._migrate_legacy_results()
            self.connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS players (
                    device_id TEXT PRIMARY KEY,
                    display_name TEXT NOT NULL,
                    rating REAL NOT NULL DEFAULT 1500,
                    games_played INTEGER NOT NULL DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS match_results (
                    game_id TEXT PRIMARY KEY,
                    player_a_device_id TEXT NOT NULL,
                    player_a_display_name TEXT NOT NULL,
                    player_b_device_id TEXT NOT NULL,
                    player_b_display_name TEXT NOT NULL,
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
            self._copy_legacy_players()

    def _migrate_legacy_players(self) -> None:
        if not self._table_exists("players"):
            return
        columns = self._columns("players")
        if "device_id" not in columns and not self._table_exists("players_legacy"):
            self.connection.execute("ALTER TABLE players RENAME TO players_legacy")

    def _migrate_legacy_results(self) -> None:
        if not self._table_exists("match_results"):
            return
        columns = self._columns("match_results")
        if "player_a_device_id" not in columns and not self._table_exists("match_results_legacy"):
            self.connection.execute("ALTER TABLE match_results RENAME TO match_results_legacy")

    def _copy_legacy_players(self) -> None:
        if not self._table_exists("players_legacy"):
            return
        self.connection.execute(
            """
            INSERT OR IGNORE INTO players(device_id, display_name, rating, games_played)
            SELECT name, name, rating, games_played FROM players_legacy
            """
        )

    def _table_exists(self, table: str) -> bool:
        row = self.connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (table,)
        ).fetchone()
        return row is not None

    def _columns(self, table: str) -> set[str]:
        rows = self.connection.execute(f"PRAGMA table_info({table})").fetchall()
        return {str(row["name"]) for row in rows}

    def ensure_player(self, device_id: str, display_name: str) -> sqlite3.Row:
        clean_name = display_name.strip() or "Player"
        with self.lock:
            with self.connection:
                self.connection.execute(
                    """
                    INSERT INTO players(device_id, display_name) VALUES (?, ?)
                    ON CONFLICT(device_id) DO UPDATE SET display_name = excluded.display_name
                    """,
                    (device_id, clean_name),
                )
            row = self.connection.execute(
                "SELECT * FROM players WHERE device_id = ?", (device_id,)
            ).fetchone()
        if row is None:
            raise RuntimeError(f"Unable to load player {device_id}")
        return cast(sqlite3.Row, row)

    def close(self) -> None:
        with self.lock:
            self.connection.close()
