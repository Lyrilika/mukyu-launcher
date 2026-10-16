-----BEGIN PGP SIGNED MESSAGE-----
Hash: SHA512

Format: 3.0 (quilt)
Source: libsoup3
Binary: libsoup-3.0-dev, libsoup-3.0-0, libsoup-3.0-common, libsoup-3.0-doc, gir1.2-soup-3.0, libsoup-3.0-tests
Architecture: any all
Version: 3.4.4-5ubuntu0.9
Maintainer: Ubuntu Developers <ubuntu-devel-discuss@lists.ubuntu.com>
Uploaders: Iain Lane <laney@debian.org>, Jeremy Bícha <jbicha@ubuntu.com>, Michael Biebl <biebl@debian.org>, Sebastien Bacher <seb128@debian.org>
Homepage: https://wiki.gnome.org/Projects/libsoup
Standards-Version: 4.6.2
Vcs-Browser: https://salsa.debian.org/gnome-team/libsoup3
Vcs-Git: https://salsa.debian.org/gnome-team/libsoup3.git
Testsuite: autopkgtest
Testsuite-Triggers: build-essential, dbus, gnome-desktop-testing, winbind, xauth, xvfb
Build-Depends: apache2 <!nocheck> <!noinsttest>, curl <!nocheck> <!noinsttest>, debhelper-compat (= 13), dh-sequence-gir, dh-sequence-gnome, gir1.2-gio-2.0-dev, glib-networking, gi-docgen, libapache2-mod-php (<< 2:9) [!i386] <!nocheck> <!noinsttest>, libbrotli-dev, libgirepository1.0-dev, libglib2.0-dev (>= 2.69), libgnutls28-dev <!nocheck>, libkrb5-dev, libnghttp2-dev, libnss-myhostname [linux-any] <!nocheck>, libpsl-dev, libsqlite3-dev, libsysprof-capture-4-dev [linux-any], meson, php (<< 2:9) [!i386] <!nocheck> <!noinsttest>, python3-quart <!nocheck>, valac, winbind
Build-Depends-Indep: libglib2.0-doc
Package-List:
 gir1.2-soup-3.0 deb introspection optional arch=any
 libsoup-3.0-0 deb libs optional arch=any
 libsoup-3.0-common deb devel optional arch=all
 libsoup-3.0-dev deb libdevel optional arch=any
 libsoup-3.0-doc deb doc optional arch=all
 libsoup-3.0-tests deb misc optional arch=any profile=!noinsttest
Checksums-Sha1:
 a9c0167761df09cc9167ef967b0fef65228bf914 1536268 libsoup3_3.4.4.orig.tar.xz
 79337ab3c14429dff4076ff286b5712303c2874e 68128 libsoup3_3.4.4-5ubuntu0.9.debian.tar.xz
Checksums-Sha256:
 291c67725f36ed90ea43efff25064b69c5a2d1981488477c05c481a3b4b0c5aa 1536268 libsoup3_3.4.4.orig.tar.xz
 4899814656cac84e1e024d6b81f285f1416e0d2b81e503ee49017acf62426124 68128 libsoup3_3.4.4-5ubuntu0.9.debian.tar.xz
Files:
 a63ea04a9686e9e4470b127ffe1eb96b 1536268 libsoup3_3.4.4.orig.tar.xz
 c7b971c3421e58995a5e89c3d6099be2 68128 libsoup3_3.4.4-5ubuntu0.9.debian.tar.xz
Original-Maintainer: Debian GNOME Maintainers <pkg-gnome-maintainers@lists.alioth.debian.org>

-----BEGIN PGP SIGNATURE-----

iQJPBAEBCgA5FiEEuEg4xBTSeUWY0Nx77tH0LvjAvecFAmrAJdwbHGt5bGUua2Vy
bmlja0BjYW5vbmljYWwuY29tAAoJEO7R9C74wL3ni1kP/0TT5Zc449QmC4LkXnAi
aDkgKx5TFyYlmezMeu7JTMZmqCsY/aRdMct3W7FG5tfrnUbSLPtSOI0JtShEj+v2
Hh31iubf/weM3hXC6bGkPvHUJLlvQqH+DWpLUyrhxDjSriKeCK3q1c+neQqM0l7e
0IdZcy/I5/92c/jCldX1OHwth8MO49zJzvlEWi1JCoZhqZ3ekVzT8rBfwKu/jxeh
KOpMkvHI+/uG1wQXFGgDxgGUEZAuU81RRiiWkWVe2Vck44N297AzFA2pw9674KL9
LdVX5cbKIVEfbYgfTnOCqiN24iM+tHg2VOagrhKJY3zLVlTsNYfJ2Cs4Qz5ONZ1n
fTNAtbnv4XDeHOy8Xlw91RLSP6QCoeRXg3DooRuqCBedPariAcEncAckG3FgAAw3
2b2bmSTE+4Ksigms/EUlrQaf6Ip848nMD81LdNMWSY/PqM/2Aftz2vfWBbMp/2Zx
ULZZMhhnw6W0JJsJzZ/qBAyJA/+Gk1/SYAM+7ytHciSX5Lt748L+/C9o6R8GcNIl
3Qy17Gs0ceWb3flEpq4gNqwnvlSrZjUFoN2aTWkieugECy6IoZH5fmmcHfRjVh18
bUpHlqosukiP5y3ukwmyuAWeh2k0m8/FuqWK39oXIxsXhzJHN+j8pBwlsK14pUII
wL3rXPrqpUEAccpxQUk6cokw
=kgOp
-----END PGP SIGNATURE-----
