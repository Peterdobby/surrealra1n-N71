#!/bin/bash
# Dispatch the read-only N71 mode before upstream initialization.
if [[ "${1:-}" == "--n71-port" ]]; then
    shift
    N71_SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)" || exit 1
    if ! command -v python3 >/dev/null 2>&1; then
        echo "N71 port check requires Python 3.9 or newer." >&2
        exit 1
    fi
    exec python3 -B "$N71_SCRIPT_DIR/n71/check.py" "$@"
fi

printf "%s\n" "Use ./surrealra1n.sh --n71-port --help for N71 commands." >&2
exit 2
