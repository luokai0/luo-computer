#!/usr/bin/env bash
# One-line installer for luo-computer
set -euo pipefail
PREFIX="${PREFIX:-$HOME/.local}"
echo "Installing luo-computer to ${PREFIX}..."
cmake -B build -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX="${PREFIX}"
cmake --build build --parallel
cmake --install build
echo "Done. Run: ${PREFIX}/bin/luo-computer"
