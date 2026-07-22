from __future__ import annotations

from collections import OrderedDict
from random import Random
from uuid import uuid4

from catur_jawa.application.events import CommandResponse, committed_payload
from catur_jawa.domain.models import GameEvent, Phase, PlayerSide
from catur_jawa.domain.rules import RuleError, apply_move, apply_penalty_selection, resign
from catur_jawa.domain.state import GameState


class HostMatch:
    def __init__(self, game_id: str | None = None, seed: int | None = None, cache_size: int = 256):
        rng = Random(seed)
        starting_player = PlayerSide.A if rng.randrange(2) == 0 else PlayerSide.B
        self.state = GameState.new(game_id or str(uuid4()), starting_player)
        self.command_cache: OrderedDict[str, CommandResponse] = OrderedDict()
        self.cache_size = cache_size

    def start_event(self) -> GameEvent:
        return GameEvent(
            event_id=str(uuid4()),
            event_type="GAME_STARTED",
            actor=self.state.current_player,
            turn_number=self.state.turn_number,
            human_message=f"Game started. Player {self.state.current_player.value} moves first.",
            phase=self.state.phase,
            state_hash=self.state.hash(),
        )

    def process_move(
        self,
        command_id: str,
        side: PlayerSide,
        expected_turn: int,
        expected_hash: str,
        source: str,
        destination: str,
    ) -> CommandResponse:
        cached = self._cached(command_id)
        if cached:
            return cached
        if expected_turn != self.state.turn_number or expected_hash != self.state.hash():
            return self._store(
                command_id,
                CommandResponse(
                    False,
                    "COMMAND_REJECTED",
                    {
                        "reason": "State mismatch; request a resync.",
                        "turn_number": self.state.turn_number,
                        "state_hash": self.state.hash(),
                    },
                ),
            )
        try:
            events = apply_move(self.state, side, source, destination)
        except RuleError as exc:
            return self._store(
                command_id, CommandResponse(False, "COMMAND_REJECTED", {"reason": str(exc)})
            )
        message_type = "GAME_OVER" if self.state.phase is Phase.FINISHED else "MOVE_COMMITTED"
        return self._store(command_id, CommandResponse(True, message_type, committed_payload(self.state, events)))

    def process_penalty(
        self, command_id: str, side: PlayerSide, expected_turn: int, expected_hash: str, nodes: list[str]
    ) -> CommandResponse:
        cached = self._cached(command_id)
        if cached:
            return cached
        if expected_turn != self.state.turn_number or expected_hash != self.state.hash():
            return self._store(
                command_id,
                CommandResponse(
                    False,
                    "COMMAND_REJECTED",
                    {"reason": "State mismatch; request a resync."},
                ),
            )
        try:
            events = apply_penalty_selection(self.state, side, nodes)
        except RuleError as exc:
            return self._store(
                command_id, CommandResponse(False, "COMMAND_REJECTED", {"reason": str(exc)})
            )
        message_type = "GAME_OVER" if self.state.phase is Phase.FINISHED else "MOVE_COMMITTED"
        return self._store(command_id, CommandResponse(True, message_type, committed_payload(self.state, events)))

    def process_resign(self, command_id: str, side: PlayerSide) -> CommandResponse:
        cached = self._cached(command_id)
        if cached:
            return cached
        try:
            events = resign(self.state, side)
        except RuleError as exc:
            return self._store(
                command_id, CommandResponse(False, "COMMAND_REJECTED", {"reason": str(exc)})
            )
        return self._store(
            command_id, CommandResponse(True, "GAME_OVER", committed_payload(self.state, events))
        )

    def snapshot_payload(self) -> dict[str, object]:
        return {
            "game_id": self.state.game_id,
            "turn_number": self.state.turn_number,
            "state_hash": self.state.hash(),
            "state": self.state.to_json(),
        }

    def _cached(self, command_id: str) -> CommandResponse | None:
        response = self.command_cache.get(command_id)
        if response:
            self.command_cache.move_to_end(command_id)
        return response

    def _store(self, command_id: str, response: CommandResponse) -> CommandResponse:
        self.command_cache[command_id] = response
        self.command_cache.move_to_end(command_id)
        while len(self.command_cache) > self.cache_size:
            self.command_cache.popitem(last=False)
        return response
