-----BEGIN PGP SIGNED MESSAGE-----
Hash: SHA512

Format: 3.0 (quilt)
Source: librsvg
Binary: librsvg2-dev, librsvg2-2, librsvg2-common, librsvg2-doc, librsvg2-bin, librsvg2-tests, gir1.2-rsvg-2.0
Architecture: any all
Version: 2.58.0+dfsg-1ubuntu0.1
Maintainer: Ubuntu Developers <ubuntu-devel-discuss@lists.ubuntu.com>
Uploaders: Emilio Pozuelo Monfort <pochu@debian.org>, Jeremy Bícha <jbicha@ubuntu.com>, Laurent Bigonville <bigon@debian.org>, Michael Biebl <biebl@debian.org>, Tim Lunn <tim@feathertop.org>
Homepage: https://wiki.gnome.org/Projects/LibRsvg
Standards-Version: 4.6.2
Vcs-Browser: https://salsa.debian.org/gnome-team/librsvg
Vcs-Git: https://salsa.debian.org/gnome-team/librsvg.git
Testsuite: autopkgtest
Testsuite-Triggers: build-essential, file, gnome-desktop-testing
Build-Depends: debhelper-compat (= 13), cargo, dh-sequence-gir, jq, libcairo2-dev (>= 1.2.0), libfreetype-dev (>= 2.8.0), libgdk-pixbuf-2.0-dev (>= 2.23.5-2), libglib2.0-dev (>= 2.50.0), libharfbuzz-dev, libpango1.0-dev (>= 1.48.11), libxml2-dev (>= 2.9.0), libgirepository1.0-dev, gir1.2-gobject-2.0-dev <!nogir>, gir1.2-gdkpixbuf-2.0-dev <!nogir>, gir1.2-gio-2.0-dev <!nogir>, gir1.2-cairo-1.0-dev <!nogir>, locales, python3-docutils <!nodoc>, rustc (>= 1.70), valac (>= 0.17.5)
Build-Depends-Indep: gi-docgen <!nodoc>
Package-List:
 gir1.2-rsvg-2.0 deb introspection optional arch=any
 librsvg2-2 deb libs optional arch=any
 librsvg2-bin deb graphics optional arch=any
 librsvg2-common deb libs optional arch=any
 librsvg2-dev deb libdevel optional arch=any
 librsvg2-doc deb doc optional arch=all profile=!nodoc
 librsvg2-tests deb misc optional arch=any
Checksums-Sha1:
 b165ade1f068cf6cdb0ef762b73f2d711761d72a 5736316 librsvg_2.58.0+dfsg.orig.tar.xz
 a44733e2c7a39e3e9ab0c7b4b09c486d52d4ff7c 29523476 librsvg_2.58.0+dfsg-1ubuntu0.1.debian.tar.xz
Checksums-Sha256:
 5e59425031069e9310207664e8fd75004d1dc7ce09f1750f7978aa8e87ab7e49 5736316 librsvg_2.58.0+dfsg.orig.tar.xz
 440d8c3af3510a03e7cace1ca940495b02893309d8a7b04329cd611fcb95147f 29523476 librsvg_2.58.0+dfsg-1ubuntu0.1.debian.tar.xz
Files:
 d0f34591bae921743fe612b8cdcb96c5 5736316 librsvg_2.58.0+dfsg.orig.tar.xz
 651a8757c81d31b53dba73d7342138e9 29523476 librsvg_2.58.0+dfsg-1ubuntu0.1.debian.tar.xz
Original-Maintainer: Debian GNOME Maintainers <pkg-gnome-maintainers@lists.alioth.debian.org>

-----BEGIN PGP SIGNATURE-----

iHUEARYKAB0WIQRTrw6YrvFKWlQ5EXf8zkxKtwaNUgUCasQKzgAKCRD8zkxKtwaN
Ur7lAQCcl04g7JU6DoLQyzxb7C/pYAOMs9BcbjGiVLUporoF9gD9F0pX81OjNas1
bORCJK+hNAcd44AWemeqURY/rSkH3gU=
=Fo4O
-----END PGP SIGNATURE-----
