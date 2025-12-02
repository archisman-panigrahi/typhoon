Name:           typhoon
Version:        1.3
Release:        1%{?dist}
Summary:        Simple weather application, powered by Open-Meteo and OpenStreetMap

License:        MIT
URL:            https://archisman-panigrahi.github.io/typhoon
Source0:        https://github.com/archisman-panigrahi/typhoon/archive/refs/heads/master.tar.gz
BuildArch:      noarch

BuildRequires:  meson
BuildRequires:  python3-setuptools
BuildRequires:  glib2-devel
BuildRequires:  gtk3-devel
BuildRequires:  webkit2gtk4.1-devel
BuildRequires:  dbus-devel
BuildRequires:  python3-dbus
BuildRequires:  desktop-file-utils

Requires:       glib2
Requires:       gtk3
Requires:       webkit2gtk4.1
Requires:       ImageMagick
Requires:       dbus
Requires:       python3-dbus
Requires:       libnotify
Requires:       libportal
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

