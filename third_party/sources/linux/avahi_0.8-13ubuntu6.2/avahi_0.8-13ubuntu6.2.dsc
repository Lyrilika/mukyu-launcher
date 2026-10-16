-----BEGIN PGP SIGNED MESSAGE-----
Hash: SHA256

Format: 3.0 (quilt)
Source: avahi
Binary: avahi-daemon, avahi-dnsconfd, avahi-autoipd, python3-avahi, avahi-utils, avahi-discover, libavahi-common3, libavahi-common-data, libavahi-common-dev, libavahi-core7, libavahi-core-dev, libavahi-client3, libavahi-client-dev, libavahi-glib1, libavahi-glib-dev, libavahi-gobject0, libavahi-gobject-dev, libavahi-compat-libdnssd1, libavahi-compat-libdnssd-dev, libavahi-ui-gtk3-0, libavahi-ui-gtk3-dev, avahi-ui-utils, gir1.2-avahi-0.6
Architecture: any all
Version: 0.8-13ubuntu6.2
Maintainer: Ubuntu Developers <ubuntu-devel-discuss@lists.ubuntu.com>
Uploaders: Sjoerd Simons <sjoerd@debian.org>, Sebastian Dröge <slomo@debian.org>, Loic Minier <lool@dooz.org>, Michael Biebl <biebl@debian.org>
Homepage: https://avahi.org/
Standards-Version: 4.6.2
Vcs-Browser: https://salsa.debian.org/utopia-team/avahi
Vcs-Git: https://salsa.debian.org/utopia-team/avahi.git
Testsuite: autopkgtest
Testsuite-Triggers: build-essential, pkgconf
Build-Depends: debhelper (>= 13.11.6~), debhelper-compat (= 13), dh-sequence-gir <!nogir>, dh-sequence-python3, intltool, libcap-dev [linux-any], libdaemon-dev, libdbus-1-dev, libexpat-dev, libgdbm-dev, libgirepository1.0-dev <!nogir>, libglib2.0-dev, libgtk-3-dev <!pkg.avahi.nogui>, pkgconf, python-gi-dev <!nopython>, python3, python3-dbus <!nopython>, python3-gdbm, python3-gi <!nopython>, xmltoman
Package-List:
 avahi-autoipd deb net optional arch=linux-any
 avahi-daemon deb net optional arch=any
 avahi-discover deb net optional arch=all profile=!nopython,!pkg.avahi.nogui
 avahi-dnsconfd deb net optional arch=any
 avahi-ui-utils deb utils optional arch=any profile=!pkg.avahi.nogui
 avahi-utils deb net optional arch=any
 gir1.2-avahi-0.6 deb introspection optional arch=any profile=!nogir
 libavahi-client-dev deb libdevel optional arch=any
 libavahi-client3 deb libs optional arch=any
 libavahi-common-data deb libs optional arch=any
 libavahi-common-dev deb libdevel optional arch=any
 libavahi-common3 deb libs optional arch=any
 libavahi-compat-libdnssd-dev deb libdevel optional arch=any
 libavahi-compat-libdnssd1 deb libs optional arch=any
 libavahi-core-dev deb libdevel optional arch=any
 libavahi-core7 deb libs optional arch=any
 libavahi-glib-dev deb libdevel optional arch=any
 libavahi-glib1 deb libs optional arch=any
 libavahi-gobject-dev deb libdevel optional arch=any profile=!nogir
 libavahi-gobject0 deb libs optional arch=any
 libavahi-ui-gtk3-0 deb libs optional arch=any profile=!pkg.avahi.nogui
 libavahi-ui-gtk3-dev deb libdevel optional arch=any profile=!pkg.avahi.nogui
 python3-avahi deb python optional arch=any profile=!nopython
Checksums-Sha1:
 969a50ae18c8d8e2288435a75666dd076e69852a 1591458 avahi_0.8.orig.tar.gz
 528e90c297c00225bc44b9c105f729a826cf37c4 52976 avahi_0.8-13ubuntu6.2.debian.tar.xz
Checksums-Sha256:
 060309d7a333d38d951bc27598c677af1796934dbd98e1024e7ad8de798fedda 1591458 avahi_0.8.orig.tar.gz
 2504d0970d1d599750b437bfd614e2fd587a40a20de686beb39d0db5e1ae62c9 52976 avahi_0.8-13ubuntu6.2.debian.tar.xz
Files:
 229c6aa30674fc43c202b22c5f8c2be7 1591458 avahi_0.8.orig.tar.gz
 a85815d384fcdd8175fcf30702d52117 52976 avahi_0.8-13ubuntu6.2.debian.tar.xz
Original-Maintainer: Utopia Maintenance Team <pkg-utopia-maintainers@lists.alioth.debian.org>

-----BEGIN PGP SIGNATURE-----

iQJqBAEBCABUFiEEhC9y9XdAFQPCvYXchGmXSGiknnUFAmn7NogbFIAAAAAABAAO
bWFudTIsMi41KzEuMTIsMCwyGhxhbGxlbi5odWFuZ0BjYW5vbmljYWwuY29tAAoJ
EIRpl0hopJ51ojUP/2s2haVACW3+CRgDa6UUR1h4cT+j6qjJEdZZVMLhkKTu9JM1
S0ORchPYWeoelMOSVgh4QaW8mQBi16aHFmxBIyFQbj8vEmJRxgkDZPM3F6+2Rcdl
0HGNs8uhs9iiQDvibrRhZlb0M2tjs5uCgmDekmvgbKeGCuSLwq2KEEGSR8wqcsMa
3uTSal/XVj1EmErwCZijCGvVBL28O5GnpZKpPVGoGnhoQTlwwaYVpedbTGk4uwQU
DEtizVrLSOjuiHjf/qzQF6aY/J7Vk3vsPEyImPhydC/SPhy1L1RZS6ldAXynv9bv
wIee3zQzUz0mES+m1bTcIorK5LnY0lM3jEKh3c+5VYMuBZZVjJMNi6Wb9uD34z9Q
vHViyhxwlyfQpK3zgBfeRPm7AtKExIJcWcYikQvk+ELA9KLigdxseJft2g2lpa3C
evR4z/0Iyn+8Uy0q2viytINSiS9004gMjRd9q7fsv1zSJL0ELX2vXFQUtdfvPra/
DR2R5y049j1n/Few0DfxEjGXo3RRn/vOGYb/mwSXpRl+REqA23lRCJH0vcAbpyZ0
LKdTQo3YfvRIoXNjWOUThv/H2+L3UQrMnPPr5LOMrLu6Zd8LXCQJ7PRbn5eN+JQ9
nNqawwcRCv0lUBw2uXjYAgZWaVHz2TH6x1a/7+jcFoJDEmTPjOOdBiLPb8Fq
=dPyW
-----END PGP SIGNATURE-----
