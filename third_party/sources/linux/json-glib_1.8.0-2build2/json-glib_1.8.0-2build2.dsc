-----BEGIN PGP SIGNED MESSAGE-----
Hash: SHA512

Format: 3.0 (quilt)
Source: json-glib
Binary: libjson-glib-1.0-0, libjson-glib-dev, libjson-glib-1.0-common, libjson-glib-doc, gir1.2-json-1.0, json-glib-tools
Architecture: any all
Version: 1.8.0-2build2
Maintainer: Ubuntu Developers <ubuntu-devel-discuss@lists.ubuntu.com>
Uploaders: Iain Lane <laney@debian.org>, Jeremy Bícha <jbicha@ubuntu.com>, Laurent Bigonville <bigon@debian.org>, Michael Biebl <biebl@debian.org>
Homepage: https://wiki.gnome.org/Projects/JsonGlib
Standards-Version: 4.6.2
Vcs-Browser: https://salsa.debian.org/gnome-team/json-glib
Vcs-Git: https://salsa.debian.org/gnome-team/json-glib.git
Testsuite: autopkgtest
Testsuite-Triggers: build-essential, gnome-desktop-testing
Build-Depends: debhelper-compat (= 13), dh-sequence-gir, dh-sequence-gnome, gi-docgen, gir1.2-glib-2.0 (>= 0.9.12), gtk-doc-tools (>= 1.20), libgirepository1.0-dev (>= 0.9.12), libglib2.0-dev (>= 2.54.0), meson (>= 0.55.3), python3-jinja2, python3-toml, python3-typogrify, xsltproc
Build-Depends-Indep: libglib2.0-doc <!nodoc>
Package-List:
 gir1.2-json-1.0 deb introspection optional arch=any
 json-glib-tools deb devel optional arch=any
 libjson-glib-1.0-0 deb libs optional arch=any
 libjson-glib-1.0-common deb libs optional arch=all
 libjson-glib-dev deb libdevel optional arch=any
 libjson-glib-doc deb doc optional arch=all profile=!nodoc
Checksums-Sha1:
 f03be83e1ded3ac21df25921699583fd212e291e 157300 json-glib_1.8.0.orig.tar.xz
 dfa410b8f3c7c0e904d796bb3effdee0a0c514e6 9200 json-glib_1.8.0-2build2.debian.tar.xz
Checksums-Sha256:
 97ef5eb92ca811039ad50a65f06633f1aae64792789307be7170795d8b319454 157300 json-glib_1.8.0.orig.tar.xz
 a523c9ffb1cfbf21f26e495a09e966819a947291291e45248df39a0f1b973177 9200 json-glib_1.8.0-2build2.debian.tar.xz
Files:
 f1aac2b8a17fd68646653cc4d8426486 157300 json-glib_1.8.0.orig.tar.xz
 5a3ad5365df8facfc8ddd43f1c0e0a76 9200 json-glib_1.8.0-2build2.debian.tar.xz
Original-Maintainer: Debian GNOME Maintainers <pkg-gnome-maintainers@lists.alioth.debian.org>

-----BEGIN PGP SIGNATURE-----

iQJOBAEBCgA4FiEErEg/aN5yj0PyIC/KVo0w8yGyEz0FAmYIu+0aHHN0ZXZlLmxh
bmdhc2VrQHVidW50dS5jb20ACgkQVo0w8yGyEz1bjBAAvb2bqhWGIWceN+93PFwT
2L7dQESgxxrchEYRt2X07RjFrmh0yR8i/r+Jbi2iFCh6Y/HKVXI3iNvznw1PcaJV
QPuxtoz3TOaehaJrmHPXtHUkXgLlFFrKZdCRCuptsLx2h98B+FFG/Ne5mKhDHlgM
dyNDsQ5NBS5e/S6gt3SW791CzGS3CmNg+7YyNRKMjlQd/gwQwUZA18wBR6qVxCGs
0lRMoTAtwN1j+g9r1Mw+sS+QgMHQogfxz9Lrmah0ZHzg0VTs3qjT/CaKVkpbHt65
IsZYMKE6nm18crAUOxhdDuR0UG2JukHx2W5mnk2vO0twCzQEX7a6ehVlUqUC8j3p
CQtoVwoxGwlM+iHrZ0pLl826HvuTm2EZlAEAzvktiMAwyZTOA7DKIJ+b8OLYutaE
o65Rxg2JpKH6KafYNO9WmTSA1ik9wmIi3q2F4E7c1Q3dXGnz7FUz/bW23Fv2pgNK
0GV8THV0oPnxxajL/xk+kfhJHxSdHkG5QuoalH87UjVX7ormzWaxAile4/1CbMMQ
FwMlr4xBKSK8PlMnAQb897slHIPB/Mf+slJqmuXDHMcwl7m1HubuJ5puZ3gjWkIt
4EuYQm+AM86sf462IdIJOUxNp5KjT6HGnWmEmkRYl1ZT9ILxPYYOXuYCm4nNgVm+
8sQp4+Brq415R6NCXvUtaz4=
=GG7w
-----END PGP SIGNATURE-----
