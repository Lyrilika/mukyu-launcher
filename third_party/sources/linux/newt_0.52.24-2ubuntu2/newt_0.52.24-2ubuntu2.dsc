-----BEGIN PGP SIGNED MESSAGE-----
Hash: SHA512

Format: 3.0 (quilt)
Source: newt
Binary: libnewt-dev, libnewt-pic, libnewt0.52-udeb, newt-tcl, python3-newt, libnewt0.52, whiptail
Architecture: any
Version: 0.52.24-2ubuntu2
Maintainer: Ubuntu Developers <ubuntu-devel-discuss@lists.ubuntu.com>
Homepage: https://pagure.io/newt
Standards-Version: 4.6.2
Vcs-Browser: https://salsa.debian.org:/mckinstry/newt.git
Vcs-Git: https://salsa.debian.org:/mckinstry/newt.git -b debian/latest
Build-Depends: debhelper-compat (= 13), docbook-utils, automake (>= 1.16), libslang2-dev (>= 2.0.4-2), libpopt-dev, gettext, libfribidi-dev, tcl8.6-dev, dh-sequence-python3 <!nopython>, python3-all-dev:any <!nopython>, python3-all-dbg:any <!nopython>, libpython3-all-dev <!nopython>, libpython3-all-dbg <!nopython>
Package-List:
 libnewt-dev deb libdevel optional arch=any
 libnewt-pic deb libdevel optional arch=any
 libnewt0.52 deb libs optional arch=any
 libnewt0.52-udeb udeb debian-installer optional arch=any
 newt-tcl deb interpreters optional arch=any
 python3-newt deb python optional arch=any profile=!nopython
 whiptail deb utils optional arch=any
Checksums-Sha1:
 ec2263cac2c9dc995f1e629192c7aeb46e174d84 141424 newt_0.52.24.orig.tar.xz
 cce1765d7a682d2c7c095493eb488d6aae0adcc4 42196 newt_0.52.24-2ubuntu2.debian.tar.xz
Checksums-Sha256:
 e5b21c09874abc0115af38cf1fbe3172985b8340b184dbdd8b11796e71e6e28d 141424 newt_0.52.24.orig.tar.xz
 14c57919f43ebfa73bc5c269907577aa93b1d6ac636d44cbdc76c443d402fe09 42196 newt_0.52.24-2ubuntu2.debian.tar.xz
Files:
 f2dbda3ad31234641fd7f43d9b45764d 141424 newt_0.52.24.orig.tar.xz
 b272c1c2f5a0372e9ed391b9b3b21d36 42196 newt_0.52.24-2ubuntu2.debian.tar.xz
Original-Maintainer: Alastair McKinstry <mckinstry@debian.org>

-----BEGIN PGP SIGNATURE-----

iQJOBAEBCgA4FiEErEg/aN5yj0PyIC/KVo0w8yGyEz0FAmYJGl8aHHN0ZXZlLmxh
bmdhc2VrQHVidW50dS5jb20ACgkQVo0w8yGyEz1NEhAAm73L8UW14lzeGa7Juxdh
U+O1LogI4dTgrFDWmKxrvpo5FNWmEz/r6zvV0iW5+Q7tnoFaUSvvNon/3ZJCBcI1
1L++r//uUDxkwhVbU7+IWsyVxVKqEgwZmlicbNSXzzA9TUDNq96YGHLmJ5QC+s3A
5jeYAEBqzWnPrAx63oLhP0pYsxQPQFVEszS3vQQn9J7dplGg1UxhxVHjpIAM7yTR
68hgc8yVARtWbBK+Ro8VAK8O8nzi2ghDqTJOujZCSGi5sAfUUfMK4BNCpuamYKSy
4TKVdFhJ/E11/q4ENH+Pg/0mhqAKsT3DHMQBqzSpNKruhLqN4Hnm7n00EboXK9w1
/tXoponKiouW+MKXFfwupYb7qZKQ0HHbZ1Zsy+zGtdaRGT3sEMClOBzghpoYSWz9
qmzkEqIbZUZLWcoz4AejNUVTJkd+H8evuYCYW8sMjTW34NXIQMuBsfgNoVhiavj3
wypwutHU+VKSlihZKBJ1QDNXm/Zr3jxgPumqQEzcLEJJDxLGY7J8iQEz1y+Sxloj
rGn0V/OIjT6Q8S7LSgccInIwqANig0XPUkAgSPYvT4Zh4Ttc8vFTbFAM20CnglsJ
AoLuo8cPa98PG7I66vNy0WoSl0Sk2UruAHdI0B6joedgjHQkfaRrsLaivgnx5WDj
5QccHtvVBCZWUxti4W32uN8=
=xxZ6
-----END PGP SIGNATURE-----
