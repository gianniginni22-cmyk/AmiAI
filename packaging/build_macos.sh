#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -m pip install -r requirements-desktop.txt
rm -rf build dist
python3 -m PyInstaller packaging/AmigurumiAI.spec --clean
# PyInstaller produces a macOS .app only when configured with BUNDLE; for a release build use the macOS spec variant.
python3 -m PyInstaller --name AmigurumiAI --windowed --onedir --add-data "app/static:app/static" desktop.py
printf '\nApp bundle: dist/AmigurumiAI.app\n'
