# Typhoon

> Simple weather application, powered by [OpenWeather](https://openweathermap.org/)

Based on [Stormcloud](http://github.com/consindo/stormcloud/) 1.1 by [Jono Cooper](https://twitter.com/consindo).

## Climacons

Thanks to [Adam Whitcroft](https://twitter.com/AdamWhitcroft) for [Climacons](http://adamwhitcroft.com/climacons/).

## Installation
On Ubuntu you can use the official [PPA](https://launchpad.net/~apandada1/+archive/ubuntu/typhoon).

```
sudo add-apt-repository ppa:apandada1/typhoon
sudo apt update
sudo apt install typhoon
```

It is also available on the [AUR](https://aur.archlinux.org/packages/typhoon-git),
```
yay -S typhoon-git
```

## Build System
This project uses the Meson build system for configuration and installation.

### Build Instructions
1. Ensure you have Meson and Ninja installed on your system.
2. Navigate to the project directory.
3. Run the following commands to build and install the application:

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