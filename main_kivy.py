# -*- coding: utf-8 -*-
"""
نقطه‌ی ورود برنامه‌ی گرافیکی
"""

import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

# تنظیمات پنجره
from kivy.config import Config
Config.set("graphics", "width", "480")
Config.set("graphics", "height", "800")
Config.set("graphics", "resizable", "1")
Config.set("kivy", "exit_on_escape", "1")


if __name__ == "__main__":
    from ui.app import LoadingApp
    LoadingApp().run()

