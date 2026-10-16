-----BEGIN PGP SIGNED MESSAGE-----
Hash: SHA512

Format: 3.0 (quilt)
Source: cryptsetup
Binary: cryptsetup, cryptsetup-bin, cryptsetup-ssh, cryptsetup-initramfs, cryptsetup-suspend, libcryptsetup12, libcryptsetup-dev, cryptsetup-udeb, libcryptsetup12-udeb
Architecture: linux-any all
Version: 2:2.7.0-1ubuntu4.2
Maintainer: Ubuntu Developers <ubuntu-devel-discuss@lists.ubuntu.com>
Uploaders: Jonas Meurer <jonas@freesources.org>, Guilhem Moulin <guilhem@debian.org>
Homepage: https://gitlab.com/cryptsetup/cryptsetup
Standards-Version: 4.6.2
Vcs-Browser: https://salsa.debian.org/cryptsetup-team/cryptsetup
Vcs-Git: https://salsa.debian.org/cryptsetup-team/cryptsetup.git -b debian/latest
Testsuite: autopkgtest
Testsuite-Triggers: bsdextrautils, btrfs-progs, dmsetup, dosfstools, e2fsprogs, expect, fdisk, gcc, genext2fs, initramfs-tools-core, jq, keyutils, kmod, libdevmapper-dev, libjson-perl, linux-image-686-pae, linux-image-amd64, linux-image-arm64, linux-image-armmp-lpae, linux-image-generic, lvm2, mdadm, netcat-openbsd, openssh-client, openssh-server, openssl, procps, qemu-efi-aarch64, qemu-efi-arm, qemu-system, qemu-system-arm, qemu-system-x86, sharutils, sshpass, udev, xxd, zstd
Build-Depends: asciidoctor <!nodoc>, autoconf, automake (>= 1:1.12), autopoint, debhelper-compat (= 13), dh-strip-nondeterminism, docbook-xml <!nodoc>, docbook-xsl <!nodoc>, gettext, jq <!nocheck>, libargon2-dev, libblkid-dev, libdevmapper-dev, libjson-c-dev, libpopt-dev, libselinux1-dev, libsepol-dev, libssh-dev, libssl-dev, libtool, pkgconf, po-debconf, procps <!nocheck>, uuid-dev, xsltproc <!nodoc>, xxd <!nocheck>
Package-List:
 cryptsetup deb admin optional arch=linux-any
 cryptsetup-bin deb admin optional arch=linux-any
 cryptsetup-initramfs deb admin optional arch=all
 cryptsetup-ssh deb admin optional arch=linux-any
 cryptsetup-suspend deb admin optional arch=amd64,arm64,armhf,ppc64el,riscv64,s390x
 cryptsetup-udeb udeb debian-installer optional arch=linux-any profile=!noudeb
 libcryptsetup-dev deb libdevel optional arch=linux-any
 libcryptsetup12 deb libs optional arch=linux-any
 libcryptsetup12-udeb udeb debian-installer optional arch=linux-any profile=!noudeb
Checksums-Sha1:
 f8d47320dae75ad194e4089d8a28d308b1eda208 11754085 cryptsetup_2.7.0.orig.tar.gz
 4a5f90a47c7f22de235cc83e18a3f7571de880f7 169908 cryptsetup_2.7.0-1ubuntu4.2.debian.tar.xz
Checksums-Sha256:
 f0d490f2eb32d1648d586d56fab1329666d34e69e0db3bd6f0ac16fb3de816a2 11754085 cryptsetup_2.7.0.orig.tar.gz
 f219b25303b8f934780c6f348c71387ddc1597906d3b7fe5960f1678a5b8098a 169908 cryptsetup_2.7.0-1ubuntu4.2.debian.tar.xz
Files:
 3f984ff4e595bdfd8b3329a8d35a763d 11754085 cryptsetup_2.7.0.orig.tar.gz
 88105e37eb95d4a3f149b9014b9b3c9d 169908 cryptsetup_2.7.0-1ubuntu4.2.debian.tar.xz
Original-Maintainer: Debian Cryptsetup Team <pkg-cryptsetup-devel@alioth-lists.debian.net>

-----BEGIN PGP SIGNATURE-----

iQIzBAEBCgAdFiEE4qlMxBx1Pex4dJYuxTfgBIBe5lcFAmeaa4gACgkQxTfgBIBe
5leEkQ//Tq5VPSG+nr3UME4Q6hrahBiTV6GYutUkGEEO/+wgUNnjVrwNHuMH2al9
o5Zx9NySuQGy9Fz1PBIkcptUiGHG95yf4INweM0B7WaZt2eywS3D1VPRtBbIV1oN
p2STnlNeXorTqYnqtoPaU+3WWed/2Tx+IAA6Y0CfS7Yu8f7+67rRFy/TwbjNbJji
gX7dC617gqikbItnUKPmZ7Axka1bVHJorq+GGM8N5di0Ky9uTU9KEeJRQxQfvOL7
wcVifuFIZMkdEW6bB/zkPZ08GJc89IalAWAxnL9A9DgLHQ1Hcdh/GgdwqCXzAO/l
l3wJ4HRbROPxzo2l/dQHCaCuBoM8pi+H8NK7k5oLSl89Ll8cloC2YTb+p7PYgwsl
b//pM/n33ezOkORv5X4qupqKv6/2W691IQ5E+GHrw6+MkuDMk6MX3AZLtWFSbK5e
ZR6TBo7RLL34Zig0cOUlkkc9uhXk2m901kh3r5f9Lww28zZYYs+vtq/O940lnrma
1fAgFUSqc2vd4YSHqjRqmBe5HfCi6tX4iCxTli9TUWe4hlre2LcNOeT0OQ5Jrzqi
7XmSSDfipyEfJy0Djz4464VE+VuFG2jKbyLHyCsjgzJee//HbpEdutiLjmbDMIPn
g4T84fAH9AGlQjAeJcjR0tuWUxtrdtJ7rZCjFbfQY03u/AgrhWE=
=Di3n
-----END PGP SIGNATURE-----
