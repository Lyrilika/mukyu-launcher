-----BEGIN PGP SIGNED MESSAGE-----
Hash: SHA512

Format: 3.0 (quilt)
Source: pipewire
Binary: libpipewire-0.3-0t64, libpipewire-0.3-common, libpipewire-0.3-dev, libpipewire-0.3-modules, libpipewire-0.3-modules-x11, libspa-0.2-dev, libspa-0.2-modules, pipewire-doc, pipewire, pipewire-bin, pipewire-pulse, pipewire-alsa, pipewire-jack, pipewire-v4l2, pipewire-tests, gstreamer1.0-pipewire, libspa-0.2-bluetooth, libspa-0.2-jack, libspa-0.2-libcamera, pipewire-audio-client-libraries, pipewire-audio, pipewire-libcamera
Architecture: any all
Version: 1.0.5-1ubuntu3.3
Maintainer: Ubuntu Developers <ubuntu-devel-discuss@lists.ubuntu.com>
Uploaders: Jeremy Bicha <jbicha@debian.org>, Dylan Aïssi <daissi@debian.org>
Homepage: https://pipewire.org/
Standards-Version: 4.6.2
Vcs-Browser: https://salsa.debian.org/utopia-team/pipewire
Vcs-Git: https://salsa.debian.org/utopia-team/pipewire.git
Testsuite: autopkgtest
Testsuite-Triggers: build-essential, gnome-desktop-testing, gstreamer1.0-tools, pkg-config
Build-Depends: dpkg-dev (>= 1.22.5), debhelper-compat (= 13), doxygen <!nodoc>, graphviz <!nodoc>, libapparmor-dev [linux-any], libasound2-dev, libavahi-client-dev, libbluetooth-dev [linux-any], libcamera-dev (>= 0.2.0) [!m68k !hurd-any], libdbus-1-dev, libffado-dev, libfreeaptx-dev, libglib2.0-dev, libgstreamer-plugins-base1.0-dev, libgstreamer1.0-dev, libjack-jackd2-dev, libcanberra-dev, liblc3-dev, libldacbt-abr-dev [!s390x !hppa !m68k !powerpc !ppc64 !sparc64], libldacbt-enc-dev [!s390x !hppa !m68k !powerpc !ppc64 !sparc64], liblilv-dev, libmysofa-dev, libncurses-dev, libopus-dev, libpulse-dev, libreadline-dev, libroc-dev (>= 0.3.0+dfsg-3), libsbc-dev, libsdl2-dev <!noinsttest>, libsnapd-glib-dev [amd64 arm64 armhf i386 powerpc ppc64el riscv64 s390x], libsndfile1-dev, libssl-dev, libsystemd-dev [linux-any], libudev-dev [linux-any], libusb-1.0-0-dev, libv4l-dev, libwebrtc-audio-processing-dev, libxfixes-dev (>= 1:6.0.0), meson (>= 0.61.1), modemmanager-dev, pkgconf, python3-docutils, systemd-dev
Build-Conflicts: libfdk-aac-dev
Package-List:
 gstreamer1.0-pipewire deb libs optional arch=any
 libpipewire-0.3-0t64 deb libs optional arch=any
 libpipewire-0.3-common deb libs optional arch=all
 libpipewire-0.3-dev deb libdevel optional arch=any
 libpipewire-0.3-modules deb libs optional arch=any
 libpipewire-0.3-modules-x11 deb libs optional arch=any
 libspa-0.2-bluetooth deb libs optional arch=any
 libspa-0.2-dev deb libdevel optional arch=any
 libspa-0.2-jack deb libs optional arch=any
 libspa-0.2-libcamera deb video optional arch=amd64,arm64,armel,armhf,i386,mips64el,mipsel,ppc64el,s390x,alpha,hppa,ia64,powerpc,ppc64,riscv64,sh4,sparc64,x32
 libspa-0.2-modules deb libs optional arch=any
 pipewire deb video optional arch=any
 pipewire-alsa deb sound optional arch=any
 pipewire-audio deb sound optional arch=all
 pipewire-audio-client-libraries deb oldlibs optional arch=all
 pipewire-bin deb video optional arch=any
 pipewire-doc deb doc optional arch=all profile=!nodoc
 pipewire-jack deb sound optional arch=any
 pipewire-libcamera deb oldlibs optional arch=all
 pipewire-pulse deb sound optional arch=any
 pipewire-tests deb misc optional arch=any profile=!noinsttest
 pipewire-v4l2 deb video optional arch=any
Checksums-Sha1:
 c0fd0549f7908586ea8ee59b3e3f6cadb31e54e3 1698291 pipewire_1.0.5.orig.tar.bz2
 54bad05ea820fc2bd2e5db75bb67494a9d03b8eb 51808 pipewire_1.0.5-1ubuntu3.3.debian.tar.xz
Checksums-Sha256:
 d5e5f3d0b8460e5711c1571c500156fd61768ba55a062eaeb94356abdb955a56 1698291 pipewire_1.0.5.orig.tar.bz2
 a1650f8e95859b3a8057ea95dad7e0509bfed9896db5b0d17c70910c4e9a3ff0 51808 pipewire_1.0.5-1ubuntu3.3.debian.tar.xz
Files:
 c60c630dd31d0213a78bcebf06dfc6ed 1698291 pipewire_1.0.5.orig.tar.bz2
 6a07798868cab30ab1d8d147bcfc2865 51808 pipewire_1.0.5-1ubuntu3.3.debian.tar.xz
Original-Maintainer: Utopia Maintenance Team <pkg-utopia-maintainers@alioth-lists.debian.net>

-----BEGIN PGP SIGNATURE-----

iQJPBAEBCgA5FiEEuEg4xBTSeUWY0Nx77tH0LvjAvecFAmpO57obHGt5bGUua2Vy
bmlja0BjYW5vbmljYWwuY29tAAoJEO7R9C74wL3nx1YP/RXNnljFFj0HFXboy4pF
H/EXv98EO2i3skOUnfZ8stl8vgi6s8vAMf4a0292RipTb8/OgU5dqnvhl2O0zGDT
Bk6HSyVKT9VJHTtoSZL22Ncs8C3rj1bNXqlxJB9/8z7h/7tHCc65vn91mnLc/VkM
D60gUHzZ5BFOL4wT/Nx7ujo+l8/G5Rnet6xzZBh1fCKeWXICs/B09cOlrAgoO76j
+0xNzRb81XgKk5axp+z1o3msfEBZH48TpLRbAYwRwKnp49c4QBoTRRIX2+P9IAcB
tb/ASajTmMZMZV4T9h+YU0fRdpSiw2F2ADKy+6Um+KbtoqknuVN3fE7w3pCbW58H
E8fViVx96iF74zWzupub/C8HoQHUFDGqkdQaIu3AB2R3Jv75Tj+o0OL6NL21+sqW
v35Gv7anKg8KZV1FzwTpsl/cs5+8Ra/ZIhEIAyU6SFx7wE9GjNmPlwddeoivsTGa
7V0jXYe63O5zhW10kRSDSi38EH3AG222dB7iddgNunvU6eha42UB3c+NJx2cioqC
+ilFnnT18jdctlRtIBNT+TqzCRZksjxT/QL6R7+jM3U986vjkGbVuXM/Qbrb5ivZ
Ackg3v2IbUN5+7TlNq+2tzEDt/+XXU846th+xW22yMh/KYqnsTIbtKxcDvIMdpsC
CkjPzbJafCZ1ojdDI7qwtPz4
=c6yv
-----END PGP SIGNATURE-----
