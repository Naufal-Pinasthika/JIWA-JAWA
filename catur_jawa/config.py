from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RuntimeConfig:
    bind_host: str = "0.0.0.0"
    port: int = 9999
    peer_host: str = "127.0.0.1"
    log_dir: str = "logs"
    rto_ms: int = 300
    max_rto_ms: int = 2000

    @classmethod
    def from_env(cls) -> "RuntimeConfig":
        return cls(
            bind_host=os.getenv("CATUR_JAWA_BIND_HOST", "0.0.0.0"),
            port=int(os.getenv("CATUR_JAWA_PORT", "9999")),
            peer_host=os.getenv("CATUR_JAWA_PEER_HOST", "127.0.0.1"),
            log_dir=os.getenv("CATUR_JAWA_LOG_DIR", "logs"),
            rto_ms=int(os.getenv("CATUR_JAWA_RTO_MS", "300")),
            max_rto_ms=int(os.getenv("CATUR_JAWA_MAX_RTO_MS", "2000")),
        )
