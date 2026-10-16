-----BEGIN PGP SIGNED MESSAGE-----
Hash: SHA512

Format: 3.0 (quilt)
Source: gtk+3.0
Binary: libgtk-3-0t64, libgtk-3-0-udeb, libgtk-3-common, libgtk-3-bin, libgtk-3-dev, libgtk-3-doc, gtk-3-examples, gir1.2-gtk-3.0, gtk-update-icon-cache, libgail-3-0t64, libgail-3-dev, libgail-3-doc
Architecture: any all
Version: 3.24.41-4ubuntu1.3
Maintainer: Ubuntu Developers <ubuntu-devel-discuss@lists.ubuntu.com>
Uploaders: Simon McVittie <smcv@debian.org>, Dmitry Shachnev <mitya57@debian.org>, Jeremy Bícha <jbicha@ubuntu.com>
Homepage: https://www.gtk.org/
Standards-Version: 4.6.2
Vcs-Browser: https://salsa.debian.org/gnome-team/gtk3/tree/ubuntu/noble
Vcs-Git: https://salsa.debian.org/gnome-team/gtk3.git -b ubuntu/noble
Testsuite: autopkgtest
Testsuite-Triggers: adwaita-icon-theme, at-spi2-core, build-essential, dbus-daemon, dpkg-dev, dpkg-repack, gnome-desktop-testing, librsvg2-common, python3-gi, xauth, xvfb
Build-Depends: adwaita-icon-theme (>= 45.0-4~) <!nocheck>, at-spi2-core <!nocheck>, dbus-daemon <!nocheck>, debhelper-compat (= 13), dh-sequence-gir, dh-sequence-translations, docbook-xml <!nodoc>, docbook-xsl <!nodoc>, dpkg-dev (>= 1.22.5), fonts-cantarell <!nocheck>, fonts-dejavu-core <!nocheck>, gir1.2-atk-1.0-dev <pkg.gobject-introspection.todo>, gir1.2-cairo-1.0-dev | libgirepository1.0-dev, gir1.2-gdkpixbuf-2.0-dev, gir1.2-gio-2.0-dev | libgirepository1.0-dev, gir1.2-pango-1.0-dev, gir1.2-xlib-2.0-dev | libgirepository1.0-dev, gnome-pkg-tools (>= 0.11), gobject-introspection (>= 1.78.1-9~) | libgirepository1.0-dev (>= 1.41.3), gobject-introspection (>= 1.78.1-9~) <cross>, gsettings-desktop-schemas <!nocheck>, libatk-bridge2.0-dev (>= 2.15.1), libatk1.0-dev (>= 2.35.1), libcairo2-dev (>= 1.14.0), libcloudproviders-dev (>= 0.3.2), libcolord-dev (>= 0.1.9), libcups2-dev (>= 1.7), libegl1-mesa-dev [linux-any], libepoxy-dev (>= 1.4), libfontconfig-dev, libfreetype-dev (>= 2.7.1), libfribidi-dev (>= 0.19.7), libgdk-pixbuf-2.0-dev (>= 2.40.0), libglib2.0-dev (>= 2.57.2), libharfbuzz-dev (>= 2.2.0), libjson-glib-dev:native, libpango1.0-dev (>= 1.44.0), librsvg2-common [amd64 arm64 armel armhf i386 mips64el mipsel ppc64el s390x powerpc ppc64 riscv64 sparc64] <!nocheck>, libwayland-dev (>= 1.14.91) [linux-any], libx11-dev, libxcomposite-dev, libxcursor-dev, libxdamage-dev, libxext-dev, libxfixes-dev, libxi-dev, libxinerama-dev, libxkbcommon-dev (>= 0.2.0), libxkbfile-dev, libxml2-utils, libxrandr-dev (>= 2:1.5.0), meson (>= 0.60.0), ninja-build, pkgconf, pkgconf:native, sassc, wayland-protocols (>= 1.17) [linux-any], xauth <!nocheck>, xsltproc <!nodoc>, xvfb <!nocheck>
Build-Depends-Indep: gtk-doc-tools (>= 1.20) <!nodoc>, libatk1.0-doc <!nodoc>, libcairo2-doc <!nodoc>, libglib2.0-doc <!nodoc>, libpango1.0-doc <!nodoc>
Package-List:
 gir1.2-gtk-3.0 deb introspection optional arch=any
 gtk-3-examples deb x11 optional arch=any
 gtk-update-icon-cache deb misc optional arch=any
 libgail-3-0t64 deb libs optional arch=any
 libgail-3-dev deb libdevel optional arch=any
 libgail-3-doc deb doc optional arch=all profile=!nodoc
 libgtk-3-0-udeb udeb debian-installer optional arch=any profile=!noudeb
 libgtk-3-0t64 deb libs optional arch=any
 libgtk-3-bin deb misc optional arch=any
 libgtk-3-common deb misc optional arch=all
 libgtk-3-dev deb libdevel optional arch=any
 libgtk-3-doc deb doc optional arch=all profile=!nodoc
Checksums-Sha1:
 f7736ddc3c3ec27699d2b3f8cbbbbfe2886fb61c 13188312 gtk+3.0_3.24.41.orig.tar.xz
 a629b3662155a688d41327d4b7333847e681aff8 3666360 gtk+3.0_3.24.41-4ubuntu1.3.debian.tar.xz
Checksums-Sha256:
 47da61487af3087a94bc49296fd025ca0bc02f96ef06c556e7c8988bd651b6fa 13188312 gtk+3.0_3.24.41.orig.tar.xz
 1a82c70d722296f15af0a00a737a0c552580c6bf3f527f9ef7e66f192fe1831c 3666360 gtk+3.0_3.24.41-4ubuntu1.3.debian.tar.xz
Files:
 2321e8158feac093b6ed82aac66dbbfd 13188312 gtk+3.0_3.24.41.orig.tar.xz
 1eea46b98b436da798fa51b211791026 3666360 gtk+3.0_3.24.41-4ubuntu1.3.debian.tar.xz
Debian-Vcs-Browser: https://salsa.debian.org/gnome-team/gtk3
Debian-Vcs-Git: https://salsa.debian.org/gnome-team/gtk3.git
Original-Maintainer: Debian GNOME Maintainers <pkg-gnome-maintainers@lists.alioth.debian.org>

-----BEGIN PGP SIGNATURE-----

iQIzBAEBCgAdFiEETQvhLw5HdtiqzpaW5mx3Wuv+bH0FAmeX5VgACgkQ5mx3Wuv+
bH1bQhAA1UHxp760bMwPtmHG7ZcbxZVNeuX0bO7dctW3L2SQDiizD09aYqByQO4H
i3RPWuv78SvEGmOEtQMtY2jca3v0240RDzj7YZAa5tMDb7BKvMeSUcMYpQ5MlrZC
JMG0h0HqpOW/tuTl4FdDvlrYvmksxq/5jZ6Xqi5+R7/42SdmWJBbh8jxpHcreB9H
LftBNEOIiXEuAJQUd0F95lJzWf0PZyEj/B4Rjoif6WippHdMkInXHXREnaF0/psg
OSv5K+5gtkRzvU7SLbbxO0/DpOXzHpMs1+WueSTfWlz3msnsbAEYbYqgXwDR8FFi
K5q3ZKjiAQ8gvQJTYHygog1cicpqevtun/rih6TnboIGUz5KHSc65ASCBrb+nujo
HD1NwWB9/PB/O5f+41wCec9XXPBXHmGgOaienWJZ9Eku/X31ijflLvpTe9QvBMTA
rsszYNq8QhrB2cb7FxlOXrsGHI2GmUVdr5VZZjEJZ/lJnpUkmj+fHyvYCApGukCz
iP+csBs7jk00YsxeamBz0rzv9QSPvlNcXRQScV7dN6Vt1xOswphUEpH5WAosuG3m
B9qnQZZYSdxoo+Iu/eMsajBdCaqnotwmCjJFGO///1KkDghwZg6mVFTnNZdzBL4f
do8Hl7m6anygRwICApvT4/9EKOWeYsPIfpovNtbxaaRYx9b5U7w=
=GO42
-----END PGP SIGNATURE-----
