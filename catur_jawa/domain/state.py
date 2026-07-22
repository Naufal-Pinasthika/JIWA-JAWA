from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from catur_jawa.domain.board import STANDARD_BOARD, Board
from catur_jawa.domain.models import Phase, Piece, PlayerSide
from catur_jawa.domain.serialization import state_hash


@dataclass(slots=True)
class GameState:
    game_id: str
    current_player: PlayerSide
    turn_number: int = 0
    phase: Phase = Phase.NORMAL
    pieces: dict[str, Piece] = field(default_factory=dict)
    pending_penalty_for: PlayerSide | None = None
    pending_penalty_by: PlayerSide | None = None
    penalty_removed: list[str] = field(default_factory=list)
    winner: PlayerSide | None = None
    result_persisted: bool = False
    board: Board = field(default=STANDARD_BOARD, repr=False, compare=False)

    @classmethod
    def new(cls, game_id: str, starting_player: PlayerSide = PlayerSide.A) -> "GameState":
        pieces: dict[str, Piece] = {}
        for side in (PlayerSide.A, PlayerSide.B):
            for index, node in enumerate(STANDARD_BOARD.initial_nodes[side], start=1):
                pieces[f"{side.value}{index:02d}"] = Piece(f"{side.value}{index:02d}", side, node)
        return cls(game_id=game_id, current_player=starting_player, pieces=pieces)

    @property
    def occupied(self) -> dict[str, Piece]:
        return {piece.node: piece for piece in self.pieces.values()}

    def piece_at(self, node: str) -> Piece | None:
        return self.occupied.get(node)

    def pieces_for(self, side: PlayerSide) -> list[Piece]:
        return sorted((p for p in self.pieces.values() if p.owner is side), key=lambda p: p.id)

    def to_json(self) -> dict[str, Any]:
        return {
            "game_id": self.game_id,
            "current_player": self.current_player.value,
            "turn_number": self.turn_number,
            "phase": self.phase.value,
            "pieces": [p.to_json() for p in sorted(self.pieces.values(), key=lambda piece: piece.id)],
            "pending_penalty_for": self.pending_penalty_for.value if self.pending_penalty_for else None,
            "pending_penalty_by": self.pending_penalty_by.value if self.pending_penalty_by else None,
            "penalty_removed": sorted(self.penalty_removed),
            "winner": self.winner.value if self.winner else None,
            "result_persisted": self.result_persisted,
        }

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "GameState":
        state = cls(
            game_id=str(data["game_id"]),
            current_player=PlayerSide(str(data["current_player"])),
            turn_number=int(data["turn_number"]),
            phase=Phase(str(data["phase"])),
            pieces={p["id"]: Piece.from_json(p) for p in data["pieces"]},
            pending_penalty_for=(
                PlayerSide(str(data["pending_penalty_for"])) if data["pending_penalty_for"] else None
            ),
            pending_penalty_by=(
                PlayerSide(str(data["pending_penalty_by"])) if data["pending_penalty_by"] else None
            ),
            penalty_removed=list(data.get("penalty_removed", [])),
            winner=PlayerSide(str(data["winner"])) if data.get("winner") else None,
            result_persisted=bool(data.get("result_persisted", False)),
        )
        return state

    def hash(self) -> str:
        return state_hash(self.to_json())
