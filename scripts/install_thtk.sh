#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET_DIR="$SCRIPT_DIR/tools/thtk"
BIN_DIR="$TARGET_DIR/bin"
THDAT="$BIN_DIR/thdat"
TMP_ROOT="${TMPDIR:-/tmp}/mukyulauncher-thtk"
SOURCE_DIR="$TMP_ROOT/source"
BUILD_DIR="$TMP_ROOT/build"
INSTALL_LOG="$TMP_ROOT/build.log"
REPO_URL="https://github.com/thpatch/thtk.git"

ASSUME_YES=0
FORCE_UPDATE=0

usage() {
    cat <<USAGE
Usage: $(basename "$0") [options]

Build the latest thtk master revision and install its thdat utility into:
  $THDAT

Options:
  --yes       Automatically install missing system build dependencies when
              a supported package manager is available.
  --update    Rebuild thdat even if a bundled copy already exists.
  --help      Show this help.
USAGE
}

for arg in "$@"; do
    case "$arg" in
        --yes) ASSUME_YES=1 ;;
        --update) FORCE_UPDATE=1 ;;
        --help|-h) usage; exit 0 ;;
        *)
            echo "Unknown option: $arg" >&2
            usage >&2
            exit 2
            ;;
    esac
done

if [[ -x "$THDAT" && "$FORCE_UPDATE" -eq 0 ]]; then
    echo "thdat is already installed:"
    echo "  $THDAT"
    echo
    echo "Use --update to rebuild it from the latest thtk master revision."
    exit 0
fi

command_exists() {
    command -v "$1" >/dev/null 2>&1
}

need_cmds=(git cmake flex bison)
missing=()
for cmd in "${need_cmds[@]}"; do
    if ! command_exists "$cmd"; then
        missing+=("$cmd")
    fi
done

if ! command_exists cc && ! command_exists gcc && ! command_exists clang; then
    missing+=("a C compiler")
fi

install_deps() {
    local sudo_cmd=
    if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
        if ! command_exists sudo; then
            echo "sudo is required to install build dependencies on this system." >&2
            exit 1
        fi
        sudo_cmd=sudo
    fi

    if command_exists pacman; then
        echo "Installing build dependencies with pacman..."
        $sudo_cmd pacman -S --needed --noconfirm base-devel cmake git flex bison
        return
    fi

    if command_exists apt-get; then
        echo "Installing build dependencies with apt..."
        $sudo_cmd apt-get update
        $sudo_cmd apt-get install -y build-essential cmake git flex bison
        return
    fi

    if command_exists dnf; then
        echo "Installing build dependencies with dnf..."
        $sudo_cmd dnf install -y gcc gcc-c++ make cmake git flex bison
        return
    fi

    if command_exists zypper; then
        echo "Installing build dependencies with zypper..."
        $sudo_cmd zypper --non-interactive install gcc gcc-c++ make cmake git flex bison
        return
    fi

    if command_exists apk; then
        echo "Installing build dependencies with apk..."
        $sudo_cmd apk add build-base cmake git flex bison
        return
    fi

    echo "No supported package manager was found." >&2
    echo "Install these tools manually, then run this script again:" >&2
    printf '  %s\n' "${missing[@]}" >&2
    exit 1
}

if ((${#missing[@]})); then
    echo "Missing build dependencies: ${missing[*]}"
    if [[ "$ASSUME_YES" -eq 1 ]]; then
        install_deps
    else
        if [[ -t 0 ]]; then
            printf 'Install the missing dependencies automatically? [Y/n] '
            read -r answer
            answer="${answer:-Y}"
            if [[ "$answer" =~ ^[Yy]([Ee][Ss])?$ ]]; then
                install_deps
            else
                echo "Install them manually and run this script again." >&2
                exit 1
            fi
        else
            echo "Run with --yes to let this script install dependencies on a supported distro." >&2
            echo "Otherwise install them manually and rerun." >&2
            exit 1
        fi
    fi
fi

for cmd in git cmake flex bison; do
    if ! command_exists "$cmd"; then
        echo "Required command is still missing after dependency installation: $cmd" >&2
        exit 1
    fi
done

if ! command_exists cc && ! command_exists gcc && ! command_exists clang; then
    echo "No C compiler was found after dependency installation." >&2
    exit 1
fi

rm -rf "$TMP_ROOT"
mkdir -p "$TMP_ROOT" "$BIN_DIR"

cleanup() {
    rm -rf "$TMP_ROOT"
}
trap cleanup EXIT

echo "Downloading the latest thtk source..."
git clone \
    --depth 1 \
    --recurse-submodules \
    --shallow-submodules \
    "$REPO_URL" \
    "$SOURCE_DIR"

REVISION="$(git -C "$SOURCE_DIR" rev-parse --short=12 HEAD)"
echo "Building thtk revision $REVISION..."

cmake -S "$SOURCE_DIR" -B "$BUILD_DIR" \
    -DCMAKE_BUILD_TYPE=Release \
    -DBUILD_SHARED_LIBS=OFF \
    -DWITH_LIBPNG_SOURCE=ON \
    -DWITH_OPENMP=OFF \
    -DCONTRIB_UTHDAT=OFF \
    -DCMAKE_INSTALL_PREFIX="$TARGET_DIR" \
    -DCMAKE_INSTALL_LIBDIR=lib64 \
    >"$INSTALL_LOG" 2>&1

cmake --build "$BUILD_DIR" --target thdat --parallel "$(getconf _NPROCESSORS_ONLN 2>/dev/null || printf '1')" \
    >>"$INSTALL_LOG" 2>&1

THDAT_BUILD="$(find "$BUILD_DIR" -type f -name thdat -perm -u+x -print -quit)"
if [[ -z "$THDAT_BUILD" ]]; then
    echo "Build completed without producing thdat." >&2
    echo "Build log: $INSTALL_LOG" >&2
    exit 1
fi

install -m 0755 "$THDAT_BUILD" "$THDAT"

mkdir -p "$SCRIPT_DIR/tools/licenses/thtk"
for license in COPYING COPYING.zlib COPYING.libpng; do
    if [[ -f "$SOURCE_DIR/$license" ]]; then
        install -m 0644 "$SOURCE_DIR/$license" "$SCRIPT_DIR/tools/licenses/thtk/$license"
    fi
done

printf '%s\n' "$REVISION" > "$TARGET_DIR/REVISION"
mkdir -p "$SCRIPT_DIR/build/dependency-sources"
tar --exclude=.git -czf "$SCRIPT_DIR/build/dependency-sources/thtk-$REVISION.tar.gz" -C "$TMP_ROOT" source

if ! "$THDAT" --help >/dev/null 2>&1; then
    if ! file "$THDAT" | grep -q 'ELF'; then
        echo "thdat was built, but the installed executable does not appear to be an ELF binary." >&2
        exit 1
    fi
fi

echo
echo "THTK installed successfully."
echo "  Revision: $REVISION"
echo "  Binary:   $THDAT"
echo
echo "The launcher will automatically use this bundled thdat before checking PATH."
echo
if command_exists file; then
    file "$THDAT"
fi
