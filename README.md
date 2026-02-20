

# <img src="typhoon/io.github.archisman_panigrahi.typhoon.svg" align="left" width="100" height="100">  <br> Typhoon

> Stylish weather application, powered by [Open-Meteo](https://open-meteo.com/), [OpenStreetMap](https://www.openstreetmap.org/) and [ipapi](https://ipapi.co/).

<img src="https://archisman-panigrahi.github.io/typhoon/assets/img/typhoon.png" align="left" width="240" height="400"> <br>
<img src="./assets/screenshots/typhoon_animation.gif" align="center" width="180" height="300">
<img src="./assets/screenshots/typhoon-left-right.gif" align="center" width="180" height="300">

Typhoon is a beautiful weather application that provides real-time weather updates and forecasts in a highly configurable and colorful widget inspired by the Metro interface in Windows 8.

Originally based on [Stormcloud](http://github.com/consindo/stormcloud/) 1.1 by [Jono Cooper](http://github.com/consindo), Typhoon is powered by Open-Meteo, OpenStreetMap and ipapi.

### Features

- Real-time weather updates and forecasts for up to four days
- Customizable units of measurement
- Displays current temperature as launcher count
- Displays precipitation warning within app
- Displays system notifications for rain, snow or thunderstorm
- Configurable widget opacity and color
- Chameleonic background color based on wallpaper or accent color
- Temperature-based background color
- Supports customizable background color
- Powered by Open-Meteo, OpenStreetMap and ipapi
- Supports IP address-based location detection
- Supports multiple locations

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=archisman-panigrahi/typhoon&type=date&legend=top-left)](https://www.star-history.com/#archisman-panigrahi/typhoon&type=date&legend=top-left)

[![Stargazers repo roster for @archisman-panigrahi/typhoon](https://reporoster.com/stars/archisman-panigrahi/typhoon)](https://github.com/archisman-panigrahi/typhoon/stargazers)

## Climacons

Thanks to [Adam Whitcroft](https://adamwhitcroft.com/) for [Climacons](https://web.archive.org/web/20160531215708/http://adamwhitcroft.com/climacons/).

## Installation
On **Ubuntu** you can use the official [PPA](https://launchpad.net/~apandada1/+archive/ubuntu/typhoon).
<a href="https://repology.org/project/typhoon/versions">
    <img src="https://repology.org/badge/vertical-allrepos/typhoon.svg" alt="Packaging status" align="right">
</a>

```
sudo add-apt-repository ppa:apandada1/typhoon
sudo apt update
sudo apt install typhoon
```
On **Debian**, you can install the prebuild **.deb** package on [GitHub releases](https://github.com/archisman-panigrahi/typhoon/releases).

For **Arch** based distros Typhoon is available on the [AUR](https://aur.archlinux.org/packages/typhoon),
```
yay -S typhoon
```

On **Fedora**, you can install the prebuild **.rpm** package on [GitHub releases](https://github.com/archisman-panigrahi/typhoon/releases).

**Distro agnostic** packages: 
Typhoon is available on [Flathub](https://flathub.org) and the [Snap Store](https://snapcraft.io/typhoon) (thanks to @soumyaDghosh).

<a href='https://flathub.org/apps/io.github.archisman_panigrahi.typhoon'>
    <img height='55' alt='Get it on Flathub' src='https://flathub.org/api/badge?locale=en'/>
  </a>
<a href="https://snapcraft.io/typhoon">
    <img height='55' alt="Get it from the Snap Store" src=https://snapcraft.io/en/dark/install.svg />
</a>

*Note that the chameleonic background does not work in the flatpak and snap packages. To use this feature, use the native packages instead.*

On **Windows** you can [install typhoon via WSL](https://archisman-panigrahi.github.io/typhoon/windows-wsl).



## Build System
This project uses the Meson build system for configuration and installation.

### Build Instructions
1. Ensure you have Meson and Ninja installed on your system.
2. Install the dependencies: `webkit2gtk`, `gtk3`, `imagemagick`.
3. Navigate to the project directory.
4. Run the following commands to build and install the application:

```bash
meson setup builddir --prefix=/usr
sudo ninja -C builddir install
```

To uninstall, run

```bash
sudo ninja -C builddir uninstall
```

### Running the Application
After installation, you can run the application using:

```bash
typhoon
```

## License
This project is licensed under the GPL-3. See the [LICENSE file](https://github.com/archisman-panigrahi/typhoon/blob/master/COPYING) for more details.
