from __future__ import annotations

from catur_jawa.rating.repository import RatingRepository


def k_factor(games_played: int) -> int:
    if games_played < 10:
        return 40
    if games_played < 30:
        return 24
    return 16


def expected_score(rating_a: float, rating_b: float) -> float:
    return 1 / (1 + 10 ** ((rating_b - rating_a) / 400))


class RatingService:
    def __init__(self, repository: RatingRepository):
        self.repository = repository

    def record_result(
        self, game_id: str, player_a: str, player_b: str, score_a: float
    ) -> tuple[float, float] | None:
        score_b = 1.0 - score_a
        with self.repository.connection:
            exists = self.repository.connection.execute(
                "SELECT 1 FROM match_results WHERE game_id = ?", (game_id,)
            ).fetchone()
            if exists:
                return None
            a = self.repository.ensure_player(player_a)
            b = self.repository.ensure_player(player_b)
            exp_a = expected_score(float(a["rating"]), float(b["rating"]))
            exp_b = 1 - exp_a
            new_a = float(a["rating"]) + k_factor(int(a["games_played"])) * (score_a - exp_a)
            new_b = float(b["rating"]) + k_factor(int(b["games_played"])) * (score_b - exp_b)
            self.repository.connection.execute(
                "UPDATE players SET rating = ?, games_played = games_played + 1 WHERE name = ?",
                (new_a, player_a),
            )
            self.repository.connection.execute(
                "UPDATE players SET rating = ?, games_played = games_played + 1 WHERE name = ?",
                (new_b, player_b),
            )
            self.repository.connection.execute(
                """
                INSERT INTO match_results(
                    game_id, player_a, player_b, score_a, score_b,
                    rating_a_before, rating_b_before, rating_a_after, rating_b_after
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    game_id,
                    player_a,
                    player_b,
                    score_a,
                    score_b,
                    float(a["rating"]),
                    float(b["rating"]),
                    new_a,
                    new_b,
                ),
            )
            return new_a, new_b

    def leaderboard(self, limit: int = 10) -> list[tuple[str, float, int]]:
        rows = self.repository.connection.execute(
            "SELECT name, rating, games_played FROM players ORDER BY rating DESC, name LIMIT ?",
            (limit,),
        ).fetchall()
        return [(str(row["name"]), float(row["rating"]), int(row["games_played"])) for row in rows]
