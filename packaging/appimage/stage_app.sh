#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
APPDIR="${1:?Usage: stage_app.sh /path/to/AppDir}"
mkdir -p "$APPDIR"
APPDIR="$(cd -- "$APPDIR" && pwd)"
APP="$APPDIR/usr/share/mukyulauncher"
mkdir -p "$APP"
tar -C "$ROOT" --exclude='__pycache__' --exclude='*.pyc' --exclude='*.pyo' \
    --exclude='*.exe' --exclude='*.dll' --exclude='tools/windows' \
    -cf - main.py README.md LICENSE requirements.txt mukyu assets scripts tools | tar -C "$APP" -xf -
for tool in tools/thtk/bin/thdat tools/pc98/bin/pmd_render tools/pc98/bin/mdt_render tools/umu/umu-run; do
    if [ -f "$APP/$tool" ]; then chmod +x "$APP/$tool"; fi
done
install -m 755 "$ROOT/packaging/appimage/AppRun" "$APPDIR/AppRun"
install -m 644 "$ROOT/packaging/appimage/mukyulauncher.desktop" "$APPDIR/mukyulauncher.desktop"
install -m 644 "$ROOT/assets/icons/hicolor/scalable/apps/mukyulauncher.png" "$APPDIR/mukyulauncher.png"
ln -sf mukyulauncher.png "$APPDIR/.DirIcon"
mkdir -p "$APP/assets/icons/hicolor/256x256/apps"
cp "$APPDIR/mukyulauncher.png" "$APP/assets/icons/hicolor/256x256/apps/mukyulauncher.png"
