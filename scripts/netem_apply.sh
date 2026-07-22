#!/usr/bin/env bash
set -euo pipefail

IFACE="${1:-}"
LOSS="${2:-50}"
if [[ -z "$IFACE" ]]; then
  echo "Usage: sudo $0 <interface> [loss_percent]" >&2
  echo "Run 'ip link' to list interfaces. Do not apply this to an SSH/Internet interface casually." >&2
  exit 2
fi

echo "Current qdisc for $IFACE:"
tc qdisc show dev "$IFACE" || true
echo "Applying netem loss ${LOSS}% to $IFACE"
tc qdisc replace dev "$IFACE" root netem loss "${LOSS}%"
tc qdisc show dev "$IFACE"
