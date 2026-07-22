from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QWidget

from catur_jawa.domain.models import Move, PlayerSide
from catur_jawa.domain.rules import legal_captures, legal_moves
from catur_jawa.domain.state import GameState
from catur_jawa.ui import theme


@dataclass(frozen=True, slots=True)
class BoardInteraction:
    selected_node: str | None = None
    penalty_nodes: frozenset[str] = frozenset()
    last_source: str | None = None
    last_destination: str | None = None
    disabled: bool = False
    show_coordinates: bool = False


class BoardView(QWidget):
    node_clicked = Signal(str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setMinimumSize(520, 460)
        self.setMouseTracking(True)
        self.state: GameState | None = None
        self.local_side = PlayerSide.A
        self.interaction = BoardInteraction()
        self._node_positions: dict[str, QPointF] = {}
        self._hover_node: str | None = None

    def set_position(
        self,
        state: GameState | None,
        local_side: PlayerSide,
        interaction: BoardInteraction,
    ) -> None:
        self.state = state
        self.local_side = local_side
        self.interaction = interaction
        self.update()

    def paintEvent(self, _event: object) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self.state is None:
            self._draw_empty(painter)
            return
        self._calculate_positions()
        self._draw_edges(painter)
        self._draw_nodes_and_pieces(painter)
        if self.interaction.disabled:
            painter.fillRect(self.rect(), QColor(24, 14, 8, 44))

    def mousePressEvent(self, event: object) -> None:
        if self.state is None:
            return
        pos = event.position()  # type: ignore[attr-defined]
        radius = self._piece_radius()
        for node_id, point in self._node_positions.items():
            if (point - pos).manhattanLength() <= radius * 1.3:
                self.node_clicked.emit(node_id)
                return

    def mouseMoveEvent(self, event: object) -> None:
        if self.state is None:
            return
        pos = event.position()  # type: ignore[attr-defined]
        radius = self._piece_radius()
        hovered = None
        for node_id, point in self._node_positions.items():
            if (point - pos).manhattanLength() <= radius * 1.25:
                hovered = node_id
                break
        if hovered != self._hover_node:
            self._hover_node = hovered
            self.update()

    def leaveEvent(self, _event: object) -> None:
        self._hover_node = None
        self.update()

    def _draw_empty(self, painter: QPainter) -> None:
        painter.setPen(QColor(theme.MUTED))
        painter.setFont(QFont("Nunito Sans", 20, QFont.Weight.Bold))
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Waiting for match state")

    def _calculate_positions(self) -> None:
        if self.state is None:
            return
        xs = [node.x for node in self.state.board.nodes.values()]
        ys = [node.y for node in self.state.board.nodes.values()]
        margin = 64
        available = QRectF(
            margin,
            margin,
            max(10, self.width() - margin * 2),
            max(10, self.height() - margin * 2),
        )
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        scale = min(available.width() / (max_x - min_x), available.height() / (max_y - min_y))
        board_width = (max_x - min_x) * scale
        board_height = (max_y - min_y) * scale
        offset_x = available.left() + (available.width() - board_width) / 2
        offset_y = available.top() + (available.height() - board_height) / 2
        self._node_positions = {
            node.id: QPointF(offset_x + (node.x - min_x) * scale, offset_y + (node.y - min_y) * scale)
            for node in self.state.board.nodes.values()
        }

    def _draw_edges(self, painter: QPainter) -> None:
        if self.state is None:
            return
        painter.setPen(QPen(QColor(71, 36, 17, 115), 7, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        for a, b in sorted(self.state.board.edges):
            painter.drawLine(self._node_positions[a], self._node_positions[b])
        painter.setPen(QPen(QColor(theme.BOARD_LINE), 4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        for a, b in sorted(self.state.board.edges):
            painter.drawLine(self._node_positions[a], self._node_positions[b])

    def _draw_nodes_and_pieces(self, painter: QPainter) -> None:
        if self.state is None:
            return
        legal_destinations = self._legal_destinations()
        legal_capture_destinations = self._legal_capture_destinations()
        occupied = self.state.occupied
        for node_id, point in sorted(self._node_positions.items()):
            piece = occupied.get(node_id)
            self._draw_node_state(painter, node_id, point, node_id in legal_destinations, node_id in legal_capture_destinations)
            if piece is not None:
                self._draw_piece(painter, piece.owner, piece.king, node_id, point)
            if self.interaction.show_coordinates:
                self._draw_label(painter, node_id, point, piece is not None)

    def _draw_node_state(
        self,
        painter: QPainter,
        node_id: str,
        point: QPointF,
        is_destination: bool,
        is_capture_destination: bool,
    ) -> None:
        radius = self._piece_radius()
        painter.setBrush(QColor(theme.BOARD_NODE))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(point, max(4.5, radius * 0.20), max(4.5, radius * 0.20))
        if node_id == self.interaction.last_source:
            painter.setBrush(QColor(240, 185, 79, 70))
            painter.setPen(QPen(QColor(theme.WARNING), 2))
            painter.drawEllipse(point, radius * 0.95, radius * 0.95)
        if node_id == self.interaction.last_destination:
            painter.setBrush(QColor(85, 198, 90, 70))
            painter.setPen(QPen(QColor(theme.SUCCESS), 2))
            painter.drawEllipse(point, radius * 1.00, radius * 1.00)
        if is_destination:
            color = QColor(theme.CAPTURE if is_capture_destination else theme.ACCENT)
            painter.setBrush(QColor(color.red(), color.green(), color.blue(), 58))
            painter.setPen(QPen(color, 3 if is_capture_destination else 2))
            painter.drawEllipse(point, radius * (0.88 if is_capture_destination else 0.72), radius * (0.88 if is_capture_destination else 0.72))
            if is_capture_destination:
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawEllipse(point, radius * 1.06, radius * 1.06)
        if node_id in self.interaction.penalty_nodes:
            painter.setBrush(QColor(212, 91, 85, 92))
            painter.setPen(QPen(QColor(theme.DANGER), 4))
            painter.drawEllipse(point, radius * 1.24, radius * 1.24)
            order = sorted(self.interaction.penalty_nodes).index(node_id) + 1
            painter.setPen(QColor(theme.TEXT))
            painter.setFont(QFont("Nunito Sans", max(10, int(radius * 0.60)), QFont.Weight.Bold))
            painter.drawText(
                QRectF(point.x() - radius, point.y() - radius * 1.8, radius * 2, radius),
                Qt.AlignmentFlag.AlignCenter,
                str(order),
            )
        if node_id == self._hover_node:
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(QColor(theme.ACCENT_HOVER), 2))
            painter.drawEllipse(point, radius * 1.18, radius * 1.18)

    def _draw_piece(
        self,
        painter: QPainter,
        owner: PlayerSide,
        king: bool,
        node_id: str,
        point: QPointF,
    ) -> None:
        radius = self._piece_radius()
        fill = QColor(theme.PIECE_A_FILL if owner is PlayerSide.A else theme.PIECE_B_FILL)
        outline = QColor(247, 229, 198, 160) if owner is PlayerSide.A else QColor(20, 24, 26, 150)
        if node_id == self.interaction.selected_node:
            outline = QColor(theme.ACCENT)
            radius *= 1.13
        painter.setBrush(QColor(27, 13, 6, 80))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPointF(point.x() + 2, point.y() + 3), radius * 1.02, radius * 1.02)
        painter.setBrush(fill)
        painter.setPen(QPen(outline, 4 if node_id == self.interaction.selected_node else 2))
        painter.drawEllipse(point, radius, radius)
        painter.setPen(QColor(theme.PIECE_A_TEXT if owner is PlayerSide.A else theme.PIECE_B_TEXT))
        painter.setFont(QFont("Nunito Sans", max(11, int(radius * 0.72)), QFont.Weight.Bold))
        painter.drawText(
            QRectF(point.x() - radius, point.y() - radius * 0.62, radius * 2, radius * 1.24),
            Qt.AlignmentFlag.AlignCenter,
            owner.value,
        )
        if king:
            painter.setPen(QPen(QColor(theme.WARNING), 2))
            painter.setFont(QFont("Nunito Sans", max(12, int(radius * 0.62)), QFont.Weight.Bold))
            painter.drawText(
                QRectF(point.x() - radius, point.y() - radius * 1.00, radius * 2, radius * 0.72),
                Qt.AlignmentFlag.AlignCenter,
                "*",
            )

    def _draw_label(self, painter: QPainter, node_id: str, point: QPointF, occupied: bool) -> None:
        color = QColor(theme.TEXT if not occupied else theme.TEXT_MUTED)
        color.setAlpha(150 if not occupied else 95)
        painter.setPen(color)
        painter.setFont(QFont("Nunito Sans", 9, QFont.Weight.Bold))
        painter.drawText(
            QRectF(point.x() - 22, point.y() + self._piece_radius() + 3, 44, 16),
            Qt.AlignmentFlag.AlignCenter,
            node_id,
        )

    def _piece_radius(self) -> float:
        return max(13.0, min(self.width(), self.height()) / 32)

    def _legal_destinations(self) -> set[str]:
        if self.state is None or self.interaction.selected_node is None:
            return set()
        return {
            move.destination
            for move in legal_moves(self.state, self.local_side, self.interaction.selected_node)
        }

    def _legal_capture_destinations(self) -> set[str]:
        if self.state is None or self.interaction.selected_node is None:
            return set()
        return {
            move.destination
            for move in legal_captures(self.state, self.local_side, self.interaction.selected_node)
        }

    def selected_legal_moves(self) -> list[Move]:
        if self.state is None or self.interaction.selected_node is None:
            return []
        return legal_moves(self.state, self.local_side, self.interaction.selected_node)

    def visual_bounds(self) -> QRectF:
        self._calculate_positions()
        if not self._node_positions:
            return QRectF()
        radius = self._piece_radius() * 2.6
        min_x = min(point.x() for point in self._node_positions.values()) - radius
        max_x = max(point.x() for point in self._node_positions.values()) + radius
        min_y = min(point.y() for point in self._node_positions.values()) - radius
        max_y = max(point.y() for point in self._node_positions.values()) + radius
        return QRectF(QPointF(min_x, min_y), QPointF(max_x, max_y))
