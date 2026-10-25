# -*- coding: utf-8 -*-
"""
انتخاب عکس از گالری یا گرفتن عکس با دوربین.
- اندروید: دوربین با plyer + گالری با Intent
- دسکتاپ: فایل‌پیکر با tkinter
"""

import os
import platform
import shutil
import tempfile
from datetime import datetime


def is_android():
    return platform.system() == "Android"


def is_camera_available():
    if is_android():
        try:
            from plyer import camera
            return True
        except Exception:
            return False
    # روی دسکتاپ دوربین معمولاً نیست
    return False


def is_gallery_available():
    return True


# ==========================================
# دوربین (اندروید)
# ==========================================

def take_photo():
    """
    گرفتن عکس با دوربین.
    خروجی: مسیر فایل موقت (jpg) یا None.
    """
    if not is_android():
        return None

    try:
        from plyer import camera
    except ImportError:
        return None

    try:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        temp_dir = tempfile.gettempdir()
        path = os.path.join(temp_dir, f"receipt_{ts}.jpg")

        camera.take_picture(filename=path, on_complete=None)

        # plyer async است؛ معمولاً بعد از برگشت on_complete
        # ولی اگر کار نکرد، فایل ممکن است هنوز ساخته نشده باشد
        return path if os.path.exists(path) else None

    except Exception as e:
        print(f"Camera error: {e}")
        return None


# ==========================================
# گالری (اندروید)
# ==========================================

def pick_from_gallery_android(on_result):
    """
    باز کردن گالری اندروید با Intent.
    on_result(path_or_none) وقتی انتخاب شد صدا زده می‌شود.

    نیاز به این در buildozer.spec:
        android.permissions = READ_EXTERNAL_STORAGE
        android.add_src = ...
    """
    if not is_android():
        on_result(None)
        return

    try:
        from android import activity
        from android.permissions import request_permissions, Permission
        from jnius import autoclass, cast

        Intent = autoclass("android.content.Intent")
        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        Uri = autoclass("android.net.Uri")

        def on_activity_result(request_code, result_code, data):
            if request_code != 0x101:
                return
            activity.unbind(on_activity_result=on_activity_result)

            if result_code != -1:  # RESULT_OK
                on_result(None)
                return

            try:
                uri = data.getData()
                # خواندن مسیر از URI
                from helpers.android_utils import uri_to_path
                path = uri_to_path(uri)
                on_result(path)
            except Exception as e:
                print(f"URI error: {e}")
                on_result(None)

        request_permissions([
            Permission.READ_EXTERNAL_STORAGE,
        ])

        intent = Intent(Intent.ACTION_GET_CONTENT)
        intent.setType("image/*")
        intent.addCategory(Intent.CATEGORY_OPENABLE)

        current = PythonActivity.mActivity
        activity.bind(on_activity_result=on_activity_result)
        current.startActivityForResult(
            Intent.createChooser(intent, "انتخاب عکس"),
            0x101,
        )

    except Exception as e:
        print(f"Gallery error: {e}")
        on_result(None)


# ==========================================
# گالری (دسکتاپ)
# ==========================================

def pick_from_gallery_desktop():
    if is_android():
        return None

    try:
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)

        path = filedialog.askopenfilename(
            title="انتخاب عکس قبض",
            filetypes=[
                ("Image files", "*.jpg *.jpeg *.png *.bmp"),
                ("All files", "*.*"),
            ],
        )

        root.destroy()
        return path or None

    except Exception as e:
        print(f"Desktop gallery error: {e}")
        return None


def pick_image(source="gallery", on_result=None):
    """
    entry point اصلی:
    - source = "camera" → دوربین (اندروید)
    - source = "gallery" → گالری (اندروید) یا فایل‌پیکر (دسکتاپ)
    """
    if source == "camera":
        path = take_photo()
        if on_result:
            on_result(path)
        return path

    # gallery
    if is_android():
        pick_from_gallery_android(on_result or (lambda p: None))
        return None
    else:
        path = pick_from_gallery_desktop()
        if on_result:
            on_result(path)
        return path
