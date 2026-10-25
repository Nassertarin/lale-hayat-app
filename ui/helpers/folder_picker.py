# -*- coding: utf-8 -*-
"""
انتخاب پوشه — cross-platform
"""

import os
import platform


def pick_folder_via_tkinter(initial_dir=None):
    """
    باز کردن دیالوگ انتخاب پوشه با tkinter.
    فقط روی دسکتاپ (ویندوز/لینوکس/مک).
    اگه نشد، None برمی‌گردونه.
    """

    if platform.system() == "Android":
        return None

    try:
        import tkinter as tk
        from tkinter import filedialog

        # مخفی کردن پنجره‌ی اصلی tkinter
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)

        if initial_dir is None:
            initial_dir = os.path.expanduser("~")

        folder = filedialog.askdirectory(
            title="انتخاب پوشه",
            initialdir=initial_dir,
            mustexist=False,
        )

        root.destroy()

        if folder:
            return folder
        return None

    except Exception as e:
        print(f"❌ خطا در tkinter: {e}")
        return None


def is_folder_picker_available():
    """آیا انتخاب پوشه‌ی بومی ممکنه؟"""
    if platform.system() == "Android":
        return False

    try:
        import tkinter
        return True
    except ImportError:
        return False
