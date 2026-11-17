Source archives for third-party programs shipped inside the release builds:

- umu-launcher (GPL-3.0)     tools/umu/umu-run (Linux AppImage)
- type2-runtime (MIT)         packaging/appimage/runtime-x86_64
                              packaging/appimage/runtime-aarch64
- libfuse (LGPL-2.1)          statically linked into the AppImage runtime

thtk (thdat), 98fmplayer and libx86emu are built from the upstream revisions
recorded in tools/thtk/REVISION and tools/pc98/BUILD_INFO.txt. PDFium comes
from https://github.com/bblanchon/pdfium-binaries (BSD-3-Clause / Apache-2.0);
see tools/licenses/THIRD_PARTY_NOTICES.txt.
