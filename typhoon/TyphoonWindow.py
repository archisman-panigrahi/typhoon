# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
### BEGIN LICENSE
# Copyright (C) 2014 Archisman Panigrahi <apandada1@gmail.com>
# Thanks to Adam Whitcroft <adamwhitcroft.com> for Climacons!
# This program is free software: you can redistribute it and/or modify it 
# under the terms of the GNU General Public License version 3, as published 
# by the Free Software Foundation.
# 
# This program is distributed in the hope that it will be useful, but 
# WITHOUT ANY WARRANTY; without even the implied warranties of 
# MERCHANTABILITY, SATISFACTORY QUALITY, or FITNESS FOR A PARTICULAR 
# PURPOSE.  See the GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License along 
# with this program.  If not, see <http://www.gnu.org/licenses/>.
### END LICENSE

import locale
from locale import gettext as _
locale.textdomain('typhoon')

import gi
# gi.require_version('Gtk', '3.0')  # Explicitly require GTK 3
# gi.require_version('WebKit2', '4.0')  # Explicitly require WebKit2

import subprocess
import logging
from gi.repository import Gtk, WebKit2  # Explicitly using GTK 3 and WebKit2

logger = logging.getLogger('typhoon')

from typhoon_lib import Window
from typhoon_lib.helpers import get_media_file

try:
    from gi.repository import Unity
except ImportError:
    Unity = None


# See typhoon_lib.Window.py for more details about how this class works
class TyphoonWindow(Window):
    __gtype_name__ = "TyphoonWindow"
    
    def finish_initializing(self, builder):  # pylint: disable=E1002
        """Set up the main window"""
        super(TyphoonWindow, self).finish_initializing(builder)

        self.box = self.builder.get_object("box")
        self.window = self.builder.get_object("typhoon_window")
        self.drag = True

        # Code for other initialization actions should be added here.
        self.webview = WebKit2.WebView()  # Explicitly using WebKit2
        self.box.add(self.webview)
        self.webview.props.settings.enable_default_context_menu = False
        self.webviewsettings = self.webview.get_settings()
        self.webviewsettings.set_property("javascript-can-open-windows-automatically", True)
        self.webviewsettings.set_property("enable-universal-access-from-file-uris", True)
        self.webviewsettings.set_property('enable-default-context-menu', False)
        self.webview.load_uri(get_media_file('app.html'))
        self.box.show_all()

        if Unity:
            try:
                launcher = Unity.LauncherEntry.get_for_desktop_id("typhoon.desktop")
                launcher.set_property("count_visible", False)
            except NameError:
                pass

        def navigation_requested_cb(view, frame, networkRequest):
            uri = networkRequest.get_uri()
            subprocess.Popen(['xdg-open', uri])
            return 1

        def console_message_cb(widget, message, line, source):
            logger.debug(f'{source}:{line} "{message}"')  # Updated to f-string
            return True

        def title_changed(widget, frame, title):
            print(title)  # Updated to Python 3 print function

            if title == "close":
                Gtk.main_quit()
            elif title == "minimize":
                self.window.iconify()

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

        def press_button(widget, event):
            if event.button == 1:
                if self.drag:
                    Gtk.Window.begin_move_drag(self.window, event.button, event.x_root, event.y_root, event.time)

        self.webview.connect('title-changed', title_changed)
        self.webview.connect('navigation-requested', navigation_requested_cb)
        self.webview.connect('console-message', console_message_cb)
        self.webview.connect('button-press-event', press_button)
