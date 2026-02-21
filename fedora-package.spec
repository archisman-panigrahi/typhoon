Name:           typhoon
Version:        1.6.0
Release:        1%{?dist}
Summary:        Check the weather with style

License:        MIT
URL:            https://archisman-panigrahi.github.io/typhoon
Source0:        https://github.com/archisman-panigrahi/typhoon/archive/refs/heads/master.tar.gz
BuildArch:      noarch

BuildRequires:  meson
BuildRequires:  python3-setuptools
BuildRequires:  dbus-devel
BuildRequires:  python3-dbus
BuildRequires:  python3-qt6
BuildRequires:  python3-qt6-webengine
BuildRequires:  libportal-devel
BuildRequires:  python3-gobject-base
BuildRequires:  desktop-file-utils

Requires:       dbus
Requires:       python3-dbus
Requires:       python3-qt6
Requires:       python3-qt6-webengine
Requires:       libportal
Requires:       python3-gobject-base
Recommends:     python3-cairosvg

%description
Typhoon is a free and open source weather application. It is a continuation
of the discontinued Stormcloud 1.1, however with some changes. It is and
always will be free.

%global debug_package %{nil}
%prep
%autosetup -n %{name}-master

%build
%meson
%meson_build

%install
%meson_install

%files
%license COPYING
%doc README.md
%{_bindir}/typhoon
%{_datadir}/typhoon/
%{_datadir}/applications/io.github.archisman_panigrahi.typhoon.desktop
%{_datadir}/icons/hicolor/scalable/apps/io.github.archisman_panigrahi.typhoon.svg
%{_datadir}/metainfo/io.github.archisman_panigrahi.typhoon.metainfo.xml

%changelog
* Mon Apr 28 2025 Archisman Panigrahi <apandada1@gmail.com> - 0.9.87-1
- Initial package
