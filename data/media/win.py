import sys
import os
import gi
import subprocess  # Import subprocess for xdg-open

gi.require_version("Gtk", "3.0")
gi.require_version("WebKit2", "4.1")
from gi.repository import Gtk, WebKit2

class WebKitWindow(Gtk.Window):
    def __init__(self):
        super().__init__(title="WebKit Window")
        self.set_default_size(300, 500)
        
        self.webview = WebKit2.WebView()
        self.webview.connect("decide-policy", self.on_decide_policy)
        self.webview.connect("notify::title", self.on_title_changed)  # Connect to title change signal
        local_url = os.path.abspath("app.html")
        self.webview.load_uri(f"file://{local_url}")
        
        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.add(self.webview)
        
        self.add(scrolled_window)
        self.connect("destroy", Gtk.main_quit)
    
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
        print(f"{webview.get_title()}")

if __name__ == "__main__":
    win = WebKitWindow()
    win.show_all()
    Gtk.main()

