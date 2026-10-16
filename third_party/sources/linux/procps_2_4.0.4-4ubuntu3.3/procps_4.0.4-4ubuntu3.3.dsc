-----BEGIN PGP SIGNED MESSAGE-----
Hash: SHA512

Format: 3.0 (quilt)
Source: procps
Binary: procps, libproc2-0, libproc2-dev
Architecture: any
Version: 2:4.0.4-4ubuntu3.3
Maintainer: Ubuntu Developers <ubuntu-devel-discuss@lists.ubuntu.com>
Homepage: https://gitlab.com/procps-ng/procps
Standards-Version: 4.6.2
Vcs-Browser: https://salsa.debian.org/debian/procps
Vcs-Git: https://salsa.debian.org/debian/procps.git
Testsuite: autopkgtest
Testsuite-Triggers: shunit2
Build-Depends: debhelper-compat (= 13), dh-exec (>= 0.3), libncurses-dev, dejagnu, libnuma-dev [amd64 i386 ia64 mips mipsel mips64 mips64el powerpc ppc64el], pkg-config, libsystemd-dev (>= 209) [linux-any]
Package-List:
 libproc2-0 deb libs optional arch=any
 libproc2-dev deb libdevel optional arch=any
 procps deb admin important arch=any
Checksums-Sha1:
 2b859acd7060e9898ac457dbd26dbebf563cc44b 1401540 procps_4.0.4.orig.tar.xz
 fa4c0b6c2da7ef0f5bdd8cee77899a7ede3b45e9 39588 procps_4.0.4-4ubuntu3.3.debian.tar.xz
Checksums-Sha256:
 22870d6feb2478adb617ce4f09a787addaf2d260c5a8aa7b17d889a962c5e42e 1401540 procps_4.0.4.orig.tar.xz
 895493786388b9ffa8a9ba894f473371cd4bbd2aa5089a8327cfdf00cf7cbc2d 39588 procps_4.0.4-4ubuntu3.3.debian.tar.xz
Files:
 2f747fc7df8ccf402d03e375c565cf96 1401540 procps_4.0.4.orig.tar.xz
 ec1c5134c01a9d9c8c671f2db9d3ffe6 39588 procps_4.0.4-4ubuntu3.3.debian.tar.xz
Original-Maintainer: Craig Small <csmall@debian.org>

-----BEGIN PGP SIGNATURE-----

iQJJBAEBCgAzFiEEO+EUUxKLErUg53wTEr7aOaHncEIFAmpnb9YVHGRnYWRvbXNr
aUB1YnVudHUuY29tAAoJEBK+2jmh53BC2mwP/AhPileTdDhCfW6106id+sD2PWUw
5A1g17bcy9pOAYTt4rZ0sQ+nD8OMcT7Om42vXY2de4pcPFBsL0TzHYAhv9rBcHwv
muUmCCQvCaxJDydxRjO36HOMH/MoqozYYrBHm16m9Qvr/qBqaQQxWTiV9KEdCShI
BOrSXXqOfynEJkmM7l/yHyMBzd2zgEhs2UYIcmVxBgaGODE95ap0Qo5g+SSlqxk3
WLiFHPQkiOb5/4ElGTzyEQIwSWdkfKOQR5DW+xZInQZtFLZtcrIK5ZRX+pBx7us/
gF8B7D4qttu2oc6me/FR4A2Q4o6HcrQpDCwGgARaKaLgjXT1ExJ4L/yWrQ1mrkpN
cVjDehREMjDkWMm5G9dhCPHzjMcyoDdWkVg3fMlZ0nd0K8oRjZrhtKFqG8HRXCcg
7qyh+qz40OvwefQaXL/OJsOSP5XiN2/iom2Y9m7zylwPEyKkOvKkyNDftINOFxDC
n6wZTKQ8u6Oo6JnZHPbb9wuAuyUq28p425XiXQ87R5Ev3GAW8CJG/4JkDbtcDgnd
6UVVLEohjCzxPEr1VV73rRu6nXiZ1d4Jwj7nMKEDFJCAwa5MCWt3H38FG2nyVHFq
X+sKydfsHk4O8cAh3xI2enc55HTWJJipQ47r2nG4AhaO3DzZKCSVpkoz+ewrLFJH
bx1jS4ULxrRzZ3iZ
=JWhp
-----END PGP SIGNATURE-----
