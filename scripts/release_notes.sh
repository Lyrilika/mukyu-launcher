#!/usr/bin/env bash
set -euo pipefail
TAG="${1:?release tag, e.g. v1.2.6}"
REPO="${2:-Lyrilika/mukyu-launcher}"
BASE="https://github.com/$REPO/releases/download/$TAG"

appimage() {
    printf '[AppImage](%s/Mukyu_Launcher-%s.AppImage) ([zsync](%s/Mukyu_Launcher-%s.AppImage.zsync))' "$BASE" "$1" "$BASE" "$1"
}

setup() {
    printf '[Setup](%s/%s)' "$BASE" "$1"
}

cat <<EOF
## Packages

### Targets

Each build is made for a specific architecture.

- **x86_64 (amd64):** For 64-bit Intel and AMD CPUs.
- **aarch64 (arm64):** For devices that use the armv8-a instruction set; e.g. Snapdragon X laptops, Raspberry Pi 4/5 with a 64-bit OS, Apple Silicon Macs running Asahi Linux.
- **i686 (x86):** For 32-bit Intel and AMD CPUs, or 64-bit PCs running a 32-bit OS.
- **armhf:** For 32-bit ARM devices (armv7); e.g. Raspberry Pi running a 32-bit OS.

### glibc or musl

Linux builds come in two flavors, depending on your distro's C library.

- **glibc:** For almost every distro; e.g. Ubuntu, Debian, Fedora, Arch, Mint, openSUSE, SteamOS.
- **musl:** For musl-based distros; e.g. Alpine, Void Linux (musl), Chimera Linux.

### Linux

.zsync files are optional, Mukyu Launcher can update itself.

| Build Type | glibc | musl | Notes |
|---|---|---|---|
| x86_64 | $(appimage x86_64) | $(appimage x86_64-musl) | |
| aarch64 | $(appimage aarch64) | $(appimage aarch64-musl) | |
| i686 | $(appimage i686) | $(appimage i686-musl) | musl only: No runners provided, need manual set up |
| armhf | $(appimage armhf) | | No runners provided, need manual set up |

### Windows

Windows packages are installers.

| Build Type | Installer | Notes |
|---|---|---|
| x64 | $(setup Mukyu_Launcher_Setup.exe) | Windows 10 version 1607 or newer |
| arm64 | $(setup Mukyu_Launcher_Setup_arm64.exe) | Windows 10 version 1709 or newer |
| x86 | $(setup Mukyu_Launcher_Setup_x86.exe) | 32-bit Windows 10 version 1607 or newer |
EOF
