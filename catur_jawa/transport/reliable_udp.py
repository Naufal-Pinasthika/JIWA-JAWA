from __future__ import annotations

import socket
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Callable, cast

from catur_jawa.transport.protocol import Envelope, ProtocolError, decode, encode, make_envelope

Address = tuple[str, int]
ReceiveCallback = Callable[[Envelope, Address], None]
DiagnosticCallback = Callable[[str, dict[str, object]], None]


@dataclass(slots=True)
class PendingPacket:
    envelope: Envelope
    address: Address
    rto: float
    next_send: float
    transmissions: int = 0


class ReliableUDP:
    def __init__(
        self,
        bind: Address,
        session_id: str,
        sender_id: str,
        on_message: ReceiveCallback,
        on_diagnostic: DiagnosticCallback | None = None,
        peer: Address | None = None,
        rto_ms: int = 300,
        max_rto_ms: int = 2000,
        history_size: int = 512,
    ):
        self.bind = bind
        self.session_id = session_id
        self.sender_id = sender_id
        self.peer = peer
        self.rto = rto_ms / 1000
        self.max_rto = max_rto_ms / 1000
        self.on_message = on_message
        self.on_diagnostic = on_diagnostic or (lambda _event, _fields: None)
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._socket.settimeout(0.1)
        self._sequence = 0
        self._lock = threading.RLock()
        self._pending: dict[str, PendingPacket] = {}
        self._seen: OrderedDict[str, None] = OrderedDict()
        self._history_size = history_size
        self._stopped = threading.Event()
        self._recv_thread = threading.Thread(target=self._recv_loop, name=f"udp-recv-{sender_id}", daemon=True)
        self._retry_thread = threading.Thread(
            target=self._retry_loop, name=f"udp-retry-{sender_id}", daemon=True
        )

    def start(self) -> None:
        self._socket.bind(self.bind)
        self._recv_thread.start()
        self._retry_thread.start()

    def close(self) -> None:
        self._stopped.set()
        try:
            self._socket.close()
        except OSError:
            self.on_diagnostic("PACKET_REJECTED", {"reason": "socket close failed"})
        self._recv_thread.join(timeout=1)
        self._retry_thread.join(timeout=1)

    def set_peer(self, peer: Address) -> None:
        with self._lock:
            self.peer = peer

    def local_address(self) -> Address:
        return cast(Address, self._socket.getsockname())

    def send(
        self,
        message_type: str,
        payload: dict[str, object] | None = None,
        address: Address | None = None,
        reliable: bool = True,
        ack_for: str | None = None,
    ) -> str:
        with self._lock:
            target = address or self.peer
            if target is None:
                raise RuntimeError("No peer address is known.")
            self._sequence += 1
            envelope = make_envelope(
                message_type=message_type,
                session_id=self.session_id,
                sender_id=self.sender_id,
                sequence=self._sequence,
                payload=dict(payload or {}),
                ack_for=ack_for,
            )
            packet = encode(envelope)
            self._socket.sendto(packet, target)
            self.on_diagnostic("PACKET_SENT", {"message_type": message_type, "message_id": envelope.message_id})
            if reliable and message_type != "ACK":
                self._pending[envelope.message_id] = PendingPacket(
                    envelope=envelope,
                    address=target,
                    rto=self.rto,
                    next_send=time.monotonic() + self.rto,
                    transmissions=1,
                )
            return envelope.message_id

    def pending_count(self) -> int:
        with self._lock:
            return len(self._pending)

    def _recv_loop(self) -> None:
        while not self._stopped.is_set():
            try:
                data, address = self._socket.recvfrom(4096)
            except socket.timeout:
                continue
            except OSError:
                break
            try:
                envelope = decode(data)
            except ProtocolError as exc:
                self.on_diagnostic("PACKET_REJECTED", {"reason": str(exc)})
                continue
            if envelope.message_type == "HELLO_ACK" and self.session_id != envelope.session_id:
                with self._lock:
                    self.session_id = envelope.session_id
            if envelope.session_id != self.session_id and envelope.message_type not in {"HELLO", "HELLO_ACK"}:
                self.on_diagnostic("PACKET_REJECTED", {"reason": "stale session"})
                continue
            with self._lock:
                if self.peer is None and envelope.message_type in {"HELLO", "HELLO_ACK", "READY"}:
                    self.peer = address
                if envelope.ack_for:
                    self._pending.pop(envelope.ack_for, None)
                    self.on_diagnostic("ACK_RECEIVED", {"ack_for": envelope.ack_for})
                    if envelope.message_type == "ACK":
                        continue
                duplicate = envelope.message_id in self._seen
                self._remember(envelope.message_id)
            if envelope.message_type != "ACK":
                self._send_ack(envelope, address)
            if duplicate:
                self.on_diagnostic(
                    "DUPLICATE_RECEIVED",
                    {"message_type": envelope.message_type, "message_id": envelope.message_id},
                )
                continue
            self.on_message(envelope, address)

    def _send_ack(self, envelope: Envelope, address: Address) -> None:
        try:
            self.send("ACK", {"for_sequence": envelope.sequence}, address, reliable=False, ack_for=envelope.message_id)
        except OSError:
            self.on_diagnostic("PACKET_REJECTED", {"reason": "unable to send ack"})

    def _retry_loop(self) -> None:
        while not self._stopped.is_set():
            now = time.monotonic()
            due: list[PendingPacket] = []
            with self._lock:
                for pending in self._pending.values():
                    if pending.next_send <= now:
                        due.append(pending)
                for pending in due:
                    try:
                        self._socket.sendto(encode(pending.envelope), pending.address)
                    except OSError:
                        self.on_diagnostic(
                            "PACKET_REJECTED",
                            {"reason": "unable to retransmit", "message_id": pending.envelope.message_id},
                        )
                        continue
                    pending.transmissions += 1
                    pending.rto = min(self.max_rto, pending.rto * 1.8)
                    pending.next_send = now + pending.rto
                    self.on_diagnostic(
                        "PACKET_RETRANSMITTED",
                        {
                            "message_type": pending.envelope.message_type,
                            "message_id": pending.envelope.message_id,
                            "transmissions": pending.transmissions,
                            "next_rto_ms": int(pending.rto * 1000),
                        },
                    )
            time.sleep(0.03)

    def _remember(self, message_id: str) -> None:
        self._seen[message_id] = None
        self._seen.move_to_end(message_id)
        while len(self._seen) > self._history_size:
            self._seen.popitem(last=False)
