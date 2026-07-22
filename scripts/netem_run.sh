#!/usr/bin/env bash
set -euo pipefail

IFACE="${1:-}"
LOSS="${2:-50}"
shift 2 || true
if [[ -z "$IFACE" || "$#" -eq 0 ]]; then
  echo "Usage: sudo $0 <interface> [loss_percent] -- <command> [args...]" >&2
  exit 2
fi
if [[ "${1:-}" == "--" ]]; then
  shift
fi
cleanup() {
  "$(dirname "$0")/netem_clear.sh" "$IFACE" || true
}
trap cleanup EXIT INT TERM HUP
"$(dirname "$0")/netem_apply.sh" "$IFACE" "$LOSS"
"$@"
