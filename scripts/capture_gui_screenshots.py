from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import cast

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from catur_jawa.domain.models import Phase, PlayerSide  # noqa: E402
from catur_jawa.domain.state import GameState  # noqa: E402
from catur_jawa.ui.gui import GameWindow  # noqa: E402


@dataclass(slots=True)
class FakeTransport:
    peer: tuple[str, int] | None = ("127.0.0.1", 9999)
    pending: int = 0

    def pending_count(self) -> int:
        return self.pending


class FakeInbox:
    def empty(self) -> bool:
        return True

    def get(self) -> str:
        return ""


class FakeRuntime:
    def __init__(self, state: GameState, side: PlayerSide, pending: int = 0, peer: bool = True):
        self.name = f"Player {side.value}"
        self.side = side
        self.state = state
        self.history: list[object] = []
        self.inbox = FakeInbox()
        self.transport = FakeTransport(("127.0.0.1", 9999) if peer else None, pending)

    def start(self) -> None:
        return None

    def close(self) -> None:
        return None

    def submit_local_move(self, _source: str, _destination: str) -> str:
        return "Demo move submitted."

    def submit_move(self, _source: str, _destination: str) -> str:
        return "Demo move request sent."

    def submit_penalty(self, _nodes: list[str]) -> str:
        return "Demo penalty submitted."

    def submit_resign(self) -> str:
        return "Demo resignation submitted."


def _state(name: str, phase: Phase = Phase.NORMAL) -> GameState:
    state = GameState.new(name, PlayerSide.A)
    state.phase = phase
    return state


def _save(
    app: QApplication,
    path: Path,
    state: GameState,
    side: PlayerSide,
    pending: int = 0,
    peer: bool = True,
    size: tuple[int, int] = (1280, 760),
    drawer: str | None = None,
) -> None:
    runtime = FakeRuntime(state, side, pending, peer)
    window = GameWindow(cast(object, runtime), side, runtime.name)  # type: ignore[arg-type]
    window.resize(*size)
    window.show()
    for _ in range(4):
        app.processEvents()
    if drawer:
        window.page.drawer.open(drawer, window.page.width())
        for _ in range(8):
            app.processEvents()
    window.grab().save(str(path))
    window.close()


def main() -> int:
    app = QApplication.instance() or QApplication([])
    out = Path("docs/screenshots")
    out.mkdir(parents=True, exist_ok=True)

    host = _state("gui-host-demo")
    _save(app, out / "host-normal.png", host, PlayerSide.A)
    _save(app, out / "layout-1280x720.png", host, PlayerSide.A, size=(1280, 720))
    _save(app, out / "layout-1366x768.png", host, PlayerSide.A, size=(1366, 768))
    _save(app, out / "layout-1600x900.png", host, PlayerSide.A, size=(1600, 900))
    _save(app, out / "layout-1920x1080.png", host, PlayerSide.A, size=(1920, 1080))
    _save(app, out / "layout-info-open.png", host, PlayerSide.A, size=(1280, 720), drawer="Info")
    _save(
        app,
        out / "layout-history-open.png",
        host,
        PlayerSide.A,
        size=(1280, 720),
        drawer="History",
    )

    client = _state("gui-client-demo")
    client.current_player = PlayerSide.A
    _save(app, out / "client-normal.png", client, PlayerSide.B)

    degraded = _state("gui-degraded-demo")
    _save(app, out / "packet-loss-degraded.png", degraded, PlayerSide.A, pending=4)

    penalty = _state("gui-penalty-demo", Phase.PENALTY_SELECTION)
    penalty.pending_penalty_by = PlayerSide.B
    penalty.pending_penalty_for = PlayerSide.A
    penalty.current_player = PlayerSide.B
    _save(app, out / "penalty-selection.png", penalty, PlayerSide.B)

    game_over = _state("gui-game-over-demo", Phase.FINISHED)
    game_over.winner = PlayerSide.A
    _save(app, out / "game-over.png", game_over, PlayerSide.A)

    print(f"Wrote screenshots to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
