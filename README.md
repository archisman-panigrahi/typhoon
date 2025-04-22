

# <img src="typhoon/typhoon.svg" align="left" width="100" height="100">  <br> Typhoon

> Simple weather application, powered by [Open-Meteo](https://open-meteo.com/) and [OpenStreetMap](https://www.openstreetmap.org/).

<img src="https://archisman-panigrahi.github.io/typhoon/assets/img/typhoon.png" align="center">

Based on [Stormcloud](http://github.com/consindo/stormcloud/) 1.1 by [Jono Cooper](https://twitter.com/consindo).

## Climacons

Thanks to [Adam Whitcroft](https://adamwhitcroft.com/) for [Climacons](https://web.archive.org/web/20160531215708/http://adamwhitcroft.com/climacons/).

## Installation

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
