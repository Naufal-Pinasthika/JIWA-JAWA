from __future__ import annotations

import sys
from typing import cast
from uuid import uuid4

from PySide6.QtCore import QSettings, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QCloseEvent, QFont, QMouseEvent
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from catur_jawa.application.host import HostRuntime
from catur_jawa.domain.models import PlayerSide
from catur_jawa.session.addressing import room_address
from catur_jawa.session.config import ConfigError, HostConfig, JoinConfig
from catur_jawa.session.controller import ActiveSession, SessionController
from catur_jawa.session.states import UiSessionState
from catur_jawa.ui import metrics, theme, typography
from catur_jawa.ui.gui import GamePage, MahoganyRoot, PlayerBadge, rating_snapshot_lines


class GlassPanel(QFrame):
    def __init__(self, width: int = metrics.MENU_PANEL_WIDTH) -> None:
        super().__init__()
        self.setObjectName("GlassPanel")
        self.setMinimumWidth(min(width, 420))
        self.setMaximumWidth(width)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        self.setStyleSheet(
            f"QFrame#GlassPanel {{ background: {theme.GLASS_SURFACE}; "
            f"border: 1px solid {theme.GLASS_OUTLINE}; border-radius: {metrics.PANEL_RADIUS}px; }}"
        )


class AppTitleBar(QFrame):
    def __init__(self, window: QMainWindow):
        super().__init__()
        self.parent_window = window
        self.drag_start: object | None = None
        self.setFixedHeight(50)
        self.setStyleSheet(
            f"background: {theme.TOP_BAR_SURFACE}; border-bottom: 1px solid {theme.GLASS_OUTLINE};"
        )
        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 6, 12, 6)
        layout.setSpacing(10)
        emblem = QLabel("CJ")
        emblem.setAlignment(Qt.AlignmentFlag.AlignCenter)
        emblem.setFixedSize(34, 34)
        emblem.setStyleSheet(
            f"border: 1px solid {theme.MUTED}; border-radius: 17px; color: {theme.MUTED}; "
            "font-weight: 900;"
        )
        title = QLabel("Catur Jawa")
        title.setFont(typography.font(18, QFont.Weight.ExtraBold))
        title.setStyleSheet(f"color: {theme.TEXT};")
        self.minimize = QPushButton("−")
        self.maximize = QPushButton("□")
        self.close_button = QPushButton("×")
        for button in (self.minimize, self.maximize, self.close_button):
            button.setObjectName("LinkButton")
            button.setFixedSize(38, 34)
        layout.addWidget(emblem)
        layout.addWidget(title)
        layout.addStretch(1)
        layout.addWidget(self.minimize)
        layout.addWidget(self.maximize)
        layout.addWidget(self.close_button)
        self.minimize.clicked.connect(window.showMinimized)
        self.maximize.clicked.connect(self._toggle_maximized)
        self.close_button.clicked.connect(window.close)

    def mouseDoubleClickEvent(self, _event: QMouseEvent) -> None:
        self._toggle_maximized()

    def _toggle_maximized(self) -> None:
        if self.parent_window.isMaximized():
            self.parent_window.showNormal()
        else:
            self.parent_window.showMaximized()


class BasePage(MahoganyRoot):
    def __init__(self) -> None:
        super().__init__()
        self.outer = QVBoxLayout(self)
        self.outer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.outer.setContentsMargins(32, 28, 32, 32)

    def resizeEvent(self, event: object) -> None:
        margin = metrics.page_margin(self.width())
        self.outer.setContentsMargins(margin, 24, margin, 32)
        super().resizeEvent(event)  # type: ignore[arg-type]


class ActionButton(QPushButton):
    def __init__(self, title: str, subtitle: str = "", primary: bool = False):
        text = title if not subtitle else f"{title}\n{subtitle}"
        super().__init__(text)
        self.setMinimumHeight(metrics.PRIMARY_HEIGHT)
        self.setObjectName("Primary" if primary else "SecondaryAction")
        self.setFont(typography.font(16, QFont.Weight.Bold))
        self.setStyleSheet(
            "QPushButton#SecondaryAction {"
            f"background: {theme.GLASS_SURFACE}; color: {theme.TEXT}; border: 1px solid {theme.GLASS_OUTLINE}; "
            "border-radius: 18px; padding: 10px 18px; text-align: left; font-weight: 800;}"
            f"QPushButton#SecondaryAction:hover {{ background: {theme.GLASS_HOVER}; }}"
        )


class FieldGroup(QWidget):
    def __init__(
        self,
        label: str,
        field: QWidget,
        helper: str = "",
        token: QLabel | None = None,
    ):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(7)
        label_row = QHBoxLayout()
        label_widget = QLabel(label)
        label_widget.setObjectName("FieldLabel")
        label_widget.setFont(typography.label())
        label_row.addWidget(label_widget)
        label_row.addStretch(1)
        if token is not None:
            label_row.addWidget(token)
        layout.addLayout(label_row)
        field.setMinimumHeight(metrics.CONTROL_HEIGHT)
        layout.addWidget(field)
        if helper:
            helper_label = QLabel(helper)
            helper_label.setObjectName("HelperText")
            helper_label.setWordWrap(True)
            layout.addWidget(helper_label)


def _token(side: str) -> QLabel:
    label = QLabel(side)
    label.setObjectName("TokenA" if side == "A" else "TokenB")
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    return label


class MainMenuPage(BasePage):
    host_requested = Signal()
    join_requested = Signal()
    how_requested = Signal()
    settings_requested = Signal()
    quit_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        panel = GlassPanel(metrics.MENU_PANEL_WIDTH)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(46, 42, 46, 42)
        layout.setSpacing(16)
        emblem = QLabel("◇")
        emblem.setObjectName("MenuEmblem")
        emblem.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title = QLabel("Catur Jawa")
        title.setObjectName("MenuTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc = QLabel("A relaxed multiplayer Dam-daman experience")
        desc.setObjectName("PageDescription")
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.host = ActionButton("Host Game", "Create a room for another player", primary=True)
        self.join = ActionButton("Join Game", "Connect to a friend's room")
        secondary = QHBoxLayout()
        self.how = QPushButton("How to Play")
        self.how.setObjectName("LinkButton")
        self.settings = QPushButton("Settings")
        self.settings.setObjectName("LinkButton")
        self.quit = QPushButton("Quit")
        self.quit.setObjectName("LinkButton")
        secondary.addWidget(self.how)
        secondary.addWidget(self.settings)
        layout.addWidget(emblem)
        layout.addWidget(title)
        layout.addWidget(desc)
        layout.addSpacing(18)
        layout.addWidget(self.host)
        layout.addWidget(self.join)
        layout.addSpacing(12)
        layout.addLayout(secondary)
        layout.addWidget(self.quit, alignment=Qt.AlignmentFlag.AlignCenter)
        self.outer.addWidget(panel)
        self.host.clicked.connect(self.host_requested)
        self.join.clicked.connect(self.join_requested)
        self.how.clicked.connect(self.how_requested)
        self.settings.clicked.connect(self.settings_requested)
        self.quit.clicked.connect(self.quit_requested)


class SetupPage(BasePage):
    back_requested = Signal()

    def _header(self, title: str, description: str, layout: QVBoxLayout) -> None:
        back = QPushButton("‹ Back")
        back.setObjectName("LinkButton")
        back.setFixedWidth(104)
        page_title = QLabel(title)
        page_title.setObjectName("PageTitle")
        page_title.setFont(typography.page_title())
        desc = QLabel(description)
        desc.setObjectName("PageDescription")
        desc.setWordWrap(True)
        layout.addWidget(back)
        layout.addSpacing(6)
        layout.addWidget(page_title)
        layout.addWidget(desc)
        back.clicked.connect(self.back_requested)


class HostSetupPage(SetupPage):
    create_requested = Signal(str, str, int)

    def __init__(self, settings: QSettings):
        super().__init__()
        panel = GlassPanel(metrics.SETUP_PANEL_WIDTH)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(38, 34, 38, 34)
        layout.setSpacing(16)
        self._header("Host a Game", "Create a room and invite another player.", layout)
        self.name = QLineEdit(str(settings.value("display_name", "Player A")))
        self.bind_host = QLineEdit("0.0.0.0")
        self.port = QSpinBox()
        self.port.setRange(1, 65535)
        self.port.setValue(int(cast(str | int, settings.value("last_port", 9999))))
        self.advanced = QWidget()
        advanced_layout = QVBoxLayout(self.advanced)
        advanced_layout.setContentsMargins(0, 0, 0, 0)
        advanced_layout.addWidget(FieldGroup("Bind address", self.bind_host, "Default works for LAN play."))
        self.advanced.hide()
        self.advanced_button = QPushButton("Advanced settings")
        self.advanced_button.setObjectName("LinkButton")
        self.error = QLabel("")
        self.error.setObjectName("ErrorText")
        self.error.setWordWrap(True)
        self.create_button = QPushButton("Create Game")
        self.create_button.setObjectName("Primary")
        self.create_button.setMinimumHeight(metrics.PRIMARY_HEIGHT)
        layout.addWidget(FieldGroup("Display name", self.name, token=_token("A")))
        layout.addWidget(FieldGroup("Port", self.port, "Your friend will use this port when joining."))
        layout.addWidget(self.advanced_button)
        layout.addWidget(self.advanced)
        layout.addWidget(self.error)
        layout.addSpacing(4)
        layout.addWidget(self.create_button)
        self.outer.addWidget(panel)
        self.advanced_button.clicked.connect(lambda: self.advanced.setVisible(not self.advanced.isVisible()))
        self.create_button.clicked.connect(
            lambda: self.create_requested.emit(self.name.text(), self.bind_host.text(), self.port.value())
        )

    def show_error(self, message: str) -> None:
        self.error.setText(message)


class JoinSetupPage(SetupPage):
    connect_requested = Signal(str, str, int)

    def __init__(self, settings: QSettings):
        super().__init__()
        panel = GlassPanel(metrics.SETUP_PANEL_WIDTH)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(38, 34, 38, 34)
        layout.setSpacing(16)
        self._header("Join a Game", "Enter the room address shared by your friend.", layout)
        saved = str(settings.value("last_host_address", "127.0.0.1:9999"))
        host, port = _split_address(saved)
        self.name = QLineEdit(str(settings.value("display_name", "Player B")))
        self.host = QLineEdit(host)
        self.port = QSpinBox()
        self.port.setRange(1, 65535)
        self.port.setValue(port)
        self.error = QLabel("")
        self.error.setObjectName("ErrorText")
        self.error.setWordWrap(True)
        self.connect_button = QPushButton("Connect")
        self.connect_button.setObjectName("Primary")
        self.connect_button.setMinimumHeight(metrics.PRIMARY_HEIGHT)
        layout.addWidget(FieldGroup("Display name", self.name, token=_token("B")))
        layout.addWidget(
            FieldGroup("Host address", self.host, "Examples: 100.101.22.33, 192.168.1.20, or localhost.")
        )
        layout.addWidget(FieldGroup("Port", self.port, "Default: 9999."))
        layout.addWidget(self.error)
        layout.addSpacing(4)
        layout.addWidget(self.connect_button)
        self.outer.addWidget(panel)
        self.connect_button.clicked.connect(
            lambda: self.connect_requested.emit(self.name.text(), self.host.text(), self.port.value())
        )

    def show_error(self, message: str) -> None:
        self.error.setText(message)


class ConnectingPage(BasePage):
    cancel_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        panel = GlassPanel(metrics.MENU_PANEL_WIDTH)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(42, 38, 42, 38)
        layout.setSpacing(16)
        title = QLabel("Connecting...")
        title.setObjectName("PageTitle")
        title.setFont(typography.page_title())
        self.target = QLabel("Joining the game")
        self.target.setObjectName("PageDescription")
        self.detail = QLabel("Retrying automatically")
        self.detail.setObjectName("HelperText")
        cancel = QPushButton("Cancel")
        layout.addWidget(title)
        layout.addWidget(self.target)
        layout.addWidget(self.detail)
        layout.addSpacing(16)
        layout.addWidget(cancel)
        self.outer.addWidget(panel)
        cancel.clicked.connect(self.cancel_requested)

    def set_target(self, address: str) -> None:
        self.target.setText(f"Joining friend's game\n{address}")


class LobbyPage(BasePage):
    start_requested = Signal()
    cancel_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.session: ActiveSession | None = None
        panel = GlassPanel(metrics.LOBBY_PANEL_WIDTH)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(42, 38, 42, 38)
        layout.setSpacing(18)
        self.title = QLabel("Game Lobby")
        self.title.setObjectName("PageTitle")
        self.title.setFont(typography.page_title())
        self.player_a = PlayerBadge(PlayerSide.A, "Alice")
        self.player_b = PlayerBadge(PlayerSide.B, "Waiting")
        self.status = QLabel("Waiting for another player...")
        self.status.setObjectName("PageDescription")
        self.rating = QLabel("")
        self.rating.setObjectName("HelperText")
        self.rating.setWordWrap(True)
        self.address = QLabel("")
        self.address.setObjectName("HelperText")
        self.copy = QPushButton("Copy Address")
        self.start = QPushButton("Start Game")
        self.start.setObjectName("Primary")
        self.cancel = QPushButton("Cancel Game")
        layout.addWidget(self.title)
        layout.addWidget(self.player_a)
        layout.addWidget(self.player_b)
        layout.addWidget(self.status)
        layout.addWidget(self.rating)
        layout.addWidget(self.address)
        layout.addSpacing(8)
        layout.addWidget(self.copy)
        layout.addWidget(self.start)
        layout.addWidget(self.cancel)
        self.outer.addWidget(panel)
        self.start.clicked.connect(self.start_requested)
        self.cancel.clicked.connect(self.cancel_requested)
        self.copy.clicked.connect(self._copy_address)

    def set_session(self, session: ActiveSession) -> None:
        self.session = session
        self.refresh()

    def refresh(self) -> None:
        if self.session is None:
            return
        runtime = self.session.runtime
        if self.session.side.value == "A":
            local = runtime.transport.local_address() if isinstance(runtime, HostRuntime) else ("0.0.0.0", 9999)
            address = room_address(local[1])
            peer_ready = bool(getattr(runtime, "peer_ready", False))
            name = str(getattr(runtime, "name", "Alice"))
            self.player_a = self._replace_badge(self.player_a, "A", f"{name} · Host · Ready")
            self.player_b = self._replace_badge(
                self.player_b,
                "B",
                "Player B · Connected" if peer_ready else "Waiting for Player B",
            )
            self.status.setText("Player B connected." if peer_ready else "Waiting for another player...")
            self.rating.setText("\n".join(rating_snapshot_lines(getattr(runtime, "rating_snapshot", None))))
            self.address.setText(f"Room address: {address}")
            self.start.setText("Start Game")
            self.start.setEnabled(peer_ready)
            self.copy.setEnabled(True)
        else:
            ready = getattr(runtime, "state", None) is not None
            self.player_a = self._replace_badge(self.player_a, "A", "Host · Ready")
            self.player_b = self._replace_badge(self.player_b, "B", f"{runtime.name} · Player B")
            self.status.setText("Connected to host." if ready else "Connecting to the game...")
            self.rating.setText("\n".join(rating_snapshot_lines(getattr(runtime, "rating_snapshot", None))))
            self.address.setText("Assigned side: Player B")
            self.start.setText("Enter Game")
            self.start.setEnabled(ready)
            self.copy.setEnabled(False)

    def _replace_badge(self, old: QWidget, side: str, text: str) -> PlayerBadge:
        badge = PlayerBadge(PlayerSide(side), text)
        parent = old.parentWidget()
        if parent is None:
            return badge
        layout = cast(QVBoxLayout, parent.layout())
        index = layout.indexOf(old)
        layout.removeWidget(old)
        old.deleteLater()
        layout.insertWidget(index, badge)
        return badge

    def _copy_address(self) -> None:
        QApplication.clipboard().setText(self.address.text().replace("Room address: ", ""))


class HowToPlayPage(BasePage):
    back_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        panel = GlassPanel(metrics.TEXT_PANEL_WIDTH)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(42, 36, 42, 36)
        layout.setSpacing(14)
        back = QPushButton("‹ Back")
        back.setObjectName("LinkButton")
        back.setFixedWidth(104)
        title = QLabel("How to Play")
        title.setObjectName("PageTitle")
        title.setFont(typography.page_title())
        content = QLabel(
            "<b>Goal</b><br>Remove all opposing pieces.<br><br>"
            "<b>Movement</b><br>Move one connected line forward, sideways, or diagonally. Ordinary pieces cannot move backward.<br><br>"
            "<b>Capture</b><br>Jump exactly one adjacent opponent piece and land on an empty node in the same line.<br><br>"
            "<b>Ignored-capture penalty</b><br>If you ignore an available capture, the opponent removes up to three of your pieces.<br><br>"
            "<b>Promotion</b><br>Reach the opponent's outer triangle to become a king.<br><br>"
            "<b>Winning</b><br>A player wins when all opponent pieces are removed."
        )
        content.setObjectName("PageDescription")
        content.setWordWrap(True)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        holder = QWidget()
        holder_layout = QVBoxLayout(holder)
        holder_layout.addWidget(content)
        scroll.setWidget(holder)
        layout.addWidget(back)
        layout.addWidget(title)
        layout.addWidget(scroll, 1)
        self.outer.addWidget(panel)
        back.clicked.connect(self.back_requested)


class SettingsPage(BasePage):
    back_requested = Signal()

    def __init__(self, settings: QSettings):
        super().__init__()
        self.settings = settings
        panel = GlassPanel(metrics.LOBBY_PANEL_WIDTH)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(42, 36, 42, 36)
        layout.setSpacing(14)
        back = QPushButton("‹ Back")
        back.setObjectName("LinkButton")
        back.setFixedWidth(104)
        title = QLabel("Settings")
        title.setObjectName("PageTitle")
        title.setFont(typography.page_title())
        self.coordinates = QCheckBox("Show board coordinates")
        self.coordinates.setChecked(_setting_bool(settings, "show_coordinates"))
        self.reduced_motion = QCheckBox("Reduced motion")
        self.reduced_motion.setChecked(_setting_bool(settings, "reduced_motion"))
        self.default_name = QLineEdit(str(settings.value("display_name", "Player")))
        reset = QPushButton("Reset all preferences")
        reset.setObjectName("Danger")
        layout.addWidget(back)
        layout.addWidget(title)
        layout.addWidget(QLabel("Appearance"))
        layout.addWidget(self.coordinates)
        layout.addWidget(self.reduced_motion)
        layout.addWidget(FieldGroup("Default display name", self.default_name))
        layout.addSpacing(12)
        layout.addWidget(reset)
        self.outer.addWidget(panel)
        back.clicked.connect(self._save_and_back)
        reset.clicked.connect(self._reset)

    def _save_and_back(self) -> None:
        self.settings.setValue("show_coordinates", self.coordinates.isChecked())
        self.settings.setValue("reduced_motion", self.reduced_motion.isChecked())
        self.settings.setValue("display_name", self.default_name.text())
        self.back_requested.emit()

    def _reset(self) -> None:
        self.settings.clear()
        self.coordinates.setChecked(False)
        self.reduced_motion.setChecked(False)
        self.default_name.setText("Player")


class MainWindow(QMainWindow):
    def __init__(self, controller: SessionController, settings: QSettings):
        super().__init__()
        self.controller = controller
        self.settings = settings
        self.device_id = _device_id(settings)
        self.game_page: GamePage | None = None
        self.setWindowTitle("Catur Jawa")
        window_size = settings.value("window_size")
        if isinstance(window_size, QSize):
            self.resize(window_size)
        else:
            self.resize(*metrics.WINDOW_DEFAULT)
        self.setMinimumSize(*metrics.WINDOW_MINIMUM)
        self.setStyleSheet(theme.stylesheet())
        shell = QWidget()
        shell_layout = QVBoxLayout(shell)
        shell_layout.setContentsMargins(0, 0, 0, 0)
        shell_layout.setSpacing(0)
        self.stack = QStackedWidget()
        self.menu = MainMenuPage()
        self.host_setup = HostSetupPage(settings)
        self.join_setup = JoinSetupPage(settings)
        self.connecting = ConnectingPage()
        self.lobby = LobbyPage()
        self.how_to_play = HowToPlayPage()
        self.settings_page = SettingsPage(settings)
        for page in (
            self.menu,
            self.host_setup,
            self.join_setup,
            self.connecting,
            self.lobby,
            self.how_to_play,
            self.settings_page,
        ):
            self.stack.addWidget(page)
        shell_layout.addWidget(self.stack)
        self.setCentralWidget(shell)
        self._wire()
        self.lobby_timer = QTimer(self)
        self.lobby_timer.timeout.connect(self._refresh_waiting_pages)
        self.lobby_timer.start(250)

    def _wire(self) -> None:
        self.menu.host_requested.connect(lambda: self._show(self.host_setup, UiSessionState.HOST_CONFIG))
        self.menu.join_requested.connect(lambda: self._show(self.join_setup, UiSessionState.JOIN_CONFIG))
        self.menu.how_requested.connect(lambda: self._show(self.how_to_play, UiSessionState.MENU))
        self.menu.settings_requested.connect(lambda: self._show(self.settings_page, UiSessionState.MENU))
        self.menu.quit_requested.connect(self.close)
        self.host_setup.back_requested.connect(self.return_to_menu)
        self.join_setup.back_requested.connect(self.return_to_menu)
        self.connecting.cancel_requested.connect(self.return_to_menu)
        self.how_to_play.back_requested.connect(self.return_to_menu)
        self.settings_page.back_requested.connect(self.return_to_menu)
        self.host_setup.create_requested.connect(self._create_host)
        self.join_setup.connect_requested.connect(self._join_host)
        self.lobby.cancel_requested.connect(self.return_to_menu)
        self.lobby.start_requested.connect(self._enter_game)

    def _show(self, widget: QWidget, state: UiSessionState) -> None:
        self.controller.state = state
        self.stack.setCurrentWidget(widget)

    def _create_host(self, name: str, bind_host: str, port: int) -> None:
        try:
            session = self.controller.start_host(HostConfig(name, bind_host, port), self.device_id)
        except (ConfigError, OSError) as exc:
            self.host_setup.show_error(_friendly_host_error(port, exc))
            return
        self.settings.setValue("display_name", name)
        self.settings.setValue("last_port", port)
        self.lobby.set_session(session)
        self._show(self.lobby, UiSessionState.HOST_LOBBY)

    def _join_host(self, name: str, host: str, port: int) -> None:
        try:
            config = JoinConfig.parse(name, f"{host}:{port}")
            session = self.controller.join_host(config, self.device_id)
        except (ConfigError, OSError) as exc:
            self.join_setup.show_error(str(exc))
            return
        self.settings.setValue("display_name", name)
        self.settings.setValue("last_host_address", f"{config.host}:{config.port}")
        self.connecting.set_target(f"{config.host}:{config.port}")
        self.lobby.set_session(session)
        self._show(self.connecting, UiSessionState.CONNECTING)

    def _refresh_waiting_pages(self) -> None:
        if self.stack.currentWidget() is self.lobby:
            self.lobby.refresh()
        if self.stack.currentWidget() is self.connecting and self.controller.active is not None:
            runtime = self.controller.active.runtime
            if getattr(runtime, "state", None) is not None:
                self._show(self.lobby, UiSessionState.JOIN_LOBBY)

    def _enter_game(self) -> None:
        session = self.controller.enter_game()
        self.game_page = GamePage(session.runtime, session.side, session.runtime.name)
        self.game_page.show_coordinates = bool(self.settings.value("show_coordinates", False, bool))
        self.game_page.leave_requested.connect(self.return_to_menu)
        self.stack.addWidget(self.game_page)
        self.stack.setCurrentWidget(self.game_page)

    def return_to_menu(self) -> None:
        if self.game_page is not None:
            self.game_page.close_session()
            self.stack.removeWidget(self.game_page)
            self.game_page.deleteLater()
            self.game_page = None
            self.controller.active = None
            self.controller.state = UiSessionState.MENU
        else:
            self.controller.disconnect()
        self.stack.setCurrentWidget(self.menu)

    def closeEvent(self, event: QCloseEvent) -> None:
        self.settings.setValue("window_size", self.size())
        if self.game_page is not None:
            self.game_page.close_session()
            self.game_page = None
            self.controller.active = None
        else:
            self.controller.disconnect()
        super().closeEvent(event)


def _split_address(value: str) -> tuple[str, int]:
    if ":" not in value:
        return value, 9999
    host, port_text = value.rsplit(":", 1)
    try:
        return host or "127.0.0.1", int(port_text)
    except ValueError:
        return host or "127.0.0.1", 9999


def _setting_bool(settings: QSettings, key: str) -> bool:
    value = settings.value(key, False)
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in {"1", "true", "yes", "on"}
    return False


def _friendly_host_error(port: int, exc: BaseException) -> str:
    if isinstance(exc, ConfigError):
        return str(exc)
    return (
        f"Could not create the game on port {port}. "
        "Another application may already be using that port."
    )


def _device_id(settings: QSettings) -> str:
    value = settings.value("device_id")
    if isinstance(value, str) and value:
        return value
    generated = str(uuid4())
    settings.setValue("device_id", generated)
    return generated


def main(argv: list[str] | None = None) -> int:
    _ = argv
    try:
        app = QApplication.instance() or QApplication(sys.argv[:1])
    except Exception as exc:  # noqa: BLE001
        print(f"PySide6 GUI is unavailable: {exc}")
        return 2
    settings = QSettings("JIWA-JAWA", "Catur Jawa")
    controller = SessionController()
    window = MainWindow(controller, settings)
    window.show()
    return int(app.exec())


if __name__ == "__main__":
    raise SystemExit(main())
