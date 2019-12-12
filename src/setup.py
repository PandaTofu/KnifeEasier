#!/usr/bin/env python
# -*- coding: utf-8 -*-

from distutils.core import setup
import py2exe
import glob


options = {"py2exe":{"compressed": 1, "optimize": 2, "bundle_files": 1}}

data_files=[("images",  glob.glob("images\\*.png")), ("qss", ["qss/knife_ui.qss"]), ("conf", ["conf/config.js"])]
setup(windows=[{"script": "KnifeEasier.py", "icon_resources": [(1, 'bug.ico')]}], data_files=data_files, options=options)

