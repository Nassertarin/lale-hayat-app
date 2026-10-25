# -*- coding: utf-8 -*-
"""
ابزارهای تاریخ شمسی (بازه‌های آماده)
"""

from datetime import datetime, timedelta

try:
    import jdatetime
    HAS_JDATETIME = True
except ImportError:
    HAS_JDATETIME = False


def today_shamsi():
    """امروز به شمسی"""
    if HAS_JDATETIME:
        return jdatetime.date.today().strftime("%Y/%m/%d")
    return datetime.now().strftime("%Y/%m/%d")


def date_to_shamsi(date_obj):
    """تبدیل datetime میلادی به شمسی"""
    if HAS_JDATETIME:
        return jdatetime.date.fromgregorian(
            date=date_obj
        ).strftime("%Y/%m/%d")
    return date_obj.strftime("%Y/%m/%d")


def get_preset_range(preset):
    """
    برگرداندن (date_from, date_to) برای بازه‌های آماده.
    preset: today / week / month / all
    """

    if preset == "all":
        return (None, None)

    today = datetime.now()

    if preset == "today":
        start = today

    elif preset == "week":
        # ۷ روز اخیر
        start = today - timedelta(days=7)

    elif preset == "month":
        # ۳۰ روز اخیر
        start = today - timedelta(days=30)

    else:
        return (None, None)

    return (
        date_to_shamsi(start),
        date_to_shamsi(today),
    )


def validate_shamsi_date(text):
    """
    بررسی اعتبار تاریخ شمسی.
    نمونه: 1404/07/15
    """
    if not text:
        return None

    text = text.replace("-", "/")
    parts = text.split("/")

    if len(parts) != 3:
        return None

    try:
        y = int(parts[0])
        m = int(parts[1])
        d = int(parts[2])
    except ValueError:
        return None

    if not (1300 <= y <= 1500):
        return None
    if not (1 <= m <= 12):
        return None
    if not (1 <= d <= 31):
        return None

    return f"{y:04d}/{m:02d}/{d:02d}"
