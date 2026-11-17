#!/usr/bin/env bash
set -euo pipefail
PLATFORM="${1:?linux or windows}"
OUT="${2:?output directory}"
ARCH="${3:-x64}"
VERSION="7543"
case "$ARCH" in
    x64|x86_64|amd64) ARCH=x64 ;;
    arm64|aarch64) ARCH=arm64 ;;
    *) echo "unknown architecture: $ARCH" >&2; exit 2 ;;
esac
case "$PLATFORM" in
    linux) ASSET="pdfium-linux-$ARCH.tgz"; LIB="lib/libpdfium.so" ;;
    windows) ASSET="pdfium-win-$ARCH.tgz"; LIB="bin/pdfium.dll" ;;
    *) echo "unknown platform: $PLATFORM" >&2; exit 2 ;;
esac
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
curl -fsSL --retry 3 -o "$TMP/pdfium.tgz" \
    "https://github.com/bblanchon/pdfium-binaries/releases/download/chromium/$VERSION/$ASSET"
tar -xzf "$TMP/pdfium.tgz" -C "$TMP"
mkdir -p "$OUT"
install -m 0755 "$TMP/$LIB" "$OUT/"
mkdir -p "$OUT/licenses"
cp "$TMP/LICENSE" "$OUT/licenses/PDFium-LICENSE.txt" 2>/dev/null || true
echo "PDFium $VERSION ($ARCH) -> $OUT/$(basename "$LIB")"
