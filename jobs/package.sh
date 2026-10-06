#!/bin/bash
set -euo pipefail
input="$1"
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
cp -r "$input/mcc" "$input/pyproject.toml" "$input/LICENSE" "$input/README.md" "$work/"
cd "$work"
python3 -m venv build-env
build-env/bin/python -m pip install --disable-pip-version-check setuptools==75.8.0 wheel==0.45.1 > "$input/artifacts/result/package-build.log" 2>&1
build-env/bin/python -m pip wheel --no-deps --no-build-isolation -w dist . >> "$input/artifacts/result/package-build.log" 2>&1
python3 -m venv install-env
install-env/bin/python -m pip install --no-index --no-deps dist/*.whl > "$input/artifacts/result/package-install.log" 2>&1
mkdir -m700 "$work/home"
HOME="$work/home" install-env/bin/mcc-owner --help > "$input/artifacts/result/package-owner-help.log"
HOME="$work/home" install-env/bin/mcc --help > "$input/artifacts/result/package-viewer-help.log"
HOME="$work/home" install-env/bin/mcc-bridge --help > "$input/artifacts/result/package-bridge-help.log"
install-env/bin/python "$input/jobs/package_check.py" "$work/dist" "$input/artifacts/result" "$input/LICENSE"
cp dist/*.whl "$input/artifacts/result/"
