#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
WORK="${WORK:-$ROOT/build/appimage}"
APPDIR="$WORK/AppDir"
OUT="$ROOT/dist"
ARCH=x86_64

rm -rf "$WORK"; mkdir -p "$APPDIR/usr/bin" "$APPDIR/usr/lib" "$APPDIR/usr/share/mukyulauncher" "$OUT"

echo "== Building"
cargo build --release --locked --manifest-path "$ROOT/Cargo.toml"
install -m 755 "$ROOT/target/release/mukyulauncher" "$APPDIR/usr/bin/mukyulauncher"

echo "== PDFium"
bash "$ROOT/scripts/fetch_pdfium.sh" linux "$APPDIR/usr/lib"

echo "== Resources"
APP="$APPDIR/usr/share/mukyulauncher"
cp -a "$ROOT/assets" "$APP/"
mkdir -p "$APP/tools"
for item in thtk pc98 umu licenses; do
    [ -e "$ROOT/tools/$item" ] && cp -a "$ROOT/tools/$item" "$APP/tools/"
done
rm -rf "$APP/tools/pc98/src"
mv "$APPDIR/usr/lib/licenses/"* "$APP/tools/licenses/" 2>/dev/null || true
rmdir "$APPDIR/usr/lib/licenses" 2>/dev/null || true
cp "$ROOT/ui/fonts/OFL.txt" "$APP/tools/licenses/Rubik-OFL.txt"
cp "$ROOT/LICENSE" "$APP/LICENSE"
for tool in tools/thtk/bin/thdat tools/pc98/bin/pmd_render tools/pc98/bin/mdt_render tools/umu/umu-run; do
    [ -f "$APP/$tool" ] && chmod +x "$APP/$tool"
done

install -m 755 "$ROOT/packaging/appimage/AppRun" "$APPDIR/AppRun"
install -m 644 "$ROOT/packaging/appimage/mukyulauncher.desktop" "$APPDIR/mukyulauncher.desktop"
install -m 644 "$ROOT/assets/icons/hicolor/scalable/apps/mukyulauncher.png" "$APPDIR/mukyulauncher.png"
ln -sf mukyulauncher.png "$APPDIR/.DirIcon"

echo "== Smoke test"
MUKYU_ROOT="$APP" MUKYU_PDFIUM="$APPDIR/usr/lib/libpdfium.so" "$APPDIR/usr/bin/mukyulauncher" --bgm-report >/dev/null

echo "== Packing"
TOOL="$WORK/appimagetool"
curl -fsSL -o "$TOOL" "https://github.com/AppImage/appimagetool/releases/download/1.9.0/appimagetool-$ARCH.AppImage"
chmod +x "$TOOL"
install -m 755 "$ROOT/packaging/appimage/runtime-x86_64" "$WORK/runtime-x86_64"
ARCH=$ARCH "$TOOL" --appimage-extract-and-run --no-appstream --runtime-file "$WORK/runtime-x86_64" \
    "$APPDIR" "$OUT/Mukyu_Launcher-$ARCH.AppImage"
echo "Built: $OUT/Mukyu_Launcher-$ARCH.AppImage ($(du -h "$OUT/Mukyu_Launcher-$ARCH.AppImage" | cut -f1))"
