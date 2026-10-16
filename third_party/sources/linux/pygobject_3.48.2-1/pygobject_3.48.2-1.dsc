-----BEGIN PGP SIGNED MESSAGE-----
Hash: SHA512

Format: 3.0 (quilt)
Source: pygobject
Binary: python3-gi, python-gi-dev, python3-gi-cairo
Architecture: any
Version: 3.48.2-1
Maintainer: Debian GNOME Maintainers <pkg-gnome-maintainers@lists.alioth.debian.org>
Uploaders: Iain Lane <laney@debian.org>, Jeremy Bícha <jbicha@ubuntu.com>, Laurent Bigonville <bigon@debian.org>, Sebastien Bacher <seb128@debian.org>
Homepage: https://pygobject.readthedocs.io/
Standards-Version: 4.6.2
Vcs-Browser: https://salsa.debian.org/gnome-team/pygobject
Vcs-Git: https://salsa.debian.org/gnome-team/pygobject.git
Testsuite: autopkgtest
Testsuite-Triggers: build-essential, gir1.2-glib-2.0, python3-all, python3-all-dbg, python3-all-dev, python3-dev
Build-Depends: at-spi2-core <!nocheck>, dbus-daemon <!nocheck>, debhelper-compat (= 13), dh-sequence-python3, gir1.2-gtk-3.0 <!nocheck>, gir1.2-girepository-2.0 <!nocheck>, libcairo2-dev, libffi-dev (>= 3.3), libgirepository1.0-dev (>= 1.64.0~), libglib2.0-dev (>= 2.64.0), locales <!nocheck>, meson, python3-all-dev, python3-cairo-dev (>= 1.16.0), python3-flake8 <!nocheck>, python3-pytest <!nocheck>, python3-setuptools, xauth <!nocheck>, xvfb <!nocheck>
Package-List:
 python-gi-dev deb python optional arch=any
 python3-gi deb python optional arch=any
 python3-gi-cairo deb python optional arch=any
Checksums-Sha1:
 6265ec360141872dcc907eb590a238cbf33c5a78 556244 pygobject_3.48.2.orig.tar.xz
 4f689eb58aa3bfc4724a6067c996d54f075f6cb1 23512 pygobject_3.48.2-1.debian.tar.xz
Checksums-Sha256:
 0794aeb4a9be31a092ac20621b5f54ec280f9185943d328b105cdae6298ad1a7 556244 pygobject_3.48.2.orig.tar.xz
 bf966176896ff0cc9970b79552a38816b9417a72997c24bba2f5bfd4ac0cf896 23512 pygobject_3.48.2-1.debian.tar.xz
Files:
 fe1cb825adc8a49d1629b97b7d26dffc 556244 pygobject_3.48.2.orig.tar.xz
 dade83948103bc4b861ac9d393d49207 23512 pygobject_3.48.2-1.debian.tar.xz

-----BEGIN PGP SIGNATURE-----

iQIzBAEBCgAdFiEETQvhLw5HdtiqzpaW5mx3Wuv+bH0FAmYRKPoACgkQ5mx3Wuv+
bH30hQ//XNuAAvl5t/+/VfUMeQ4uWZcpDV0m8Kz4+F8LCnn3JyGwukSiMKfJAvD3
Y9pVUndxa4jHe2oy1IhI9eLA8I91S6dKYp4izUyovwxyk7Jgw/IBbafuuDPjuc8G
J40OUyU3aLXCoCjpBPrqWqqk7CKWWjtLCR7j21awcppAE5zsZy1qM3cbJRfCDRca
umjulyml/xMyqip7gDyQIVUh3QAJnnyu14wQ2bNZpHv4cgcQ1djbxlRecW8D6HEJ
NbBoeteaC+Ih0bGYuTP8vhmfYM1ifhMl9P2hKkR0sUwiF6lPVFIpHzpKRoKPRsOS
aUDRlPbbRF5vas0o31wMtXQoD/6xgtxkE28Vim4iGiqGAvcKTdJwdLxDP3pRvUr6
EJdzmhJBUI3eyi/A5FG/jqZJ4PaQ0aR9UAGT0lKbGvNyHPHXoVehyj5KL+bZZYag
4CsVYTy9ZzoUgjT4+W3eoIugwlZ53QE6heLQtv4s7QkvBIAiZLwCxgy8R7n7MCVm
8NS6ZH3YQT2jZU/3kBi5WitsCh9MUzi4Cf1TZf2pxAuiEXb/5dWeJOvLi8kRsIDf
l7XQG8T7uepwx/sxvXruwSRW7hnKvslCI5sJtbK4J4S2Y7R6TCyiqF7swoCoINrb
eJf5BWWjkhJkQm7TqBY7PrwjRGxu1/Xzb205/yLsi7SKrqVwMIY=
=N5Dq
-----END PGP SIGNATURE-----
