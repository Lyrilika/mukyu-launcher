-----BEGIN PGP SIGNED MESSAGE-----
Hash: SHA512

Format: 3.0 (quilt)
Source: colord
Binary: libcolord-dev, libcolord2, colord, colord-sensor-argyll, colord-data, gir1.2-colord-1.0, libcolorhug-dev, libcolorhug2, gir1.2-colorhug-1.0, colord-tests
Architecture: linux-any all
Version: 1.4.7-1build2
Maintainer: Ubuntu Developers <ubuntu-devel-discuss@lists.ubuntu.com>
Uploaders: Christopher James Halse Rogers <raof@ubuntu.com>, Jeremy Bícha <jbicha@ubuntu.com>,
Homepage: https://www.freedesktop.org/software/colord/
Standards-Version: 4.6.2
Vcs-Browser: https://salsa.debian.org/debian/colord
Vcs-Git: https://salsa.debian.org/debian/colord.git
Testsuite: autopkgtest
Testsuite-Triggers: dbus, gnome-desktop-testing, gnome-session, gnome-settings-daemon, xauth, xvfb
Build-Depends: bash-completion, debhelper-compat (= 13), dh-sequence-gir, docbook-xsl-ns, gtk-doc-tools, libdbus-1-dev, libgirepository1.0-dev, libglib2.0-dev (>= 2.58), libgudev-1.0-dev, libgusb-dev (>= 0.2.7), libjson-glib-dev, liblcms2-dev, libpolkit-gobject-1-dev (>= 0.103), libsane-dev [linux-any], libsqlite3-dev, libsystemd-dev [linux-any], libudev-dev, meson (>= 0.52.0), pkgconf, polkitd, shared-mime-info <!nocheck>, systemd-dev [linux-any], valac (>= 0.20), xsltproc
Build-Depends-Indep: argyll [linux-any]
Package-List:
 colord deb graphics optional arch=linux-any
 colord-data deb graphics optional arch=all
 colord-sensor-argyll deb graphics optional arch=linux-any
 colord-tests deb graphics optional arch=linux-any
 gir1.2-colord-1.0 deb introspection optional arch=linux-any
 gir1.2-colorhug-1.0 deb introspection optional arch=linux-any
 libcolord-dev deb libdevel optional arch=linux-any
 libcolord2 deb libs optional arch=linux-any
 libcolorhug-dev deb libdevel optional arch=linux-any
 libcolorhug2 deb libs optional arch=linux-any
Checksums-Sha1:
 5f1819ecd0b1b38fa070a3f9419030fb23513033 1799168 colord_1.4.7.orig.tar.xz
 0c81212ac12d2597e2838443bebd619e2f325324 488 colord_1.4.7.orig.tar.xz.asc
 fe55c0102c441f227e334dcddc53c9d9a4362fdb 32572 colord_1.4.7-1build2.debian.tar.xz
Checksums-Sha256:
 de02d9910634ae159547585cec414e450f711c27235453b4f9b38a9f2361a653 1799168 colord_1.4.7.orig.tar.xz
 d5978308314fa371dc18da192db7182e3710d479d8dcc378f4ccb07b11459b60 488 colord_1.4.7.orig.tar.xz.asc
 207b1db79b231c22215c438e46c4140f934fa4ca28bd44ce9851ea20131857db 32572 colord_1.4.7-1build2.debian.tar.xz
Files:
 94bd795efa1931a34990345e4ac439a8 1799168 colord_1.4.7.orig.tar.xz
 51b468fdbf8b5dc0123e7ccb34e58ca8 488 colord_1.4.7.orig.tar.xz.asc
 33860f3c96fbda385284cb8fb5a1642c 32572 colord_1.4.7-1build2.debian.tar.xz
Original-Maintainer: Debian freedesktop.org maintainers <pkg-freedesktop-maintainers@lists.alioth.debian.org>

-----BEGIN PGP SIGNATURE-----

iQJOBAEBCgA4FiEErEg/aN5yj0PyIC/KVo0w8yGyEz0FAmYJESIaHHN0ZXZlLmxh
bmdhc2VrQHVidW50dS5jb20ACgkQVo0w8yGyEz12Wg//TonYixPaLDlV7m9cCZIw
CkUHxDf7Lgzj9ZTEBl00v2NXIYofH5ID5VOwMF+zpbSZ2VZdKnMXKtpPoHmmjWdn
hoxmm3nk7p2y24pmmdH3SAPLwyu8+DDM0nMaAGxGTtdi52KjpR7om9OPmraJtsWS
pCkfWuRkCNsLxbDXLowk2ZBRmOPQm0hJn8U+/aUAYqtNsOVXIqmz/ja/XcvejsHT
7795yxvEdGipZhpOf+HC0G27cEupBWIxIQjmBpeTccbjWG7B0eroLY4zPu2wBwmc
cAWNSPMDHXUNJXLQnvxB+Wpa/Nd4d+ZBYc3Sjd3Fr+Na+1N+WZbgilc5dFM9ASw9
IC/McgAGMNSMzxnfAhRnm1apVIa5UId6f5TylcfB7BWKKtB39OMYmQY75T3AnRrg
SSbXvCItnvaBbhe054r8JFLiY+/ZrCRipf6qWfm3PYvCKDAI/WyDbwz9O0ukiF4A
1KSHjgfTGl2/y/AqNJNDilUBn/BaZ/5pI8KqOeTLSUOMaBKClV2YaihxqAuZF4q0
n8MQQlLU9ZFv6N7YVJl5FfuTbMripMKeaalwcCvkkE2SgahkR2b7XipLAcGrBLz/
txmo8ozEbbZZWgZ+3CtZPbEzDj4XbkbW7VtdEQxW737TSh6QS/HJGdZFVrvxF9eu
pW8AlbOgrRRUoXezHFR8K2Y=
=WEXF
-----END PGP SIGNATURE-----
