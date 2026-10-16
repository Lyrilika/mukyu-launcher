-----BEGIN PGP SIGNED MESSAGE-----
Hash: SHA512

Format: 3.0 (quilt)
Source: gdk-pixbuf
Binary: libgdk-pixbuf-2.0-0, libgdk-pixbuf2.0-bin, libgdk-pixbuf2.0-common, libgdk-pixbuf-2.0-dev, libgdk-pixbuf2.0-doc, libgdk-pixbuf2.0-0-udeb, libgdk-pixbuf-2.0-0-udeb, gir1.2-gdkpixbuf-2.0, gdk-pixbuf-tests
Architecture: any all
Version: 2.42.10+dfsg-3ubuntu3.3
Maintainer: Ubuntu Developers <ubuntu-devel-discuss@lists.ubuntu.com>
Uploaders: Emilio Pozuelo Monfort <pochu@debian.org>, Iain Lane <laney@debian.org>, Jeremy Bicha <jbicha@ubuntu.com>, Laurent Bigonville <bigon@debian.org>
Homepage: https://www.gtk.org/
Standards-Version: 4.6.2
Vcs-Browser: https://salsa.debian.org/gnome-team/gdk-pixbuf
Vcs-Git: https://salsa.debian.org/gnome-team/gdk-pixbuf.git
Testsuite: autopkgtest
Testsuite-Triggers: build-essential, gnome-desktop-testing, pkg-config
Build-Depends: debhelper-compat (= 13), dh-sequence-gir, gi-docgen, libgirepository1.0-dev (>= 1.78.1-5~), libglib2.0-dev, libjpeg-dev, libpng-dev (<< 1.7), libtiff-dev, meson, python3-docutils <!nodoc>, shared-mime-info, xsltproc <!noudeb>
Package-List:
 gdk-pixbuf-tests deb libs optional arch=any
 gir1.2-gdkpixbuf-2.0 deb introspection optional arch=any
 libgdk-pixbuf-2.0-0 deb libs optional arch=any
 libgdk-pixbuf-2.0-0-udeb udeb debian-installer optional arch=any profile=!noudeb
 libgdk-pixbuf-2.0-dev deb libdevel optional arch=any
 libgdk-pixbuf2.0-0-udeb udeb debian-installer optional arch=any profile=!noudeb
 libgdk-pixbuf2.0-bin deb libs optional arch=any
 libgdk-pixbuf2.0-common deb libs optional arch=all
 libgdk-pixbuf2.0-doc deb doc optional arch=all profile=!nodoc
Checksums-Sha1:
 08baf45662714b21a1fa78d1ade4926cee1a5506 6439240 gdk-pixbuf_2.42.10+dfsg.orig.tar.xz
 3417fc74debe91dd58e3ae274c72f4ed96697049 29808 gdk-pixbuf_2.42.10+dfsg-3ubuntu3.3.debian.tar.xz
Checksums-Sha256:
 46663e445468e92f4a0ca876b02aed4f8758595ee3acfaa6ef3ba2b29e1c1930 6439240 gdk-pixbuf_2.42.10+dfsg.orig.tar.xz
 62966dc916fb4476b0d36ccdb53040845290a55f2f3efe2358ecb567c8295906 29808 gdk-pixbuf_2.42.10+dfsg-3ubuntu3.3.debian.tar.xz
Files:
 25dc1bf2c14ae78161f603fe62dad38f 6439240 gdk-pixbuf_2.42.10+dfsg.orig.tar.xz
 b0882991efada8f431f812eea3eed5c9 29808 gdk-pixbuf_2.42.10+dfsg-3ubuntu3.3.debian.tar.xz
Original-Maintainer: Debian GNOME Maintainers <pkg-gnome-maintainers@lists.alioth.debian.org>

-----BEGIN PGP SIGNATURE-----

iQIzBAEBCgAdFiEEUMSg3c8x5FLOsZtRZWnYVadEvpMFAmnOdZ0ACgkQZWnYVadE
vpOQyg/7BZZ0zaD7cKsoUFJ3e9Bd0wb3TCjS9sK7UcDrxn+qe0V53ItDVTGuj0X6
IinIHNzdNKufQkGiP+C7i9QS1nRUT/uBv5yzm0mXv3iLZrHoVlGokVyx0WT6Qdjj
sBNbJJmOO4CYwPjUbtGp5Up7CSHOEzO3g5ZJkGZk9AeEFf/ZVZFOGwyyLoy/6lDd
jYTzJOpEz6foLkPgt1VY2kQIdv+OlxBnIeY8A0NUpuG8i6C3b47cyptXVqvVh0eF
YO4yae5ZHn7c4Lag7dcYISlQ9mFQogzHS6a0pcVPwlKih7yOc6jNNkz+AcO1vzoT
+UpCLa/zPu5t1gSnIY+/G2BWXsK+/FW7nQGuQsOb+aEICVwQGbgweWMpR0cczk33
SZqshsy0jN+4zD/A0bsw38WMf5pAsmx1Pr3NocSdouIOIBeVbASLHox0hehkkRVl
kg2q47gbXs9ftu4fnxxZT/rachRacBMO57wBIHPtb8fhXpda8TB7uLURC+JeWUHS
tswk692Gh1uTrStwI1mi44fAwxIWmg67WHdBwD76XA7Meo1S/bWabbJCbNO44TmO
VBzNj6UiVGITWkaVtVhtASSVDuSOxEAhTqxrg4A3wPZbSlARfn3md5lSY7QSFutI
u9J8nvcOwPMtahH5oN32Iagn7Vro24UwnxgNzpdYPiDRgvlkTrU=
=ulzP
-----END PGP SIGNATURE-----
