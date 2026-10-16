-----BEGIN PGP SIGNED MESSAGE-----
Hash: SHA512

Format: 3.0 (quilt)
Source: audit
Binary: auditd, libauparse0t64, libauparse-dev, libaudit1, libaudit-common, libaudit-dev, python3-audit, golang-redhat-audit-dev, audispd-plugins
Architecture: linux-any all
Version: 1:3.1.2-2.1ubuntu0.1
Maintainer: Ubuntu Developers <ubuntu-devel-discuss@lists.ubuntu.com>
Homepage: https://people.redhat.com/sgrubb/audit/
Standards-Version: 4.6.2
Vcs-Browser: https://salsa.debian.org/debian/audit
Vcs-Git: https://salsa.debian.org/debian/audit.git
Testsuite: autopkgtest
Testsuite-Triggers: build-essential, pkg-config, python3-all
Build-Depends: dpkg-dev (>= 1.22.5), debhelper-compat (= 13), dh-python <!nopython>, libcap-ng-dev, libkrb5-dev, libldap2-dev <!pkg.audit.noldap>, libwrap0-dev, linux-libc-dev (>= 5.9~), python3-all-dev:any <!nopython>, libpython3-all-dev <!nopython>, swig
Build-Depends-Indep: golang-any
Package-List:
 audispd-plugins deb admin optional arch=linux-any profile=!pkg.audit.noldap profile:v1=!pkg.audit.noldap
 auditd deb admin optional arch=linux-any
 golang-redhat-audit-dev deb golang optional arch=all
 libaudit-common deb libs optional arch=all
 libaudit-dev deb libdevel optional arch=linux-any
 libaudit1 deb libs optional arch=linux-any
 libauparse-dev deb libdevel optional arch=linux-any
 libauparse0t64 deb libs optional arch=linux-any
 python3-audit deb python optional arch=linux-any profile=!nopython profile:v1=!nopython
Checksums-Sha1:
 45cffb1ded9a57a79b33547f58228131d3eb14a6 1219860 audit_3.1.2.orig.tar.gz
 4db59921b538efcf6e76976fda517c27697acb07 19524 audit_3.1.2-2.1ubuntu0.1.debian.tar.xz
Checksums-Sha256:
 c0b1792d1f0a88c6f1828710509cbb987059fc68712c97669ca90eae103d287d 1219860 audit_3.1.2.orig.tar.gz
 4af490a6361d5f4e4fca5b72fd72e1b265e01d95c511ee0a85e89a67c33a98df 19524 audit_3.1.2-2.1ubuntu0.1.debian.tar.xz
Files:
 9d325b543f79b20a8f7ff2021ebac0c3 1219860 audit_3.1.2.orig.tar.gz
 f0c3693995a56e5d3bbf3629689b6985 19524 audit_3.1.2-2.1ubuntu0.1.debian.tar.xz
Original-Maintainer: Laurent Bigonville <bigon@debian.org>

-----BEGIN PGP SIGNATURE-----

iQIzBAEBCgAdFiEEiYfY5F8zkxDOZhouZMRpvlnA3qIFAmpzsYUACgkQZMRpvlnA
3qJg8RAAtkIYry9CJvXL6brdirOsSJOZ08mMhHPovPyZp14rLaWToQJ5MaMHLsP7
Zrgb9D87vKWYkYQdkLsEdvyDrcZOkuyP/x2zK4qQ/3DS6EGEFxXIjd/xHMmkzlug
bYtrvuNpi9xvhT4MxknOGjDl4ke8dbJ0S907i/AaiSuOdvo7JCybySP6yojTddUr
KUaZIUPkaSbijBUOgGdv5yqR3WXNC46m9Oje6SGvmtfFzyNXZRomhlDSCiNiuEcj
MXPiRPyPrfzPjNBRmkj1jCFb5xoo2BzAFTNBq9LqQU1QMRAuCQ2HJfx07OEoJdX4
Ptlcb/lZAB9a0T9yq+Qo28e9yDUUNeucB63wZBzhQ24QIyVqwSUT82k7YBz6y8BF
LxQ0M++Tfde1tBH2ujVYNvbNzmjMxiiK1ks4/unB1nViPcME03fYwVUQe5SRm3bl
rQZSKg0AO4kWWb6KmOJCN1QKzyjT6mr7z1esNGzlgbMlTSZA2rgh8irzjcsexdb/
6IeW26c9N027UrpNUurF4jrfZAjnrXbtc9hagaKN7rxkTv72lCwc/howzmaDMoW9
yhId4uahL/HesVJ4Vjq9Kkekng8C/37lzWP7PbtLIQj1rXCtvyxnFCLllchwlgPk
ANBlre2Vaiq1eD9AWxU0kq0/1mknc6H8huoYi0n8eYWRNCaJT2g=
=Aehp
-----END PGP SIGNATURE-----
