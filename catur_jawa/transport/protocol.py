from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

PROTOCOL_VERSION = 1
MAX_DATAGRAM_BYTES = 8192


class ProtocolError(ValueError):
    """Raised when a UDP envelope is malformed or incompatible."""


@dataclass(frozen=True, slots=True)
class Envelope:
    protocol_version: int
    message_type: str
    session_id: str
    message_id: str
    sender_id: str
    sequence: int
    ack_for: str | None
    sent_at_ms: int
    payload: dict[str, Any]
    payload_sha256: str

    def to_json(self) -> dict[str, Any]:
        return {
            "protocol_version": self.protocol_version,
            "message_type": self.message_type,
            "session_id": self.session_id,
            "message_id": self.message_id,
            "sender_id": self.sender_id,
            "sequence": self.sequence,
            "ack_for": self.ack_for,
            "sent_at_ms": self.sent_at_ms,
            "payload": self.payload,
            "payload_sha256": self.payload_sha256,
        }


def payload_hash(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode(
        "utf-8"
    )
    return hashlib.sha256(encoded).hexdigest()


def make_envelope(
    message_type: str,
    session_id: str,
    sender_id: str,
    sequence: int,
    payload: dict[str, Any] | None = None,
    ack_for: str | None = None,
    message_id: str | None = None,
) -> Envelope:
    actual_payload = payload or {}
    return Envelope(
        protocol_version=PROTOCOL_VERSION,
        message_type=message_type,
        session_id=session_id,
        message_id=message_id or str(uuid4()),
        sender_id=sender_id,
        sequence=sequence,
        ack_for=ack_for,
        sent_at_ms=int(time.time() * 1000),
        payload=actual_payload,
        payload_sha256=payload_hash(actual_payload),
    )


def encode(envelope: Envelope) -> bytes:
    data = json.dumps(envelope.to_json(), sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode(
        "utf-8"
    )
    if len(data) > MAX_DATAGRAM_BYTES:
        raise ProtocolError(
            f"Datagram is {len(data)} bytes; limit is {MAX_DATAGRAM_BYTES} bytes to avoid fragmentation."
        )
    return data


def decode(data: bytes) -> Envelope:
    try:
        raw = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProtocolError("Invalid UTF-8 JSON datagram.") from exc
    if raw.get("protocol_version") != PROTOCOL_VERSION:
        raise ProtocolError("Incompatible protocol version.")
    payload = raw.get("payload")
    if not isinstance(payload, dict):
        raise ProtocolError("Payload must be an object.")
    if raw.get("payload_sha256") != payload_hash(payload):
        raise ProtocolError("Payload hash mismatch.")
    try:
        return Envelope(
            protocol_version=int(raw["protocol_version"]),
            message_type=str(raw["message_type"]),
            session_id=str(raw["session_id"]),
            message_id=str(raw["message_id"]),
            sender_id=str(raw["sender_id"]),
            sequence=int(raw["sequence"]),
            ack_for=raw["ack_for"] if raw.get("ack_for") is not None else None,
            sent_at_ms=int(raw["sent_at_ms"]),
            payload=payload,
            payload_sha256=str(raw["payload_sha256"]),
        )
    except KeyError as exc:
        raise ProtocolError(f"Missing envelope field: {exc}") from exc
