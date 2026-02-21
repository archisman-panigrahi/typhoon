#!/usr/bin/python3

import os
import sys
import gi
import subprocess  # For increased robustness of chameleonic background
import dbus
import dbus.service
import dbus.mainloop.glib
import logging
from gi.repository import GLib
import threading
import glob
import configparser

try:
    import cairosvg
except ImportError:
    cairosvg = None

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
gi.require_version("Xdp", "1.0")
gi.require_version("WebKit", "6.0")
from gi.repository import Gtk, WebKit, GdkPixbuf, Gdk, Xdp, Gio

try:
    from gi.repository import Unity
except ImportError:
    Unity = None


logger = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s - %(message)s",
)


class TyphoonWindow(Gtk.ApplicationWindow):
    def __init__(self, application):
        super().__init__(application=application, title="Typhoon")
        self.aspect_ratio = 3 / 5  # Desired aspect ratio (width / height)
        self.drag_enabled = True
        self._resizing = False
        self._min_width = 210
        self._min_height = 350
        self._max_width = None
        self._max_height = None

        self._initialize_window()
        self._setup_webview()
        self._setup_scrolled_window()
        self._setup_unity_launcher()

        self.connect("close-request", self._on_close_request)

        # Set size constraints.
        self._set_size_constraints()

        # Retrieve the last remembered size from a configuration file.
        last_width, last_height = self._get_last_window_size()
        self._set_window_size(last_width, last_height)

        # Enable resizing by setting the window as resizable.
        self.set_resizable(True)

        # Add the resize grip.
        self.add_resize_grip()

    def _on_close_request(self, widget):
        """Stops the D-Bus service when the application is closed."""
        if hasattr(self, "launcher_service"):
            self.launcher_service = None
        return False

    def _initialize_window(self):
        """Initializes the main window properties."""
        self.set_decorated(False)  # Hide the title bar
        self._set_window_icon()

        # Use an overlay to combine the WebView and the resize grip.
        self.overlay = Gtk.Overlay()
        self.set_child(self.overlay)

        self.connect("notify::maximized", self._on_maximized_changed)

    def _set_window_icon(self):
        """Sets the window icon if available."""
        try:
            self.set_icon_name("io.github.archisman_panigrahi.typhoon")
        except Exception:
            pass

    def add_resize_grip(self):
        """Adds a resize grip to the bottom-right corner of the window."""
        grip = Gtk.Box()

        label = Gtk.Label(label="⇲")
        label.add_css_class("resize-grip")
        grip.append(label)

        resize_gesture = Gtk.GestureDrag.new()
        resize_gesture.connect("drag-begin", self._start_resize)
        resize_gesture.connect("drag-update", self._resize_window)
        resize_gesture.connect("drag-end", self._end_resize)
        grip.add_controller(resize_gesture)

        # Position the grip in the bottom-right corner using the overlay.
        self.overlay.add_overlay(grip)
        grip.set_halign(Gtk.Align.END)
        grip.set_valign(Gtk.Align.END)

        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(
            b"""
            .resize-grip {
                color: white;
            }
            """
        )
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

    def _start_resize(self, gesture, start_x, start_y):
        """Starts the resize operation."""
        self._resizing = True
        self._resize_start_width = self.get_width()
        self._resize_start_height = self.get_height()

    def _resize_window(self, gesture, offset_x, offset_y):
        """Handles the resize operation."""
        if not self._resizing:
            return

        delta_x = int(offset_x)
        new_width = self._resize_start_width + delta_x
        new_height = int(new_width / self.aspect_ratio)
        self._set_window_size(new_width, new_height)

    def _end_resize(self, gesture, offset_x, offset_y):
        """Ends the resize operation."""
        self._resizing = False

    def _set_window_size(self, width, height=None):
        """Sets window size while enforcing aspect ratio and min/max constraints."""
        if height is None:
            height = int(width / self.aspect_ratio)

        width = max(int(width), self._min_width)
        height = max(int(height), self._min_height)

        if self._max_width is not None:
            width = min(width, self._max_width)
        if self._max_height is not None:
            height = min(height, self._max_height)

        # Keep aspect ratio stable after clamping.
        width = int(height * self.aspect_ratio)
        if self._max_width is not None and width > self._max_width:
            width = self._max_width
            height = int(width / self.aspect_ratio)

        self.set_default_size(width, height)
        self._save_window_size(width, height)

    def _setup_webview(self):
        """Sets up the WebKit WebView and connects signals."""
        self.webview = WebKit.WebView()

        settings = self.webview.get_settings()
        settings.set_user_agent("Typhoon Weather App (https://github.com/archisman-panigrahi/typhoon)")

        self.webview.connect("decide-policy", self._handle_policy_decision)
        self.webview.connect("notify::title", self._handle_title_change)
        self.webview.connect("context-menu", self._handle_context_menu)

        click_controller = Gtk.GestureClick.new()
        click_controller.set_button(0)
        click_controller.connect("pressed", self._handle_webview_click)
        self.webview.add_controller(click_controller)

        html_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "typhoon.html")
        self.webview.load_uri(f"file://{html_path}")

        self.webview.connect("load-changed", self._on_load_changed)

    def _on_load_changed(self, webview, load_event):
        """Handles the load-changed event for the WebView."""
        if load_event == WebKit.LoadEvent.FINISHED:
            # Try to get the dominant color from the wallpaper.
            try:
                wallpaper_path = self.get_wallpaper_path()
                dominant_color = self._extract_dominant_color(wallpaper_path)
                if dominant_color and dominant_color.startswith("#"):
                    print(f"Extracted hex color from wallpaper: {dominant_color}")
                    self.send_message_to_webview(f"'{dominant_color[1:]}'")
                    return
                raise ValueError("Invalid color format from wallpaper method")
            except Exception as e:
                print(f"Error determining color from wallpaper: {e}")

            # Fallback to the xprop method.
            try:
                xprop_process = subprocess.Popen(
                    ["xprop", "-root"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                grep_process = subprocess.Popen(
                    ["grep", "_GNOME_BACKGROUND_REPRESENTATIVE_COLORS"],
                    stdin=xprop_process.stdout,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                xprop_process.stdout.close()
                output, _ = grep_process.communicate()

                if output and "_GNOME_BACKGROUND_REPRESENTATIVE_COLORS" in output:
                    try:
                        rgb_string = output.split('"')[1].strip()
                        rgb_values = rgb_string[4:-1].split(",")
                        rgb = tuple(map(int, rgb_values))
                        hex_color = "{:02x}{:02x}{:02x}".format(rgb[0], rgb[1], rgb[2])
                        print(f"Extracted hex color from xprop: #{hex_color}")
                        self.send_message_to_webview(f"'{hex_color}'")
                    except (IndexError, ValueError) as e:
                        print(f"Error parsing RGB values from xprop: {e}")
                        raise Exception("Fallback to Xdp")
                else:
                    print("No representative colors found in xprop output.")
                    raise Exception("Fallback to Xdp")
            except Exception as e:
                print(f"Error running xprop or no colors found: {e}")
                self._get_accent_color()

    def _extract_dominant_color(self, wallpaper_path):
        if wallpaper_path.lower().endswith(".svg") and cairosvg:
            png_bytes = cairosvg.svg2png(url=wallpaper_path, output_width=16, output_height=16)
            loader = GdkPixbuf.PixbufLoader.new_with_type("png")
            loader.write(png_bytes)
            loader.close()
            pixbuf = loader.get_pixbuf()
            pixels = pixbuf.get_pixels()
            n_channels = pixbuf.get_n_channels()
            width, height = pixbuf.get_width(), pixbuf.get_height()
            r = g = b = count = 0
            for y in range(height):
                for x in range(width):
                    i = (y * width + x) * n_channels
                    r += pixels[i]
                    g += pixels[i + 1]
                    b += pixels[i + 2]
                    count += 1
            avg = (r // count, g // count, b // count)
            return "#{:02x}{:02x}{:02x}".format(*avg)

        command = f'convert "{wallpaper_path}" -resize 1x1 txt:- | awk \'NR==2 {{print $3}}\''
        dominant_color = subprocess.check_output(command, shell=True, text=True).strip()
        return dominant_color if dominant_color.startswith("#") else None

    def _get_accent_color(self):
        logger.info("Getting System Accent Color")
        portal = Xdp.Portal()
        settings = portal.get_settings()
        accent_color = settings.read_value("org.freedesktop.appearance", "accent-color")
        if accent_color is not None:
            r, g, b = accent_color
            hex_color = "{:02x}{:02x}{:02x}".format(int(r * 255), int(g * 255), int(b * 255))
            logger.info(f"Accent color found in settings: '#{hex_color}'")
        else:
            logger.error("Accent color not found in settings")
            logger.warning("Note that currently the accent color only works in GNOME and KDE Plasma 6")
            logger.warning("Using Purple default color")
            hex_color = "575591"
        self.send_message_to_webview(f"'{hex_color}'")

    def send_message_to_webview(self, message):
        """Sends a message to the WebView."""
        js_code = f"receiveMessage({message});"
        self.webview.evaluate_javascript(js_code, len(js_code), None, None, None, None, None)

    def _send_dbus_notification(self, message):
        """Sends a notification via D-Bus asynchronously."""
        try:
            bus = dbus.SessionBus()
            notify_obj = bus.get_object("org.freedesktop.Notifications", "/org/freedesktop/Notifications")
            notify_interface = dbus.Interface(notify_obj, "org.freedesktop.Notifications")

            hints = {"desktop-entry": dbus.String("io.github.archisman_panigrahi.typhoon")}

            notify_interface.Notify(
                "Weather Alert",
                0,
                "io.github.archisman_panigrahi.typhoon",
                message,
                "Take care and stay safe.",
                dbus.Array([], signature="s"),
                hints,
                -1,
            )
        except Exception as e:
            logger.error(f"Failed to send D-Bus notification: {e}")

    def _setup_scrolled_window(self):
        """Wraps the WebView in a scrolled window and adds it to the overlay."""
        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_child(self.webview)
        self.overlay.set_child(scrolled_window)

    def _setup_unity_launcher(self):
        """Configures Unity launcher integration if available."""
        self.launcher_visible = False
        self._pending_launcher_count = None
        if Unity:
            try:
                self.launcher = Unity.LauncherEntry.get_for_desktop_id("io.github.archisman_panigrahi.typhoon.desktop")
                self.launcher.set_property("count_visible", False)
            except NameError:
                self.launcher = None
        else:
            self._ensure_launcher_service()

    def _ensure_launcher_service(self):
        if not hasattr(self, "launcher_service"):
            self.launcher_service = Service()
            self.launcher_thread = threading.Thread(target=self.launcher_service.run, daemon=True)
            self.launcher_thread.start()

    def _set_size_constraints(self):
        """Sets the minimum and maximum size constraints for the window."""
        display = Gdk.Display.get_default()
        monitors = display.get_monitors()
        monitor = monitors.get_item(0) if monitors.get_n_items() > 0 else None

        if monitor:
            monitor_geometry = monitor.get_geometry()
            screen_height = monitor_geometry.height
        else:
            screen_height = 900

        self._max_width = int(screen_height * 0.9 * 3 / 5)
        self._max_height = int(screen_height * 0.9)
        self.set_size_request(self._min_width, self._min_height)

    def _get_config_dir(self):
        """Returns the Flatpak-compatible configuration directory."""
        config_dir = os.getenv("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))
        app_config_dir = os.path.join(config_dir, "io.github.archisman_panigrahi.typhoon")
        os.makedirs(app_config_dir, exist_ok=True)
        return app_config_dir

    def _get_last_window_size(self):
        """Retrieves the last remembered window size from a configuration file."""
        config_file = os.path.join(self._get_config_dir(), "typhoon_size.conf")
        try:
            with open(config_file, "r") as file:
                size = file.read().strip().split("x")
                width, height = int(size[0]), int(size[1])
                return width, height
        except (FileNotFoundError, ValueError):
            return 300, 500

    def _save_window_size(self, width, height):
        """Saves the current window size to a configuration file."""
        config_file = os.path.join(self._get_config_dir(), "typhoon_size.conf")
        with open(config_file, "w") as file:
            file.write(f"{width}x{height}")

    def _handle_policy_decision(self, webview, decision, decision_type):
        """Handles navigation policy decisions for the WebView."""
        if decision_type == WebKit.PolicyDecisionType.NAVIGATION_ACTION:
            navigation_action = decision.get_navigation_action()
            uri = navigation_action.get_request().get_uri()
            print(f"Navigation request URI: {uri}")

            if uri.startswith("file://"):
                print("Internal navigation detected, allowing WebView to handle it.")
            else:
                print("Opening Link Externally")
                Gtk.show_uri(self, uri, Gdk.CURRENT_TIME)
                decision.ignore()
                return True
        return False

    def _handle_title_change(self, webview, param):
        """Handles title changes in the WebView."""
        title = webview.get_title()
        print(f"{title}")

        if title and title.startswith("notify:"):
            message = title[len("notify:"):]
            if not message:
                message = "Weather alert"
            threading.Thread(target=self._send_dbus_notification, args=(message,), daemon=True).start()
            return

        if not title:
            return

        if title.startswith("height="):
            try:
                height = int(title.split("=")[1])
                width = int(0.6 * height)
                self._set_window_size(width, height)
                print(f"Window resized to width={width}, height={height}")
            except ValueError:
                print("Invalid height value in title.")
        elif title == "close":
            self._toggle_unity_launcher("disable_launcher")
            app = self.get_application()
            if app:
                app.quit()
        elif title == "minimize":
            self.minimize()
        elif title == "disabledrag":
            self.drag_enabled = False
        elif title == "enabledrag":
            self.drag_enabled = True
        elif title.startswith("o"):
            self._set_opacity_from_title(title)
        elif title == "reset":
            self._toggle_unity_launcher("disable_launcher")
            self._set_window_size(300, 500)
        elif title in ["enable_launcher", "disable_launcher"]:
            self._toggle_unity_launcher(title)
        elif title.lstrip("-").isdigit():
            self._update_unity_count(title)

    def _set_opacity_from_title(self, title):
        """Sets the window opacity based on the title."""
        try:
            opacity = float(title[1:])
            self.set_opacity(opacity)
        except ValueError:
            pass

    def _toggle_unity_launcher(self, title):
        """Enables or disables the Unity launcher count visibility."""
        visible = title == "enable_launcher"
        self.launcher_visible = visible

        if Unity and self.launcher:
            print(f"{'Enabling' if visible else 'Disabling'} Unity launcher count.")
            self.launcher.set_property("count_visible", visible)
        else:
            try:
                self._ensure_launcher_service()
                print(f"{'Enabling' if visible else 'Disabling'} dbus launcher count.")
                self.launcher_service.Update(
                    "application://io.github.archisman_panigrahi.typhoon.desktop",
                    {"count-visible": dbus.Boolean(visible)},
                )
            except ValueError:
                pass

    def _update_unity_count(self, title):
        """Updates the Unity launcher count based on the title."""
        try:
            count = int(title)
        except ValueError:
            return

        # On Plasma startup, the launcher badge may ignore initial state updates.
        # Reproduce the manual working path once: disable -> enable -> count.
        if not self.launcher_visible:
            self._toggle_unity_launcher("disable_launcher")
            GLib.timeout_add(80, self._deferred_toggle_launcher, "enable_launcher")
            GLib.timeout_add(180, self._deferred_set_launcher_count, count)
            GLib.timeout_add(480, self._deferred_set_launcher_count, count)
            GLib.timeout_add(1200, self._deferred_reassert_launcher_count, count)
            GLib.timeout_add(2200, self._deferred_reassert_launcher_count, count)
            return

        self._pending_launcher_count = count
        self._set_launcher_count_value(count)
        GLib.timeout_add(1200, self._deferred_reassert_launcher_count, count)

    def _set_launcher_count_value(self, count):
        if Unity and self.launcher:
            try:
                self.launcher.set_property("count", count)
            except (ValueError, NameError):
                pass
        else:
            self._ensure_launcher_service()
            self.launcher_service.Update(
                "application://io.github.archisman_panigrahi.typhoon.desktop",
                {"count": dbus.Int64(count)},
            )

    def _deferred_toggle_launcher(self, title):
        self._toggle_unity_launcher(title)
        return False

    def _deferred_set_launcher_count(self, count):
        self._pending_launcher_count = count
        self._set_launcher_count_value(count)
        return False

    def _deferred_reassert_launcher_count(self, count):
        if not self.launcher_visible:
            return False
        if self._pending_launcher_count != count:
            return False
        self._toggle_unity_launcher("enable_launcher")
        self._set_launcher_count_value(count)
        return False

    def _get_primary_monitor(self):
        """Get the primary monitor name using xrandr, or fallback to first connected monitor."""
        try:
            xrandr_output = subprocess.check_output("xrandr --current | grep -w connected", shell=True, text=True)
            primary_monitor = None
            for line in xrandr_output.splitlines():
                if "primary" in line:
                    primary_monitor = line.split()[0]
                    break
            if not primary_monitor:
                primary_monitor = xrandr_output.splitlines()[0].split()[0]
            return primary_monitor
        except Exception:
            return None

    def get_wallpaper_path(self):
        """Retrieves the current wallpaper path based on the desktop environment."""
        if os.environ.get("FLATPAK_ID") is not None or os.environ.get("SNAP") is not None:
            raise Exception("Flatpak or Snap detected, use xprop method for wallpaper color.")

        de = os.environ.get("XDG_CURRENT_DESKTOP", "").lower()

        if "gnome" in de:
            command = "gsettings get org.gnome.desktop.background picture-uri"
            wallpaper = subprocess.check_output(command, shell=True).decode().strip().strip("'").split("file://")[-1]
        elif "cinnamon" in de:
            command = "gsettings get org.cinnamon.desktop.background picture-uri"
            wallpaper = subprocess.check_output(command, shell=True).decode().strip().strip("'").split("file://")[-1]
        elif "mate" in de:
            command = "gsettings get org.mate.background picture-filename"
            wallpaper = subprocess.check_output(command, shell=True).decode().strip().strip("'").split("file://")[-1]
        elif "xfce" in de:
            primary_monitor = self._get_primary_monitor()
            if not primary_monitor:
                raise Exception("Could not detect primary monitor for XFCE")
            key = f"/backdrop/screen0/monitor{primary_monitor}/workspace0/last-image"
            wallpaper = subprocess.check_output(
                f'xfconf-query -c xfce4-desktop -p "{key}"', shell=True, text=True
            ).strip()
        elif "kde" in de:
            config_file = os.path.expanduser("~/.config/plasma-org.kde.plasma.desktop-appletsrc")
            with open(config_file, "r") as file:
                for line in file:
                    if line.strip().startswith("Image="):
                        wallpaper = line.strip().split("=", 1)[1]
                        if wallpaper.endswith("/"):
                            print("kde: wallpaper it is a directory")
                            wallpaper = os.path.join(wallpaper, "contents", "images")
                            for image_file in os.listdir(wallpaper):
                                if image_file.lower().endswith((".jpg", ".png")):
                                    wallpaper = os.path.join(wallpaper, image_file)
                                    break
                        break
        elif "lxde" in de or "labwc:wlroots" in de:
            config_pattern = os.path.expanduser("~/.config/pcmanfm/*/desktop-items-*.conf")
            config_files = glob.glob(config_pattern)

            wallpaper = None
            primary_monitor = self._get_primary_monitor()

            if primary_monitor:
                config_files.sort(key=lambda f: 0 if primary_monitor in f else 1)

            for config_file in config_files:
                try:
                    config = configparser.ConfigParser()
                    config.read(config_file)
                    if config.has_option("*", "wallpaper"):
                        wallpaper = config.get("*", "wallpaper")
                        break
                except Exception:
                    continue

            if not wallpaper:
                raise Exception("Could not find wallpaper in PCManFM config")
        else:
            raise Exception(f"Unsupported desktop environment: {de}")

        print(f"Wallpaper path: {wallpaper}")
        return wallpaper

    def _handle_webview_click(self, gesture, n_press, x, y):
        """Handles webview click events for drag behavior."""
        button = gesture.get_current_button()
        if button == 3:
            return
        if self.drag_enabled and button in (1, 2):
            device = gesture.get_current_event_device()
            timestamp = gesture.get_current_event_time()
            if device is None:
                return
            surface = self.get_surface()
            if surface is not None:
                # Use coordinates provided by GestureClick; Gdk.Event.get_position()
                # returns a tuple shape that varies in introspection bindings.
                Gdk.Toplevel.begin_move(surface, device, button, float(x), float(y), timestamp)

    def _handle_context_menu(self, *args):
        """Prevents the default webview context menu."""
        return True

    def _on_maximized_changed(self, widget, _param):
        if self.is_maximized():
            self.unmaximize()


class Service(dbus.service.Object):
    def __init__(self):
        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
        bus_name = dbus.service.BusName("io.github.archisman_panigrahi.typhoon", dbus.SessionBus())
        dbus.service.Object.__init__(self, bus_name, "/io/github/archisman_panigrahi/typhoon")

    def run(self):
        GLib.idle_add(lambda: self.Update("application://io.github.archisman_panigrahi.typhoon.desktop", {}))

    @dbus.service.signal(dbus_interface="com.canonical.Unity.LauncherEntry", signature="sa{sv}")
    def Update(self, app_uri, properties):
        print(app_uri, properties)


class TyphoonApplication(Gtk.Application):
    def __init__(self):
        super().__init__(
            application_id="io.github.archisman_panigrahi.typhoon",
            flags=Gio.ApplicationFlags.FLAGS_NONE,
        )
        self.window = None

    def do_activate(self):
        if self.window is None:
            self.window = TyphoonWindow(application=self)
        self.window.present()


if __name__ == "__main__":
    app = TyphoonApplication()
    app.run(sys.argv)
