from __future__ import annotations

from uuid import uuid4

from catur_jawa.domain.board import middle_node_on_line, straight_landing_node
from catur_jawa.domain.models import GameEvent, Move, Phase, Piece, PlayerSide
from catur_jawa.domain.state import GameState


class RuleError(ValueError):
    """Raised when a submitted action violates Dam-daman rules."""


def _movement_allowed(piece: Piece, state: GameState, destination: str) -> bool:
    if piece.king:
        return True
    source_node = state.board.node(piece.node)
    dest_node = state.board.node(destination)
    dx = dest_node.x - source_node.x
    return dx == 0 or dx * piece.owner.forward_dx > 0


def legal_simple_moves(state: GameState, side: PlayerSide, source: str | None = None) -> list[Move]:
    occupied = state.occupied
    moves: list[Move] = []
    for piece in state.pieces_for(side):
        if source and piece.node != source:
            continue
        for dest in state.board.neighbors(piece.node):
            if dest in occupied:
                continue
            if _movement_allowed(piece, state, dest):
                moves.append(Move(piece.node, dest))
    return moves


def legal_captures(state: GameState, side: PlayerSide, source: str | None = None) -> list[Move]:
    occupied = state.occupied
    captures: list[Move] = []
    for piece in state.pieces_for(side):
        if source and piece.node != source:
            continue
        for jumped in state.board.neighbors(piece.node):
            jumped_piece = occupied.get(jumped)
            if not jumped_piece or jumped_piece.owner is side:
                continue
            dest = straight_landing_node(state.board, piece.node, jumped)
            if not dest or dest in occupied:
                continue
            if _movement_allowed(piece, state, dest):
                captures.append(Move(piece.node, dest, jumped))
    return captures


def legal_moves(state: GameState, side: PlayerSide, source: str | None = None) -> list[Move]:
    return legal_captures(state, side, source) + legal_simple_moves(state, side, source)


def _event(
    state: GameState,
    event_type: str,
    actor: PlayerSide | None,
    message: str,
    source: str | None = None,
    destination: str | None = None,
    captured: list[str] | None = None,
    promotion: list[str] | None = None,
) -> GameEvent:
    return GameEvent(
        event_id=str(uuid4()),
        event_type=event_type,
        actor=actor,
        turn_number=state.turn_number,
        source=source,
        destination=destination,
        captured_piece_ids=captured or [],
        promotion=promotion or [],
        phase=state.phase,
        state_hash=state.hash(),
        human_message=message,
    )


def apply_move(state: GameState, side: PlayerSide, source: str, destination: str) -> list[GameEvent]:
    if state.phase is not Phase.NORMAL:
        raise RuleError("Match is waiting for penalty piece selection.")
    if state.current_player is not side:
        raise RuleError(f"It is Player {state.current_player.value}'s turn.")
    piece = state.piece_at(source)
    if not piece or piece.owner is not side:
        raise RuleError(f"No Player {side.value} piece at {source}.")
    if destination not in state.board.nodes:
        raise RuleError(f"Unknown destination node {destination}.")
    if state.piece_at(destination):
        raise RuleError(f"Destination {destination} is occupied.")

    captures_available = legal_captures(state, side)
    captured_piece_ids: list[str] = []
    event_type = "MOVE_COMMITTED"
    jumped = middle_node_on_line(state.board, source, destination)
    capture_move = next(
        (m for m in legal_captures(state, side, source) if m.destination == destination),
        None,
    )
    simple_move = next(
        (m for m in legal_simple_moves(state, side, source) if m.destination == destination),
        None,
    )
    if capture_move:
        jumped_piece = state.piece_at(capture_move.captured_node or "")
        if jumped_piece is None:
            raise RuleError("Capture target disappeared before commit.")
        del state.pieces[jumped_piece.id]
        captured_piece_ids.append(jumped_piece.id)
        event_type = "CAPTURE_COMMITTED"
    elif simple_move:
        if jumped is not None:
            raise RuleError("Jumping is only legal over one adjacent opponent piece.")
    else:
        raise RuleError(f"Illegal move from {source} to {destination}.")

    piece.node = destination
    promotion: list[str] = []
    if not piece.king and destination in state.board.promotion_nodes[side]:
        piece.king = True
        promotion.append(piece.id)

    state.turn_number += 1
    state.current_player = side.opponent
    if captures_available and not capture_move:
        state.phase = Phase.PENALTY_SELECTION
        state.pending_penalty_for = side
        state.pending_penalty_by = side.opponent
        state.penalty_removed = []
    _check_victory_or_stalemate(state)

    events = [
        _event(
            state,
            event_type,
            side,
            f"Player {side.value} moved {source} to {destination}.",
            source,
            destination,
            captured_piece_ids,
            promotion,
        )
    ]
    if captures_available and not capture_move and state.phase is Phase.PENALTY_SELECTION:
        events.extend(
            [
                _event(state, "CAPTURE_IGNORED", side, f"Player {side.value} ignored a capture."),
                _event(
                    state,
                    "PENALTY_STARTED",
                    side.opponent,
                    f"Player {side.opponent.value} may remove up to three Player {side.value} pieces.",
                ),
            ]
        )
    for piece_id in promotion:
        events.append(
            _event(state, "PIECE_PROMOTED", side, f"Piece {piece_id} became a king.", destination=destination)
        )
    if state.phase is Phase.FINISHED:
        events.append(_game_ended_event(state))
    return events


def apply_penalty_selection(state: GameState, side: PlayerSide, nodes: list[str]) -> list[GameEvent]:
    if state.phase is not Phase.PENALTY_SELECTION:
        raise RuleError("No penalty selection is active.")
    if state.pending_penalty_by is not side or state.pending_penalty_for is None:
        selector = state.pending_penalty_by.value if state.pending_penalty_by else "the opponent"
        raise RuleError(f"Only Player {selector} may select penalty pieces.")
    offender = state.pending_penalty_for
    remaining = len(state.pieces_for(offender))
    needed = min(3 - len(state.penalty_removed), remaining)
    unique_nodes = list(dict.fromkeys(nodes))
    if len(unique_nodes) != needed:
        raise RuleError(f"Select exactly {needed} piece node(s).")

    events: list[GameEvent] = []
    for node in unique_nodes:
        piece = state.piece_at(node)
        if not piece or piece.owner is not offender:
            raise RuleError(f"{node} does not contain a Player {offender.value} piece.")
        del state.pieces[piece.id]
        state.penalty_removed.append(piece.id)
        events.append(
            _event(
                state,
                "PENALTY_PIECE_REMOVED",
                side,
                f"Penalty removed {piece.id} from {node}.",
                source=node,
                captured=[piece.id],
            )
        )

    state.phase = Phase.NORMAL
    state.pending_penalty_for = None
    state.pending_penalty_by = None
    state.penalty_removed = []
    _check_victory_or_stalemate(state)
    if state.phase is Phase.FINISHED:
        events.append(_game_ended_event(state))
    return events


def resign(state: GameState, side: PlayerSide) -> list[GameEvent]:
    if state.phase is Phase.FINISHED:
        raise RuleError("The match has already finished.")
    state.phase = Phase.FINISHED
    state.winner = side.opponent
    state.turn_number += 1
    return [
        _event(state, "PLAYER_RESIGNED", side, f"Player {side.value} resigned."),
        _game_ended_event(state),
    ]


def _check_victory_or_stalemate(state: GameState) -> None:
    if state.phase is Phase.FINISHED:
        return
    for side in (PlayerSide.A, PlayerSide.B):
        if not state.pieces_for(side):
            state.phase = Phase.FINISHED
            state.winner = side.opponent
            return
    if state.phase is Phase.NORMAL and not legal_moves(state, state.current_player):
        state.phase = Phase.FINISHED
        state.winner = state.current_player.opponent


def _game_ended_event(state: GameState) -> GameEvent:
    winner = state.winner.value if state.winner else "none"
    return _event(state, "GAME_ENDED", state.winner, f"Game ended. Winner: Player {winner}.")
