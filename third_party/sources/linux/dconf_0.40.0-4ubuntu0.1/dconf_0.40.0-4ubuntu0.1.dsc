-----BEGIN PGP SIGNED MESSAGE-----
Hash: SHA512

Format: 3.0 (quilt)
Source: dconf
Binary: libdconf1, libdconf-dev, libdconf-doc, dconf-cli, dconf-gsettings-backend, dconf-service
Architecture: any all
Version: 0.40.0-4ubuntu0.1
Maintainer: Ubuntu Developers <ubuntu-devel-discuss@lists.ubuntu.com>
Uploaders: Iain Lane <laney@debian.org>, Laurent Bigonville <bigon@debian.org>, Marco Trevisan (Treviño) <marco@ubuntu.com>, Michael Biebl <biebl@debian.org>, Sebastien Bacher <seb128@debian.org>
Homepage: https://wiki.gnome.org/Projects/dconf
Standards-Version: 4.6.0
Vcs-Browser: https://salsa.debian.org/gnome-team/dconf
Vcs-Git: https://salsa.debian.org/gnome-team/dconf.git
Testsuite: autopkgtest
Testsuite-Triggers: build-essential, pkg-config
Build-Depends: bash-completion, dbus <!nocheck>, debhelper-compat (= 13), dh-sequence-gnome, docbook-xsl, libdbus-1-dev, libglib2.0-dev (>= 2.44.0), meson (>= 0.47.0), procps <!nocheck>, valac (>= 0.18.0), xsltproc
Build-Depends-Indep: gtk-doc-tools (>= 1.15) <!nodoc>, libglib2.0-doc <!nodoc>
Package-List:
 dconf-cli deb utils optional arch=any
 dconf-gsettings-backend deb libs optional arch=any
 dconf-service deb libs optional arch=any
 libdconf-dev deb libdevel optional arch=any
 libdconf-doc deb doc optional arch=all profile=!nodoc
 libdconf1 deb libs optional arch=any
Checksums-Sha1:
 c8e12b98b2b10ccae4ee13395a39b3e913f58ab6 117764 dconf_0.40.0.orig.tar.xz
 be3154f622d661551c5fa21abd49c2e42178f653 12104 dconf_0.40.0-4ubuntu0.1.debian.tar.xz
Checksums-Sha256:
 cf7f22a4c9200421d8d3325c5c1b8b93a36843650c9f95d6451e20f0bcb24533 117764 dconf_0.40.0.orig.tar.xz
 5ff0fb472fd6a451142c052ebe06df43444a57a42c305af89036c7c5265776d6 12104 dconf_0.40.0-4ubuntu0.1.debian.tar.xz
Files:
 ac8db20b0d6b996d4bbbeb96463d01f0 117764 dconf_0.40.0.orig.tar.xz
 2e1a6668d10ec5d35c825d2f050a5350 12104 dconf_0.40.0-4ubuntu0.1.debian.tar.xz
Original-Maintainer: Debian GNOME Maintainers <pkg-gnome-maintainers@lists.alioth.debian.org>

-----BEGIN PGP SIGNATURE-----

iQIzBAEBCgAdFiEEiYfY5F8zkxDOZhouZMRpvlnA3qIFAmiULVIACgkQZMRpvlnA
3qJw8A//f0q1sGDEa8rZwqWOKRlirMCx5A3meKIcCq/A1CztGEaG1DpJJ1OjOWX/
CIfixVz4qz3r+sx35aVZPWACyCFtOF0p58lZ+9n03UT2M7ccB5IciytF2qHacPcF
D9gTPVBm2OH9QkL3G/E+A+pLnI68oG8lAgp0PWEQGoBTRrvhwQ1ufxOmb0IYaph0
MsLeSzgOGaQ3vj4ExQVYvWUL2UE2fKXYrnOT9BeAfL+ozC1Tab7jUOc0XmDAQObW
uMggZPgVw7WZsZC2QyjY+GoGDpnSGeEPc7OmNha58IQZDfdEjT0UGLz12Cw/WZcT
9oJ+Y2QggelKvD7KONDR/DXwxQkx8wJeDq1WM7DCSZQNN8o2pYvNHj4HSLNAslaN
0FZNFCYnmGyPJu/H2uF7yVwN9xbEzh8PIPpnKaNPVQ9Twf9d9qq3KQ5AnOBgwyM6
hyDLm8zq3D32QdpwsYmwnar1seodjcDuzxdes1LF1PqbIlh5OdnG94nsgSAHyeKw
JflDGK5zvZOYAJ8ct6GsjBUzH/E3viCYRwvvBl0rMQhQCtAMxHBSc/SOY67Oxnnf
8XipfTEhvDQA9r2dtg6n6iqw3lqpfuQn/5zBA1NMoOFRbA3+quRuFWw30a9YiXBq
kaw2YuxXF3/7iun7xbdnyP9woFh2ja5NW/wJXJTG3h+e0MBa5xA=
=Ov00
-----END PGP SIGNATURE-----
