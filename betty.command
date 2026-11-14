#!/usr/bin/env bash
# Double-click me on macOS (or run ./betty.command on Linux). Needs Python 3.10+.
cd "$(dirname "$0")"
command -v python3 >/dev/null || { echo "Python 3 is not installed: https://www.python.org/downloads/"; read -r; exit 1; }
python3 -c "import betty" 2>/dev/null || python3 -m pip install --quiet -e .
python3 -m betty "$@"
echo; read -r -p "Press Enter to close..."
