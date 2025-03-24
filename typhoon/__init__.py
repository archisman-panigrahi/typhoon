# -*- coding: utf-8 -*-
### BEGIN LICENSE
# Copyright (C) 2014 Archisman Panigrahi <apandada1@gmail.com>
# Thanks to Adam Whitcroft <adamwhitcroft.com> for Climacons!
# This program is free software: you can redistribute it and/or modify it 
# under the terms of the GNU General Public License version 3, as published 
# by the Free Software Foundation.
# 
# This program is distributed in the hope that it will be useful, but 
# WITHOUT ANY WARRANTY; without even the implied warranty of 
# MERCHANTABILITY, SATISFACTORY QUALITY, or FITNESS FOR A PARTICULAR 
# PURPOSE.  See the GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License along 
# with this program.  If not, see <http://www.gnu.org/licenses/>.
### END LICENSE

import argparse
import locale
from locale import gettext as _
locale.textdomain('typhoon')

import gi
gi.require_version('Gtk', '3.0')  # Explicitly require GTK 3
try:
    gi.require_version('WebKit2', '4.0')  # Try WebKit2 4.0
except ValueError:
    gi.require_version('WebKit2', '4.1')  # Fallback to WebKit2 4.1

from gi.repository import Gtk  # pylint: disable=E0611

from typhoon import TyphoonWindow
from typhoon_lib import set_up_logging, get_version


def parse_options():
    """Support for command line options"""
    parser = argparse.ArgumentParser(description="Typhoon Weather Application")
    parser.add_argument(
        "-v", "--verbose", action="count", dest="verbose", default=0,
        help=_("Show debug messages (-vv debugs typhoon_lib also)")
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {get_version()}",
        help=_("Show program's version number and exit")
    )
    options = parser.parse_args()

    set_up_logging(options)


def main():
    """Constructor for your class instances"""
    parse_options()

    # Run the application.
    window = TyphoonWindow.TyphoonWindow()
    window.show()
    Gtk.main()
