# Catur Jawa: Dam-daman over Reliable UDP

Two independent Python processes play Dam-daman Jawa through UDP sockets. Player A is the
authoritative host, Player B joins as a client, and reliability is implemented above UDP with
versioned JSON envelopes, ACKs, retransmission, payload hashes, deduplication, and session IDs.

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

The old host/join CLI files have been removed. Host and join setup now happen inside the GUI.

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

## Game Controls

Click a piece, then click a highlighted destination. History, actions, info, resync, coordinates,
and resignation are available through the right-side utility drawer.

## Netem Warning

Identify your interface with `ip link`. Applying loss to a remote-access interface can interrupt SSH
or Internet access.

```bash
sudo ./scripts/netem_apply.sh wlp2s0 50
sudo ./scripts/netem_status.sh wlp2s0
sudo ./scripts/netem_clear.sh wlp2s0
```

## Documentation

See `docs/USAGE.md` and `docs/USAGE.pdf` for the usage guide, `docs/BOARD.md` for coordinates,
`docs/PROTOCOL.md` for reliable UDP, and `docs/TESTING.md` for verified commands.

References:

- Dam-daman Jawa Wikibooks: https://id.wikibooks.org/wiki/Permainan_Tradisional_%22Catur%22_di_Indonesia/Dam-daman_%28Jawa%29
- Linux netem: https://wiki.linuxfoundation.org/networking/netem
- Elo rating: https://en.wikipedia.org/wiki/Elo_rating_system