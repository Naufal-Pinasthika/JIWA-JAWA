from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from catur_jawa.domain.models import GameEvent


class GameLogger:
    def __init__(self, root: str | Path, game_id: str, player_id: str):
        self.path = Path(root) / game_id / f"{player_id}.jsonl"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._file = self.path.open("a", encoding="utf-8")

    def write_event(self, event: GameEvent) -> None:
        record: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "game_id": self.path.parent.name,
            **event.to_json(),
        }
        self._file.write(json.dumps(record, sort_keys=True) + "\n")
        self._file.flush()

    def write_network(self, event_type: str, **fields: Any) -> None:
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "game_id": self.path.parent.name,
            "event_type": event_type,
            **fields,
        }
        self._file.write(json.dumps(record, sort_keys=True) + "\n")
        self._file.flush()

    def close(self) -> None:
        self._file.close()

    def __enter__(self) -> "GameLogger":
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()
