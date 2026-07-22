from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from catur_jawa.domain.models import GameEvent
from catur_jawa.domain.state import GameState


@dataclass(slots=True)
class CommandResponse:
    ok: bool
    message_type: str
    payload: dict[str, Any]


def committed_payload(state: GameState, events: list[GameEvent]) -> dict[str, Any]:
    return {
        "game_id": state.game_id,
        "turn_number": state.turn_number,
        "state_hash": state.hash(),
        "events": [event.to_json() for event in events],
        "state": state.to_json(),
    }
