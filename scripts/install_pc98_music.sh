#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="$ROOT/tools/pc98/bin"
SRC="$ROOT/tools/pc98/src"
FM_REV=4fa914e4b2b994cb3ccf92d571a20a7cdf1fe36a
X86_REV=ce81129c57fdfbf690bebc210a8db97d926cc5e7
FORCE=0
EXT=
LINK=(-static-libstdc++ -static-libgcc)
case "$(uname -s)" in MINGW*|MSYS*) EXT=.exe; LINK=(-static) ;; esac
for arg in "$@"; do
    case "$arg" in
        --force|--update) FORCE=1 ;;
        --help|-h) echo "Usage: $(basename "$0") [--force]"; exit 0 ;;
        *) echo "Unknown option: $arg" >&2; exit 2 ;;
    esac
done
if [[ "$FORCE" -eq 0 && -x "$BIN/pmd_render$EXT" && -x "$BIN/mdt_render$EXT" && -f "$ROOT/tools/pc98/BUILD_INFO.txt" ]] && grep -q "$FM_REV" "$ROOT/tools/pc98/BUILD_INFO.txt"; then
    echo "PC-98 helpers are already installed (use --force to rebuild)."
    exit 0
fi
for cmd in git g++ gcc tar; do
    command -v "$cmd" >/dev/null 2>&1 || { echo "Missing build prerequisite: $cmd" >&2; exit 1; }
done
TMP_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/mukyulauncher-pc98.XXXXXXXX")"
trap 'rm -rf "$TMP_ROOT"' EXIT
fetch() {
    git init -q "$TMP_ROOT/$1"
    git -C "$TMP_ROOT/$1" remote add origin "$2"
    git -C "$TMP_ROOT/$1" fetch -q --depth 1 origin "$3"
    git -C "$TMP_ROOT/$1" checkout -q --detach FETCH_HEAD
    [[ "$(git -C "$TMP_ROOT/$1" rev-parse HEAD)" == "$3" ]]
}
fetch 98fmplayer https://github.com/myon98/98fmplayer.git "$FM_REV"
fetch libx86emu https://github.com/wfeldt/libx86emu.git "$X86_REV"
FM="$TMP_ROOT/98fmplayer"
X86="$TMP_ROOT/libx86emu"
if [[ -n "$EXT" ]]; then
    sed -i 's|^#if defined(__i386__) \|\| defined (__x86_64__)$|#if (defined(__i386__) \|\| defined (__x86_64__)) \&\& !defined(_WIN32)|' "$X86/mem.c"
    grep -q '!defined(_WIN32)' "$X86/mem.c" || { echo "libx86emu Windows patch failed" >&2; exit 1; }
fi
mkdir -p "$TMP_ROOT/obj" "$BIN" "$ROOT/tools/licenses"
FM_OBJECTS=()
for file in opna opnafm opnassg opnassg-sinc-c opnassg-sinc-sse2 opnadrum opnaadpcm; do
    gcc -std=c11 -O3 -flto -I"$FM" -c "$FM/libopna/$file.c" -o "$TMP_ROOT/obj/$file.o"
    FM_OBJECTS+=("$TMP_ROOT/obj/$file.o")
done
PMD_OBJECTS=()
for file in fmdriver_pmd fmdriver_common ppz8; do
    gcc -std=c11 -O3 -flto -I"$FM" -c "$FM/fmdriver/$file.c" -o "$TMP_ROOT/obj/$file.o"
    PMD_OBJECTS+=("$TMP_ROOT/obj/$file.o")
done
gcc -std=c11 -O3 -flto -I"$FM" -c "$SRC/pmd_driver.c" -o "$TMP_ROOT/obj/pmd_driver.o"
g++ -std=c++14 -O3 -flto -I"$FM" "${LINK[@]}" "$SRC/pmd_render.cpp" "$TMP_ROOT/obj/pmd_driver.o" \
    "${PMD_OBJECTS[@]}" "${FM_OBJECTS[@]}" -lm -o "$TMP_ROOT/pmd_render$EXT"
X86_OBJECTS=()
for file in api decode mem ops ops2 prim_ops; do
    gcc -O3 -flto -I"$X86/include" -c "$X86/$file.c" -o "$TMP_ROOT/obj/x86_$file.o"
    X86_OBJECTS+=("$TMP_ROOT/obj/x86_$file.o")
done
g++ -std=c++14 -O3 -flto -I"$FM" -I"$X86/include" "${LINK[@]}" "$SRC/mdt_render.cpp" \
    "${FM_OBJECTS[@]}" "${X86_OBJECTS[@]}" -lm -o "$TMP_ROOT/mdt_render$EXT"
install -m 755 "$TMP_ROOT/pmd_render$EXT" "$BIN/pmd_render$EXT"
install -m 755 "$TMP_ROOT/mdt_render$EXT" "$BIN/mdt_render$EXT"
install -m 644 "$FM/LICENSE" "$ROOT/tools/licenses/98fmplayer-LICENSE"
install -m 644 "$X86/LICENSE" "$ROOT/tools/licenses/libx86emu-LICENSE"
{
    printf '98fmplayer %s\nlibx86emu %s\n' "$FM_REV" "$X86_REV"
    printf 'Build recipe: scripts/install_pc98_music.sh\n'
    if [[ -n "$EXT" ]]; then printf 'libx86emu mem.c: disable Linux-specific memory code on Windows.\n'; fi
    gcc --version | head -1
    g++ --version | head -1
} > "$ROOT/tools/pc98/BUILD_INFO.txt"
echo "Built BSD-licensed PC-98 helpers."
