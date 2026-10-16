-----BEGIN PGP SIGNED MESSAGE-----
Hash: SHA512

Format: 3.0 (quilt)
Source: dbus
Binary: dbus, dbus-session-bus-common, dbus-system-bus-common, dbus-bin, dbus-daemon, dbus-1-doc, dbus-tests, dbus-udeb, dbus-user-session, dbus-x11, libdbus-1-3, libdbus-1-3-udeb, libdbus-1-dev
Architecture: any all
Version: 1.14.10-4ubuntu4.1
Maintainer: Ubuntu Developers <ubuntu-devel-discuss@lists.ubuntu.com>
Uploaders:  Sjoerd Simons <sjoerd@debian.org>, Sebastian Dröge <slomo@debian.org>, Michael Biebl <biebl@debian.org>, Loic Minier <lool@dooz.org>, Simon McVittie <smcv@debian.org>,
Homepage: https://dbus.freedesktop.org/
Standards-Version: 4.6.2
Vcs-Browser: https://salsa.debian.org/utopia-team/dbus
Vcs-Git: https://salsa.debian.org/utopia-team/dbus.git
Testsuite: autopkgtest
Testsuite-Triggers: apparmor, build-essential, gnome-desktop-testing, init, systemd, xauth, xvfb
Build-Depends: autoconf-archive, automake, debhelper (>= 13.11.6~), debhelper-compat (= 13), dh-exec, libapparmor-dev [linux-any], libaudit-dev [linux-any], libcap-ng-dev [linux-any], libexpat-dev, libglib2.0-dev <!nocheck> <!noinsttest>, libnss-wrapper <!nocheck>, libselinux1-dev [linux-any], libsystemd-dev [linux-any], libx11-dev, pkgconf, valgrind-if-available, xml-core, xmlto <!nodoc>
Build-Depends-Indep: doxygen <!nodoc>, ducktype <!nodoc>, xsltproc <!nodoc>, yelp-tools <!nodoc>
Package-List:
 dbus deb admin standard arch=any
 dbus-1-doc deb doc optional arch=all profile=!nodoc
 dbus-bin deb admin optional arch=any
 dbus-daemon deb admin optional arch=any
 dbus-session-bus-common deb admin optional arch=all
 dbus-system-bus-common deb admin optional arch=all
 dbus-tests deb misc optional arch=any profile=!noinsttest
 dbus-udeb udeb debian-installer optional arch=any profile=!noudeb
 dbus-user-session deb admin optional arch=linux-any
 dbus-x11 deb x11 optional arch=any
 libdbus-1-3 deb libs optional arch=any
 libdbus-1-3-udeb udeb debian-installer optional arch=any profile=!noudeb
 libdbus-1-dev deb libdevel optional arch=any
Checksums-Sha1:
 47f03306a491509cdebacded837e51b086835252 1372328 dbus_1.14.10.orig.tar.xz
 76219dcec55c66705eb1a311d11ced2df190758d 833 dbus_1.14.10.orig.tar.xz.asc
 ae57bf2cdb405a217f0945de5fc27e1335670426 69668 dbus_1.14.10-4ubuntu4.1.debian.tar.xz
Checksums-Sha256:
 ba1f21d2bd9d339da2d4aa8780c09df32fea87998b73da24f49ab9df1e36a50f 1372328 dbus_1.14.10.orig.tar.xz
 5f292cd0603c3d736026ed3f4d1c1937847981669c1f0a389083518f013e1081 833 dbus_1.14.10.orig.tar.xz.asc
 c28e0e4840bf3c3f3cbdacae9b7228bb4694dd234f325535942dde76af3c322e 69668 dbus_1.14.10-4ubuntu4.1.debian.tar.xz
Files:
 46070a3487817ff690981f8cd2ba9376 1372328 dbus_1.14.10.orig.tar.xz
 a790dcc5fd84835ed9147c9679af551f 833 dbus_1.14.10.orig.tar.xz.asc
 1945902413dec63ac81673424cef83c7 69668 dbus_1.14.10-4ubuntu4.1.debian.tar.xz
Original-Maintainer: Utopia Maintenance Team <pkg-utopia-maintainers@lists.alioth.debian.org>
-----BEGIN PGP SIGNATURE-----

iQIzBAEBCgAdFiEEVovyKmYzfL/Jprm3LIPbyOm9DjcFAma1goUACgkQLIPbyOm9
DjcoExAAh3IxyyYvIi/Tj/QUgyt+M4IPIRJT+FUj4WvZZqYpFQ3T2u/gFPcdMXZS
FdCoHStBf/DrzLIm7vWAI4e1UoTRzAZpEUvw9pjlgMkPuben8KTt3LkCHSyDkkC6
4xC+Qu86Fk3cLAHSV5Ry9RKPvB/JzDQmss//XRHWCt8ajY2R03cI9K4LkJQ+QbDQ
0uOInULKnJXqjKUsiWAJmLH10oDyrdjMM3XRg8TSJ7LvD+tXI3piczarYUO4hfPp
9MkLG86brk4TGW7zKhhYeoEBgcuTTEK5Ie+nItEQDp8uNMP2DxaK9bQWUoUTDQFa
2Lamf05lEe8yNpL8Vxay1tgeq3VTWRw3vTSHNCexnVqqmcz6Km75Vefj97DMsk7p
cW8RJD67T9+k5+ntw+t6FwUIgUhnUB+QyUW6nXRUeIxF0jdk1wz5Wlu2Zi5h+yM/
oWZjg1881xHULV+VB8Q/9/5UzLjYhdY4JxkY8+YIpwi2e0K5qLvKjAwW7a6Lb2J0
8xmP63E9MOMktEjfvtEDNea+WOsTWqZ79iiFP24YLwO/NBpg1SGDYcXApyoEXPUI
+cDfXX831FYSC/fqqZ4kLx9yQI9MPU06eCUFvawXEDZGaCBGkVWT3NPrYJklU/O7
nZGsSGZlHx6I/NNYR5IXYIiDBiaxMHakki54w3Jo65F+x/DYs20=
=W+Cb
-----END PGP SIGNATURE-----
