-----BEGIN PGP SIGNED MESSAGE-----
Hash: SHA512

Format: 3.0 (quilt)
Source: cups
Binary: libcups2t64, cups, cups-bsd, cups-client, cups-common, cups-core-drivers, cups-daemon, cups-ipp-utils, cups-ppdc, cups-server-common, libcups2-dev, libcupsimage2t64, libcupsimage2-dev
Architecture: any all
Version: 2.4.7-1.2ubuntu7.14
Maintainer: Ubuntu Developers <ubuntu-devel-discuss@lists.ubuntu.com>
Uploaders:  Till Kamppeter <till.kamppeter@gmail.com>, Thorsten Alteholz <debian@alteholz.de>,
Homepage: https://github.com/OpenPrinting/cups/
Standards-Version: 4.6.2
Vcs-Browser: https://salsa.debian.org/printing-team/cups
Vcs-Git: https://salsa.debian.org/printing-team/cups.git
Testsuite: autopkgtest
Build-Depends: dpkg-dev (>= 1.22.5), autoconf, automake, debhelper-compat (= 13), dh-strip-nondeterminism, libavahi-client-dev, libavahi-common-dev, libdbus-1-dev, libgnutls28-dev, libkrb5-dev, libpam0g-dev, libpaper-dev, libsystemd-dev [linux-any], libtool, libusb-1.0-0-dev [!hurd-any], patch, pkg-config, po-debconf, po4a, zlib1g-dev, libapparmor-dev, libsnapd-glib-dev (>= 1.61)
Build-Depends-Arch: dpkg-dev (>= 1.22.5), dh-apparmor
Build-Conflicts: libgmp-dev (<< 2:6)
Package-List:
 cups deb net optional arch=any
 cups-bsd deb net optional arch=any
 cups-client deb net optional arch=any
 cups-common deb net optional arch=all
 cups-core-drivers deb net optional arch=any
 cups-daemon deb net optional arch=any
 cups-ipp-utils deb net optional arch=any
 cups-ppdc deb utils optional arch=any
 cups-server-common deb net optional arch=all
 libcups2-dev deb libdevel optional arch=any
 libcups2t64 deb libs optional arch=any
 libcupsimage2-dev deb libdevel optional arch=any
 libcupsimage2t64 deb libs optional arch=any
Checksums-Sha1:
 9c6155dfa367eee9a88ad08cf83b1dc6c446309f 8134809 cups_2.4.7.orig.tar.gz
 a39bf24142112485a24c37b7cc9bc20ea06320f1 431720 cups_2.4.7-1.2ubuntu7.14.debian.tar.xz
Checksums-Sha256:
 dd54228dd903526428ce7e37961afaed230ad310788141da75cebaa08362cf6c 8134809 cups_2.4.7.orig.tar.gz
 dede081be847c8d86dc6fa5060a03ddbd0787d8cd83d6aa9213fc53bb4c2a640 431720 cups_2.4.7-1.2ubuntu7.14.debian.tar.xz
Files:
 e0a5ddbf53dfad41da26fc1ef60b2256 8134809 cups_2.4.7.orig.tar.gz
 c9cd44481b960ed719423d5eae331041 431720 cups_2.4.7-1.2ubuntu7.14.debian.tar.xz
Original-Maintainer: Debian Printing Team <debian-printing@lists.debian.org>

-----BEGIN PGP SIGNATURE-----

iQIzBAEBCgAdFiEEUMSg3c8x5FLOsZtRZWnYVadEvpMFAmoqznQACgkQZWnYVadE
vpN9ChAAp8HN57M35F/rwYQi1ztub80Fd0iyx19VE5cUnJqdS/XcgeOfa5ZZPL8E
bwYwzKjm/DGEmx4+QdW/0U2TBJmDufvuV/N5J4WmNOhGJbc30ocR+gwvzn3nV9G/
xawx4bLgh+nJ8QSckPN01i+eEXwXhwvIBqxmsquAK9CwLWiYDETazvNdCwEK+69b
mmSauvfGovahAOdBoYqBgrU92mCpWL+AJaAXvp6cc7ZgSGyoYWTlQX2zLQgE+CEC
pnSdkm7OTVuOtc8o9EkwSuYuckJb1nmheSuLLImBGVnTlAZ2+1Km2FdjH9n5I+gk
vO+TdlIlIz54Jl8Xr4vAsFmYonx2YgZwPeCz83AMrr/a1u3j7Fe8nA8XhMdbam5B
8k4XD7h2VO+s7hG3tXKLsN+YMLcl68KylzRM9O0ddkhHd34e9qVwVerpQwnwdHiD
M7PzFpOQclCvgHdiYCjxAXcI5CpepJ4+LtM70bAfz6ICsTPDAajiPGEMSGG/jib9
D0OCUemGk2Lxfs/ge06n8r2TGyKahjSTMU8wcvo5cku1/RJfpzpCWw1egmLw4mnc
nE4txsCqKvj1tz6ewKBQykYx+JRQSzhlqI4xoQb4eSPWpFNDDnGwMp6VuuP0fmLY
IsfbU9wdrh6tLjyUOOBIL4ojOE9TaUXRGnW+7AfvGXEUN9Deq6I=
=vD9D
-----END PGP SIGNATURE-----
