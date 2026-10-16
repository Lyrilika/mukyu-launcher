#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
WORK="${WORK:-$ROOT/build/appimage}"
APPDIR="$WORK/AppDir"
DEBS="$WORK/debs"
OUT="$ROOT/dist"
ARCH=x86_64

rm -rf "$WORK"; mkdir -p "$APPDIR" "$DEBS" "$OUT"

echo "== Build prerequisites"
apt-get update -qq
apt-get install -y --no-install-recommends git build-essential cmake flex bison curl python3-pip
python3 "$ROOT/packaging/licenses/repository_sources.py" fetch --platform linux --output "$DEBS"
bash "$ROOT/scripts/install_pc98_music.sh" --force
bash "$ROOT/scripts/install_thtk.sh" --update

echo "== Unpacking"
for d in "$DEBS"/*.deb; do dpkg -x "$d" "$APPDIR"; done

for d in bin lib lib64 sbin; do
  if [ -d "$APPDIR/$d" ] && [ ! -L "$APPDIR/$d" ]; then
    mkdir -p "$APPDIR/usr/$d"; cp -a "$APPDIR/$d/." "$APPDIR/usr/$d/"; rm -rf "$APPDIR/$d"
  fi
done
cd "$APPDIR/usr/bin" && ln -sf python3.12 python3 2>/dev/null || true
[ -x "$APPDIR/usr/bin/python3.12" ] || { echo "python3.12 missing from AppDir"; exit 1; }
ln -sf python3.12 "$APPDIR/usr/bin/mukyulauncher"

for lib in libgtk-4.so.1 libgraphene-1.0.so.0 libgstreamer-1.0.so.0 libpango-1.0.so.0; do
  [ -e "$APPDIR/usr/lib/x86_64-linux-gnu/$lib" ] || { echo "Required library missing from AppDir: $lib"; exit 1; }
done

mkdir -p "$APPDIR/usr/share/common-licenses"
cp -a /usr/share/common-licenses/. "$APPDIR/usr/share/common-licenses/"

echo "== Trimming"
rm -rf "$APPDIR"/usr/share/{man,info,lintian,locale,bash-completion,applications} \
       "$APPDIR"/var "$APPDIR"/etc 2>/dev/null || true
rm -rf "$APPDIR"/usr/lib/python3.12/{test,idlelib,tkinter,turtledemo,lib2to3,ensurepip} 2>/dev/null || true
find "$APPDIR" -name '__pycache__' -type d -prune -exec rm -rf {} + 2>/dev/null || true

echo "== AppDir size after trimming"
du -sh "$APPDIR"
set +o pipefail
du -s "$APPDIR"/usr/lib/x86_64-linux-gnu/* "$APPDIR"/usr/share/* 2>/dev/null | sort -rn | head -15 | awk '{printf "%6d MB  %s\n", $1/1024, $2}' 2>/dev/null
set -o pipefail

echo "== Stripping libraries"
find "$APPDIR/usr" -type f \( -name '*.so' -o -name '*.so.*' \) -exec strip --strip-unneeded {} + 2>/dev/null || true

echo "== Compiling GSettings schemas"
SCHEMAS="$APPDIR/usr/share/glib-2.0/schemas"
if [ -d "$SCHEMAS" ]; then glib-compile-schemas "$SCHEMAS"; fi

echo "== pypdfium2"
/usr/bin/python3 -m pip install --quiet --break-system-packages --no-compile \
    --no-cache-dir --only-binary=:all: \
    --target "$APPDIR/usr/lib/python3/dist-packages" pypdfium2==5.14.0

install -m 755 "$ROOT/packaging/appimage/runtime-x86_64" "$WORK/runtime-x86_64"

echo "== Launcher files"
bash "$ROOT/packaging/appimage/stage_app.sh" "$APPDIR"

echo "== Packing"
TOOL="$WORK/appimagetool"
curl -fsSL -o "$TOOL" "https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-$ARCH.AppImage"
chmod +x "$TOOL"
ARCH=$ARCH "$TOOL" --appimage-extract-and-run --no-appstream --runtime-file "$WORK/runtime-x86_64" "$APPDIR" "$OUT/Mukyu_Launcher-$ARCH.AppImage"
echo "Built: $OUT/Mukyu_Launcher-$ARCH.AppImage"
