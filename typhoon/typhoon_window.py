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
from gi.repository import Gtk, WebKit2, GdkPixbuf

try:
    from gi.repository import Unity
except ImportError:
    Unity = None


class TyphoonWindow(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, title="Typhoon")
        self._initialize_window()
        self._setup_webview()
        self._setup_scrolled_window()
        self._setup_unity_launcher()
        self.drag_enabled = True  # Enable dragging by default

    def _initialize_window(self):
        """Initializes the main window properties."""
        self.set_default_size(300, 500)
        self.set_decorated(False)  # Hide the title bar
        self.connect("destroy", Gtk.main_quit)
        self._set_window_icon()

    def _set_window_icon(self):
        """Sets the window icon if available."""
        icon_theme = Gtk.IconTheme.get_default()
        icon = icon_theme.load_icon("typhoon", 48, 0)  # Load icon of size 48
        if icon:
            self.set_icon(icon)

    def _setup_webview(self):
        """Sets up the WebKit2 WebView and connects signals."""
        self.webview = WebKit2.WebView()
        self.webview.connect("decide-policy", self._handle_policy_decision)
        self.webview.connect("notify::title", self._handle_title_change)
        self.webview.connect("button-press-event", self._handle_mouse_press)

        # Enable developer tools in the WebView
        settings = self.webview.get_settings()
        settings.set_property("enable-developer-extras", True)

        # Load the local HTML file
        html_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app.html")
        self.webview.load_uri(f"file://{html_path}")

    def _setup_scrolled_window(self):
        """Wraps the WebView in a scrolled window and adds it to the main window."""
        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.add(self.webview)
        self.add(scrolled_window)

    def _setup_unity_launcher(self):
        """Configures Unity launcher integration if available."""
        if Unity:
            try:
                self.launcher = Unity.LauncherEntry.get_for_desktop_id("typhoon.desktop")
                self.launcher.set_property("count_visible", False)
            except NameError:
                self.launcher = None

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

        if title == "close":
            Gtk.main_quit()
        elif title == "minimize":
            self.iconify()
        elif title == "disabledrag":
            self.drag_enabled = False
        elif title == "enabledrag":
            self.drag_enabled = True
        elif title.startswith("o"):
            self._set_opacity_from_title(title)
        elif title in ["enable_launcher", "disable_launcher"]:
            self._toggle_unity_launcher(title)
        else:
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

