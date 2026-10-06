#!/bin/bash
set -euo pipefail
input="$1"
rm -f "$input/artifacts/result/PASS"
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
cp -r "$input/mcc" "$input/tests" "$input/examples" "$input/contracts" "$input/onboarding" "$input/docs" "$work/"
cd "$work"
python3 -m unittest discover -s tests -v > "$input/artifacts/result/tests.log" 2>&1
python3 --version > "$input/artifacts/result/toolchain.txt"
sha256sum "$input/mcc/owner.py" "$input/tests/test_owner.py" "$input/mcc/static/app.js" "$input/mcc/server.py" > "$input/artifacts/result/source.sha256"
printf 'deterministic tests passed; not model/channel proof\n' > "$input/artifacts/result/UNIT-PASS"
