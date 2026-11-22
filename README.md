<p align="center">
  <img src="assets/icons/hicolor/scalable/apps/mukyulauncher.png" alt="Mukyu Launcher icon" width="128" height="128">
</p>

<h1 align="center">Mukyu Launcher</h1>

<p align="center">
  <a href="../../releases/latest"><img alt="Latest release" src="https://badgen.net/github/release/Lyrilika/mukyu-launcher/latest?label=release&amp;labelColor=30262e&amp;color=963f89"></a>
  <img alt="Platforms" src="https://badgen.net/badge/platform/Linux%20%7C%20Windows/594b61?labelColor=30262e">
</p>

<p align="center">
  <b>A multi-purpose Touhou launcher made for Linux. (with windows 10/11 support)</b>
</p>

Mukyu Launcher brings your Touhou collection and related media into one app: launch your games, listen to [Gensokyo Radio](https://gensokyoradio.net/) or the music from your own game files, and download and read official Touhou print works.


## Screenshots:

<table width="100%">
  <tr>
    <td width="50%" align="center" valign="top">
      <a href=".github/screenshots/game-library.jpg"><img src=".github/screenshots/game-library.jpg" alt="Game library showing Touhou mainline games and spin-offs" width="100%"></a>
      <br><b>Game library</b>
    </td>
    <td width="50%" align="center" valign="top">
      <a href=".github/screenshots/desktop-media.jpg"><img src=".github/screenshots/desktop-media.jpg" alt="Hyprland desktop media widget displaying the current game soundtrack and playback controls" width="100%"></a>
      <br><b>Media control widget support</b>
    </td>
  </tr>
  <tr>
    <td width="50%" align="center" valign="top">
      <a href=".github/screenshots/game-music.jpg"><img src=".github/screenshots/game-music.jpg" alt="Game BGM player with album art, track list and English or Japanese titles" width="100%"></a>
      <br><b>Game soundtracks</b>
    </td>
    <td width="50%" align="center" valign="top">
      <a href=".github/screenshots/gensokyo-radio.jpg"><img src=".github/screenshots/gensokyo-radio.jpg" alt="Gensokyo Radio player showing live song information and album art" width="100%"></a>
      <br><b>Gensokyo Radio</b>
    </td>
  </tr>
  <tr>
    <td width="50%" align="center" valign="top">
      <a href=".github/screenshots/printworks-library.jpg"><img src=".github/screenshots/printworks-library.jpg" alt="Print Works library with book covers, descriptions and reading controls" width="100%"></a>
      <br><b>Print Works library</b>
    </td>
    <td width="50%" align="center" valign="top">
      <a href=".github/screenshots/printworks-reader.jpg"><img src=".github/screenshots/printworks-reader.jpg" alt="Built-in fullscreen reader displaying Eastern and Little Nature Deity" width="100%"></a>
      <br><b>Built-in reader</b>
    </td>
  </tr>
</table>

## Features

- **Game library** — Launch every mainline and spin-off game from one library. Wine, GE-Proton and DOSBox-X are handled for you, with per-game launch options and playtime tracking.
- **Music player** — Stream [Gensokyo Radio](https://gensokyoradio.net/) with live song info and album art, or play the soundtrack straight from your own game files, PC-98 included. Favourites, shuffle and repeat.
- **Print Works** — Download official Touhou print works and read them in the built-in PDF reader.
- **Theming** — Dark/Light with a custom accent colour.

## Notices

- Touhou Project is created by ZUN / Team Shanghai Alice. All related names and artwork belong to their respective owners.
- Mukyu Launcher is a community-made project. It is **not affiliated with, endorsed by, or sponsored by ZUN or Team Shanghai Alice**
- Mukyu Launcher does **not** distribute games or music files. You need your own copies of the games.
- Gensokyo Radio is an external service. Its availability and content are controlled by its operators.
- [AI disclosure](DISCLOSURE.md)

## Installation

### Download (Recommended)

Download the build for your system from the [latest release](../../releases/latest).

### Build from source

**Linux:** needs Rust 1.92+ and the ALSA, fontconfig, xkbcommon and Wayland headers
(Debian/Ubuntu: `libasound2-dev libfontconfig1-dev libxkbcommon-dev libwayland-dev`,
Alpine: `alsa-lib-dev fontconfig-dev libxkbcommon-dev wayland-dev`).

```bash
./scripts/install_thtk.sh
./scripts/install_pc98_music.sh
./scripts/install_umu.sh   # only needed for Proton (64-bit glibc)
```

Get PDFium for your system:

| System | Command |
|---|---|
| x86_64 | `./scripts/fetch_pdfium.sh linux lib` |
| aarch64 | `./scripts/fetch_pdfium.sh linux lib arm64` |
| i686 | `./scripts/fetch_pdfium.sh linux lib x86` |
| armhf | `./scripts/fetch_pdfium.sh linux lib arm` |
| x86_64 musl | `./scripts/fetch_pdfium.sh linux-musl lib` |
| aarch64 musl | `./scripts/fetch_pdfium.sh linux-musl lib arm64` |
| i686 musl | `./scripts/fetch_pdfium.sh linux-musl lib x86` |

Then run it with `cargo run --release`, or build an AppImage with
`bash packaging/appimage/build_appimage.sh`.

**Windows:**

```powershell
packaging/windows/build_windows_tools.ps1
cargo build --release
packaging/windows/stage.ps1 -Tools .
```

Before staging, get PDFium: `bash scripts/fetch_pdfium.sh windows build/pdfium`
(add `arm64` for ARM or `x86` for 32-bit). Then compile `packaging/windows/installer.iss`
with Inno Setup.

## License and third-party notices

Mukyu Launcher's original code is licensed under the **GNU Affero General Public
License, version 3 or any later version (AGPL-3.0-or-later)**.
Third-party code, libraries and artwork retain their own copyrights and licenses.

See [third-party notices](tools/licenses/THIRD_PARTY_NOTICES.txt) for credits,
license locations and upstream projects.

## Acknowledgements

Mukyu Launcher builds on the work of open-source projects and services, such as:

- [Slint](https://slint.dev)
- [Symphonia](https://github.com/pdeljanov/Symphonia)
- [PDFium](https://pdfium.googlesource.com/pdfium/)
- [umu-launcher](https://github.com/Open-Wine-Components/umu-launcher)
- [thtk](https://github.com/thpatch/thtk)
- [98fmplayer](https://github.com/myon98/98fmplayer)
- [libx86emu](https://github.com/wfeldt/libx86emu)
- [135tk](https://github.com/brliron/135tk)
- [foo_thbgm](https://github.com/nyfair/foo_thbgm)
- [DOSBox-X](https://dosbox-x.com/)

## Issues and discussions

- Use [Issues](https://github.com/Lyrilika/mukyu-launcher/issues) to report bugs. Include your operating system, launcher version, and steps to reproduce the problem when you can. For a game-specific issue, include the Touhou title and runner you used.
- Use [Discussions](https://github.com/Lyrilika/mukyu-launcher/discussions) for questions, ideas, and feedback. A discussion is a good place to start if you are planning a larger change.

## Contributions

If you'd like to contribute, see the [contribution guide](CONTRIBUTING.md)
