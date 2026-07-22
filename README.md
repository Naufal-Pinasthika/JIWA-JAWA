# Catur Jawa: Dam-daman over Reliable UDP

Two independent Python processes play Dam-daman Jawa through UDP sockets. One Player act as an 
authoritative host, while another player joins as a client.

## Feature Matrix

| Feature | Status |
| --- | --- |
| Pure Dam-daman domain engine | Implemented |
| Host-authoritative two-process GUI | Implemented |
| Reliable UDP transport | Implemented |
| JSONL local gameplay logs | Implemented |
| Netem helper scripts | Implemented |
| PDF usage guide | Implemented |
| SQLite Elo-style rating service | Implemented |
| PySide6 GUI | Implemented |
| Raft logger | Documented as not implemented |

## Quick Start

```bash
chmod +x scripts/bootstrap_linux.sh
./scripts/bootstrap_linux.sh
source .venv/bin/activate
pytest -q
```

Run the normal GUI:

```bash
python3 main.py
```

Package command:

```bash
catur-jawa
```

For one-machine testing, open two terminals and run `python3 main.py` in each. In the first window
choose Host Game. In the second window choose Join Game and connect to `127.0.0.1:9999`.

## Two Machines

On Player A's machine, run `python3 main.py`, choose Host Game, and share the room address shown in
the lobby. On Player B's machine, run `python3 main.py`, choose Join Game, and enter that address.

Open UDP port `9999` in the firewall if needed. Host and peer addresses are configured through the
GUI setup screens.

2 Devices on a different network will require VPN like Tailscale to make it work.

## Game Controls

Click a piece, then click a highlighted destination. History, actions, info, resync, coordinates,
and resignation are available through the right-side utility drawer.
