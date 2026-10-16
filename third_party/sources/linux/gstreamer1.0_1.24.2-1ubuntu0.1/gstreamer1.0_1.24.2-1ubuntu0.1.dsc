-----BEGIN PGP SIGNED MESSAGE-----
Hash: SHA512

Format: 3.0 (quilt)
Source: gstreamer1.0
Binary: libgstreamer1.0-0, libgstreamer1.0-dev, gstreamer1.0-tools, gir1.2-gstreamer-1.0
Architecture: any
Version: 1.24.2-1ubuntu0.1
Maintainer: Ubuntu Developers <ubuntu-devel-discuss@lists.ubuntu.com>
Uploaders: Sebastian Dröge <slomo@debian.org>, Sjoerd Simons <sjoerd@debian.org>, Marc Leeman <marc.leeman@gmail.com>,
Homepage: https://gstreamer.freedesktop.org
Standards-Version: 4.6.2
Vcs-Browser: https://salsa.debian.org/gstreamer-team/gstreamer1.0/
Vcs-Git: https://salsa.debian.org/gstreamer-team/gstreamer1.0.git
Build-Depends: debhelper-compat (= 13), dh-sequence-gir, meson (>= 0.62), pkgconf, perl-doc, zlib1g-dev, libglib2.0-dev, libgmp-dev <!nocheck> | libgmp3-dev <!nocheck>, libgsl-dev <!nocheck> | libgsl0-dev <!nocheck>, libunwind-dev [i386 amd64 armel armhf arm64 powerpc ppc64 ppc64el mipsel mips64el riscv64], libdw-dev [i386 amd64 armel armhf arm64 powerpc ppc64 ppc64el mipsel mips64el riscv64], bison, flex, rustc, libgirepository1.0-dev, gir1.2-glib-2.0, gir1.2-freedesktop, bash-completion, libcap2-bin [linux-any], libcap-dev [linux-any]
Package-List:
 gir1.2-gstreamer-1.0 deb introspection optional arch=any
 gstreamer1.0-tools deb utils optional arch=any
 libgstreamer1.0-0 deb libs optional arch=any
 libgstreamer1.0-dev deb libdevel optional arch=any
Checksums-Sha1:
 3f3c79c48a49ffe04e5584b4cc33b15afa3901d9 1850672 gstreamer1.0_1.24.2.orig.tar.xz
 e1ee979a15c619cf066727f263248e4f876c8e92 833 gstreamer1.0_1.24.2.orig.tar.xz.asc
 fefe2f6db2e644b3479ab073aed0f5e66176bdf8 50960 gstreamer1.0_1.24.2-1ubuntu0.1.debian.tar.xz
Checksums-Sha256:
 9cafdd23bd180f1681c56cd3a6879a8497ccf24da6f422a6b6f356fa074a8481 1850672 gstreamer1.0_1.24.2.orig.tar.xz
 360f2173830a1624f6eb09fae72d5487f2cbd99b2cf83174890607e1eda96ec4 833 gstreamer1.0_1.24.2.orig.tar.xz.asc
 a2e8ac4ff91003ca640e62c2d29afa1cee706ecc0988a28aa3c3e23e12e1591b 50960 gstreamer1.0_1.24.2-1ubuntu0.1.debian.tar.xz
Files:
 fd0faca3054dd579768f81288be822d4 1850672 gstreamer1.0_1.24.2.orig.tar.xz
 1ab72835e0ffdb537f02735ba8c1d9e1 833 gstreamer1.0_1.24.2.orig.tar.xz.asc
 f4a24d7cbc2fdf813bc09dc105bd3b78 50960 gstreamer1.0_1.24.2-1ubuntu0.1.debian.tar.xz
Original-Maintainer: Maintainers of GStreamer packages <gstreamer1.0@packages.debian.org>

-----BEGIN PGP SIGNATURE-----

iQIzBAEBCgAdFiEEUMSg3c8x5FLOsZtRZWnYVadEvpMFAmdhdwoACgkQZWnYVadE
vpMwtQ//dwQ5s8bdenk7J1AERZR7Ye0aaSiDM/D419SDV+xuqfJJTHIgdSVqvr16
RR9JBwrPPk/mFotpUEMzAbqSjoJDYJ3GoO5tyaLbHYy8Qu2HCULcqcfW0RNxY4CK
k2ztbTUYOXtxxwP5Xbz9YnXn153KPqcMSgn/GB6beU3qpihBq1B1VfGwADWIkyb5
WSjF6qFl+ixkiVD8uid5B1MKri0WsARVcCOacM48nvYAHE1vecr20OfOYAeMSJd4
4ODUEEJUWZ82UgVQWTQR7aN6ck3CoTEzakEEScMamDUCZ6XOR74+eymFUZIYnB7c
VpeXubjagWVROBRrXakhqh91/Rn7VU8nvQG8yk3W/hyl0p5hUdbJGGfuPjVh9Lz+
ZgMHUetQY5eZbtccoVDYNlwDLgaP7KUd3w3EOaVhkfPo3erf1hefktEO2FNm+RH6
B3Y/oIQQ38xNDjfjzXMzoiAvX40NlhhFb9vhDKMgkLmaF1pusEe9zcTQjWBSWkb3
6LS0bcLL/8S066vvYtiARsNm9zFetTbMcLEGd6lGltFyPVSGU/QzYsEucxFRgoby
6+78OhiPXe2YWWSvCnGYCakZogKL1lNaSiWhS+62pVlCc530mP4UfJqhXB2Ahomt
D1sJcyoCjtcO2Vi6iiK33Stfurv8LdqERzBKR8LgOkIUkMW+zzs=
=TRDs
-----END PGP SIGNATURE-----
