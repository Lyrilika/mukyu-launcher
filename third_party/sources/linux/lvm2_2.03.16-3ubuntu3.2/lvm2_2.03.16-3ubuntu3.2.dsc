-----BEGIN PGP SIGNED MESSAGE-----
Hash: SHA512

Format: 3.0 (quilt)
Source: lvm2
Binary: lvm2, lvm2-udeb, lvm2-dbusd, lvm2-lockd, libdevmapper-dev, libdevmapper1.02.1, libdevmapper1.02.1-udeb, dmsetup, dmsetup-udeb, libdevmapper-event1.02.1, dmeventd, liblvm2cmd2.03, liblvm2-dev
Architecture: linux-any all
Version: 2.03.16-3ubuntu3.2
Maintainer: Ubuntu Developers <ubuntu-devel-discuss@lists.ubuntu.com>
Uploaders: Bastian Blank <waldi@debian.org>
Homepage: https://sourceware.org/lvm2/
Standards-Version: 4.1.1
Vcs-Browser: https://salsa.debian.org/lvm-team/lvm2
Vcs-Git: https://salsa.debian.org/lvm-team/lvm2.git
Build-Depends: debhelper-compat (= 13), autoconf-archive, automake, libaio-dev, libblkid-dev, pkg-config, systemd-dev (>= 255~rc1-1), thin-provisioning-tools
Build-Depends-Arch: libcmap-dev, libcorosync-common-dev, libcpg-dev, libdlm-dev (>> 2), libdlmcontrol-dev, libedit-dev, libquorum-dev, libsanlock-dev, libselinux1-dev, libsystemd-dev, libudev-dev
Build-Depends-Indep: dh-sequence-python3, python3-dev, python3-dbus, python3-pyudev
Package-List:
 dmeventd deb admin optional arch=linux-any
 dmsetup deb admin optional arch=linux-any
 dmsetup-udeb udeb debian-installer optional arch=linux-any profile=!noudeb
 libdevmapper-dev deb libdevel optional arch=linux-any
 libdevmapper-event1.02.1 deb libs optional arch=linux-any
 libdevmapper1.02.1 deb libs optional arch=linux-any
 libdevmapper1.02.1-udeb udeb debian-installer optional arch=linux-any profile=!noudeb
 liblvm2-dev deb libdevel optional arch=linux-any
 liblvm2cmd2.03 deb libs optional arch=linux-any
 lvm2 deb admin optional arch=linux-any
 lvm2-dbusd deb admin optional arch=all
 lvm2-lockd deb admin optional arch=linux-any
 lvm2-udeb udeb debian-installer optional arch=linux-any profile=!noudeb
Checksums-Sha1:
 71c96f51e73d4e8cd8378fb23ed54ac42c14dce7 1790340 lvm2_2.03.16.orig.tar.xz
 92052905996cad9a726dee2e3119107054f033f5 46896 lvm2_2.03.16-3ubuntu3.2.debian.tar.xz
Checksums-Sha256:
 9eee14d34f7962ade7d4624114ce7b6bd3d868d210afb72b3769f8c6a082646e 1790340 lvm2_2.03.16.orig.tar.xz
 0d2c6a297fb6bad3702806fabaf04ba30447674ec2cc2c19d8840c001b54f258 46896 lvm2_2.03.16-3ubuntu3.2.debian.tar.xz
Files:
 2587b136c4774389600884b03386cf61 1790340 lvm2_2.03.16.orig.tar.xz
 728b392891139a4bc3688ac7aae43934 46896 lvm2_2.03.16-3ubuntu3.2.debian.tar.xz
Original-Maintainer: Debian LVM Team <team+lvm@tracker.debian.org>

-----BEGIN PGP SIGNATURE-----

iQIzBAEBCgAdFiEE4qlMxBx1Pex4dJYuxTfgBIBe5lcFAmdXPpsACgkQxTfgBIBe
5leAJA/+JB0byK3xHJm6tXC97i5ZDlzokFyOOEeOXO/Fl79CtScNEcxsHe7eKiAY
ZudAmjNROtYEsUXATzFDHLr1OX6zf9eac23/Mr/02nsoIP3w29+TmYOSs02mAzMZ
NIQi+gpoVvs+kYfba0wNq41OvyV/OqTsc0C56xu27dfwEQsbqeiaP1iBL79N8Pfo
0tHcuyuc59gryGD9b3oJFL68IlQ9WQeyyi0RWi4CNmIwoTQk5Xg6vlpzdWnZ2962
6go/qDX85XTFQdwXm5xp3Kr4SLIVs98YGC982uJZGf5NF8T8UhSNP3Yo8M58y8Vu
r7+3dOf1Eaqjl03W4z/dasO5hgC+nz1wUlrYe6RV9EJxE/9jm+wYSnANJPpUg0HQ
XlVwTNLJByKbdPRRY/JVhZs5v/ai23Mpt2dQuGqxpu7+roYpN5r4gECQPEh0rTJj
qtgMoLA5a+jbM7SKQHRIlP0KKeQyV9tAk5BeXHMWtZqCM1tse2XRd/NKADqmyf+k
rozqxohz7LjYiVAbfmvwiYcMqqhGV0xuilPXX6DZL03khcRqunw8uPymtcxsjEW1
db5jZBHqeebJ+gtMLiXpUIhV7iBELyLb9VdiX2mH20pDeMQj9/4fO0UXkEoyq1/3
PHyT8tIWvqhwb/UzkSLDUwaj3irxRm2YG9LIsK73+eFdY4Cl6U8=
=8STM
-----END PGP SIGNATURE-----
