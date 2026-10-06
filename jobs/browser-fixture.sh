#!/bin/bash
set -euo pipefail
input="$1"
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
cp -r "$input/mcc" "$work/"
cd "$work"
PYTHONPATH="$work" python3 "$input/jobs/browser_fixture.py" "$input/artifacts/result"
