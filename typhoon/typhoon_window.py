#!/usr/bin/python3

import os
import sys
import gi
import subprocess  # For opening external links with xdg-open

gi.require_version("Gtk", "3.0")
try:
    gi.require_version("WebKit2", "4.1")  # Attempt to use WebKit2 4.1
except ValueError:
    gi.require_version("WebKit2", "4.0")  # Fallback to WebKit2 4.0
from gi.repository import Gtk, WebKit2, GdkPixbuf, Gdk

try:
    from gi.repository import Unity
except ImportError:
    Unity = None


class TyphoonWindow(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, title="Typhoon")
        self.aspect_ratio = 3/5  # Desired aspect ratio (width / height)
        self._initialize_window()
        self._setup_webview()
        self._setup_scrolled_window()
        self._setup_unity_launcher()
        self.drag_enabled = True  # Enable dragging by default

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

    def _set_window_icon(self):
        """Sets the window icon if available."""
        icon_theme = Gtk.IconTheme.get_default()
        icon = icon_theme.load_icon("typhoon", 48, 0)  # Load icon of size 48
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
            # Run the xprop command to get the GNOME background representative colors
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
                        print(f"Extracted hex color: {hex_color}")  # Debugging: Print the hex color

                        # Send the hex color to the WebView
                        self.send_message_to_webview(f"'{hex_color}'")
                    except (IndexError, ValueError) as e:
                        print(f"Error parsing RGB values: {e}")
                        self.send_message_to_webview("'575591'")  # Default to purple
                else:
                    print("No representative colors found in xprop output.")
                    self.send_message_to_webview("'575591'")  # Default to purple
            except Exception as e:
                print(f"Error running xprop: {e}")
                self.send_message_to_webview("'575591'")  # Default to purple

    def send_message_to_webview(self, message):
        """Sends a message to the WebView."""
        js_code = f"receiveMessage({message});"  # Call the JavaScript function with the message
        self.webview.run_javascript(js_code, None, None, None)

    def _setup_scrolled_window(self):
        """Wraps the WebView in a scrolled window and adds it to the overlay."""
        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.add(self.webview)
        self.overlay.add(scrolled_window)

    def _setup_unity_launcher(self):
        """Configures Unity launcher integration if available."""
        if Unity:
            try:
                self.launcher = Unity.LauncherEntry.get_for_desktop_id("typhoon.desktop")
                self.launcher.set_property("count_visible", False)
            except NameError:
                self.launcher = None

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

    def _get_last_window_size(self):
        """Retrieves the last remembered window size from a configuration file."""
        config_file = os.path.expanduser("~/.config/typhoon_size.conf")
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
        config_file = os.path.expanduser("~/.config/typhoon_size.conf")
        with open(config_file, "w") as file:
            file.write(f"{width}x{height}")

    def _get_last_window_position(self):
        """Retrieves the last remembered window position from a configuration file."""
        config_file = os.path.expanduser("~/.config/typhoon_position.conf")
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
        config_file = os.path.expanduser("~/.config/typhoon_position.conf")
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
                print("Opening external link with xdg-open.")
                subprocess.run(["xdg-open", uri])  # Open external links
                decision.ignore()  # Prevent WebView from handling the navigation
                return True
        return False

    def _handle_title_change(self, webview, param):
        """Handles title changes in the WebView."""
        title = webview.get_title()
        print(f"{title}")  # Debugging: Print the title

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
            self.resize(300, 500)  # Reset the window size to 300x500
        elif title in ["enable_launcher", "disable_launcher"]:
            self._toggle_unity_launcher(title)
        else:
            self._update_unity_count(title)

    def _set_opacity_from_title(self, title):
        """Sets the window opacity based on the title."""
        try:
            opacity = float(title[1:])
            if self.get_window():  # Ensure the window is realized
                self.get_window().set_opacity(opacity)
        except ValueError:
            pass

    def _toggle_unity_launcher(self, title):
        """Enables or disables the Unity launcher count visibility."""
        if Unity and self.launcher:
            visible = title == "enable_launcher"
            print(f"{'Enabling' if visible else 'Disabling'} Unity launcher count.")
            self.launcher.set_property("count_visible", visible)

    def _update_unity_count(self, title):
        """Updates the Unity launcher count based on the title."""
        if Unity and self.launcher:
            try:
                count = int(title)
                self.launcher.set_property("count", count)
            except (ValueError, NameError):
                pass

    def _handle_mouse_press(self, widget, event):
        """Handles mouse button press events."""
        if event.button == 3:  # Right mouse button
            return True  # Prevent default right-click behavior
        if self.drag_enabled and event.button in [1, 2]:  # Left or middle button
            self.begin_move_drag(event.button, event.x_root, event.y_root, event.time)


if __name__ == "__main__":
    app = TyphoonWindow()
    app.show_all()
    Gtk.main()

