from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PeerStatus:
    connected: bool = False
    degraded: bool = False
    last_message: str = "disconnected"


def parse_address(value: str) -> tuple[str, int]:
    if ":" not in value:
        raise ValueError("Address must use host:port format.")
    host, port = value.rsplit(":", 1)
    return host, int(port)
