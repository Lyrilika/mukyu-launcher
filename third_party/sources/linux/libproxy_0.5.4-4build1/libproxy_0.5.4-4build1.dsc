-----BEGIN PGP SIGNED MESSAGE-----
Hash: SHA512

Format: 3.0 (quilt)
Source: libproxy
Binary: libproxy1v5, libproxy1-plugin-gsettings, libproxy1-plugin-kconfig, libproxy1-plugin-networkmanager, libproxy1-plugin-webkit, libproxy-dev, libproxy-tools
Architecture: any
Version: 0.5.4-4build1
Maintainer: Ubuntu Developers <ubuntu-devel-discuss@lists.ubuntu.com>
Uploaders: Iain Lane <laney@debian.org>, Jeremy Bícha <jbicha@ubuntu.com>, Laurent Bigonville <bigon@debian.org>
Homepage: https://libproxy.github.io/libproxy/
Standards-Version: 4.6.2
Vcs-Browser: https://salsa.debian.org/gnome-team/libproxy
Vcs-Git: https://salsa.debian.org/gnome-team/libproxy.git
Testsuite: autopkgtest
Testsuite-Triggers: build-essential, gsettings-desktop-schemas, pkg-config
Build-Depends: debhelper-compat (= 13), dh-sequence-gnome, duktape-dev, gsettings-desktop-schemas-dev, meson, netbase <!nocheck>, valac, zlib1g-dev, libnm-dev [linux-any], libcurl4-gnutls-dev, libdbus-1-dev, libkf5config-bin <!nocheck !stage1>, libwebkit2gtk-4.1-dev <!nocheck !stage1>, libjavascriptcoregtk-4.1-dev <!stage1>, libglib2.0-dev (>= 2.26) <!stage1>, libxmu-dev <!nocheck !stage1>
Package-List:
 libproxy-dev deb libdevel optional arch=any
 libproxy-tools deb utils optional arch=any
 libproxy1-plugin-gsettings deb oldlibs optional arch=any
 libproxy1-plugin-kconfig deb oldlibs optional arch=any
 libproxy1-plugin-networkmanager deb oldlibs optional arch=linux-any
 libproxy1-plugin-webkit deb oldlibs optional arch=any
 libproxy1v5 deb libs optional arch=any
Checksums-Sha1:
 0c19d6eb29d3b81fcd12e76e23692940391aa517 60605 libproxy_0.5.4.orig.tar.gz
 55526f8303427270c8b5f08da7238875cff8a98e 15932 libproxy_0.5.4-4build1.debian.tar.xz
Checksums-Sha256:
 a6e2220349b2025de9b6d9d7f8bb347bf0c728f02a921761ad5f9f66c7436de9 60605 libproxy_0.5.4.orig.tar.gz
 d64cf4ebb48bd4aa333527bcfe196d8a95f741415ba928ea9b59d63f27a33790 15932 libproxy_0.5.4-4build1.debian.tar.xz
Files:
 49b7d74fa996eccf0270f4cee9bc9c16 60605 libproxy_0.5.4.orig.tar.gz
 29c0008a6412f5b5a9142949e989be7e 15932 libproxy_0.5.4-4build1.debian.tar.xz
Original-Maintainer: Debian GNOME Maintainers <pkg-gnome-maintainers@lists.alioth.debian.org>

-----BEGIN PGP SIGNATURE-----

iQJOBAEBCgA4FiEErEg/aN5yj0PyIC/KVo0w8yGyEz0FAmYJFyIaHHN0ZXZlLmxh
bmdhc2VrQHVidW50dS5jb20ACgkQVo0w8yGyEz3OORAAiL95GBb5wGp6tK0S5Br3
+bLHgk/VEBm9qjPO+eCMnFim9QILYhwptTWIb6+aOuHxGksx7vclFm5BLctRY+7w
EjnCCGxEoq2uqipMsK4WiJ2kZ4aexDXsMAYNzmoggtTfLZJ+K4kKZmUAH/EarrMr
xpe67hmBib+6mXL8Xv4tJdfRcu78l+cBKwA1PRBVCoONVKhUnHvJgVMbF+U0xtPZ
jMSOtInWn7cDagjig2W8gto4HPG75TGaJLAXnG66IlVgs15rL4dPleZZz91Ruxtp
OhzK5/DSWy7YKOlpBicTqVA2AT4gym8rfzgq3F3HOs3XFXeLGJxN76n1vKHx8kTc
K3TN16j9hgWpz8xY7Bdz1KXFBDgcz46EMYtj2VGqCptGP4hME/YTiILzNbqylZns
zJ4oQrc24+rtShYlXqbyt6tdRWY5hQviiaHfvmJgey0zN4ZUiWN3FR1MkNk7U+4c
yLEp0flgafoAhHwQ9MNKl5Smr9vkLn3uYeLHL6dlSKjI1+CYaB6FPXBEWZ6s0mN3
3hygz29jQTBAycHK1L57My94jE/Uy6+Hzlga3i6WL84ZbIrA028Rm98Byu5l9Lvh
/rXrJu8d0rfZdP6O1Pi62KODWgglvIp1f5Z9Mhav5dB/B6C/zyosr9gBTiWP3iKX
mfd/XzqCyl1RHT9Y0htdCXw=
=7WXt
-----END PGP SIGNATURE-----
