-----BEGIN PGP SIGNED MESSAGE-----
Hash: SHA512

Format: 3.0 (quilt)
Source: gobject-introspection
Binary: libgirepository-1.0-1, libgirepository1.0-dev, libgirepository-1.0-dev, libgirepository1.0-doc, gobject-introspection, gobject-introspection-bin, gir1.2-girepository-2.0, gir1.2-girepository-2.0-dev, gir1.2-freedesktop, gir1.2-freedesktop-dev
Architecture: any all
Version: 1.80.1-1
Maintainer: Debian GNOME Maintainers <pkg-gnome-maintainers@lists.alioth.debian.org>
Uploaders: Iain Lane <laney@debian.org>, Jeremy Bícha <jbicha@ubuntu.com>, Laurent Bigonville <bigon@debian.org>, Marco Trevisan (Treviño) <marco@ubuntu.com>, Matthias Klumpp <mak@debian.org>, Michael Biebl <biebl@debian.org>, Tim Lunn <tim@feathertop.org>, Simon McVittie <smcv@debian.org>,
Homepage: https://wiki.gnome.org/GObjectIntrospection
Standards-Version: 4.6.2
Vcs-Browser: https://salsa.debian.org/gnome-team/gobject-introspection
Vcs-Git: https://salsa.debian.org/gnome-team/gobject-introspection.git
Testsuite: autopkgtest
Testsuite-Triggers: build-essential, file, gir1.2-gtk-3.0, libcairo2-dev, pkgconf
Build-Depends: bison, debhelper-compat (= 13), dh-sequence-python3, flex, gir1.2-glib-2.0-dev (>= 2.80.0) <!nogir>, gobject-introspection (>= 1.78.1-17~) <cross !nogir>, libcairo2-dev, libelf-dev, libelf-dev:native, libffi-dev (>= 3.4), libglib2.0-dev (>= 2.80.0), libpython3-dev, libtool, meson (>= 0.60.0), pkgconf, python3-debian:native, python3-dev:any, python3-docutils <!nodoc>, python3-mako:native, python3-markdown:native, python3-setuptools, python3:native, qemu-user <cross>
Build-Depends-Indep: gtk-doc-tools, libglib2.0-doc (>= 2.80.0)
Package-List:
 gir1.2-freedesktop deb introspection optional arch=any profile=!nogir
 gir1.2-freedesktop-dev deb libdevel optional arch=any profile=!nogir
 gir1.2-girepository-2.0 deb introspection optional arch=any profile=!nogir
 gir1.2-girepository-2.0-dev deb libdevel optional arch=any profile=!nogir
 gobject-introspection deb devel optional arch=any
 gobject-introspection-bin deb devel optional arch=any
 libgirepository-1.0-1 deb libs optional arch=any
 libgirepository-1.0-dev deb libdevel optional arch=any
 libgirepository1.0-dev deb libdevel optional arch=any profile=!nogir
 libgirepository1.0-doc deb doc optional arch=all
Checksums-Sha1:
 a86f8979d6e2cba0ff9122a6f699025b2d81bab6 5475296 gobject-introspection_1.80.1.orig-glib.tar.xz
 175e675d09eae3a997e4cd4cfb19228e1cbd508c 1040228 gobject-introspection_1.80.1.orig.tar.xz
 140b4301ca6a46dd1ad03fd3ff41838a63b720ae 56948 gobject-introspection_1.80.1-1.debian.tar.xz
Checksums-Sha256:
 b3764dd6e29b664085921dd4dd6ba2430fc19760ab6857ecfa3ebd4e8c1d114c 5475296 gobject-introspection_1.80.1.orig-glib.tar.xz
 a1df7c424e15bda1ab639c00e9051b9adf5cea1a9e512f8a603b53cd199bc6d8 1040228 gobject-introspection_1.80.1.orig.tar.xz
 ca74639e51c61b6790192a553825a5392018f2b1b25cad571ac71a977775ec0c 56948 gobject-introspection_1.80.1-1.debian.tar.xz
Files:
 9df2169686c0b7f891067017002ad111 5475296 gobject-introspection_1.80.1.orig-glib.tar.xz
 ef1496a7a7abfcd31d25b3459ea86ebb 1040228 gobject-introspection_1.80.1.orig.tar.xz
 c22915555d921ee31ad9c0cdf3e6ddf6 56948 gobject-introspection_1.80.1-1.debian.tar.xz

-----BEGIN PGP SIGNATURE-----

iQIzBAEBCgAdFiEETQvhLw5HdtiqzpaW5mx3Wuv+bH0FAmYKxLgACgkQ5mx3Wuv+
bH1mJxAA4onPsOtOTMrDX+Jh9Htv2atkIaTwxKQZEPv6yBROd8HAzYBrC4Ki2E7f
jCm+VeCD4xw+nfypDP0ZpNr3groSOmAZplzMAP7hwWJTZRZ3vPDveY1+YIcwFGjV
IiPTzMSD0qBTcQrDAUnkHVHx2kk0CdKdBtLXnekaRQi3T2rHOlw1iHC1HfTF41k4
DNb6G45TB67+9fxcsgig6C4aGEG3brk3a5ADbbvr/L8i8PLvYtVOwwuw/CuLkIXk
YPz1/1hADUAOsHR8JPyKBi4KAxi09g6IwRkyM6oYGwOtMWRJHqny5TXn0QfBqatI
rt531vlouxhsMnVMBFgJjS92ttgAKKFrXW0OnCb/cHODcp7hTBpIzK7r3HA4ncLC
BkKMjj0LRrnMCteFPFNsTBYfUf8yeO0mUNTOYirPcLf40GK2t8bzwm3WYr6cMZkg
5q3eQ6aFYs7NGeDs0HnXxPS9fNE9I4vNga/bVIkfJOJEcK/oyZ+/bE170UJpNvkq
OjoB895z9mITsbzqnuZhRp9R0QQX0+nAU1URvIfWaWBN5QyAhjKxE6U+2Ie3wq/3
R9HF5JRDkgykbO2naOSB3utqjTpsuiVD65oKFH4w4KntvmA1V3K7dnjYU4P0LC5Q
93iezf8Az31h3uO9qpGrm9DCd6OIyH/x6hkqCmFGvR7oj5+S6XI=
=df7w
-----END PGP SIGNATURE-----
