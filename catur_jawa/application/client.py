from __future__ import annotations

from queue import Queue
from typing import Any
from uuid import uuid4

from catur_jawa.domain.models import GameEvent, PlayerSide
from catur_jawa.domain.state import GameState
from catur_jawa.logging.game_logger import GameLogger
from catur_jawa.transport.protocol import Envelope
from catur_jawa.transport.reliable_udp import ReliableUDP


class ClientRuntime:
    def __init__(
        self,
        bind: tuple[str, int],
        peer: tuple[str, int],
        name: str,
        log_dir: str,
        session_id: str,
        rto_ms: int = 300,
        max_rto_ms: int = 2000,
        device_id: str = "player-b-device",
    ):
        self.name = name
        self.device_id = device_id
        self.host_name = "Player A"
        self.host_device_id = "player-a-device"
        self.side = PlayerSide.B
        self.state: GameState | None = None
        self.inbox: Queue[str] = Queue()
        self.history: list[GameEvent] = []
        self.last_rating_result: dict[str, object] | None = None
        self.rating_snapshot: dict[str, object] | None = None
        self.transport = ReliableUDP(
            bind,
            session_id,
            "player-b",
            self._on_message,
            self._on_diag,
            peer=peer,
            rto_ms=rto_ms,
            max_rto_ms=max_rto_ms,
        )
        self.logger: GameLogger | None = None
        self.log_dir = log_dir

    def start(self) -> None:
        self.transport.start()
        self.transport.send(
            "HELLO",
            {"name": self.name, "device_id": self.device_id, "protocol_version": 1},
        )
        self.inbox.put(f"Joining host at {self.transport.peer}")

    def close(self) -> None:
        self.transport.close()
        if self.logger:
            self.logger.close()

    def submit_move(self, source: str, destination: str) -> str:
        if not self.state:
            return "Not connected yet."
        self.transport.send(
            "MOVE_REQUEST",
            {
                "command_id": str(uuid4()),
                "expected_turn": self.state.turn_number,
                "expected_hash": self.state.hash(),
                "source": source,
                "destination": destination,
            },
        )
        return "Move request sent; waiting for host commit."

    def submit_penalty(self, nodes: list[str]) -> str:
        if not self.state:
            return "Not connected yet."
        self.transport.send(
            "PENALTY_SELECTION",
            {
                "command_id": str(uuid4()),
                "expected_turn": self.state.turn_number,
                "expected_hash": self.state.hash(),
                "nodes": nodes,
            },
        )
        return "Penalty selection sent; waiting for host commit."

    def submit_resign(self) -> str:
        self.transport.send("RESIGN", {"command_id": str(uuid4())})
        return "Resignation sent."

    def request_state(self) -> str:
        self.transport.send("STATE_REQUEST", {})
        return "State request sent."

    def _on_message(self, envelope: Envelope, _address: tuple[str, int]) -> None:
        if envelope.message_type == "HELLO_ACK":
            self.host_name = str(envelope.payload.get("host_name", self.host_name))
            self.host_device_id = str(envelope.payload.get("host_device_id", self.host_device_id))
            self._load_rating_snapshot(envelope.payload)
            self._load_state(envelope.payload["state"])
            self.transport.send("READY", {"name": self.name, "device_id": self.device_id})
            self.inbox.put("Handshake complete; sent READY.")
            return
        if envelope.message_type in {"GAME_STARTED", "MOVE_COMMITTED", "GAME_OVER", "STATE_SNAPSHOT"}:
            if "state" in envelope.payload:
                self._load_state(envelope.payload["state"])
            rating_result = envelope.payload.get("rating_result")
            if isinstance(rating_result, dict):
                self.last_rating_result = dict(rating_result)
            self._load_rating_snapshot(envelope.payload)
            if envelope.message_type == "STATE_SNAPSHOT":
                self.inbox.put("STATE_RESYNC completed from host snapshot.")
            events = self._events_from_payload(envelope.payload)
            self._commit_events(events)
            return
        if envelope.message_type == "COMMAND_REJECTED":
            self.inbox.put(f"Command rejected: {envelope.payload.get('reason')}")

    def _load_state(self, payload: Any) -> None:
        self.state = GameState.from_json(dict(payload))
        if self.logger is None:
            self.logger = GameLogger(self.log_dir, self.state.game_id, "player-b")

    def _load_rating_snapshot(self, payload: dict[str, Any]) -> None:
        snapshot = payload.get("rating_snapshot")
        if isinstance(snapshot, dict):
            self.rating_snapshot = dict(snapshot)

    def _events_from_payload(self, payload: dict[str, Any]) -> list[GameEvent]:
        events: list[GameEvent] = []
        for raw in payload.get("events", []):
            events.append(
                GameEvent(
                    event_id=str(raw["event_id"]),
                    event_type=str(raw["event_type"]),
                    actor=PlayerSide(str(raw["actor"])) if raw.get("actor") else None,
                    turn_number=int(raw["turn_number"]),
                    human_message=str(raw["human_message"]),
                    source=raw.get("source"),
                    destination=raw.get("destination"),
                    captured_piece_ids=[str(x) for x in raw.get("captured_piece_ids", [])],
                    promotion=[str(x) for x in raw.get("promotion", [])],
                    state_hash=str(raw.get("state_hash", "")),
                )
            )
        return events

    def _commit_events(self, events: list[GameEvent]) -> None:
        for event in events:
            self.history.append(event)
            if self.logger:
                self.logger.write_event(event)
            self.inbox.put(event.human_message)

    def _on_diag(self, event: str, fields: dict[str, object]) -> None:
        if self.logger:
            self.logger.write_network(event, **fields)
