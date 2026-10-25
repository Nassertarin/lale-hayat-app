# -*- coding: utf-8 -*-
"""
ابزارهای کار با فایل — انتخاب مسیر، باز کردن فایل
"""

import os
import sys
import subprocess
import platform


def open_folder_in_explorer(folder_path):
    """باز کردن پوشه در File Explorer"""
    if not os.path.exists(folder_path):
        return False

    try:
        if platform.system() == "Windows":
            os.startfile(folder_path)
        elif platform.system() == "Darwin":  # macOS
            subprocess.Popen(["open", folder_path])
        else:  # Linux
            subprocess.Popen(["xdg-open", folder_path])
        return True
    except Exception:
        return False


def open_file(path):
    """باز کردن فایل با برنامه‌ی پیش‌فرض سیستم"""
    if not os.path.exists(path):
        return False

    try:
        if platform.system() == "Windows":
            os.startfile(path)
        elif platform.system() == "Darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
        return True
    except Exception:
        return False


def get_default_reports_dir():
    """پوشه‌ی پیش‌فرض گزارش‌ها (Android-safe)"""
    import sys
    if hasattr(sys, "getandroidapilevel") or "ANDROID_ARGUMENT" in os.environ:
        from kivy.app import App
        app = App.get_running_app()
        base = app.user_data_dir if app else os.path.expanduser("~")
    else:
        base = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
    reports_dir = os.path.join(base, "reports")
    os.makedirs(reports_dir, exist_ok=True)
    return reports_dir
