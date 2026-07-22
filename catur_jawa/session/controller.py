from __future__ import annotations

from dataclasses import dataclass

from catur_jawa.application.client import ClientRuntime
from catur_jawa.application.host import HostRuntime
from catur_jawa.config import RuntimeConfig
from catur_jawa.domain.models import PlayerSide
from catur_jawa.session.config import HostConfig, JoinConfig
from catur_jawa.session.states import UiSessionState


@dataclass(slots=True)
class ActiveSession:
    runtime: HostRuntime | ClientRuntime
    side: PlayerSide
    generation: int


class SessionController:
    def __init__(self, runtime_config: RuntimeConfig | None = None):
        self.runtime_config = runtime_config or RuntimeConfig.from_env()
        self.state = UiSessionState.MENU
        self.active: ActiveSession | None = None
        self.generation = 0

    def start_host(self, config: HostConfig, device_id: str = "player-a-device") -> ActiveSession:
        validated = config.validate()
        self.disconnect()
        self.state = UiSessionState.HOST_STARTING
        self.generation += 1
        runtime = HostRuntime(
            (validated.bind_host, validated.port),
            validated.display_name,
            self.runtime_config.log_dir,
            rto_ms=self.runtime_config.rto_ms,
            max_rto_ms=self.runtime_config.max_rto_ms,
            device_id=device_id,
        )
        runtime.start()
        self.active = ActiveSession(runtime, PlayerSide.A, self.generation)
        self.state = UiSessionState.HOST_LOBBY
        return self.active

    def join_host(self, config: JoinConfig, device_id: str = "player-b-device") -> ActiveSession:
        validated = config.validate()
        self.disconnect()
        self.state = UiSessionState.CONNECTING
        self.generation += 1
        runtime = ClientRuntime(
            (validated.bind_host, validated.bind_port),
            (validated.host, validated.port),
            validated.display_name,
            self.runtime_config.log_dir,
            "00000000-0000-0000-0000-000000000000",
            rto_ms=self.runtime_config.rto_ms,
            max_rto_ms=self.runtime_config.max_rto_ms,
            device_id=device_id,
        )
        runtime.start()
        self.active = ActiveSession(runtime, PlayerSide.B, self.generation)
        self.state = UiSessionState.CONNECTING
        return self.active

    def enter_game(self) -> ActiveSession:
        if self.active is None:
            raise RuntimeError("No active session.")
        self.state = UiSessionState.IN_GAME
        return self.active

    def disconnect(self) -> None:
        if self.active is not None:
            self.state = UiSessionState.DISCONNECTING
            self.active.runtime.close()
            self.active = None
        self.state = UiSessionState.MENU

    def is_current(self, generation: int) -> bool:
        return self.active is not None and self.active.generation == generation
