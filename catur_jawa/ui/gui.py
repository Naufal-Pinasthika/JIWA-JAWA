from __future__ import annotations

from argparse import Namespace
from pathlib import Path
from typing import cast

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QCloseEvent, QFont, QKeyEvent, QPainter, QPixmap, QResizeEvent
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from catur_jawa.application.client import ClientRuntime
from catur_jawa.application.host import HostRuntime
from catur_jawa.config import RuntimeConfig
from catur_jawa.domain.models import Phase, PlayerSide
from catur_jawa.domain.rules import legal_captures, legal_moves
from catur_jawa.domain.state import GameState
from catur_jawa.transport.peer import parse_address
from catur_jawa.ui import theme
from catur_jawa.ui.board_view import BoardInteraction, BoardView


def run_gui(args: Namespace) -> int:
    app = QApplication([])
    app.setApplicationName("Catur Jawa")
    cfg = RuntimeConfig.from_env()
    runtime, local_side = _create_runtime(args, cfg)
    try:
        runtime.start()
    except Exception as exc:  # noqa: BLE001
        QMessageBox.critical(None, "Catur Jawa", f"Unable to start networking:\n{exc}")
        return 2

    window = GameWindow(runtime, local_side, args.name)
    window.resize(1280, 760)
    window.show()
    try:
        return app.exec()
    finally:
        if not window.closed:
            window.page.close_session()
            window.closed = True


def _create_runtime(args: Namespace, cfg: RuntimeConfig) -> tuple[HostRuntime | ClientRuntime, PlayerSide]:
    if args.mode == "host":
        bind = parse_address(args.bind or f"{cfg.bind_host}:{cfg.port}")
        return (
            HostRuntime(
                bind,
                args.name,
                cfg.log_dir,
                seed=args.seed,
                rto_ms=cfg.rto_ms,
                max_rto_ms=cfg.max_rto_ms,
            ),
            PlayerSide.A,
        )
    peer = parse_address(args.peer or f"{cfg.peer_host}:{cfg.port}")
    bind = parse_address(args.bind)
    return (
        ClientRuntime(
            bind,
            peer,
            args.name,
            cfg.log_dir,
            args.session_id or "00000000-0000-0000-0000-000000000000",
            rto_ms=cfg.rto_ms,
            max_rto_ms=cfg.max_rto_ms,
        ),
        PlayerSide.B,
    )


class MahoganyRoot(QWidget):
    def __init__(self) -> None:
        super().__init__()
        resource = Path(__file__).with_name("resources") / "mahogany_background.webp"
        self.texture = QPixmap(str(resource)) if resource.exists() else QPixmap()

    def paintEvent(self, _event: object) -> None:
        painter = QPainter(self)
        if not self.texture.isNull():
            scaled = self.texture.scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
            x = (self.width() - scaled.width()) // 2
            y = (self.height() - scaled.height()) // 2
            painter.drawPixmap(x, y, scaled)
        else:
            painter.fillRect(self.rect(), QColor(theme.WINDOW_BG))
        painter.fillRect(self.rect(), QColor(24, 14, 8, 64))


class PlayerBadge(QWidget):
    def __init__(self, side: PlayerSide, name: str):
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        token = QLabel(side.value)
        token.setObjectName("TokenA" if side is PlayerSide.A else "TokenB")
        token.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label = QLabel(name)
        label.setFont(QFont("Nunito Sans", 16, QFont.Weight.Bold))
        layout.addWidget(token)
        layout.addWidget(label)


class ConnectionBadge(QLabel):
    def set_state(self, label: str, color: str) -> None:
        self.setObjectName("Badge")
        self.setText(f"● {label}")
        self.setStyleSheet(
            f"QLabel#Badge {{ color: {theme.TEXT}; border: 1px solid {color}; "
            "background: #2D180D; border-radius: 19px; padding: 9px 18px; "
            "font-weight: 800; }"
        )


class TopBar(QWidget):
    def __init__(self, player_a: str, player_b: str):
        super().__init__()
        self.setFixedHeight(82)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(28, 10, 22, 8)
        layout.setSpacing(22)

        self.emblem = QLabel("CJ")
        self.emblem.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.emblem.setFixedSize(42, 42)
        self.emblem.setStyleSheet(
            f"border: 2px solid {theme.MUTED}; border-radius: 21px; "
            f"color: {theme.MUTED}; font-weight: 900;"
        )
        title = QLabel("Catur Jawa")
        title.setObjectName("Title")
        self.player_a = PlayerBadge(PlayerSide.A, player_a)
        self.turn = QLabel("Preparing")
        self.turn.setObjectName("TurnPill")
        self.turn.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.player_b = PlayerBadge(PlayerSide.B, player_b)
        self.connection = ConnectionBadge()
        self.menu = QPushButton("☰")
        self.menu.setObjectName("MenuButton")
        self.menu.setToolTip("Toggle utility drawer")
        self.menu.setAccessibleName("Toggle utility drawer")

        layout.addWidget(self.emblem)
        layout.addWidget(title)
        layout.addStretch(1)
        layout.addWidget(self.player_a)
        layout.addWidget(self.turn)
        layout.addWidget(self.player_b)
        layout.addStretch(1)
        layout.addWidget(self.connection)
        layout.addWidget(self.menu)

    def refresh(self, state: GameState | None, local_side: PlayerSide, pending: int, peer_known: bool) -> None:
        if state is None:
            self.turn.setText("Synchronizing")
            self.connection.set_state("CONNECTING", theme.WARNING)
            return
        if state.phase is Phase.PENALTY_SELECTION:
            self.turn.setText("Penalty selection")
        elif state.current_player is local_side:
            self.turn.setText("Your turn")
        else:
            self.turn.setText(f"{state.current_player.value}'s turn")
        if not peer_known:
            self.connection.set_state("LISTENING", theme.SUCCESS)
        elif pending > 0:
            self.connection.set_state("RETRYING", theme.WARNING)
        else:
            self.connection.set_state("CONNECTED", theme.SUCCESS)


class UtilityRail(QFrame):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("GlassRail")
        self.setFixedWidth(112)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 18, 8, 18)
        layout.setSpacing(14)
        layout.addStretch(1)
        self.history = self._button("↶\nHistory", "H")
        self.actions_button = self._button("◎\nActions", "A")
        self.info = self._button("i\nInfo", "I")
        layout.addWidget(self.history)
        layout.addWidget(self.actions_button)
        layout.addWidget(self.info)
        layout.addStretch(1)

    def _button(self, text: str, shortcut: str) -> QPushButton:
        button = QPushButton(text)
        button.setObjectName("RailButton")
        button.setMinimumSize(82, 72)
        button.setToolTip(f"Toggle {text.splitlines()[-1]} drawer ({shortcut})")
        button.setAccessibleName(text.splitlines()[-1])
        return button


class Drawer(QFrame):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("Drawer")
        self.setMaximumWidth(0)
        self.setMinimumWidth(0)
        self.active_name: str | None = None
        self.animation = QPropertyAnimation(self, b"maximumWidth", self)
        self.animation.setDuration(180)
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)
        header = QHBoxLayout()
        self.title = QLabel("Info")
        self.title.setObjectName("Title")
        self.close_button = QPushButton("‹")
        self.close_button.setFixedSize(46, 46)
        self.close_button.setToolTip("Close drawer")
        header.addWidget(self.title)
        header.addStretch(1)
        header.addWidget(self.close_button)
        self.stack = QStackedWidget()
        self.history_view = QTextEdit()
        self.history_view.setReadOnly(True)
        self.history_view.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        self.actions_page = self._create_actions()
        self.info_page = self._create_info()
        self.stack.addWidget(self.history_view)
        self.stack.addWidget(self.actions_page)
        self.stack.addWidget(self.info_page)
        layout.addLayout(header)
        layout.addWidget(self.stack, 1)

    def _create_actions(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        self.primary = QPushButton("Confirm selection")
        self.primary.setObjectName("Primary")
        self.clear = QPushButton("Clear selection")
        self.resync = QPushButton("Request resync")
        self.resign = QPushButton("Resign")
        self.resign.setObjectName("Danger")
        layout.addWidget(self.primary)
        layout.addWidget(self.clear)
        layout.addWidget(self.resync)
        layout.addStretch(1)
        layout.addWidget(self.resign)
        return page

    def _create_info(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        self.info_text = QTextEdit()
        self.info_text.setReadOnly(True)
        self.info_text.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        self.coordinates = QCheckBox("Show board coordinates")
        self.reduced_motion = QCheckBox("Reduced motion")
        layout.addWidget(self.info_text, 1)
        layout.addWidget(self.coordinates)
        layout.addWidget(self.reduced_motion)
        return page

    def open(self, name: str, content_width: int | None = None) -> None:
        pages = {"History": 0, "Actions": 1, "Info": 2}
        self.active_name = name
        self.title.setText(name)
        self.stack.setCurrentIndex(pages[name])
        if content_width is None:
            width = 320
        else:
            width = min(360, max(240, int(content_width * 0.26)))
            if content_width < 1100:
                width = min(width, 280)
        self.setMinimumWidth(width)
        self.animation.stop()
        self.animation.setStartValue(self.maximumWidth())
        self.animation.setEndValue(width)
        self.animation.start()

    def close_drawer(self) -> None:
        self.active_name = None
        self.setMinimumWidth(0)
        self.animation.stop()
        self.animation.setStartValue(self.maximumWidth())
        self.animation.setEndValue(0)
        self.animation.start()

    def toggle(self, name: str) -> None:
        if self.active_name == name and self.maximumWidth() > 0:
            self.close_drawer()
        else:
            self.open(name)


class BottomStatus(QFrame):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("BottomStatus")
        self.setFixedHeight(66)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(22, 10, 22, 10)
        layout.setSpacing(14)
        self.dot = QLabel("●")
        self.dot.setStyleSheet(f"color: {theme.SUCCESS}; font-size: 22px;")
        self.message = QLabel("Starting match.")
        self.message.setFont(QFont("Nunito Sans", 15, QFont.Weight.Bold))
        self.mode = QLabel("Normal  ·  H/A/I/C/R")
        self.mode.setObjectName("Muted")
        layout.addWidget(self.dot)
        layout.addWidget(self.message, 1)
        layout.addWidget(self.mode)

    def set_message(self, message: str, color: str = theme.SUCCESS) -> None:
        self.dot.setStyleSheet(f"color: {color}; font-size: 22px;")
        self.message.setText(message)


class ReconnectOverlay(QFrame):
    def __init__(self) -> None:
        super().__init__()
        self.setStyleSheet(
            f"background: {theme.GLASS_SURFACE}; border-radius: 24px; "
            f"border: 1px solid {theme.GLASS_OUTLINE};"
        )
        layout = QVBoxLayout(self)
        self.title = QLabel("Reconnecting...")
        self.title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title.setFont(QFont("Nunito Sans", 22, QFont.Weight.Bold))
        self.body = QLabel("Your committed game state is preserved.")
        self.body.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.body.setObjectName("Muted")
        layout.addWidget(self.title)
        layout.addWidget(self.body)
        self.hide()


class GameOverDialog(QDialog):
    def __init__(
        self,
        state: GameState,
        rating_result: dict[str, object] | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Game Over")
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.setStyleSheet(theme.stylesheet())
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        winner = state.winner.value if state.winner else "None"
        title = QLabel(f"Winner: Player {winner}")
        title.setObjectName("Title")
        rating_text = _rating_summary(rating_result)
        message_text = f"Match {state.game_id[:8]} ended on turn {state.turn_number}."
        if rating_text:
            message_text = f"{message_text}\n\n{rating_text}"
        message = QLabel(message_text)
        message.setWordWrap(True)
        close = QPushButton("OK")
        close.setObjectName("Primary")
        close.clicked.connect(self.accept)
        layout.addWidget(title)
        layout.addWidget(message)
        layout.addWidget(close)


class GamePage(QWidget):
    leave_requested = Signal()

    def __init__(self, runtime: HostRuntime | ClientRuntime, local_side: PlayerSide, player_name: str):
        super().__init__()
        self.runtime = runtime
        self.local_side = local_side
        self.player_name = player_name
        self.selected_node: str | None = None
        self.penalty_nodes: set[str] = set()
        self.last_source: str | None = None
        self.last_destination: str | None = None
        self.status_message = "Game started. Player A moves first."
        self.status_color = theme.SUCCESS
        self.show_coordinates = False
        self._game_over_shown = False
        self._history_rendered_count = -1
        self.setStyleSheet(theme.stylesheet())
        self._build_ui()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(150)
        self.refresh()

    def _build_ui(self) -> None:
        root = MahoganyRoot()
        outer = QVBoxLayout(root)
        outer.setContentsMargins(24, 8, 24, 22)
        outer.setSpacing(10)

        self.top = TopBar("Player A", "Player B")
        outer.addWidget(self.top)

        middle = QHBoxLayout()
        middle.setContentsMargins(0, 2, 0, 0)
        middle.setSpacing(18)
        self.board_host = QWidget()
        board_layout = QVBoxLayout(self.board_host)
        board_layout.setContentsMargins(0, 0, 0, 0)
        self.board = BoardView()
        self.board.node_clicked.connect(self._handle_node_click)
        board_layout.addWidget(self.board, 1)
        self.overlay = ReconnectOverlay()
        self.overlay.setParent(self.board_host)

        self.drawer = Drawer()
        self.rail = UtilityRail()
        middle.addWidget(self.board_host, 1)
        middle.addWidget(self.drawer)
        middle.addWidget(self.rail)
        outer.addLayout(middle, 1)

        self.bottom = BottomStatus()
        outer.addWidget(self.bottom)
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.addWidget(root)

        self.top.menu.clicked.connect(lambda: self._toggle_drawer("Info"))
        self.rail.history.clicked.connect(lambda: self._toggle_drawer("History"))
        self.rail.actions_button.clicked.connect(lambda: self._toggle_drawer("Actions"))
        self.rail.info.clicked.connect(lambda: self._toggle_drawer("Info"))
        self.drawer.close_button.clicked.connect(self.drawer.close_drawer)
        self.drawer.primary.clicked.connect(self._submit_penalty)
        self.drawer.clear.clicked.connect(self._clear_selection)
        self.drawer.resync.clicked.connect(self._request_state)
        self.drawer.resign.clicked.connect(self._resign)
        self.drawer.coordinates.toggled.connect(self._set_coordinates)

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self._position_overlay()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        key = event.key()
        if key == Qt.Key.Key_Escape:
            if self.drawer.maximumWidth() > 0:
                self.drawer.close_drawer()
            else:
                self._clear_selection()
            return
        if key == Qt.Key.Key_H:
            self._toggle_drawer("History")
            return
        if key == Qt.Key.Key_A:
            self._toggle_drawer("Actions")
            return
        if key == Qt.Key.Key_I:
            self._toggle_drawer("Info")
            return
        if key == Qt.Key.Key_C:
            self.drawer.coordinates.toggle()
            return
        if key == Qt.Key.Key_R:
            self._request_state()
            return
        super().keyPressEvent(event)

    def refresh(self) -> None:
        self._drain_runtime_messages()
        state = self._state()
        pending = self._pending_count()
        peer_known = self._peer_known()
        self.top.refresh(state, self.local_side, pending, peer_known)
        self._refresh_drawer(state, pending, peer_known)
        self._refresh_status(state, pending)
        interaction = BoardInteraction(
            selected_node=self.selected_node,
            penalty_nodes=frozenset(self.penalty_nodes),
            last_source=self.last_source,
            last_destination=self.last_destination,
            disabled=self._interaction_disabled(state),
            show_coordinates=self.show_coordinates,
        )
        self.board.set_position(state, self.local_side, interaction)
        self.overlay.setVisible(state is None or (pending > 0 and not peer_known))
        self._position_overlay()
        if state is not None and state.phase is Phase.FINISHED and not self._game_over_shown:
            self._game_over_shown = True
            dialog = GameOverDialog(state, self._rating_result(), self)
            dialog.finished.connect(lambda _result: self.leave_requested.emit())
            dialog.open()

    def _handle_node_click(self, node_id: str) -> None:
        state = self._state()
        if state is None:
            self._say("Synchronizing game state.", theme.WARNING)
            return
        if state.phase is Phase.FINISHED:
            self._say("Game over.", theme.WARNING)
            return
        if state.phase is Phase.PENALTY_SELECTION:
            self._handle_penalty_click(state, node_id)
            return
        if state.current_player is not self.local_side:
            self._say("Opponent turn. Waiting for a committed move.", theme.WARNING)
            return
        piece = state.piece_at(node_id)
        if self.selected_node is None:
            if piece and piece.owner is self.local_side:
                self.selected_node = node_id
                self._say("Piece selected. Choose a highlighted destination.", theme.ACCENT)
            else:
                self._say("Select one of your pieces.", theme.WARNING)
            return

        destinations = {
            move.destination: move for move in legal_moves(state, self.local_side, self.selected_node)
        }
        if node_id in destinations:
            source = self.selected_node
            self.last_source = source
            self.last_destination = node_id
            self.selected_node = None
            if isinstance(self.runtime, HostRuntime):
                message = self.runtime.submit_local_move(source, node_id)
            else:
                message = self.runtime.submit_move(source, node_id)
            self._say(message, theme.SUCCESS)
            self.refresh()
            return
        if piece and piece.owner is self.local_side:
            self.selected_node = node_id
            self._say("Selection changed.", theme.ACCENT)
            return
        self._say("That destination is not legal.", theme.WARNING)

    def _handle_penalty_click(self, state: GameState, node_id: str) -> None:
        if state.pending_penalty_by is not self.local_side or state.pending_penalty_for is None:
            self._say("Penalty selection belongs to the opponent.", theme.WARNING)
            return
        piece = state.piece_at(node_id)
        if piece is None or piece.owner is not state.pending_penalty_for:
            self._say("Select an offending player's piece.", theme.WARNING)
            return
        needed = min(3, len(state.pieces_for(state.pending_penalty_for)))
        if node_id in self.penalty_nodes:
            self.penalty_nodes.remove(node_id)
        elif len(self.penalty_nodes) < needed:
            self.penalty_nodes.add(node_id)
        self._say(f"Select three opponent pieces: {len(self.penalty_nodes)}/{needed}.", theme.ACCENT)
        self.drawer.open("Actions", self.width())

    def _submit_penalty(self) -> None:
        state = self._state()
        if state is None or state.phase is not Phase.PENALTY_SELECTION:
            self._say("No penalty selection is active.", theme.WARNING)
            return
        if state.pending_penalty_by is not self.local_side:
            self._say("Only the authorized opponent can remove pieces.", theme.WARNING)
            return
        message = self.runtime.submit_penalty(sorted(self.penalty_nodes))
        self.penalty_nodes.clear()
        self._say(message, theme.SUCCESS)
        self.refresh()

    def _clear_selection(self) -> None:
        self.selected_node = None
        self.penalty_nodes.clear()
        self._say("Selection cleared.", theme.SUCCESS)
        self.refresh()

    def _request_state(self) -> None:
        if isinstance(self.runtime, ClientRuntime):
            self._say(self.runtime.request_state(), theme.ACCENT)
        else:
            state = self._state()
            text = f"Host state hash {state.hash()[:12]}." if state else "No state yet."
            self._say(text, theme.ACCENT)

    def _resign(self) -> None:
        result = QMessageBox.question(
            self,
            "Resign",
            "Resign this match?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if result == QMessageBox.StandardButton.Yes:
            self._say(self.runtime.submit_resign(), theme.DANGER)
            self.refresh()

    def _set_coordinates(self, enabled: bool) -> None:
        self.show_coordinates = enabled
        self._say("Board coordinates shown." if enabled else "Board coordinates hidden.", theme.ACCENT)
        self.refresh()

    def _refresh_drawer(self, state: GameState | None, pending: int, peer_known: bool) -> None:
        self._refresh_history()
        self._refresh_actions(state)
        self._refresh_info(state, pending, peer_known)

    def _refresh_history(self) -> None:
        events = cast(list[object], self.runtime.history)
        if getattr(self, "_history_rendered_count", -1) == len(events):
            return
        self._history_rendered_count = len(events)
        html = ["<style>body{font-family:'Nunito Sans','Inter','Noto Sans','DejaVu Sans',sans-serif;}"
                "hr{border:0;border-top:1px solid rgba(238,194,136,.18);}"
                ".turn{color:#C9B29A;font-weight:700;font-size:12px;}"
                ".action{color:#F6EBDD;font-weight:800;font-size:15px;}</style>"]
        for event in events[-80:]:
            turn = getattr(event, "turn_number", 0)
            event_type = getattr(event, "event_type", "EVENT")
            message = getattr(event, "human_message", "")
            html.append(
                f"<p><span class='turn'>Turn {turn} · {self._human_event_type(str(event_type))}</span><br>"
                f"<span class='action'>{self._escape_html(str(message))}</span></p><hr>"
            )
        if not events:
            html.append("<p class='action'>No committed moves yet.</p>")
        self.drawer.history_view.setHtml("".join(html))
        self.drawer.history_view.verticalScrollBar().setValue(
            self.drawer.history_view.verticalScrollBar().maximum()
        )

    def _refresh_actions(self, state: GameState | None) -> None:
        penalty_active = (
            state is not None
            and state.phase is Phase.PENALTY_SELECTION
            and state.pending_penalty_by is self.local_side
        )
        self.drawer.resync.setEnabled(isinstance(self.runtime, ClientRuntime))
        self.drawer.resign.setEnabled(state is not None and state.phase is not Phase.FINISHED)
        if penalty_active and state and state.pending_penalty_for:
            needed = min(3, len(state.pieces_for(state.pending_penalty_for)))
            self.drawer.primary.setText(f"Confirm removal ({len(self.penalty_nodes)}/{needed})")
            self.drawer.primary.setEnabled(len(self.penalty_nodes) == needed)
        else:
            self.drawer.primary.setText("Confirm selection")
            self.drawer.primary.setEnabled(False)

    def _refresh_info(self, state: GameState | None, pending: int, peer_known: bool) -> None:
        if state is None:
            html = self._info_html([("Match", [("Status", "Waiting for host snapshot.")])])
        else:
            peer = getattr(self.runtime.transport, "peer", None)
            rating_rows = self._rating_rows()
            html = self._info_html(
                [
                    (
                        "Match",
                        [
                            ("Match ID", state.game_id[:12] + "..."),
                            ("Turn", str(state.turn_number)),
                            ("Phase", state.phase.value.title().replace("_", " ")),
                            ("Current player", f"Player {state.current_player.value}"),
                        ],
                    ),
                    (
                        "Players",
                        [
                            ("You", f"{self.player_name}, Player {self.local_side.value}"),
                            ("Opponent", f"Player {self.local_side.opponent.value}"),
                        ],
                    ),
                    (
                        "Connection",
                        [
                            ("Status", "Connected" if peer_known else "Listening"),
                            ("Peer", str(peer) if peer else "Waiting"),
                            ("Pending packets", str(pending)),
                        ],
                    ),
                    ("Ratings", rating_rows),
                    (
                        "Advanced",
                        [
                            ("State hash", state.hash()[:24] + "..."),
                            ("Protocol", "v1"),
                        ],
                    ),
                ]
            )
        self.drawer.info_text.setHtml(html)

    def _refresh_status(self, state: GameState | None, pending: int) -> None:
        if pending > 0:
            self.bottom.set_message("Connection degraded. Retrying automatically.", theme.WARNING)
            return
        if state is None:
            self.bottom.set_message("Synchronizing game state.", theme.WARNING)
            return
        if state.phase is Phase.PENALTY_SELECTION:
            self.bottom.set_message("Select three opponent pieces for removal.", theme.ACCENT)
            return
        if state.current_player is self.local_side:
            if legal_captures(state, self.local_side):
                self.bottom.set_message("Capture available.", theme.CAPTURE)
            else:
                self.bottom.set_message("Your turn. Select one of your pieces.", theme.SUCCESS)
            return
        self.bottom.set_message(self.status_message, self.status_color)

    def _interaction_disabled(self, state: GameState | None) -> bool:
        if state is None or state.phase is Phase.FINISHED:
            return True
        if state.phase is Phase.PENALTY_SELECTION:
            return state.pending_penalty_by is not self.local_side
        return state.current_player is not self.local_side

    def _state(self) -> GameState | None:
        state = self.runtime.state
        return state if isinstance(state, GameState) else None

    def _pending_count(self) -> int:
        pending_count = getattr(self.runtime.transport, "pending_count", None)
        return int(pending_count()) if callable(pending_count) else 0

    def _peer_known(self) -> bool:
        return getattr(self.runtime.transport, "peer", None) is not None

    def _rating_result(self) -> dict[str, object] | None:
        result = getattr(self.runtime, "last_rating_result", None)
        return result if isinstance(result, dict) else None

    def _rating_rows(self) -> list[tuple[str, str]]:
        snapshot = getattr(self.runtime, "rating_snapshot", None)
        rows = rating_snapshot_rows(snapshot)
        return rows if rows else [("Status", "Waiting for host rating data.")]

    def _drain_runtime_messages(self) -> None:
        inbox = self.runtime.inbox
        while not inbox.empty():
            self._say(str(inbox.get()), theme.SUCCESS)

    def _say(self, message: str, color: str) -> None:
        if not message:
            return
        self.status_message = message
        self.status_color = color

    def _toggle_drawer(self, name: str) -> None:
        if self.drawer.active_name == name and self.drawer.maximumWidth() > 0:
            self.drawer.close_drawer()
        else:
            self.drawer.open(name, self.width())
        QTimer.singleShot(0, self.board.update)

    def _position_overlay(self) -> None:
        width = min(460, max(280, self.board_host.width() - 120))
        height = 118
        self.overlay.setGeometry(
            (self.board_host.width() - width) // 2,
            (self.board_host.height() - height) // 2,
            width,
            height,
        )

    def close_session(self) -> None:
        self.timer.stop()
        self.runtime.close()

    def _human_event_type(self, event_type: str) -> str:
        return event_type.replace("_", " ").title()

    def _escape_html(self, value: str) -> str:
        return value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    def _info_html(self, sections: list[tuple[str, list[tuple[str, str]]]]) -> str:
        html = [
            "<style>body{font-family:'Nunito Sans','Inter','Noto Sans','DejaVu Sans',sans-serif;}"
            ".section{color:#F0B94F;font-weight:800;font-size:14px;margin-top:12px;}"
            ".label{color:#C9B29A;font-weight:700;font-size:12px;}"
            ".value{color:#F6EBDD;font-weight:800;font-size:14px;}</style>"
        ]
        for title, rows in sections:
            html.append(f"<p class='section'>{self._escape_html(title.upper())}</p>")
            for label, value in rows:
                html.append(
                    "<p>"
                    f"<span class='label'>{self._escape_html(label)}</span><br>"
                    f"<span class='value'>{self._escape_html(value)}</span>"
                    "</p>"
                )
        return "".join(html)


def _rating_summary(rating_result: dict[str, object] | None) -> str:
    if not rating_result:
        return ""
    player_a = rating_result.get("player_a")
    player_b = rating_result.get("player_b")
    if not isinstance(player_a, dict) or not isinstance(player_b, dict):
        return ""
    return "\n".join(
        line
        for line in (
            _rating_line("Player A", player_a),
            _rating_line("Player B", player_b),
        )
        if line
    )


def rating_snapshot_lines(snapshot: object) -> list[str]:
    return [f"{label}: {value}" for label, value in rating_snapshot_rows(snapshot)]


def rating_snapshot_rows(snapshot: object) -> list[tuple[str, str]]:
    if not isinstance(snapshot, dict):
        return []
    rows: list[tuple[str, str]] = []
    player_a = snapshot.get("player_a")
    player_b = snapshot.get("player_b")
    if isinstance(player_a, dict):
        rows.append(("Player A", _snapshot_text(player_a)))
    if isinstance(player_b, dict):
        rows.append(("Player B", _snapshot_text(player_b)))
    return [(label, value) for label, value in rows if value]


def _snapshot_text(payload: dict[object, object]) -> str:
    name = str(payload.get("display_name", "Player"))
    rating = _float_value(payload.get("rating"))
    games = payload.get("games_played")
    if rating is None or not isinstance(games, int):
        return ""
    game_label = "game" if games == 1 else "games"
    return f"{name} · {rating:.0f} · {games} {game_label}"


def _rating_line(side: str, payload: dict[object, object]) -> str:
    name = str(payload.get("display_name", side))
    before = _float_value(payload.get("before"))
    after = _float_value(payload.get("after"))
    delta = _float_value(payload.get("delta"))
    if before is None or after is None or delta is None:
        return ""
    sign = "+" if delta >= 0 else ""
    return f"{side} {name}: {before:.0f} -> {after:.0f} ({sign}{delta:.0f})"


def _float_value(value: object) -> float | None:
    if isinstance(value, int | float):
        return float(value)
    return None


class GameWindow(QMainWindow):
    def __init__(self, runtime: HostRuntime | ClientRuntime, local_side: PlayerSide, player_name: str):
        super().__init__()
        self.closed = False
        self.page = GamePage(runtime, local_side, player_name)
        self.setWindowTitle(f"Catur Jawa · Player {local_side.value}")
        self.setMinimumSize(1180, 700)
        self.setStyleSheet(theme.stylesheet())
        self.setCentralWidget(self.page)

    def closeEvent(self, event: object) -> None:
        if not self.closed:
            self.page.close_session()
            self.closed = True
        super().closeEvent(cast(QCloseEvent, event))
