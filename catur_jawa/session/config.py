from __future__ import annotations

from dataclasses import dataclass


class ConfigError(ValueError):
    """Raised for friendly setup-form validation errors."""


@dataclass(frozen=True, slots=True)
class HostConfig:
    display_name: str = "Player A"
    bind_host: str = "0.0.0.0"
    port: int = 9999

    def validate(self) -> "HostConfig":
        name = self.display_name.strip()
        if not name:
            raise ConfigError("Display name is required.")
        _validate_port(self.port)
        return HostConfig(name, self.bind_host.strip() or "0.0.0.0", self.port)


@dataclass(frozen=True, slots=True)
class JoinConfig:
    display_name: str = "Player B"
    host: str = "127.0.0.1"
    port: int = 9999
    bind_host: str = "0.0.0.0"
    bind_port: int = 0

    def validate(self) -> "JoinConfig":
        name = self.display_name.strip()
        host = self.host.strip()
        if not name:
            raise ConfigError("Display name is required.")
        if not host:
            raise ConfigError("Host address is required.")
        _validate_port(self.port)
        _validate_port(self.bind_port, allow_zero=True)
        return JoinConfig(name, host, self.port, self.bind_host, self.bind_port)

    @classmethod
    def parse(cls, display_name: str, address: str, default_port: int = 9999) -> "JoinConfig":
        value = address.strip()
        if not value:
            raise ConfigError("Host address is required.")
        host = value
        port = default_port
        if ":" in value:
            host, port_text = value.rsplit(":", 1)
            if not host or not port_text.isdigit():
                raise ConfigError("The address format is invalid.")
            port = int(port_text)
        return cls(display_name=display_name, host=host, port=port).validate()


def _validate_port(port: int, allow_zero: bool = False) -> None:
    minimum = 0 if allow_zero else 1
    if port < minimum or port > 65535:
        raise ConfigError("Port must be between 1 and 65535.")
