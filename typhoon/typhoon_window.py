#!/usr/bin/python3

import sys
import os
import gi
import subprocess  # Import subprocess for xdg-open

gi.require_version("Gtk", "3.0")
try:
    gi.require_version('WebKit2', '4.1')  # Try WebKit2 4.1
except ValueError:
    gi.require_version('WebKit2', '4.0')  # Fallback to WebKit2 4.0
from gi.repository import Gtk, WebKit2, GdkPixbuf

try:
    from gi.repository import Unity
except ImportError:
    Unity = None

class WebKitWindow(Gtk.Window):
    def __init__(self):
        super().__init__(title="Typhoon")
        self.set_default_size(300, 500)
        
        self.set_decorated(False)  # Hide the title bar
        
        self.drag = True  # Initialize drag state

        self.webview = WebKit2.WebView()
        self.webview.connect("decide-policy", self.on_decide_policy)
        self.webview.connect("notify::title", self.on_title_changed)  # Connect to title change signal
        self.webview.connect('button-press-event', self.press_button)  # Connect to button-press-event
        
        icon_theme = Gtk.IconTheme.get_default()
        icon = icon_theme.load_icon("typhoon", 48, 0)  # 48 is the icon size
        if icon:
            self.set_icon(icon)

        # Enable developer tools
        settings = self.webview.get_settings()
        settings.set_property("enable-developer-extras", True)

        # Use relative path to load app.html
        script_dir = os.path.dirname(os.path.abspath(__file__))  # Get the directory of the current script
        local_url = os.path.join(script_dir, "app.html")  # Construct the relative path to app.html
        self.webview.load_uri(f"file://{local_url}")
        
        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.add(self.webview)
        
        self.add(scrolled_window)
        self.connect("destroy", Gtk.main_quit)

        if Unity:
            try:
                launcher = Unity.LauncherEntry.get_for_desktop_id("typhoon.desktop")
                launcher.set_property("count_visible", False)
            except NameError:
                pass
    
    def on_decide_policy(self, webview, decision, decision_type):
        if decision_type == WebKit2.PolicyDecisionType.NAVIGATION_ACTION:
            navigation_action = decision.get_navigation_action()
            request = navigation_action.get_request()
            uri = request.get_uri()
            print(f"Navigation request URI: {uri}")  # Debugging: Print the URI being requested
            if not uri.startswith("file://"):  # If the URI is not a local file
                print("Opening external link with xdg-open.")  # Debugging: Confirm external link handling
                subprocess.run(["xdg-open", uri])  # Open the link using xdg-open
                decision.ignore()  # Prevent the WebView from handling the navigation
                return True
            else:
                print("Internal navigation detected, allowing WebView to handle it.")  # Debugging: Internal navigation
        return False

    def on_title_changed(self, webview, param):
        # Print the title of the HTML file
        title = webview.get_title()
        print(f"{title}")

        if title == "close":
            Gtk.main_quit()
        elif title == "minimize":
            self.iconify()

        # Disables Dragging
        elif title == "disabledrag":
            self.drag = False
        elif title == "enabledrag":
            self.drag = True
        # Opacity
        elif title.startswith("o"):
            try:
                opacity = float(title[1:])
                self.set_opacity(opacity)
            except ValueError:
                pass

        # Unity Counts
        elif title == "enable_launcher":
            print("Enabling..")
            if Unity:
                try:
                    launcher.set_property("count_visible", True)
                except NameError:
                    pass
        elif title == "disable_launcher":
            print("Disabling..")
            if Unity:
                try:
                    launcher.set_property("count_visible", False)
                except NameError:
                    pass

        else:
            if Unity:
                try:
                    launcher.set_property("count", int(title))
                except (NameError, ValueError):
                    pass

    def press_button(self, widget, event):
        if event.button == 3:  # Right mouse button
            return True  # Prevent the default right-click behavior
        if event.button == 2 and self.drag:  # Middle mouse button and drag enabled
            self.begin_move_drag(event.button, event.x_root, event.y_root, event.time)
        if event.button == 1 and self.drag:  # Left mouse button and drag enabled
            self.begin_move_drag(event.button, event.x_root, event.y_root, event.time)

if __name__ == "__main__":
    win = WebKitWindow()
    win.show_all()
    Gtk.main()

