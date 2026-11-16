#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
WHAT="${1:-all}"
TMP_ROOT="${TMPDIR:-/tmp}/mukyulauncher-win-build"
rm -rf "$TMP_ROOT"; mkdir -p "$TMP_ROOT"
trap 'rm -rf "$TMP_ROOT"' EXIT

build_thtk() {
    local target="$ROOT/tools/thtk" bin="$ROOT/tools/thtk/bin"
    mkdir -p "$bin"
    echo "== thdat: fetching thtk..."
    git clone --depth 1 --recurse-submodules --shallow-submodules \
        https://github.com/thpatch/thtk.git "$TMP_ROOT/thtk"
    local rev; rev="$(git -C "$TMP_ROOT/thtk" rev-parse --short=12 HEAD)"
    echo "== thdat: building revision $rev..."
    cmake -S "$TMP_ROOT/thtk" -B "$TMP_ROOT/thtk-build" -G Ninja \
        -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=OFF \
        -DWITH_LIBPNG_SOURCE=ON -DWITH_OPENMP=OFF -DCONTRIB_UTHDAT=OFF \
        -DCMAKE_EXE_LINKER_FLAGS="-static" >"$TMP_ROOT/thtk.log" 2>&1 \
        || { tail -40 "$TMP_ROOT/thtk.log"; exit 1; }
    cmake --build "$TMP_ROOT/thtk-build" --target thdat >>"$TMP_ROOT/thtk.log" 2>&1 \
        || { tail -40 "$TMP_ROOT/thtk.log"; exit 1; }
    local exe; exe="$(find "$TMP_ROOT/thtk-build" -type f -name thdat.exe -print -quit)"
    [[ -n "$exe" ]] || { echo "thdat.exe was not produced"; tail -40 "$TMP_ROOT/thtk.log"; exit 1; }
    install -m 0755 "$exe" "$bin/thdat.exe"
    mkdir -p "$ROOT/tools/licenses/thtk"
    for l in COPYING COPYING.zlib COPYING.libpng; do
        [[ -f "$TMP_ROOT/thtk/$l" ]] && install -m 0644 "$TMP_ROOT/thtk/$l" "$ROOT/tools/licenses/thtk/$l"
    done
    printf '%s\n' "$rev" > "$target/REVISION"
    echo "== thdat.exe -> $bin/thdat.exe"
}

build_pc98() {
    bash "$ROOT/scripts/install_pc98_music.sh" --force
}

case "$WHAT" in
    thtk) build_thtk ;;
    pc98) build_pc98 ;;
    all)  build_thtk; build_pc98 ;;
    *) echo "Usage: $0 [thtk|pc98|all]" >&2; exit 2 ;;
esac
echo "Done."
