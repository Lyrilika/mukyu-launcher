Dependency sources

sources/ contains unmodified source archives and distribution packaging files.
manifest.json pins the runtime package versions and records SHA-256 checksums
for their binaries and corresponding source files. Use the same repository tag
as the application release. GitHub's automatic source downloads include this
folder; the AppImage and Windows installer exclude it.

The source archives retain their original license texts, copyright notices and
comments. The launcher license does not replace upstream licenses. Sources are
collected conservatively from distribution license inventories; the presence of
an archive does not mean its redistribution is required under every licensing
option. GCC runtime libraries use the GCC Runtime Library Exception. Build-only
compilers and their source trees are not included in this snapshot.

Debian .dsc files identify upstream archives and Debian/Ubuntu patches. MSYS2
.src.tar archives contain upstream source, patches and PKGBUILD recipes.
The common/ folder provides UMU, python-xlib and AppImage runtime/libfuse sources.
The application's adapters and helper build recipes are in tools/pc98/src,
scripts/ and packaging/. The helper dependencies use permissive licenses and
their revisions and license notices remain in those existing files.

Verify the source snapshot:
  python packaging/licenses/repository_sources.py verify --platform linux
  python packaging/licenses/repository_sources.py verify --platform windows

Restore the archives to a separate working directory:
  python packaging/licenses/repository_sources.py restore --output build/sources

Files larger than 95 MiB are split into numbered .partNNN files to fit GitHub's
regular-file size limit. The restore command joins these parts automatically.
Never strip comments or license headers from upstream source archives.

Runtime updates must update the package lock and corresponding sources together.
Do not change a package version or bypass source verification in a release build.
