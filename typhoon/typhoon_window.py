#!/usr/bin/python3

import os
import sys
import gi
import subprocess  # For increased robustness of chameleonic background
import dbus
import dbus.service
import dbus.mainloop.glib
import logging
from gi.repository import GObject, GLib
import threading
import io
try:
    import cairosvg
except ImportError:
    cairosvg = None

gi.require_version("Gtk", "3.0")
gi.require_version("Xdp", "1.0")
try:
    gi.require_version("WebKit2", "4.1")  # Attempt to use WebKit2 4.1
except ValueError:
    gi.require_version("WebKit2", "4.0")  # Fallback to WebKit2 4.0
from gi.repository import Gtk, WebKit2, GdkPixbuf, Gdk, Xdp

try:
    from gi.repository import Unity
except ImportError:
    Unity = None


logger = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s - %(message)s",
)

class TyphoonWindow(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, title="Typhoon")
        self.aspect_ratio = 3 / 5  # Desired aspect ratio (width / height)
        self._initialize_window()
        self._setup_webview()
        self._setup_scrolled_window()
        self._setup_unity_launcher()
        self.drag_enabled = True  # Enable dragging by default

        # Connect the destroy signal to stop the D-Bus service
        self.connect("destroy", self._on_destroy)

        # Retrieve the last remembered size and position from a configuration file
        last_width, last_height = self._get_last_window_size()
        last_position = self._get_last_window_position()

        self.set_default_size(last_width, last_height)
        if last_position:
            last_x, last_y = last_position
            self.move(last_x, last_y)
        else:
            self.set_position(Gtk.WindowPosition.CENTER)  # Default to center of the screen

        # Connect to the configure-event signal to maintain aspect ratio and save position
        self.connect("configure-event", self._maintain_aspect_ratio)
        self.connect("configure-event", self._save_window_position)

        # Enable resizing by setting the window as resizable
        self.set_resizable(True)

        # Set size constraints
        self._set_size_constraints()

        # Add the resize grip
        self.add_resize_grip()

    def _on_destroy(self, widget):
        """Stops the D-Bus service when the application is closed."""
        if hasattr(self, "launcher_service") and self.launcher_service:
            print("Stopping D-Bus service...")
            self.launcher_service.stop()

    def _maintain_aspect_ratio(self, widget, event):
        """Adjusts the window size to maintain the aspect ratio."""
        new_width = event.width
        new_height = int(new_width / self.aspect_ratio)

        # Prevent recursive resizing by checking if the size is already correct
        if event.height != new_height:
            self.resize(new_width, new_height)

        # Save the new size
        self._save_window_size(new_width, new_height)

    def _initialize_window(self):
        """Initializes the main window properties."""
        self.set_decorated(False)  # Hide the title bar
        self.connect("destroy", Gtk.main_quit)
        self._set_window_icon()

        # Use an overlay to combine the WebView and the resize grip
        self.overlay = Gtk.Overlay()
        self.add(self.overlay)

        self.set_type_hint(Gdk.WindowTypeHint.DIALOG)
        self.connect("window-state-event", self._on_window_state_event)

    def _set_window_icon(self):
        """Sets the window icon if available."""
        icon_theme = Gtk.IconTheme.get_default()
        try:
            icon = icon_theme.load_icon("io.github.archisman_panigrahi.typhoon", 48, 0)  # Load icon of size 48
        except GLib.Error:
            icon = None  # If loading the icon fails, set it to None
        if icon:
            self.set_icon(icon)

    def add_resize_grip(self):
        """Adds a resize grip to the bottom-right corner of the window."""
        grip = Gtk.EventBox()
        grip.set_visible_window(False)

        # Create a label and apply a CSS class to it
        label = Gtk.Label(label="⇲")  # Use the keyword argument "label" to avoid the deprecation warning
        label.get_style_context().add_class("resize-grip")
        grip.add(label)

        grip.connect("button-press-event", self._start_resize)
        grip.connect("motion-notify-event", self._resize_window)
        grip.connect("button-release-event", self._end_resize)

        # Position the grip in the bottom-right corner using the overlay
        self.overlay.add_overlay(grip)
        grip.set_halign(Gtk.Align.END)
        grip.set_valign(Gtk.Align.END)

        # Apply CSS to make the label white
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(b"""
            .resize-grip {
                color: white;
            }
        """)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

    def _start_resize(self, widget, event):
        """Starts the resize operation."""
        self._resizing = True
        self._resize_start_x = event.x_root
        self._resize_start_y = event.y_root
        self._resize_start_width, self._resize_start_height = self.get_size()

    def _resize_window(self, widget, event):
        """Handles the resize operation."""
        if self._resizing:
            delta_x = event.x_root - self._resize_start_x
            new_width = self._resize_start_width + delta_x
            new_height = int(new_width / self.aspect_ratio)
            self.resize(new_width, new_height)

    def _end_resize(self, widget, event):
        """Ends the resize operation."""
        self._resizing = False

    def _setup_webview(self):
        """Sets up the WebKit2 WebView and connects signals."""
        self.webview = WebKit2.WebView()

        # Enable Web Inspector
        # settings = self.webview.get_settings()
        # settings.set_enable_developer_extras(True)

        self.webview.connect("decide-policy", self._handle_policy_decision)
        self.webview.connect("notify::title", self._handle_title_change)
        self.webview.connect("button-press-event", self._handle_mouse_press)

        # Load the local HTML file
        html_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "typhoon.html")
        self.webview.load_uri(f"file://{html_path}")

        # Connect to the load-changed signal
        self.webview.connect("load-changed", self._on_load_changed)

    def _on_load_changed(self, webview, load_event):
        """Handles the load-changed event for the WebView."""
        if load_event == WebKit2.LoadEvent.FINISHED:
            # Try to get the dominant color from the wallpaper
            try:
                wallpaper_path = self.get_wallpaper_path()
                dominant_color = self._extract_dominant_color(wallpaper_path)
                if dominant_color and dominant_color.startswith("#"):
                    print(f"Extracted hex color from wallpaper: {dominant_color}")
                    self.send_message_to_webview(f"'{dominant_color[1:]}'")
                    return
                else:
                    raise ValueError("Invalid color format from wallpaper method")
            except Exception as e:
                print(f"Error determining color from wallpaper: {e}")

            # Fallback to the xprop method
            try:
                # Run xprop and pipe its output to grep
                xprop_process = subprocess.Popen(
                    ["xprop", "-root"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                grep_process = subprocess.Popen(
                    ["grep", "_GNOME_BACKGROUND_REPRESENTATIVE_COLORS"],
                    stdin=xprop_process.stdout,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                xprop_process.stdout.close()  # Allow xprop to receive a SIGPIPE if grep exits
                output, _ = grep_process.communicate()
                # print(f"xprop output: {output}")  # Debugging: Print the raw output

                # Check if the output contains the expected data
                if output and "_GNOME_BACKGROUND_REPRESENTATIVE_COLORS" in output:
                    # Extract the RGB color from the output
                    try:
                        # Extract the part inside the quotes, e.g., "rgb(87,134,72)"
                        rgb_string = output.split('"')[1].strip()
                        # Remove "rgb(" and ")" and split into individual components
                        rgb_values = rgb_string[4:-1].split(",")
                        rgb = tuple(map(int, rgb_values))  # Convert to integers
                        hex_color = "{:02x}{:02x}{:02x}".format(rgb[0], rgb[1], rgb[2])  # Convert to hex
                        print(f"Extracted hex color from xprop: #{hex_color}")
                        self.send_message_to_webview(f"'{hex_color}'")
                    except (IndexError, ValueError) as e:
                        print(f"Error parsing RGB values from xprop: {e}")
                        raise Exception("Fallback to Xdp")
                else:
                    print("No representative colors found in xprop output.")
                    raise Exception("Fallback to Xdp")
            except Exception as e:
                # Fallback to the Xdp method to get accent color
                print(f"Error running xprop or no colors found: {e}")
                self._get_accent_color()

    def _extract_dominant_color(self, wallpaper_path):
        if wallpaper_path.lower().endswith('.svg') and cairosvg:
            # Convert SVG to a tiny PNG in memory
            png_bytes = cairosvg.svg2png(url=wallpaper_path, output_width=16, output_height=16)
            # Load PNG from bytes using GdkPixbuf
            loader = GdkPixbuf.PixbufLoader.new_with_type('png')
            loader.write(png_bytes)
            loader.close()
            pixbuf = loader.get_pixbuf()
            # Get pixel data and average color
            pixels = pixbuf.get_pixels()
            n_channels = pixbuf.get_n_channels()
            width, height = pixbuf.get_width(), pixbuf.get_height()
            r = g = b = count = 0
            for y in range(height):
                for x in range(width):
                    i = (y * width + x) * n_channels
                    r += pixels[i]
                    g += pixels[i+1]
                    b += pixels[i+2]
                    count += 1
            avg = (r // count, g // count, b // count)
            return "#{:02x}{:02x}{:02x}".format(*avg)
        else:
            # Use ImageMagick for non-SVG
            command = f'convert "{wallpaper_path}" -resize 1x1 txt:- | awk \'NR==2 {{print $3}}\''
            dominant_color = subprocess.check_output(command, shell=True, text=True).strip()
            return dominant_color if dominant_color.startswith("#") else None

    def _get_accent_color(self):
        logger.info("Getting System Accent Color")
        portal = Xdp.Portal()
        settings = portal.get_settings()
        hex_color: str
        accent_color = settings.read_value("org.freedesktop.appearance", "accent-color")
        if accent_color is not None:
            r, g, b = accent_color
            hex_color = "{:02x}{:02x}{:02x}".format(int(r*255), int(g*255), int(b*255))
            logger.info(f"Accent color found in settings: '#{hex_color}'")
        else:
            logger.error("Accent color not found in settings")
            logger.warning("Note that currently the accent color only works in GNOME and KDE Plasma 6")
            logger.warning("Using Purple default color")
            hex_color = "575591"
        self.send_message_to_webview(f"'{hex_color}'")
        

    def send_message_to_webview(self, message):
        """Sends a message to the WebView."""
        js_code = f"receiveMessage({message});"  # Call the JavaScript function with the message
        self.webview.evaluate_javascript(js_code, len(js_code), None, None, None)

    def _send_dbus_notification(self, message):
        """Sends a notification via D-Bus asynchronously."""
        try:
            bus = dbus.SessionBus()
            notify_obj = bus.get_object('org.freedesktop.Notifications', '/org/freedesktop/Notifications')
            notify_interface = dbus.Interface(notify_obj, 'org.freedesktop.Notifications')
            
            # Load icon from theme and convert to image-data format
            hints = {"desktop-entry": dbus.String("io.github.archisman_panigrahi.typhoon")}
            
            try:
                icon_theme = Gtk.IconTheme.get_default()
                icon_info = icon_theme.lookup_icon("io.github.archisman_panigrahi.typhoon", 64, 0)
                if icon_info:
                    pixbuf = icon_info.load_icon()
                    if pixbuf:
                        # Convert pixbuf to image-data format for D-Bus
                        width = pixbuf.get_width()
                        height = pixbuf.get_height()
                        rowstride = pixbuf.get_rowstride()
                        has_alpha = pixbuf.get_has_alpha()
                        bits_per_sample = pixbuf.get_bits_per_sample()
                        channels = pixbuf.get_n_channels()
                        image_data = dbus.ByteArray(pixbuf.get_pixels())
                        
                        hints["image-data"] = dbus.Struct(
                            (width, height, rowstride, has_alpha, bits_per_sample, channels, image_data),
                            signature="iiibiiay"
                        )
            except Exception as e:
                print(f"Could not load icon for notification: {e}")
            
            # Notification parameters:
            # app_name, replaces_id, app_icon, summary, body, actions, hints, expire_timeout
            notify_interface.Notify(
                "Weather Alert",  # app_name
                0,  # replaces_id (0 means new notification)
                "io.github.archisman_panigrahi.typhoon",  # app_icon
                message,  # summary
                "",  # body
                [],  # actions
                hints,  # hints with desktop-entry and image-data
                -1  # expire_timeout (-1 for default)
            )
        except Exception as e:
            print(f"Failed to send D-Bus notification: {e}")

    def _setup_scrolled_window(self):
        """Wraps the WebView in a scrolled window and adds it to the overlay."""
        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.add(self.webview)
        self.overlay.add(scrolled_window)

    def _setup_unity_launcher(self):
        """Configures Unity launcher integration if available."""
        if Unity:
            try:
                self.launcher = Unity.LauncherEntry.get_for_desktop_id("io.github.archisman_panigrahi.typhoon.desktop")
                self.launcher.set_property("count_visible", False)
            except NameError:
                self.launcher = None
        else:
            # Fallback to dbus service if Unity is not available
            self.launcher_service = Service()
            self.launcher_thread = threading.Thread(target=self.launcher_service.run, daemon=True)
            self.launcher_thread.start()

    def _set_size_constraints(self):
        """Sets the minimum and maximum size constraints for the window."""
        display = Gdk.Display.get_default()
        monitor = display.get_monitor(0)  # Get the primary monitor
        monitor_geometry = monitor.get_geometry()
        screen_height = monitor_geometry.height  # Get the height of the screen

        # Set minimum size to 300x500 and maximum height to the screen height
        geometry = Gdk.Geometry()
        geometry.min_width = 210
        geometry.min_height = 350
        geometry.max_width = int(screen_height*0.9*3/5)
        geometry.max_height = int(screen_height*0.9)

        self.set_geometry_hints(
            None,  # No specific widget
            geometry,
            Gdk.WindowHints.MIN_SIZE | Gdk.WindowHints.MAX_SIZE,  # Use MAX_SIZE for maximum constraints
        )

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
            # Default to the minimum size if no configuration is found
            return 300, 500

    def _save_window_size(self, width, height):
        """Saves the current window size to a configuration file."""
        config_file = os.path.join(self._get_config_dir(), "typhoon_size.conf")
        with open(config_file, "w") as file:
            file.write(f"{width}x{height}")

    def _get_last_window_position(self):
        """Retrieves the last remembered window position from a configuration file."""
        config_file = os.path.join(self._get_config_dir(), "typhoon_position.conf")
        try:
            with open(config_file, "r") as file:
                position = file.read().strip().split(",")
                x, y = int(position[0]), int(position[1])
                return x, y
        except (FileNotFoundError, ValueError):
            # Return None if no configuration is found
            return None

    def _save_window_position(self, widget, event):
        """Saves the current window position to a configuration file."""
        x, y = self.get_position()
        config_file = os.path.join(self._get_config_dir(), "typhoon_position.conf")
        with open(config_file, "w") as file:
            file.write(f"{x},{y}")

    def _handle_policy_decision(self, webview, decision, decision_type):
        """Handles navigation policy decisions for the WebView."""
        if decision_type == WebKit2.PolicyDecisionType.NAVIGATION_ACTION:
            navigation_action = decision.get_navigation_action()
            uri = navigation_action.get_request().get_uri()
            print(f"Navigation request URI: {uri}")  # Debugging: Print the URI

            if uri.startswith("file://"):
                print("Internal navigation detected, allowing WebView to handle it.")
            else:
                print("Opening Link Externally")
                Gtk.show_uri_on_window(self, uri, 0)
                decision.ignore()  # Prevent WebView from handling the navigation
                return True
        return False

    def _handle_title_change(self, webview, param):
        """Handles title changes in the WebView."""
        title = webview.get_title()
        print(f"{title}")  # Debugging: Print the title

        # Handle notifications requested from the webview via document.title
        if title and title.startswith("notify:"):
            message = title[len("notify:"):]
            if not message:
                message = "Weather alert"
            # Send notification asynchronously via D-Bus to avoid blocking
            threading.Thread(target=self._send_dbus_notification, args=(message,), daemon=True).start()
            return

        if title.startswith("height="):
            try:
                # Extract the height value from the title
                height = int(title.split("=")[1])
                width = int(0.6 * height)  # Calculate the width to maintain the 3:5 aspect ratio

                # Resize the window
                self.resize(width, height)
                print(f"Window resized to width={width}, height={height}")
            except ValueError:
                print("Invalid height value in title.")
        elif title == "close":
            self._toggle_unity_launcher("disable_launcher")
            Gtk.main_quit()
        elif title == "minimize":
            self.iconify()
        elif title == "disabledrag":
            self.drag_enabled = False
        elif title == "enabledrag":
            self.drag_enabled = True
        elif title.startswith("o"):
            self._set_opacity_from_title(title)
        elif title == "reset":
            self._toggle_unity_launcher("disable_launcher")
            self.resize(300, 500)  # Reset the window size to 300x500
        elif title in ["enable_launcher", "disable_launcher"]:
            self._toggle_unity_launcher(title)
        elif title.lstrip('-').isdigit():
            self._update_unity_count(title)

    def _set_opacity_from_title(self, title):
        """Sets the window opacity based on the title."""
        try:
            opacity = float(title[1:])
            # Use gtk_widget_set_opacity for Wayland compatibility
            Gtk.Widget.set_opacity(self, opacity)
        except ValueError:
            pass

    def _toggle_unity_launcher(self, title):
        """Enables or disables the Unity launcher count visibility."""
        if Unity and self.launcher:
            visible = title == "enable_launcher"
            print(f"{'Enabling' if visible else 'Disabling'} Unity launcher count.")
            self.launcher.set_property("count_visible", visible)
        else:
            try:
                if not hasattr(self, "launcher_service"):
                    self.launcher_service = Service()
                    self.launcher_thread = threading.Thread(target=self.launcher_service.run, daemon=True)
                    self.launcher_thread.start()
                visible = title == "enable_launcher"
                print(f"{'Enabling' if visible else 'Disabling'} dbus launcher count.")
                self.launcher_service.Update("application://io.github.archisman_panigrahi.typhoon.desktop", {"count-visible": visible})
            except ValueError:
                pass

    def _update_unity_count(self, title):
        """Updates the Unity launcher count based on the title."""
        if Unity and self.launcher:
            try:
                count = int(title)
                self.launcher.set_property("count", count)
            except (ValueError, NameError):
                pass
        else:
            # Fallback to dbus service if Unity is not available
            try:
                count = int(title)
                if not hasattr(self, "launcher_service"):
                    self.launcher_service = Service()
                    self.launcher_thread = threading.Thread(target=self.launcher_service.run, daemon=True)
                    self.launcher_thread.start()
                self.launcher_service.Update("application://io.github.archisman_panigrahi.typhoon.desktop", {"count": dbus.Int64(count)})
            except ValueError:
                pass

    def get_wallpaper_path(self):
        """Retrieves the current wallpaper path based on the desktop environment."""
        # Detect Flatpak or Snap environment
        if (
            os.environ.get("FLATPAK_ID") is not None
            or os.environ.get("SNAP") is not None
        ):
            raise Exception("Flatpak or Snap detected, use xprop method for wallpaper color.")

        de = os.environ.get("XDG_CURRENT_DESKTOP", "").lower()

        if "gnome" in de:
            command = "gsettings get org.gnome.desktop.background picture-uri"
            wallpaper = subprocess.check_output(command, shell=True).decode().strip().strip("'").split('file://')[-1]
        elif "cinnamon" in de:
            command = "gsettings get org.cinnamon.desktop.background picture-uri"
            wallpaper = subprocess.check_output(command, shell=True).decode().strip().strip("'").split('file://')[-1]
        elif "mate" in de:
            command = "gsettings get org.mate.background picture-filename"
            wallpaper = subprocess.check_output(command, shell=True).decode().strip().strip("'").split('file://')[-1]
        elif "xfce" in de:
            # Use xrandr to get the primary monitor name
            xrandr_output = subprocess.check_output("xrandr --current | grep -w connected", shell=True, text=True)
            primary_monitor = None
            for line in xrandr_output.splitlines():
                if "primary" in line:
                    primary_monitor = line.split()[0]
                    break
            if not primary_monitor:
                # Fallback to the first monitor if no primary is set
                primary_monitor = xrandr_output.splitlines()[0].split()[0]
            # Query xfconf for the wallpaper of the primary monitor, workspace 0
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
                            # If it's a directory, look for jpg or png files
                            print("kde: wallpaper it is a directory")
                            wallpaper = os.path.join(wallpaper, "contents", "images")
                            for file in os.listdir(wallpaper):
                                if file.lower().endswith((".jpg", ".png")):
                                    wallpaper = os.path.join(wallpaper, file)
                                    break
                        break
        else:
            raise Exception(f"Unsupported desktop environment: {de}")

        print(f"Wallpaper path: {wallpaper}")
        return wallpaper

    def _handle_mouse_press(self, widget, event):
        """Handles mouse button press events."""
        if event.button == 3:  # Right mouse button
            return True  # Prevent default right-click behavior
        if self.drag_enabled and event.button in [1, 2]:  # Left or middle button
            self.begin_move_drag(event.button, event.x_root, event.y_root, event.time)

    def _on_window_state_event(self, widget, event):
        # Prevent maximizing only
        if (event.new_window_state & Gdk.WindowState.MAXIMIZED):
            self.unmaximize()
        return False


class Service(dbus.service.Object):
    def __init__(self):
        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
        bus_name = dbus.service.BusName("io.github.archisman_panigrahi.typhoon", dbus.SessionBus())
        dbus.service.Object.__init__(self, bus_name, "/io/github/archisman_panigrahi/typhoon")

    def run(self):
        # Use GLib.idle_add to schedule the Update signal
        GLib.idle_add(lambda: self.Update("application://io.github.archisman_panigrahi.typhoon.desktop", {}))

    @dbus.service.signal(dbus_interface="com.canonical.Unity.LauncherEntry", signature='sa{sv}')
    def Update(self, app_uri, properties):
        print(app_uri, properties)


if __name__ == "__main__":
    app = TyphoonWindow()
    app.show_all()
    Gtk.main()

