#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"
python3 aitrend_reporter.py --output-dir reports --days-back 1
