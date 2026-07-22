#!/usr/bin/env bash
set -euo pipefail

IFACE="${1:-}"
if [[ -z "$IFACE" ]]; then
  echo "Usage: sudo $0 <interface>" >&2
  exit 2
fi
echo "Clearing netem qdisc from $IFACE if present"
tc qdisc del dev "$IFACE" root 2>/dev/null || true
tc qdisc show dev "$IFACE"
