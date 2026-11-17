#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
WORK="${WORK:-$ROOT/build/appimage}"
APPDIR="$WORK/AppDir"
OUT="$ROOT/dist"
ARCH="${ARCH:-$(uname -m)}"
case "$ARCH" in
    x86_64|amd64) ARCH=x86_64; PDFIUM_ARCH=x64; ELF_ARCH="x86-64" ;;
    aarch64|arm64) ARCH=aarch64; PDFIUM_ARCH=arm64; ELF_ARCH="aarch64" ;;
    *) echo "Unsupported architecture: $ARCH" >&2; exit 1 ;;
esac

rm -rf "$WORK"; mkdir -p "$APPDIR/usr/bin" "$APPDIR/usr/lib" "$APPDIR/usr/share/mukyulauncher" "$OUT"

echo "== Building"
cargo build --release --locked --manifest-path "$ROOT/Cargo.toml"
install -m 755 "$ROOT/target/release/mukyulauncher" "$APPDIR/usr/bin/mukyulauncher"
file -b "$APPDIR/usr/bin/mukyulauncher" | grep -q "$ELF_ARCH" || { echo "mukyulauncher was not built for $ARCH"; exit 1; }

echo "== PDFium"
bash "$ROOT/scripts/fetch_pdfium.sh" linux "$APPDIR/usr/lib" "$PDFIUM_ARCH"

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
for tool in tools/thtk/bin/thdat tools/pc98/bin/pmd_render tools/pc98/bin/mdt_render; do
    if [ -f "$APP/$tool" ] && ! file -b "$APP/$tool" | grep -q "$ELF_ARCH"; then
        echo "$tool is not built for $ARCH. Rebuild it with scripts/install_thtk.sh --update and scripts/install_pc98_music.sh --force."
        exit 1
    fi
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
install -m 755 "$ROOT/packaging/appimage/runtime-$ARCH" "$WORK/runtime-$ARCH"
REPO="${GITHUB_REPOSITORY:-Lyrilika/mukyu-launcher}"
UPDATE_INFO="gh-releases-zsync|${REPO%%/*}|${REPO##*/}|latest|Mukyu_Launcher-$ARCH.AppImage.zsync"
rm -f "$OUT/Mukyu_Launcher-$ARCH.AppImage" "$OUT/Mukyu_Launcher-$ARCH.AppImage.zsync"
(cd "$OUT" && ARCH=$ARCH "$TOOL" --appimage-extract-and-run --no-appstream --runtime-file "$WORK/runtime-$ARCH" \
    -u "$UPDATE_INFO" "$APPDIR" "Mukyu_Launcher-$ARCH.AppImage")
if [ ! -s "$OUT/Mukyu_Launcher-$ARCH.AppImage.zsync" ]; then
    if command -v zsyncmake >/dev/null; then
        (cd "$OUT" && zsyncmake -u "Mukyu_Launcher-$ARCH.AppImage" "Mukyu_Launcher-$ARCH.AppImage")
    elif [ -n "${MUKYU_ALLOW_NO_ZSYNC:-}" ]; then
        echo "WARNING: zsyncmake not found, no .zsync file was created"
    else
        echo "zsyncmake is required to create the .zsync file (Debian/Ubuntu: apt install zsync, Arch: pacman -S zsync)"
        exit 1
    fi
fi
if [ -s "$OUT/Mukyu_Launcher-$ARCH.AppImage.zsync" ]; then
    grep -a -q "^Filename: Mukyu_Launcher-$ARCH.AppImage$" "$OUT/Mukyu_Launcher-$ARCH.AppImage.zsync" \
        || { echo "The .zsync file does not reference Mukyu_Launcher-$ARCH.AppImage"; exit 1; }
fi
sed -n 's/^version = "\(.*\)"/\1/p' "$ROOT/Cargo.toml" | head -1 > "$OUT/VERSION"
echo "Built: $OUT/Mukyu_Launcher-$ARCH.AppImage ($(du -h "$OUT/Mukyu_Launcher-$ARCH.AppImage" | cut -f1))"
[ -s "$OUT/Mukyu_Launcher-$ARCH.AppImage.zsync" ] && echo "Built: $OUT/Mukyu_Launcher-$ARCH.AppImage.zsync"
echo "Version: $(cat "$OUT/VERSION")"
