-----BEGIN PGP SIGNED MESSAGE-----
Hash: SHA512

Format: 3.0 (quilt)
Source: util-linux
Binary: util-linux, util-linux-locales, mount, bsdutils, bsdextrautils, fdisk, fdisk-udeb, libblkid1, libblkid1-udeb, libblkid-dev, libfdisk1, libfdisk1-udeb, libfdisk-dev, libmount1, libmount1-udeb, libmount-dev, libsmartcols1, libsmartcols1-udeb, libsmartcols-dev, libuuid1, uuid-runtime, libuuid1-udeb, uuid-dev, util-linux-udeb, rfkill, eject, eject-udeb, util-linux-extra
Architecture: any all
Version: 2.39.3-9ubuntu6.6
Maintainer: Ubuntu Developers <ubuntu-devel-discuss@lists.ubuntu.com>
Uploaders:  Chris Hofstaedtler <zeha@debian.org>
Homepage: https://www.kernel.org/pub/linux/utils/util-linux/
Standards-Version: 4.6.0
Vcs-Browser: https://salsa.debian.org/debian/util-linux
Vcs-Git: https://salsa.debian.org/debian/util-linux.git
Testsuite: autopkgtest
Testsuite-Triggers: bash, bc, build-essential, dpkg, grep, pkg-config
Build-Depends: asciidoctor <!stage1 !nodoc>, bc <!stage1 !nocheck>, bison, debhelper-compat (= 13), dh-exec, gettext, libaudit-dev [linux-any] <!stage1>, libcap-ng-dev [linux-any] <!stage1>, libcrypt-dev <!stage1>, libcryptsetup-dev [linux-any] <!pkg.util-linux.noverity>, libncurses-dev, libpam0g-dev <!stage1>, libreadline-dev, libselinux1-dev [linux-any], libsystemd-dev [linux-any] <!stage1>, libtool, libudev-dev [linux-any] <!stage1>, netbase <!stage1 !nocheck>, pkg-config, po-debconf, po4a, socat <!stage1 !nocheck>, systemd [linux-any] <!stage1>, systemd-dev [linux-any] <!stage1>, zlib1g-dev
Build-Conflicts: libedit-dev
Package-List:
 bsdextrautils deb utils optional arch=any profile=!stage1
 bsdutils deb utils required arch=any profile=!stage1 essential=yes
 eject deb utils optional arch=linux-any profile=!stage1
 eject-udeb udeb debian-installer optional arch=linux-any profile=!stage1,!noudeb
 fdisk deb utils important arch=any profile=!stage1
 fdisk-udeb udeb debian-installer optional arch=hurd-any,linux-any profile=!stage1,!noudeb
 libblkid-dev deb libdevel optional arch=any
 libblkid1 deb libs optional arch=any
 libblkid1-udeb udeb debian-installer optional arch=any profile=!noudeb
 libfdisk-dev deb libdevel optional arch=any
 libfdisk1 deb libs optional arch=any
 libfdisk1-udeb udeb debian-installer optional arch=any profile=!noudeb
 libmount-dev deb libdevel optional arch=linux-any
 libmount1 deb libs optional arch=any
 libmount1-udeb udeb debian-installer optional arch=linux-any profile=!noudeb
 libsmartcols-dev deb libdevel optional arch=any
 libsmartcols1 deb libs optional arch=any
 libsmartcols1-udeb udeb debian-installer optional arch=any profile=!noudeb
 libuuid1 deb libs optional arch=any
 libuuid1-udeb udeb debian-installer optional arch=any profile=!noudeb
 mount deb admin required arch=linux-any profile=!stage1
 rfkill deb utils optional arch=linux-any profile=!stage1
 util-linux deb utils required arch=any profile=!stage1 essential=yes
 util-linux-extra deb utils standard arch=any profile=!stage1
 util-linux-locales deb localization optional arch=all profile=!stage1
 util-linux-udeb udeb debian-installer optional arch=any profile=!stage1,!noudeb
 uuid-dev deb libdevel optional arch=any
 uuid-runtime deb utils optional arch=any profile=!stage1
Checksums-Sha1:
 9704d9927be7888b97a09735a1b5915a390d43c3 8526168 util-linux_2.39.3.orig.tar.xz
 67451ba0eae7d858a6c1cda00fa066b65931d735 155164 util-linux_2.39.3-9ubuntu6.6.debian.tar.xz
Checksums-Sha256:
 7b6605e48d1a49f43cc4b4cfc59f313d0dd5402fa40b96810bd572e167dfed0f 8526168 util-linux_2.39.3.orig.tar.xz
 d63476e26c149179ae8a19f4c701e27cf9235c3df2482714d369211683824e37 155164 util-linux_2.39.3-9ubuntu6.6.debian.tar.xz
Files:
 f3591e6970c017bb4bcd24ae762a98f5 8526168 util-linux_2.39.3.orig.tar.xz
 4ec8e817be96ff7a1651399c646a461f 155164 util-linux_2.39.3-9ubuntu6.6.debian.tar.xz
Original-Maintainer: util-linux packagers <util-linux@packages.debian.org>

-----BEGIN PGP SIGNATURE-----

iQIzBAEBCgAdFiEEUMSg3c8x5FLOsZtRZWnYVadEvpMFAmqF5YEACgkQZWnYVadE
vpOP7BAAqIl4Y/VyGprGEFauMlXu7e9zSTii0B/LS5bzkB8e/WzNJy2GdymQtD2I
qTdUYmc9wRJrNBH8jcQ0E25knHedpKoJqpTA1WzFZKzSyTZkcf/xQCJqCTtoPAhf
bzas+8o5/4Zy8mziFOhuehEZPOgd3ol8XS+oMnrMANzbpslpN2wqrGRXO1GMoSgk
+fwfWkhEC8fMa95N++VJxe8QRBkXVXqPkReUoJaPepcZiPFYlNQScFEuZdwIGD5w
lvbTR7WIV/zS6LpuLIrsrRPoc25t402ljRTs+cfvvly4yBXNATI9Njl9in9k9icY
nyjE8YSCwxg/Z9+OqwxA0Xh/Pi+kDm3LC5p1iV0Q23gYWkxx56MmatqaukbjCVlK
qgC9USVFPIoMSzAAztbtjVQH2KQGMhDMRF8OKYkPkKN2NjiLvnhYVaAlFWVLbSM/
AwLXx9AJnafuTANdTeq69pzDHxiJkUaCJIv1aj4mucWy2MedHGsYxmtfjbx7+Rcf
DYRdwYP/xj3CWUdhQqg3tnZ0PaVKnJim9BKaZAYTVQqHQr8vigkRVTKoYaUCMLWZ
ZG8KBLTakuD9cune9W9v7v+xJTsHN/rvGa536Ac4uvQtBSxs4beW9KUVfvqeCSzi
BQg+Wl93hYRx/P9ohG9hPJ9TIs5axQBD0QEm6KdiYtNiKJNooZs=
=j0Zn
-----END PGP SIGNATURE-----
