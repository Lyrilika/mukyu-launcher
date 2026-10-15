#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
WORK="${WORK:-$ROOT/build/appimage}"
APPDIR="$WORK/AppDir"
DEBS="$WORK/debs"
OUT="$ROOT/dist"
ARCH=x86_64

PACKAGES=(
  python3 python3-gi python3-gi-cairo gir1.2-gtk-4.0 gir1.2-gdkpixbuf-2.0 gir1.2-pango-1.0
  gir1.2-graphene-1.0 gir1.2-gstreamer-1.0 gir1.2-gst-plugins-base-1.0
  gstreamer1.0-plugins-base gstreamer1.0-plugins-good glib-networking
  gstreamer1.0-pulseaudio gstreamer1.0-pipewire gstreamer1.0-alsa
  librsvg2-common adwaita-icon-theme shared-mime-info fonts-dejavu-core
  libglib2.0-bin libgraphene-1.0-0
)
EXCLUDE_RE='^(libc6|libc-bin|libgcc-s1|libudev1|libgl1.*|libegl.*|libgles.*|libglx.*|libglvnd0|libdrm.*|libgbm1|mesa-.*|libvulkan.*|libnvidia-.*|libxcb-dri.*|libllvm.*|libsystemd0|dpkg|apt|debconf.*|tzdata|base-files|libc-dev-bin|gcc-.*-base|init-system-helpers|perl-base|lsb-base|libpam.*|systemd|systemd-sysv|systemd-timesyncd|udev|dbus|dbus-bin|dbus-daemon|dbus-session-bus-common|dbus-system-bus-common|adduser|passwd|login|util-linux|mount|bash|dash|coreutils|fonts-(noto|urw|texgyre|freefont|croscore|liberation|dejavu-mono).*|humanity-icon-theme|ubuntu-mono|iso-codes|xfonts-.*)$'

rm -rf "$WORK"; mkdir -p "$APPDIR" "$DEBS" "$OUT"

echo "== Resolving dependencies"
apt-get update -qq
apt-get install -y --no-install-recommends git build-essential cmake flex bison curl python3-pip
python3 - <<'SOURCES'
from pathlib import Path
p = Path('/etc/apt/sources.list.d/ubuntu.sources')
text = p.read_text()
p.with_name('mukyu-source-downloads.sources').write_text(text.replace('Types: deb', 'Types: deb-src'))
SOURCES
apt-get update -qq
bash "$ROOT/scripts/install_pc98_music.sh" --force
bash "$ROOT/scripts/install_thtk.sh" --update
mapfile -t ALL < <(apt-cache depends --recurse --no-recommends --no-suggests --no-conflicts \
    --no-breaks --no-replaces --no-enhances "${PACKAGES[@]}" | grep '^\w' | sort -u)
TO_GET=()
for p in "${ALL[@]}"; do [[ "$p" =~ $EXCLUDE_RE ]] || TO_GET+=("$p"); done
echo "   ${#TO_GET[@]} packages"

echo "== Downloading"
cd "$DEBS"
have_deb() { compgen -G "${1%%:*}_*.deb" >/dev/null; }
for attempt in 1 2 3; do
  MISSING=()
  for p in "${TO_GET[@]}"; do have_deb "$p" || MISSING+=("$p"); done
  [ "${#MISSING[@]}" -eq 0 ] && break
  echo "   attempt $attempt: ${#MISSING[@]} package(s) to download"
  printf '%s\n' "${MISSING[@]}" | xargs -P 4 -n 1 sh -c 'apt-get download -qq "$0" 2>/dev/null || echo "download failed: $0"'
done
STILL=()
for p in "${TO_GET[@]}"; do have_deb "$p" || STILL+=("$p"); done
if [ "${#STILL[@]}" -gt 0 ]; then
  echo "Could not download: ${STILL[*]}"
fi

set +o pipefail
echo "== Largest downloaded packages (MB)"
ls -S "$DEBS"/*.deb 2>/dev/null | head -25 | while read -r f; do printf '%6s  %s\n' "$(( $(stat -c%s "$f") / 1048576 ))" "$(basename "$f")"; done
set -o pipefail

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
    --target "$APPDIR/usr/lib/python3/dist-packages" pypdfium2

echo "== Matching runtime sources"
SOURCES="$WORK/sources"
python3 "$ROOT/packaging/licenses/collect_sources.py" debian --debs "$DEBS" --output "$SOURCES"
python3 "$ROOT/packaging/licenses/collect_sources.py" runtime --output "$SOURCES" \
    --binary "$WORK/runtime-x86_64" --notices "$ROOT/tools/licenses/appimage"
python3 "$ROOT/packaging/licenses/collect_sources.py" common --platform linux --output "$SOURCES"

echo "== Launcher files"
bash "$ROOT/packaging/appimage/stage_app.sh" "$APPDIR"

echo "== Packing"
TOOL="$WORK/appimagetool"
curl -fsSL -o "$TOOL" "https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-$ARCH.AppImage"
chmod +x "$TOOL"
ARCH=$ARCH "$TOOL" --appimage-extract-and-run --no-appstream --runtime-file "$WORK/runtime-x86_64" "$APPDIR" "$OUT/Mukyu_Launcher-$ARCH.AppImage"
python3 "$ROOT/packaging/licenses/collect_sources.py" pack --platform linux --sources "$SOURCES" --output "$OUT"
cp "$ROOT/tools/licenses/THIRD_PARTY_NOTICES.txt" "$OUT/Mukyu-linux-THIRD-PARTY-NOTICES.txt"
echo "Built: $OUT/Mukyu_Launcher-$ARCH.AppImage"
