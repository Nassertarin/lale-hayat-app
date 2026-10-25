# -*- coding: utf-8 -*-
"""
ابزارهای فارسی‌سازی متن برای Kivy
"""

import arabic_reshaper
from bidi.algorithm import get_display


def fa(text):
    """تبدیل متن فارسی برای نمایش در Kivy (چسباندن حروف + RTL)"""
    if text is None:
        return ""
    if not text:
        return ""
    reshaped = arabic_reshaper.reshape(str(text))
    return get_display(reshaped)


def fa_num(number, decimals=2):
    """نمایش عدد با جداکننده هزارگان"""
    return get_display(f"{number:,.{decimals}f}")
