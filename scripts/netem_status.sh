#!/usr/bin/env bash
set -euo pipefail

IFACE="${1:-}"
if [[ -z "$IFACE" ]]; then
  echo "Usage: sudo $0 <interface>" >&2
  exit 2
fi
tc qdisc show dev "$IFACE"
