-----BEGIN PGP SIGNED MESSAGE-----
Hash: SHA256

Format: 3.0 (quilt)
Source: pulseaudio
Binary: pulseaudio, pulseaudio-utils, pulseaudio-module-zeroconf, pulseaudio-module-jack, pulseaudio-module-lirc, pulseaudio-module-gsettings, pulseaudio-module-raop, pulseaudio-module-bluetooth, pulseaudio-equalizer, libpulse0, libpulse-mainloop-glib0, libpulse-dev
Architecture: any
Version: 1:16.1+dfsg1-2ubuntu10.1
Maintainer: Ubuntu Developers <ubuntu-devel-discuss@lists.ubuntu.com>
Uploaders: Sjoerd Simons <sjoerd@debian.org>, Felipe Sateler <fsateler@debian.org>, Sebastien Bacher <seb128@debian.org>
Homepage: https://www.pulseaudio.org
Standards-Version: 4.6.0
Vcs-Browser: https://salsa.debian.org/pulseaudio-team/pulseaudio
Vcs-Git: https://salsa.debian.org/pulseaudio-team/pulseaudio.git
Testsuite: autopkgtest
Testsuite-Triggers: build-essential
Build-Depends: debhelper-compat (= 13), meson, ninja-build, check <!nocheck>, desktop-file-utils <!nocheck>, dh-exec, doxygen, dpkg-dev (>= 1.17.14), intltool, libasound2-dev [linux-any], libapparmor-dev [linux-any], libasyncns-dev, libavahi-client-dev, libbluetooth-dev [linux-any] <!stage1>, libsbc-dev [linux-any], libcap-dev [linux-any], libfftw3-dev, libglib2.0-dev, libgstreamer1.0-dev (>= 1.14), libgstreamer-plugins-base1.0-dev, libgtk-3-dev, libice-dev, libjack-dev, liblirc-dev, libltdl-dev, liborc-0.4-dev, libsnapd-glib-dev, libsndfile1-dev, libsoxr-dev (>= 0.1.1), libspeexdsp-dev (>= 1.2~rc1), libssl-dev, libsystemd-dev [linux-any], libtdb-dev, libudev-dev [linux-any], libwebrtc-audio-processing-dev (>= 0.2) [linux-any], libwrap0-dev, libx11-xcb-dev, libxcb1-dev, libxml2-utils <!nocheck>, libxtst-dev, systemd [linux-any]
Package-List:
 libpulse-dev deb libdevel optional arch=any
 libpulse-mainloop-glib0 deb libs optional arch=any
 libpulse0 deb libs optional arch=any
 pulseaudio deb sound optional arch=any
 pulseaudio-equalizer deb sound optional arch=any
 pulseaudio-module-bluetooth deb sound optional arch=linux-any profile=!stage1
 pulseaudio-module-gsettings deb sound optional arch=any
 pulseaudio-module-jack deb sound optional arch=any
 pulseaudio-module-lirc deb sound optional arch=any
 pulseaudio-module-raop deb sound optional arch=any
 pulseaudio-module-zeroconf deb sound optional arch=any
 pulseaudio-utils deb sound optional arch=any
Checksums-Sha1:
 921990eedeafd42278ae6ca71487ebdf74b340e0 1437216 pulseaudio_16.1+dfsg1.orig.tar.xz
 8c42043a80e010da66a98babb58689289879af6c 98660 pulseaudio_16.1+dfsg1-2ubuntu10.1.debian.tar.xz
Checksums-Sha256:
 e471c61c47b6d95089be52a5122c87161a695b60534a0c8a36fe344310fd3d06 1437216 pulseaudio_16.1+dfsg1.orig.tar.xz
 80db1588384392c47d3233e670ca1e25e8096fd4f37e1160f3b476bc61b9668c 98660 pulseaudio_16.1+dfsg1-2ubuntu10.1.debian.tar.xz
Files:
 436f9a32a0d1588f4ac956b97c6282ea 1437216 pulseaudio_16.1+dfsg1.orig.tar.xz
 0b228b2f3ada207aea68623869e0f931 98660 pulseaudio_16.1+dfsg1-2ubuntu10.1.debian.tar.xz
Original-Maintainer: Pulseaudio maintenance team <pkg-pulseaudio-devel@lists.alioth.debian.org>

-----BEGIN PGP SIGNATURE-----

iQIzBAEBCAAdFiEEkv5Pi0DK3E7M1gwfWWH9vpxhmAkFAmdX/VYACgkQWWH9vpxh
mAn9Wg/9E5Ftoare8e8tEsqoJt2OLQ9CEtJTKdQvk/pKWLBX6Ce70aqfR+V1k8Di
5IP5CRGuJGJEBEPyqK17UjKBgZh2vOf8hZ0vvETqMJ58E/fdOeRXaGbsVUPg+DVr
kTrlbaIC9UlLa6jLAy3vPkK27h1FE4Cg78k1CGrmdq95UqyJMkn6MLKH1cxGu4BI
hRhupD1AVMU7bzLdzjVcNRCpKhbDwOk7R4wmUjX4rN+mHrlQybk+WN+IwTGuLUxB
OC32LIzO3/gtS2A2JT/W0xZTj2R3ZFWEyMJRRn+hSrdK7N8id//j2ij3iD8PxPbl
3rcUC2DaA9mCRosc+bRtAAKViUBG/eaDAyu9EpCXkksk3YWPm8F/J7h7OVyTuLsa
NotEJwbBzFtUjizRUbezhSOr5u6pwWN06j8IErkuzwmbBlX6wrySQ6OptIXOufJG
6nSPZoo0eTAH9oN7K0LooUyzgiNEMKI7Zh4onWn4i807gv6xrmDnVCAV89lKIEGz
onDuGfbyQuBsj1gI0dOpamT6g8zsXq9NwQjowOe2kTbbEnbihkuYfc3K8fIzTyuT
Ug2v8wKQmOax/6UL9baoAELTkO79iq7JGGnjB6oKTvC+hUHIXwBz0ss9SLgA8ruE
gesvP5c3rphNoBfe2xoLp7fyum9gju+4eQrC+MTBWIyzEPB9g6s=
=egjE
-----END PGP SIGNATURE-----
