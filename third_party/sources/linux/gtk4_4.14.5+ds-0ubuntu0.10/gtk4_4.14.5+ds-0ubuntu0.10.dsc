-----BEGIN PGP SIGNED MESSAGE-----
Hash: SHA512

Format: 3.0 (quilt)
Source: gtk4
Binary: libgtk-4-1, libgtk-4-1-udeb, libgtk-4-common, libgtk-4-bin, libgtk-4-dev, libgtk-4-doc, libgtk-4-media-gstreamer, gtk-4-examples, gtk-4-tests, gir1.2-gtk-4.0
Architecture: any all
Version: 4.14.5+ds-0ubuntu0.10
Maintainer: Ubuntu Developers <ubuntu-devel-discuss@lists.ubuntu.com>
Uploaders: Simon McVittie <smcv@debian.org>, Amin Bandali <bandali@ubuntu.com>, Jeremy Bícha <jbicha@ubuntu.com>
Homepage: https://www.gtk.org/
Standards-Version: 4.6.2
Vcs-Browser: https://salsa.debian.org/gnome-team/gtk4
Vcs-Git: https://salsa.debian.org/gnome-team/gtk4.git
Testsuite: autopkgtest
Testsuite-Triggers: build-essential, dbus-daemon, fonts-noto-core, gnome-desktop-testing, libgl1, libgl1-mesa-dri, locales, locales-all, python3-gi, weston, xauth, xvfb
Build-Depends: adwaita-icon-theme <!nocheck>, at-spi2-core <!nocheck>, dbus-daemon <!nocheck>, debhelper-compat (= 13), dh-exec, dh-sequence-gir, dh-sequence-gnome, fonts-cantarell <!nocheck>, fonts-noto-core <!nocheck>, gir1.2-cairo-1.0-dev, gir1.2-gio-2.0-dev, gir1.2-gdkpixbuf-2.0-dev, gir1.2-graphene-1.0-dev, gir1.2-pango-1.0-dev, gir1.2-pangocairo-1.0-dev, gir1.2-xlib-2.0-dev, glslc, gobject-introspection (>= 1.76.0), gobject-introspection (>= 1.78.1-9~) <cross>, gsettings-desktop-schemas <!nocheck>, iso-codes <!nocheck>, libcairo2-dev, libcolord-dev <!pkg.gtk4.nocolord>, libcloudproviders-dev (>= 0.3.1), libcups2-dev, libegl1-mesa-dev [linux-any], libepoxy-dev, libfontconfig-dev, libfribidi-dev, libgdk-pixbuf-2.0-dev, libglib2.0-dev (>= 2.76.0), libgraphene-1.0-dev, libgstreamer1.0-dev, libgstreamer-plugins-base1.0-dev, libharfbuzz-dev, libjpeg-dev, libjson-glib-dev:native, libpango1.0-dev (>= 1.52.0), libpng-dev, libpolkit-gobject-1-dev [linux-any], librsvg2-common [amd64 arm64 armel armhf i386 loong64 mips64el ppc64el s390x powerpc ppc64 riscv64 sparc64 x32] <!nocheck>, librsvg2-dev (>= 2.52.0) [amd64 arm64 armel armhf i386 loong64 mips64el ppc64el s390x powerpc ppc64 riscv64 sparc64 x32], libsysprof-capture-4-dev (>= 3.40.1) [amd64 arm64 armel armhf i386 mips64el ppc64el riscv64 s390x powerpc ppc64], libtiff-dev, libvulkan-dev [linux-any], libwayland-dev (>= 1.21.0) [linux-any], libx11-dev, libxcomposite-dev, libxcursor-dev, libxdamage-dev, libxext-dev, libxfixes-dev, libxi-dev, libxinerama-dev, libxkbcommon-dev, libxkbfile-dev, libxml2-utils, libxrandr-dev, locales <!nocheck> | locales-all <!nocheck>, meson (>= 0.63), pkgconf, pkgconf:native, python3-docutils <!nodoc>, python3-gi (>= 3.40) <!nocheck>, sassc, wayland-protocols (>= 1.32) [linux-any], weston [linux-any] <!nocheck>, xauth <!nocheck>, xvfb <!nocheck>
Build-Depends-Indep: gi-docgen <!nodoc>, libcairo2-doc <!nodoc>, libglib2.0-doc <!nodoc>, libpango1.0-doc <!nodoc>
Package-List:
 gir1.2-gtk-4.0 deb introspection optional arch=any
 gtk-4-examples deb x11 optional arch=any profile=!noinsttest
 gtk-4-tests deb x11 optional arch=any profile=!noinsttest
 libgtk-4-1 deb libs optional arch=any
 libgtk-4-1-udeb udeb debian-installer optional arch=any profile=!noudeb
 libgtk-4-bin deb misc optional arch=any
 libgtk-4-common deb misc optional arch=all
 libgtk-4-dev deb libdevel optional arch=any
 libgtk-4-doc deb doc optional arch=all profile=!nodoc
 libgtk-4-media-gstreamer deb x11 optional arch=any
Checksums-Sha1:
 bd6b4b954465ad810c26073cf55d5ba3ad3148c1 14173448 gtk4_4.14.5+ds.orig.tar.xz
 2890675fea9eba55da4dcc32d7f751c3aa382f73 3805968 gtk4_4.14.5+ds-0ubuntu0.10.debian.tar.xz
Checksums-Sha256:
 bd52b294cd18784339b105e2f25d2569e3db94411c64b9b141b23fe39118a0e5 14173448 gtk4_4.14.5+ds.orig.tar.xz
 17692a86b96fa9bc930f744694c02a43f7a048abdfb1f9864fe2b9925f649d00 3805968 gtk4_4.14.5+ds-0ubuntu0.10.debian.tar.xz
Files:
 242f0bfe43f6161f79ce5d4111efb96d 14173448 gtk4_4.14.5+ds.orig.tar.xz
 a2524344a141dc90b1cd1e20ff888968 3805968 gtk4_4.14.5+ds-0ubuntu0.10.debian.tar.xz
Original-Maintainer: Debian GNOME Maintainers <pkg-gnome-maintainers@lists.alioth.debian.org>

-----BEGIN PGP SIGNATURE-----

iHUEARYKAB0WIQS8J/j+939yB6e6CL4NAkbzgiDtpgUCabqoHQAKCRANAkbzgiDt
puqWAP98pdkbNFAGfMcrQr3IIVBjxLuSe2OmD/2WYmIEkxfZVAEA5/NxrXIKYmyL
UHxF7pawTn82BfwEPUdryrlCdJ2c6gc=
=VjLj
-----END PGP SIGNATURE-----
