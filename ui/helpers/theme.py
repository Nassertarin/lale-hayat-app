# -*- coding: utf-8 -*-
"""
رنگ‌ها، مسیرها و ثبت فونت
"""

import os
from kivy.core.text import LabelBase
from kivy.utils import get_color_from_hex


# مسیر ریشه‌ی پروژه
BASE_DIR = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)

FONT_PATH = os.path.join(BASE_DIR, "assets", "fonts", "Vazir.ttf")
FONT_BOLD_PATH = os.path.join(BASE_DIR, "assets", "fonts", "Vazir-Bold.ttf")
LOGO_PATH = os.path.join(BASE_DIR, "assets", "images", "logo.png")


# ── ثبت فونت وزیر ──
if os.path.exists(FONT_PATH):
    if os.path.exists(FONT_BOLD_PATH):
        LabelBase.register(
            name="Vazir",
            fn_regular=FONT_PATH,
            fn_bold=FONT_BOLD_PATH,
            fn_italic=FONT_PATH,
            fn_bolditalic=FONT_BOLD_PATH,
        )
        print(f"✅ فونت Vazir + Bold ثبت شد.")
    else:
        LabelBase.register(
            name="Vazir",
            fn_regular=FONT_PATH,
            fn_bold=FONT_PATH,
            fn_italic=FONT_PATH,
            fn_bolditalic=FONT_PATH,
        )
        print(f"⚠️ Vazir-Bold.ttf پیدا نشد. از Vazir.ttf برای Bold استفاده می‌شود.")
else:
    print(f"❌ فونت پیدا نشد: {FONT_PATH}")


# ---------- رنگ‌ها ----------
COLOR_PRIMARY = get_color_from_hex("#1B9E8F")
COLOR_PRIMARY_DARK = get_color_from_hex("#137a6f")
COLOR_BG = get_color_from_hex("#F5F5F5")
COLOR_CARD = [1, 1, 1, 1]
COLOR_ERROR = get_color_from_hex("#D32F2F")
COLOR_SUCCESS = get_color_from_hex("#2E7D32")
COLOR_WARNING = get_color_from_hex("#F57C00")
COLOR_GRAY = [0.4, 0.4, 0.4, 1]
COLOR_LIGHT_GRAY = [0.7, 0.7, 0.7, 1]
COLOR_WHITE = [1, 1, 1, 1]
COLOR_TEXT = get_color_from_hex("#212121")
