from __future__ import annotations

from queue import Queue
from pathlib import Path
from typing import Any
from uuid import uuid4

from catur_jawa.application.events import committed_payload
from catur_jawa.application.match import HostMatch
from catur_jawa.domain.models import GameEvent, Phase, PlayerSide
from catur_jawa.domain.state import GameState
from catur_jawa.logging.game_logger import GameLogger
from catur_jawa.rating.repository import RatingRepository
from catur_jawa.rating.service import RatingService
from catur_jawa.transport.protocol import Envelope
from catur_jawa.transport.reliable_udp import ReliableUDP


class HostRuntime:
    def __init__(
        self,
        bind: tuple[str, int],
        name: str,
        log_dir: str,
        seed: int | None = None,
        rto_ms: int = 300,
        max_rto_ms: int = 2000,
        device_id: str = "player-a-device",
        rating_db_path: str | Path = "ratings.sqlite3",
    ):
        self.name = name
        self.device_id = device_id
        self.side = PlayerSide.A
        self.match = HostMatch(seed=seed)
        self.inbox: Queue[str] = Queue()
        self.history: list[GameEvent] = []
        self.peer_name = "Player B"
        self.peer_device_id = "player-b-device"
        self.last_rating_result: dict[str, object] | None = None
        self.rating_snapshot: dict[str, object] | None = None
        self.rating_repository = RatingRepository(rating_db_path)
        self.rating_service = RatingService(self.rating_repository)
        self._rating_snapshot()
        self.transport = ReliableUDP(
            bind,
            self.match.state.game_id,
            "player-a",
            self._on_message,
            self._on_diag,
            rto_ms=rto_ms,
            max_rto_ms=max_rto_ms,
        )
        self.logger = GameLogger(log_dir, self.match.state.game_id, "player-a")
        self.peer_ready = False

    @property
    def state(self) -> GameState:
        return self.match.state

    def start(self) -> None:
        self.transport.start()
        event = self.match.start_event()
        self._commit_local_events([event])
        self.inbox.put(f"Host listening on {self.transport.local_address()[0]}:{self.transport.local_address()[1]}")

    def close(self) -> None:
        self.transport.close()
        self.logger.close()
        self.rating_repository.close()

    def submit_local_move(self, source: str, destination: str) -> str:
        response = self.match.process_move(
            str(uuid4()), self.side, self.state.turn_number, self.state.hash(), source, destination
        )
        return self._handle_response(response.message_type, response.payload)

    def submit_penalty(self, nodes: list[str]) -> str:
        response = self.match.process_penalty(
            str(uuid4()), self.side, self.state.turn_number, self.state.hash(), nodes
        )
        return self._handle_response(response.message_type, response.payload)

    def submit_resign(self) -> str:
        response = self.match.process_resign(str(uuid4()), self.side)
        return self._handle_response(response.message_type, response.payload)

    def _on_message(self, envelope: Envelope, address: tuple[str, int]) -> None:
        if envelope.message_type == "HELLO":
            self.peer_name = str(envelope.payload.get("name", "Player B"))
            self.peer_device_id = str(envelope.payload.get("device_id", "player-b-device"))
            self.transport.set_peer(address)
            self.transport.send(
                "HELLO_ACK",
                {
                    "assigned_player": "B",
                    "host_player": "A",
                    "host_name": self.name,
                    "host_device_id": self.device_id,
                    "game_id": self.state.game_id,
                    **self.match.snapshot_payload(),
                    "rating_snapshot": self._rating_snapshot(),
                },
                address,
            )
            self.inbox.put(f"Client hello from {address[0]}:{address[1]}")
            return
        if envelope.message_type == "READY":
            self.peer_name = str(envelope.payload.get("name", self.peer_name))
            self.peer_device_id = str(envelope.payload.get("device_id", self.peer_device_id))
            self.peer_ready = True
            payload = committed_payload(self.state, [self.history[0]]) if self.history else self.match.snapshot_payload()
            payload["rating_snapshot"] = self._rating_snapshot()
            self.transport.send("GAME_STARTED", payload, address)
            self.inbox.put("Client is ready.")
            return
        if envelope.message_type == "MOVE_REQUEST":
            p = envelope.payload
            response = self.match.process_move(
                str(p["command_id"]),
                PlayerSide.B,
                int(p["expected_turn"]),
                str(p["expected_hash"]),
                str(p["source"]),
                str(p["destination"]),
            )
            self._send_response(response.message_type, response.payload, address)
            return
        if envelope.message_type == "PENALTY_SELECTION":
            p = envelope.payload
            response = self.match.process_penalty(
                str(p["command_id"]),
                PlayerSide.B,
                int(p["expected_turn"]),
                str(p["expected_hash"]),
                [str(node) for node in p["nodes"]],
            )
            self._send_response(response.message_type, response.payload, address)
            return
        if envelope.message_type == "STATE_REQUEST":
            self.transport.send("STATE_SNAPSHOT", self.match.snapshot_payload(), address)
            return
        if envelope.message_type == "RESIGN":
            response = self.match.process_resign(str(envelope.payload["command_id"]), PlayerSide.B)
            self._send_response(response.message_type, response.payload, address)

    def _send_response(self, message_type: str, payload: dict[str, Any], address: tuple[str, int]) -> None:
        if message_type in {"MOVE_COMMITTED", "GAME_OVER"}:
            payload = self._attach_rating_result(payload)
            events = self._events_from_payload(payload)
            self._commit_local_events(events)
        self.transport.send(message_type, payload, address)
        if message_type == "COMMAND_REJECTED":
            self.inbox.put(f"Rejected client command: {payload.get('reason')}")

    def _handle_response(self, message_type: str, payload: dict[str, Any]) -> str:
        if message_type in {"MOVE_COMMITTED", "GAME_OVER"}:
            payload = self._attach_rating_result(payload)
            events = self._events_from_payload(payload)
            self._commit_local_events(events)
            if self.transport.peer:
                self.transport.send(message_type, payload)
            return str(events[-1].human_message if events else "Committed.")
        return str(payload.get("reason", "Command rejected."))

    def _attach_rating_result(self, payload: dict[str, Any]) -> dict[str, Any]:
        if self.state.phase is not Phase.FINISHED:
            return payload
        enriched = dict(payload)
        if self.last_rating_result is None and not self.state.result_persisted:
            score_a = self._score_a()
            result = self.rating_service.record_result(
                self.state.game_id,
                self.device_id,
                self.name,
                self.peer_device_id,
                self.peer_name,
                score_a,
            )
            self.state.result_persisted = True
            if result is not None:
                self.last_rating_result = result.to_json()
        if self.last_rating_result is not None:
            enriched["rating_result"] = self.last_rating_result
        enriched["rating_snapshot"] = self._rating_snapshot()
        enriched["state"] = self.state.to_json()
        enriched["state_hash"] = self.state.hash()
        enriched["turn_number"] = self.state.turn_number
        return enriched

    def _score_a(self) -> float:
        if self.state.winner is PlayerSide.A:
            return 1.0
        if self.state.winner is PlayerSide.B:
            return 0.0
        return 0.5

    def _rating_snapshot(self) -> dict[str, object]:
        player_a = self.rating_service.rating_snapshot(self.device_id, self.name)
        player_b = self.rating_service.rating_snapshot(self.peer_device_id, self.peer_name)
        self.rating_snapshot = {
            "player_a": player_a.to_json(),
            "player_b": player_b.to_json(),
        }
        return self.rating_snapshot

    def _events_from_payload(self, payload: dict[str, Any]) -> list[GameEvent]:
        # Runtime history only needs readable event dictionaries; rebuild a compact object.
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

    def _commit_local_events(self, events: list[GameEvent]) -> None:
        for event in events:
            self.history.append(event)
            self.logger.write_event(event)
            self.inbox.put(event.human_message)

    def _on_diag(self, event: str, fields: dict[str, object]) -> None:
        self.logger.write_network(event, **fields)
