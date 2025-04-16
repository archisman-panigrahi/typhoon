Name:           typhoon
Version:        0.9.80
Release:        1%{?dist}
Summary:        Quickly check the weather with this beautiful application

License:        MIT
URL:            https://archisman-panigrahi.github.io/typhoon
Source0:        https://github.com/archisman-panigrahi/typhoon/archive/refs/heads/master.tar.gz

BuildRequires:  meson
BuildRequires:  python3-setuptools
BuildRequires:  glib2-devel
BuildRequires:  gtk3-devel
BuildRequires:  webkit2gtk3-devel
BuildRequires:  ImageMagick
BuildRequires:  dbus-devel
BuildRequires:  python3-dbus

Requires:       glib2
Requires:       gtk3
Requires:       webkit2gtk3
Requires:       ImageMagick
Requires:       dbus
Requires:       python3-dbus

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
%{_datadir}/applications/typhoon.desktop
%{_datadir}/icons/hicolor/scalable/apps/typhoon.svg

%changelog
* Tue Apr 15 2025 Archisman Panigrahi <apandada1@gmail.com> - 1.0.0-1
- Initial package
