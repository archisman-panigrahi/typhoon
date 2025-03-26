# Typhoon Project

## Overview
Typhoon is a GTK-based application that utilizes WebKit to display HTML content in a window. The application handles various window events and navigation actions, providing a seamless user experience.

## Files
- **data/media/typhon_window.py**: The main application code that creates a GTK window with a WebKit view, handling navigation and window events.
- **data/media/app.html**: An HTML document that is loaded into the WebKit view.

## Build System
This project uses the Meson build system for configuration and installation.

### Build Instructions
1. Ensure you have Meson and Ninja installed on your system.
2. Navigate to the project directory.
3. Run the following commands to build and install the application:
   ```bash
   meson setup builddir
   meson compile -C builddir
   meson install -C builddir
   ```

### Running the Application
After installation, you can run the application using:
```bash
python3 data/media/typhon_window.py
```

## Options
You can customize the build process by modifying the options defined in `meson_options.txt`. The default data directory for installation is `data/media`.

## License
This project is licensed under the MIT License. See the LICENSE file for more details.