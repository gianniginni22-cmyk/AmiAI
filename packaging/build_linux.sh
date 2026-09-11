#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -m pip install -r requirements-desktop.txt
rm -rf build dist
python3 -m PyInstaller packaging/AmigurumiAI.spec --clean
printf '\nExecutable: dist/AmigurumiAI\n'
