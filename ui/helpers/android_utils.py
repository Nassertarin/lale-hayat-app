# -*- coding: utf-8 -*-
"""
ابزارهای اندروید — تبدیل URI به مسیر فایل
"""

import os
import shutil
import tempfile
from datetime import datetime


def uri_to_path(uri):
    """
    تبدیل content:// URI به مسیر فایل واقعی با کپی به کش موقت.
    اگر uri یک file:// باشد، مسیر مستقیم برمی‌گرداند.
    """
    try:
        from jnius import autoclass, cast

        Uri = autoclass("android.net.Uri")
        Build = autoclass("android.os.Build")
        PythonActivity = autoclass("org.kivy.android.PythonActivity")

        uri_str = str(uri)

        # file:// → مستقیم
        if uri_str.startswith("file://"):
            return uri_str[7:]

        content_resolver = PythonActivity.mActivity.getContentResolver()

        # گرفتن نام نمایشی برای پسوند
        ext = ".jpg"
        try:
            cursor = content_resolver.query(uri, None, None, None, None)
            if cursor is not None and cursor.moveToFirst():
                idx = cursor.getColumnIndex("_display_name")
                if idx >= 0:
                    name = cursor.getString(idx)
                    if name and "." in name:
                        ext = "." + name.rsplit(".", 1)[-1].lower()
                cursor.close()
        except Exception:
            pass

        # کپی به کش
        ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        temp_dir = tempfile.gettempdir()
        dst = os.path.join(temp_dir, f"picked_{ts}{ext}")

        input_stream = content_resolver.openInputStream(uri)
        with open(dst, "wb") as f:
            buf = bytearray(8192)
            while True:
                n = input_stream.read(buf)
                if n <= 0:
                    break
                f.write(buf[:n])
        input_stream.close()

        return dst

    except Exception as e:
        print(f"uri_to_path error: {e}")
        return None
