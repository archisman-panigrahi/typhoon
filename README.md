

# <img src="typhoon/io.github.archisman_panigrahi.typhoon.svg" align="left" width="100" height="100">  <br> Typhoon

> Stylish weather application, powered by [Open-Meteo](https://open-meteo.com/), [OpenStreetMap](https://www.openstreetmap.org/) and [ipapi](https://ipapi.co/).

<img src="https://archisman-panigrahi.github.io/typhoon/assets/img/typhoon.png" align="center">


Typhoon is a beautiful weather application that provides real-time weather updates and forecasts in a highly configurable and colorful widget inspired by the Metro interface in Windows 8.

Originally based on [Stormcloud](http://github.com/consindo/stormcloud/) 1.1 by [Jono Cooper](https://twitter.com/consindo), Typhoon is powered by Open-Meteo, OpenStreetMap and ipapi.

### Features

- Real-time weather updates and forecasts for up to four days
- Customizable units of measurement
- Displays current temperature as launcher count
- Configurable widget opacity and color
- Chameleonic background color based on wallpaper or accent color
- Temperature-based background color
- Powered by Open-Meteo, OpenStreetMap and ipapi
- Supports IP address-based location detection
- Multiple locations supported via multiple windows

## Climacons

Thanks to [Adam Whitcroft](https://adamwhitcroft.com/) for [Climacons](https://web.archive.org/web/20160531215708/http://adamwhitcroft.com/climacons/).

## Installation
Typhoon is available on [Flathub](https://flathub.org).

<a href='https://flathub.org/apps/io.github.archisman_panigrahi.typhoon'>
    <img width='240' alt='Get it on Flathub' src='https://flathub.org/api/badge?locale=en'/>
  </a>



On Ubuntu you can use the official [PPA](https://launchpad.net/~apandada1/+archive/ubuntu/typhoon).
<a href="https://repology.org/project/typhoon/versions">
    <img src="https://repology.org/badge/vertical-allrepos/typhoon.svg" alt="Packaging status" align="right">
</a>

```
sudo add-apt-repository ppa:apandada1/typhoon
sudo apt update
sudo apt install typhoon
```

It is also available on the [AUR](https://aur.archlinux.org/packages/typhoon),
```
yay -S typhoon
```
You can also find prebuild .deb and .rpm packages on [GitHub releases](https://github.com/archisman-panigrahi/typhoon/releases).

<!-- An experimetnal [flatpak installer](https://github.com/archisman-panigrahi/typhoon/releases) is also available. -->

## Build System
This project uses the Meson build system for configuration and installation.

### Build Instructions
1. Ensure you have Meson and Ninja installed on your system.
2. Install the dependencies: `webkit2gtk`, `gtk3`, `imagemagick`.
3. Navigate to the project directory.
4. Run the following commands to build and install the application:

```bash
meson setup builddir --prefix=/usr
sudo meson install -C builddir
```

To uninstall, run

```bash
sudo meson uninstall -C builddir
```

### Running the Application
After installation, you can run the application using:

```bash
typhoon
```

## License
This project is licensed under the GPL-3. See the [LICENSE file](https://github.com/archisman-panigrahi/typhoon/blob/master/COPYING) for more details.
