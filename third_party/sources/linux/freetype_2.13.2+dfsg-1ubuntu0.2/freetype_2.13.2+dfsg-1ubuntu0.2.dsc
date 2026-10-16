-----BEGIN PGP SIGNED MESSAGE-----
Hash: SHA512

Format: 3.0 (quilt)
Source: freetype
Binary: libfreetype6, libfreetype-dev, freetype2-demos, freetype2-doc, libfreetype6-udeb
Architecture: any all
Version: 2.13.2+dfsg-1ubuntu0.2
Maintainer: Ubuntu Developers <ubuntu-devel-discuss@lists.ubuntu.com>
Uploaders: Anthony Fok <foka@debian.org>, Keith Packard <keithp@keithp.com>
Homepage: https://freetype.org
Standards-Version: 4.6.2
Vcs-Browser: https://salsa.debian.org/debian/freetype
Vcs-Git: https://salsa.debian.org/debian/freetype.git
Testsuite: autopkgtest
Testsuite-Triggers: build-essential, pkg-config
Build-Depends: debhelper-compat (= 13), autoconf, bzip2, gettext, libbrotli-dev, libbz2-dev, libpng-dev, libtool, libx11-dev <!pkg.freetype.nodemos>, zlib1g-dev | libz-dev, pkg-config, x11proto-core-dev <!pkg.freetype.nodemos>
Package-List:
 freetype2-demos deb utils optional arch=any profile=!pkg.freetype.nodemos
 freetype2-doc deb doc optional arch=all
 libfreetype-dev deb libdevel optional arch=any
 libfreetype6 deb libs optional arch=any
 libfreetype6-udeb udeb debian-installer optional arch=any profile=!noudeb
Checksums-Sha1:
 655c82a431fae7f53a964bda8a7c0671531d05a4 341140 freetype_2.13.2+dfsg.orig-ft2demos.tar.xz
 ca7f1fd515f05b34d41f0438bcce3c0e7559ec67 833 freetype_2.13.2+dfsg.orig-ft2demos.tar.xz.asc
 dbed086b3dba1d748e15b28103081ed30d24e3f3 2173920 freetype_2.13.2+dfsg.orig-ft2docs.tar.xz
 645b5dee18441e95efaa790d2cc14c092f4921e2 833 freetype_2.13.2+dfsg.orig-ft2docs.tar.xz.asc
 f77455e0d78de99ad307ac2ca282cbd32e318316 2220368 freetype_2.13.2+dfsg.orig.tar.xz
 506dc5be5017429a6259445cf67e9c058e9b2680 45236 freetype_2.13.2+dfsg-1ubuntu0.2.debian.tar.xz
Checksums-Sha256:
 99ee2ed8b98bcfad17bc57c2d9699d764f20fe29ad304c69b8eb28834ca3b48e 341140 freetype_2.13.2+dfsg.orig-ft2demos.tar.xz
 e58ba462f7bdcdc5899f777d33453c1ce6f6e46b080047580f45c9fd9f2dc08c 833 freetype_2.13.2+dfsg.orig-ft2demos.tar.xz.asc
 685c25e1035a5076e5097186b3143b9c06878f3f9087d0a81e4d8538d5d15424 2173920 freetype_2.13.2+dfsg.orig-ft2docs.tar.xz
 d7e17c8a3bce50181530ebe06346f506cbfc92ecc5ca7cc395c7dbb24a71a5c0 833 freetype_2.13.2+dfsg.orig-ft2docs.tar.xz.asc
 48c78a4194adfcd15a4d089f3206dab8454c311f5577f3ef7eaef95f777f86e6 2220368 freetype_2.13.2+dfsg.orig.tar.xz
 9d0624fe997a7574250dfac286275dc5469b49bdc7a4fe5814c1ca35110dcb5e 45236 freetype_2.13.2+dfsg-1ubuntu0.2.debian.tar.xz
Files:
 e11243fb7828d2f151409720735cc451 341140 freetype_2.13.2+dfsg.orig-ft2demos.tar.xz
 c7f036af01a616f2fb2ec7e514048bae 833 freetype_2.13.2+dfsg.orig-ft2demos.tar.xz.asc
 e6466f08934ebf2d7f711b0464d7a6cf 2173920 freetype_2.13.2+dfsg.orig-ft2docs.tar.xz
 0a164c49b6e43db4d5b9b7b73dd2a5e7 833 freetype_2.13.2+dfsg.orig-ft2docs.tar.xz.asc
 7d938e51320c4cf50e2203d0c325d925 2220368 freetype_2.13.2+dfsg.orig.tar.xz
 b40426053399384b2e0a0308e003ab8b 45236 freetype_2.13.2+dfsg-1ubuntu0.2.debian.tar.xz
Original-Maintainer: Hugh McMaster <hmc@debian.org>

-----BEGIN PGP SIGNATURE-----

iQIzBAEBCgAdFiEEUMSg3c8x5FLOsZtRZWnYVadEvpMFAmrDwQ0ACgkQZWnYVadE
vpMIlhAAno9/Xm7Kf3PW+2H8PDcs0kxijoMz7pWFTX6vtbLo2aOWOSqd0Osdze6O
n7Q1AKMAvhQWd7P4DywvkxCcEHQw8mycvFHfML5nbqAOCos+MhrYalNC3IlfYRaD
p7/IsVmymPv3x4yPwfwA95v9WsX31LlgMCE8YAE3zevC1NIWQ/VR1ZQ8LcvXOUIR
B8SsKSJAQaSnso0f/W0r16wFJJVeenXAQ5KrvnB+0QF9ZNgha/fUttpeCqJs25lx
TU8s7WV/LamJGXnbKvE4jy7iGa6RVbKOpDMf4rXeYteBY2NlIasGzZoJo4/O30jt
lNR9hiltMzWJ+Qz6qTKwix2HYC7AxfpF2cA7lPOFvFWFNxRhobZE6VhUmKfHZKc8
P697woG0/Fe5+dxl2hjcS+HTdrZicY7cnoOa4O4VdFHA1BIaOPC7g0NX9ldt96EJ
+bhcOrs7tNl8vpefNhwnTZGSc+drkQ8qormbLSwGydj9kPVX3S+/ouVS6FoJrWmF
wJ7o1YhIVBtevgHuliCXwgBUQJogfSLmfX11i3IUyyQH6SWSemabVmt9A74MYPMf
B1oW0AdC+j4g2O0dzLDmEULYDCjW5/w9gd13uvAe0SnUbtmC3hBbSahgb1fUCTlQ
6ddzYv6dmuJ0otnPXdcYLXAtyKeb9KNvHrBt/3W9wB6zxwruLxE=
=GITZ
-----END PGP SIGNATURE-----
