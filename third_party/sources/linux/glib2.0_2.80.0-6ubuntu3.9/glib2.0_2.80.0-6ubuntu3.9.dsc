-----BEGIN PGP SIGNED MESSAGE-----
Hash: SHA512

Format: 3.0 (quilt)
Source: glib2.0
Binary: libglib2.0-0t64, libglib2.0-tests, libglib2.0-udeb, libglib2.0-bin, libglib2.0-dev, libglib2.0-dev-bin, libglib2.0-data, libglib2.0-doc, libgirepository-2.0-0, libgirepository-2.0-dev, gir1.2-glib-2.0, gir1.2-glib-2.0-dev, gir1.2-girepository-3.0, gir1.2-girepository-3.0-dev
Architecture: any all
Version: 2.80.0-6ubuntu3.9
Maintainer: Ubuntu Developers <ubuntu-devel-discuss@lists.ubuntu.com>
Uploaders: Jeremy Bícha <jbicha@ubuntu.com>, Marco Trevisan (Treviño) <marco@ubuntu.com>, Simon McVittie <smcv@debian.org>
Homepage: https://wiki.gnome.org/Projects/GLib
Standards-Version: 4.6.2
Vcs-Browser: https://salsa.debian.org/gnome-team/glib/tree/ubuntu/noble
Vcs-Git: https://salsa.debian.org/gnome-team/glib.git -b ubuntu/noble
Testsuite: autopkgtest
Testsuite-Triggers: build-essential, dbus-daemon, dbus-x11, dconf-gsettings-backend, dpkg-repack, gnome-desktop-testing, gsettings-desktop-schemas, locales, locales-all, xauth, xvfb
Build-Depends: dbus-daemon <!nocheck> <!noinsttest>, debhelper-compat (= 13), dh-sequence-gnome, dh-sequence-python3, docbook-xml, docbook-xsl, dpkg-dev (>= 1.22.5), gettext, libdbus-1-dev <!nocheck> <!noinsttest>, libelf-dev, libffi-dev, libmount-dev [linux-any], libpcre2-dev, libselinux1-dev [linux-any], libxml2-utils, linux-libc-dev [linux-any], meson (>= 1.2.0), pkgconf, python3-docutils <!nodoc>, python3-packaging:native, python3:native, xsltproc, zlib1g-dev
Build-Depends-Arch: desktop-file-utils <!nocheck>, dh-sequence-gir <!nogir>, gobject-introspection (>= 1.78.1-18~) <!nogir>, locales <!nocheck> | locales-all <!nocheck>, python3-dbus <!nocheck>, python3-gi <!nocheck>, qemu-user <cross !nogir>, shared-mime-info <!nocheck>, tzdata <!nocheck>, xterm <!nocheck>
Build-Depends-Indep: gi-docgen <!nodoc>, gobject-introspection (>= 1.78.1-18~) <!nodoc>, qemu-user <cross !nodoc>
Package-List:
 gir1.2-girepository-3.0 deb introspection optional arch=any profile=!nogir
 gir1.2-girepository-3.0-dev deb libdevel optional arch=any profile=!nogir
 gir1.2-glib-2.0 deb introspection optional arch=any profile=!nogir
 gir1.2-glib-2.0-dev deb libdevel optional arch=any profile=!nogir
 libgirepository-2.0-0 deb libs optional arch=any
 libgirepository-2.0-dev deb libdevel optional arch=any
 libglib2.0-0t64 deb libs optional arch=any
 libglib2.0-bin deb misc optional arch=any
 libglib2.0-data deb libs optional arch=all
 libglib2.0-dev deb libdevel optional arch=any
 libglib2.0-dev-bin deb libdevel optional arch=any
 libglib2.0-doc deb doc optional arch=all profile=!nodoc
 libglib2.0-tests deb libs optional arch=any profile=!noinsttest,!nogir
 libglib2.0-udeb udeb debian-installer optional arch=any profile=!noudeb
Checksums-Sha1:
 f9c0c1f83778f34ccfa40563d21a3535fd0485a0 263364 glib2.0_2.80.0.orig-unicode-data.tar.xz
 3416bb2ce53f451afb288e948bb7c1570307e606 5510536 glib2.0_2.80.0.orig.tar.xz
 06a2bad17f0ba0c9ce2ef92f1c620ee4641c62f2 178288 glib2.0_2.80.0-6ubuntu3.9.debian.tar.xz
Checksums-Sha256:
 38680f78a0ae6258826418cb5096c19ae3566ba8fee0a2112a0ec40056e58729 263364 glib2.0_2.80.0.orig-unicode-data.tar.xz
 8228a92f92a412160b139ae68b6345bd28f24434a7b5af150ebe21ff587a561d 5510536 glib2.0_2.80.0.orig.tar.xz
 b86a66201ce7957256126e4cd69248848ce61a9330891f24df3bc0859d1ca542 178288 glib2.0_2.80.0-6ubuntu3.9.debian.tar.xz
Files:
 52f85a65b58be1c5f2b4d0d943cff489 263364 glib2.0_2.80.0.orig-unicode-data.tar.xz
 3a51e2803ecd22c2dadcd07d9475ebe3 5510536 glib2.0_2.80.0.orig.tar.xz
 0664da84c5471dcbef9dae4f7d03f540 178288 glib2.0_2.80.0-6ubuntu3.9.debian.tar.xz
Original-Maintainer: Debian GNOME Maintainers <pkg-gnome-maintainers@lists.alioth.debian.org>

-----BEGIN PGP SIGNATURE-----

iQIzBAEBCgAdFiEEf+ebRFcoyOoAQoOeRbznW4QLH2kFAmqoR30ACgkQRbznW4QL
H2nHjQ//S+/6C+04IUip0WeGDZCoPXCv47yPKQdUfaeUmt43GvVbN0yothz43ssg
/M9fBPcSROBbvWDEe3QzNxLt4fOHXbtQ+hRrUwXcAWFMs/Rxn755Xa0oC0Ys8vCQ
KWTYLr/DnaoeEySxrOHh/PF0E2HZIYYewFH45Ft1WrxA2n8rRcLXZ8n2az+I4QLL
JfgKO1cgP+g7atSD5jFceFyiJoU+mhK/8cf3vvR7bqbA/sWt/IMIT2hDtf+EysHC
Jvrcw9L6OqS5epvJ2ov7396RXAESLZqP6SmUNaxo3pXusloDfHFPvxf+NFqG7WUg
S3DX5NHNorjjz7mpfNI2/Bo+Nz1rIzCstgWZUbWjAv8c5qLNmhNdmGK/ItKRrX14
K5M5mGC22OW+BNndAhkQo0MgbysPAhDO0fXr8Ylm5NR0Wj0WFO7kO0Jd26cc1THg
xO8ExKpyBRuXdiGkF7+og5P55N1w0zPlnZLCqj+3kDnwojc1nUsbjA7WIWSjPrrO
OA0rWQjb4O+HnAHzVHrkd86rDY4VTb8Otn6M56AjtAnkPFc1nNIn+IaHjXV/GV63
TEE8KIc2ostM8oFaFi6j88D6P3paIYlcwEuSKnSiCe6gZJcldy8gbtvZgZCbvuJQ
/mrcacdZ13nwpw4yzI4+DKK96fbwyIcZBu9y0FNTMRVWKuD2nBE=
=DJtv
-----END PGP SIGNATURE-----
