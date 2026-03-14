#!/usr/bin/env bash
# CryptoQuant — local model trainer (Linux / macOS)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Activate virtual environment
if [ -f "venv/bin/activate" ]; then
    # shellcheck source=/dev/null
    source venv/bin/activate
elif [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
else
    echo "ERROR: No virtual environment found."
    echo "Run:  python -m venv venv && pip install -r requirements.txt"
    exit 1
fi

export PYTHONPATH="$SCRIPT_DIR"

echo "=== CryptoQuant Local Trainer ==="
python local_train.py
