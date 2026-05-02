#!/usr/bin/env bash
# Step 94-95: Package luo-computer into a release archive
set -euo pipefail

BUILD_TYPE="${1:-Release}"
VERSION=$(git describe --tags --always --dirty 2>/dev/null || echo "dev")
PLATFORM=$(uname -s | tr '[:upper:]' '[:lower:]')
ARCH=$(uname -m)
PKG="luo-computer-${VERSION}-${PLATFORM}-${ARCH}"

echo "Building ${PKG} (${BUILD_TYPE})..."
cmake -B build -DCMAKE_BUILD_TYPE="${BUILD_TYPE}" -DCMAKE_INSTALL_PREFIX="dist/${PKG}"
cmake --build build --config "${BUILD_TYPE}" --parallel
cmake --install build --config "${BUILD_TYPE}"

echo "Copying docs..."
mkdir -p "dist/${PKG}/docs"
cp README.md CHANGELOG.md "dist/${PKG}/"
cp docs/*.md "dist/${PKG}/docs/"

echo "Archiving..."
cd dist
tar -czf "${PKG}.tar.gz" "${PKG}"
echo "Created dist/${PKG}.tar.gz"
