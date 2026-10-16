-----BEGIN PGP SIGNED MESSAGE-----
Hash: SHA512

Format: 3.0 (quilt)
Source: kmod
Binary: kmod, libkmod2, libkmod-dev, kmod-udeb, libkmod2-udeb
Architecture: linux-any
Version: 31+20240202-2ubuntu7.2
Maintainer: Ubuntu Developers <ubuntu-devel-discuss@lists.ubuntu.com>
Standards-Version: 4.6.2.0
Vcs-Browser: https://salsa.debian.org/md/kmod
Vcs-Git: https://salsa.debian.org/md/kmod.git
Build-Depends: debhelper-compat (= 13), autoconf, automake, libtool, pkgconf, liblzma-dev (>= 5.4.5-0.2), libssl-dev, libzstd-dev, zstd <!nocheck>, gtk-doc-tools, xsltproc
Package-List:
 kmod deb admin important arch=linux-any
 kmod-udeb udeb debian-installer important arch=linux-any
 libkmod-dev deb libdevel optional arch=linux-any
 libkmod2 deb libs optional arch=linux-any
 libkmod2-udeb udeb debian-installer important arch=linux-any
Checksums-Sha1:
 b593b081f59d0c74cc261063387e28492d12d6f7 253852 kmod_31+20240202.orig.tar.xz
 8c7f881181983a60fe19dcefb3da17fe1b5a343e 15332 kmod_31+20240202-2ubuntu7.2.debian.tar.xz
Checksums-Sha256:
 0b8521d929cc62b7594886c8ed24109a22b96e732fdcc6f0afa486bd62c487bc 253852 kmod_31+20240202.orig.tar.xz
 4025026e9e1feb507c2e98a4ce8c149f835dc4764119a86523aae3b78cd829ac 15332 kmod_31+20240202-2ubuntu7.2.debian.tar.xz
Files:
 cbfd94db609bf63658a839019d65c793 253852 kmod_31+20240202.orig.tar.xz
 4cb5853175a528b23565dcab4cbc2541 15332 kmod_31+20240202-2ubuntu7.2.debian.tar.xz
Original-Maintainer: Marco d'Itri <md@linux.it>

-----BEGIN PGP SIGNATURE-----

iQIzBAEBCgAdFiEEUMSg3c8x5FLOsZtRZWnYVadEvpMFAmnzTmoACgkQZWnYVadE
vpONiw/+PhbPyU1YDpTQbsU9I6fIwOmx9KMNOORCkOzkRPZ3DOIMY3GmLI8DFymf
wStf29h82uMxZhOOihpfYIe7LZXZ75jGndFYbBN2hTlMaQui+PHfUytTVtxA+bjJ
qos8vZ3J+j0UBCTORX/Iw13Yi9KYBq2d5ZvZETq0JtWQfVx+D0c1IZPnnlkkypWl
8EiOKsMAd4lpTcru2AXst6LOacbThxqGAGJ1RPR8IMRcjGuTKYs9sZh8VTbH+bci
fUL7Gcpz08DM8v6S3vHZYz+zSNaqVwnDud6lXJ91A1dhqnbKYjMNOaYUJnj5iUpb
kABuHsUUouyh1hWUDdwVv2VXjBKYfLrirk8k+wDhT1BJunyLBd2REQmcASTOjRXR
FPzgRLugNdjsm21Hqe0IR0jjPNS4gP/Csb9MUzVL47UTEbQOiroFG4/d2tkGHslE
Fds/2LkniosgHVE5VxFbcziNG0oNj9S8hf14pWAh1sDcaG++jRKtLaO8RSaluhQP
BoE25Oz8SYRYvoO78hS18GZHQu9Z/GgN1dL/JbBPGUx3r1gKTTWZOsD8NFtewjJV
xHP/rwI3F/lXFIEQ10FrjmtL2xmz2vkjw0r/s5TGOg8TsBy44dD/BWW2+oKDpLdT
bTHv5ajRlijJJiumq7i8gU6N735a0s63c+/2Z7QOhuldbrRGLr4=
=pWOn
-----END PGP SIGNATURE-----
