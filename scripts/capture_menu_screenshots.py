from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import cast

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSettings  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from catur_jawa.application.host import HostRuntime  # noqa: E402
from catur_jawa.main import MainWindow  # noqa: E402
from catur_jawa.domain.models import PlayerSide  # noqa: E402
from catur_jawa.session.controller import ActiveSession, SessionController  # noqa: E402


@dataclass(slots=True)
class DemoTransport:
    def local_address(self) -> tuple[str, int]:
        return ("0.0.0.0", 9999)


@dataclass(slots=True)
class DemoHostRuntime:
    name: str = "Alice"
    peer_ready: bool = False
    transport: DemoTransport = field(default_factory=DemoTransport)

    def close(self) -> None:
        return None


def _window(app: QApplication, size: tuple[int, int]) -> MainWindow:
    settings = QSettings("JIWA-JAWA-SHOT", f"Catur Jawa {size[0]}x{size[1]}")
    settings.clear()
    window = MainWindow(SessionController(), settings)
    window.resize(*size)
    window.show()
    for _ in range(4):
        app.processEvents()
    return window


def _save(window: MainWindow, app: QApplication, path: Path) -> None:
    for _ in range(4):
        app.processEvents()
    window.grab().save(str(path))
    window.close()


def main() -> int:
    app = QApplication.instance() or QApplication([])
    out = Path("docs/screenshots")
    out.mkdir(parents=True, exist_ok=True)

    menu = _window(app, (1180, 760))
    _save(menu, app, out / "menu-default.png")

    menu_large = _window(app, (1600, 900))
    _save(menu_large, app, out / "menu-large-window.png")

    menu_compact = _window(app, (960, 640))
    _save(menu_compact, app, out / "menu-compact-window.png")

    host = _window(app, (1180, 760))
    host.stack.setCurrentWidget(host.host_setup)
    _save(host, app, out / "host-setup.png")

    join = _window(app, (1180, 760))
    join.stack.setCurrentWidget(join.join_setup)
    _save(join, app, out / "join-setup.png")

    error = _window(app, (1180, 760))
    error.stack.setCurrentWidget(error.host_setup)
    error.host_setup.show_error("Display name is required.")
    _save(error, app, out / "host-validation-error.png")

    waiting = _window(app, (1180, 760))
    waiting.lobby.set_session(
        ActiveSession(cast(HostRuntime, DemoHostRuntime(peer_ready=False)), PlayerSide.A, 1)
    )
    waiting.stack.setCurrentWidget(waiting.lobby)
    _save(waiting, app, out / "host-lobby-waiting.png")

    two_players = _window(app, (1180, 760))
    two_players.lobby.set_session(
        ActiveSession(cast(HostRuntime, DemoHostRuntime(peer_ready=True)), PlayerSide.A, 1)
    )
    two_players.stack.setCurrentWidget(two_players.lobby)
    _save(two_players, app, out / "lobby-two-players.png")

    connecting = _window(app, (1180, 760))
    connecting.connecting.set_target("127.0.0.1:9999")
    connecting.stack.setCurrentWidget(connecting.connecting)
    _save(connecting, app, out / "connecting.png")

    how = _window(app, (1180, 760))
    how.stack.setCurrentWidget(how.how_to_play)
    _save(how, app, out / "how-to-play.png")

    settings = _window(app, (1180, 760))
    settings.stack.setCurrentWidget(settings.settings_page)
    _save(settings, app, out / "settings.png")

    print(f"Wrote menu screenshots to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
