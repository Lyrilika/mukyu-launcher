-----BEGIN PGP SIGNED MESSAGE-----
Hash: SHA512

Format: 3.0 (quilt)
Source: glib-networking
Binary: glib-networking, glib-networking-services, glib-networking-common, glib-networking-tests
Architecture: any all
Version: 2.80.0-1build1
Maintainer: Ubuntu Developers <ubuntu-devel-discuss@lists.ubuntu.com>
Uploaders: Iain Lane <laney@debian.org>, Jeremy Bícha <jbicha@ubuntu.com>
Standards-Version: 4.6.2
Vcs-Browser: https://salsa.debian.org/gnome-team/glib-networking
Vcs-Git: https://salsa.debian.org/gnome-team/glib-networking.git
Testsuite: autopkgtest
Testsuite-Triggers: dbus, gnome-desktop-testing, xauth, xvfb
Build-Depends: debhelper-compat (= 13), dh-sequence-gnome, meson (>= 0.60.0), libglib2.0-dev (>= 2.73.3), libgnutls28-dev (>= 3.7.4), libproxy-dev (>= 0.5), gsettings-desktop-schemas-dev, ca-certificates
Package-List:
 glib-networking deb libs optional arch=any
 glib-networking-common deb libs optional arch=all
 glib-networking-services deb libs optional arch=any
 glib-networking-tests deb misc optional arch=any
Checksums-Sha1:
 746f00f1601818ba670366c90f9511c8babec90a 287044 glib-networking_2.80.0.orig.tar.xz
 2c28b2d5485b0c744f57d8a91a2acf93c2628536 12480 glib-networking_2.80.0-1build1.debian.tar.xz
Checksums-Sha256:
 d8f4f1aab213179ae3351617b59dab5de6bcc9e785021eee178998ebd4bb3acf 287044 glib-networking_2.80.0.orig.tar.xz
 747ba889a1d2811195faddbb27921272a0fafde44b13e03ad4987e167ba0fab8 12480 glib-networking_2.80.0-1build1.debian.tar.xz
Files:
 8e13b80148e28adc9e4cf681c0b30402 287044 glib-networking_2.80.0.orig.tar.xz
 e12c25a3a01811516daf5b4decd491f1 12480 glib-networking_2.80.0-1build1.debian.tar.xz
Original-Maintainer: Debian GNOME Maintainers <pkg-gnome-maintainers@lists.alioth.debian.org>

-----BEGIN PGP SIGNATURE-----

iQJOBAEBCgA4FiEErEg/aN5yj0PyIC/KVo0w8yGyEz0FAmYI+yoaHHN0ZXZlLmxh
bmdhc2VrQHVidW50dS5jb20ACgkQVo0w8yGyEz3oMw//QhHmSTAKe+IKlJp847/i
JUyfmfKscnYrdTyGRdyNfOMVK2q5A2oEty/+6dOHNM4fwBl+pTyl+nRgB4zbCLIW
QBOmvSe06xlua26w5lmzqiRpG7C+b0ZOoIbVmMGfAtbY8Xy8Y6DF0OTfAh49me4m
vPhKQ49Y+mf80nBQz+NWWqMgbUHQOmi3bruYAb2Z2DfBEyO/u8QkU0sjDSr/0yBx
kkl9AlPlgLVPBuyK3IWKJ28LzDRQg/FRWqR/Q/IoK7RbgRrSD0i3ZiR1vw6qnXZT
WXbNXSUXG/Y/d8ZIq+G9EJGLuaCIe7PBH2AHaDpzTx53JHDrnYp0OtEWv0f7L7uf
c6s87x4VPOGqgSUk4OTsA+S5G+mKQyOAtuEo/lIbQGEylK6l49lIgsC6p0Yh6Jul
lAdLb8+laBHbaDjvtcjfSdbzfCXjSnDvFRpAr2PfJ53DQR6THe/D4xYvSDAGCNxk
FOR5KZTFsbYo2GhkpHEqqDOXUJfS1CRyVJgKzlwWsbX34zYx45Aual5gP6tWL9So
jQawiGMPu9A9yazlPTzy96DATubASxO0gx6Rg72TWQB0xwvTO+rWwPMdPPaExGIC
/9XwJdEZh9RzFiKSBiorwDF0GxwNMLN88zP3PLZu6klEW1tAXzZ2/OVokEQUkOLc
+4HyAH3BlWkPKNqs82bbvc0=
=uUcY
-----END PGP SIGNATURE-----
