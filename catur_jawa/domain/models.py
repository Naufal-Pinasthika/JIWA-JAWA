from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class PlayerSide(StrEnum):
    A = "A"
    B = "B"

    @property
    def opponent(self) -> "PlayerSide":
        return PlayerSide.B if self is PlayerSide.A else PlayerSide.A

    @property
    def forward_dx(self) -> int:
        return 1 if self is PlayerSide.A else -1


class Phase(StrEnum):
    NORMAL = "NORMAL"
    PENALTY_SELECTION = "PENALTY_SELECTION"
    FINISHED = "FINISHED"


@dataclass(frozen=True, slots=True)
class Node:
    id: str
    label: str
    x: float
    y: float


@dataclass(slots=True)
class Piece:
    id: str
    owner: PlayerSide
    node: str
    king: bool = False

    def to_json(self) -> dict[str, Any]:
        return {"id": self.id, "owner": self.owner.value, "node": self.node, "king": self.king}

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "Piece":
        return cls(
            id=str(data["id"]),
            owner=PlayerSide(str(data["owner"])),
            node=str(data["node"]),
            king=bool(data["king"]),
        )


@dataclass(frozen=True, slots=True)
class Move:
    source: str
    destination: str
    captured_node: str | None = None

    @property
    def is_capture(self) -> bool:
        return self.captured_node is not None


@dataclass(slots=True)
class GameEvent:
    event_id: str
    event_type: str
    actor: PlayerSide | None
    turn_number: int
    human_message: str
    source: str | None = None
    destination: str | None = None
    captured_piece_ids: list[str] = field(default_factory=list)
    promotion: list[str] = field(default_factory=list)
    phase: Phase = Phase.NORMAL
    state_hash: str = ""

    def to_json(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "actor": self.actor.value if self.actor else None,
            "turn_number": self.turn_number,
            "human_message": self.human_message,
            "source": self.source,
            "destination": self.destination,
            "captured_piece_ids": self.captured_piece_ids,
            "promotion": self.promotion,
            "phase": self.phase.value,
            "state_hash": self.state_hash,
        }
