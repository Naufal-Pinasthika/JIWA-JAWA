from __future__ import annotations

import ipaddress
import socket
import subprocess


TAILSCALE_CGNAT = ipaddress.IPv4Network("100.64.0.0/10")


def choose_room_host(candidates: list[str]) -> str:
    unique = list(dict.fromkeys(candidates))
    for address in unique:
        if _in_network(address, TAILSCALE_CGNAT):
            return address
    for address in unique:
        if _is_private_lan(address):
            return address
    for address in unique:
        if _is_loopback(address):
            return address
    return "127.0.0.1"


def room_address(port: int, candidates: list[str] | None = None) -> str:
    host = choose_room_host(candidates if candidates is not None else local_ipv4_addresses())
    return f"{host}:{port}"


def local_ipv4_addresses() -> list[str]:
    candidates: list[str] = []
    candidates.extend(_linux_ip_addresses())
    candidates.extend(_hostname_addresses())
    candidates.extend(_default_route_address())
    candidates.append("127.0.0.1")
    return list(dict.fromkeys(candidates))


def _linux_ip_addresses() -> list[str]:
    try:
        result = subprocess.run(
            ["ip", "-4", "-o", "addr", "show"],
            capture_output=True,
            check=False,
            text=True,
            timeout=1,
        )
    except (OSError, subprocess.SubprocessError):
        return []
    addresses: list[str] = []
    for line in result.stdout.splitlines():
        parts = line.split()
        if "inet" not in parts:
            continue
        value = parts[parts.index("inet") + 1]
        addresses.append(value.split("/", 1)[0])
    return addresses


def _hostname_addresses() -> list[str]:
    try:
        infos = socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET)
    except OSError:
        return []
    return [str(info[4][0]) for info in infos]


def _default_route_address() -> list[str]:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            return [str(sock.getsockname()[0])]
    except OSError:
        return []


def _in_network(value: str, network: ipaddress.IPv4Network) -> bool:
    try:
        return ipaddress.ip_address(value) in network
    except ValueError:
        return False


def _is_private_lan(value: str) -> bool:
    try:
        address = ipaddress.ip_address(value)
    except ValueError:
        return False
    return address.version == 4 and address.is_private and not address.is_loopback


def _is_loopback(value: str) -> bool:
    try:
        return ipaddress.ip_address(value).is_loopback
    except ValueError:
        return value == "localhost"
