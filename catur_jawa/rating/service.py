from __future__ import annotations

from dataclasses import dataclass

from catur_jawa.rating.repository import RatingRepository


def k_factor(games_played: int) -> int:
    if games_played < 10:
        return 40
    if games_played < 30:
        return 24
    return 16


def expected_score(rating_a: float, rating_b: float) -> float:
    return 1 / (1 + 10 ** ((rating_b - rating_a) / 400))


@dataclass(frozen=True, slots=True)
class RatingChange:
    device_id: str
    display_name: str
    before: float
    after: float
    games_played: int

    @property
    def delta(self) -> float:
        return self.after - self.before

    def to_json(self) -> dict[str, object]:
        return {
            "device_id": self.device_id,
            "display_name": self.display_name,
            "before": self.before,
            "after": self.after,
            "delta": self.delta,
            "games_played": self.games_played,
        }


@dataclass(frozen=True, slots=True)
class RatingResult:
    game_id: str
    player_a: RatingChange
    player_b: RatingChange
    score_a: float
    score_b: float

    def to_json(self) -> dict[str, object]:
        return {
            "game_id": self.game_id,
            "player_a": self.player_a.to_json(),
            "player_b": self.player_b.to_json(),
            "score_a": self.score_a,
            "score_b": self.score_b,
        }


@dataclass(frozen=True, slots=True)
class PlayerRating:
    device_id: str
    display_name: str
    rating: float
    games_played: int

    def to_json(self) -> dict[str, object]:
        return {
            "device_id": self.device_id,
            "display_name": self.display_name,
            "rating": self.rating,
            "games_played": self.games_played,
        }


class RatingService:
    def __init__(self, repository: RatingRepository):
        self.repository = repository

    def record_result(
        self,
        game_id: str,
        player_a_device_id: str,
        player_a_display_name: str,
        player_b_device_id: str,
        player_b_display_name: str,
        score_a: float,
    ) -> RatingResult | None:
        score_b = 1.0 - score_a
        with self.repository.lock:
            with self.repository.connection:
                exists = self.repository.connection.execute(
                    "SELECT 1 FROM match_results WHERE game_id = ?", (game_id,)
                ).fetchone()
                if exists:
                    return None
                a = self.repository.ensure_player(player_a_device_id, player_a_display_name)
                b = self.repository.ensure_player(player_b_device_id, player_b_display_name)
                exp_a = expected_score(float(a["rating"]), float(b["rating"]))
                exp_b = 1 - exp_a
                new_a = float(a["rating"]) + k_factor(int(a["games_played"])) * (score_a - exp_a)
                new_b = float(b["rating"]) + k_factor(int(b["games_played"])) * (score_b - exp_b)
                self.repository.connection.execute(
                    "UPDATE players SET rating = ?, games_played = games_played + 1 WHERE device_id = ?",
                    (new_a, player_a_device_id),
                )
                self.repository.connection.execute(
                    "UPDATE players SET rating = ?, games_played = games_played + 1 WHERE device_id = ?",
                    (new_b, player_b_device_id),
                )
                self.repository.connection.execute(
                    """
                    INSERT INTO match_results(
                        game_id,
                        player_a_device_id, player_a_display_name,
                        player_b_device_id, player_b_display_name,
                        score_a, score_b,
                        rating_a_before, rating_b_before, rating_a_after, rating_b_after
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        game_id,
                        player_a_device_id,
                        player_a_display_name,
                        player_b_device_id,
                        player_b_display_name,
                        score_a,
                        score_b,
                        float(a["rating"]),
                        float(b["rating"]),
                        new_a,
                        new_b,
                    ),
                )
                return RatingResult(
                    game_id=game_id,
                    player_a=RatingChange(
                        player_a_device_id,
                        player_a_display_name,
                        float(a["rating"]),
                        new_a,
                        int(a["games_played"]) + 1,
                    ),
                    player_b=RatingChange(
                        player_b_device_id,
                        player_b_display_name,
                        float(b["rating"]),
                        new_b,
                        int(b["games_played"]) + 1,
                    ),
                    score_a=score_a,
                    score_b=score_b,
                )

    def leaderboard(self, limit: int = 10) -> list[tuple[str, float, int]]:
        with self.repository.lock:
            rows = self.repository.connection.execute(
                "SELECT display_name, rating, games_played FROM players ORDER BY rating DESC, display_name LIMIT ?",
                (limit,),
            ).fetchall()
        return [
            (str(row["display_name"]), float(row["rating"]), int(row["games_played"]))
            for row in rows
        ]

    def rating_snapshot(self, device_id: str, display_name: str) -> PlayerRating:
        with self.repository.lock:
            row = self.repository.ensure_player(device_id, display_name)
        return PlayerRating(
            device_id=str(row["device_id"]),
            display_name=str(row["display_name"]),
            rating=float(row["rating"]),
            games_played=int(row["games_played"]),
        )
