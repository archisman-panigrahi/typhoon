#!/usr/bin/python
# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
### BEGIN LICENSE
# Copyright (C) 2013 Archisman Panigrahi <apandada1@gmail.com>
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

import sys
import os.path
import unittest
from typhoon import AboutTyphoonDialog

sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), "..")))

class TestExample(unittest.TestCase):
    def setUp(self):
        self.AboutTyphoonDialog_members = [
        'AboutDialog', 'AboutTyphoonDialog', 'gettext', 'logger', 'logging']

    def test_AboutTyphoonDialog_members(self):
        all_members = dir(AboutTyphoonDialog)
        public_members = [x for x in all_members if not x.startswith('_')]
        public_members.sort()
        self.assertEqual(self.AboutTyphoonDialog_members, public_members)

if __name__ == '__main__':    
    unittest.main()
