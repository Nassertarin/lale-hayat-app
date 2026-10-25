# -*- coding: utf-8 -*-
"""
دیالوگ انتخاب مسیر ذخیره (با پشتیبانی از انتخاب پوشه)
"""

import os
from datetime import datetime

from kivy.metrics import dp, sp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.popup import Popup
from kivy.uix.button import Button
from kivy.graphics import Color, RoundedRectangle

from .fa import fa
from .theme import (
    COLOR_PRIMARY, COLOR_PRIMARY_DARK, COLOR_ERROR,
    COLOR_TEXT, COLOR_WHITE, COLOR_SUCCESS, COLOR_GRAY,
)
from .widgets import fa_label, fa_text_input
from .file_utils import get_default_reports_dir


class SaveDialog(Popup):
    """
    دیالوگ انتخاب مسیر و نام فایل برای ذخیره.

    روی دسکتاپ (ویندوز/لینوکس/مک): دکمه‌ی «انتخاب...» نمایش داده می‌شود.
    روی اندروید: کاربر باید مسیر را دستی وارد کند.
    """

    def __init__(
        self,
        title="ذخیره فایل",
        default_folder=None,
        default_filename="",
        file_extension=".pdf",
        on_save=None,
        **kwargs,
    ):
        super().__init__(**kwargs)

        self.on_save = on_save
        self.file_extension = file_extension

        if default_folder is None:
            default_folder = get_default_reports_dir()

        # ---- تنظیمات Popup ----
        self.title = ""
        self.title_size = 0
        self.size_hint = (None, None)
        self.size = (dp(500), dp(430))
        self.auto_dismiss = False
        self.background = ""
        self.background_color = [0, 0, 0, 0.5]
        self.separator_height = 0

        # ---- محتوا ----
        content = BoxLayout(
            orientation="vertical",
            padding=dp(20),
            spacing=dp(12),
        )

        with content.canvas.before:
            Color(1, 1, 1, 1)
            content._bg = RoundedRectangle(
                pos=content.pos,
                size=content.size,
                radius=[dp(10)],
            )
        content.bind(
            pos=lambda s, v: setattr(s._bg, "pos", v),
            size=lambda s, v: setattr(s._bg, "size", v),
        )

        # ---- عنوان ----
        content.add_widget(fa_label(
            title,
            size=17,
            color=COLOR_PRIMARY_DARK,
            height=35,
            bold=True,
        ))

        # ---- پوشه ----
        content.add_widget(fa_label(
            "پوشه‌ی ذخیره:",
            size=13,
            color=COLOR_TEXT,
            height=22,
            bold=True,
            halign="right",
        ))

        folder_row = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(50),
            spacing=dp(6),
        )

        self.folder_wrap = fa_text_input(
            hint_text="مسیر پوشه",
            text=default_folder,
            height=50,
        )
        folder_row.add_widget(self.folder_wrap)

        from .folder_picker import is_folder_picker_available

        if is_folder_picker_available():
            browse_btn = Button(
                text=fa("انتخاب..."),
                font_name="Vazir",
                font_size=sp(13),
                size_hint=(None, 1),
                width=dp(100),
                background_normal="",
                background_color=COLOR_PRIMARY_DARK,
                color=COLOR_WHITE,
                bold=True,
            )
            browse_btn.bind(on_release=self._browse_folder)
            folder_row.add_widget(browse_btn)

        content.add_widget(folder_row)

        # ---- نام فایل ----
        content.add_widget(fa_label(
            f"نام فایل (پسوند {file_extension} اضافه می‌شود):",
            size=13,
            color=COLOR_TEXT,
            height=22,
            bold=True,
            halign="right",
        ))

        if default_filename.endswith(file_extension):
            default_filename = default_filename[:-len(file_extension)]

        self.name_wrap = fa_text_input(
            hint_text="نام فایل بدون پسوند",
            text=default_filename,
            height=50,
        )
        content.add_widget(self.name_wrap)

        # ---- پیام خطا ----
        self.error_label = fa_label(
            "",
            size=12,
            color=COLOR_ERROR,
            height=25,
        )
        content.add_widget(self.error_label)

        # ---- دکمه‌ها ----
        btns = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(55),
            spacing=dp(8),
        )

        cancel_btn = Button(
            text=fa("لغو"),
            font_name="Vazir",
            font_size=sp(15),
            background_normal="",
            background_color=[0.7, 0.7, 0.7, 1],
            color=COLOR_WHITE,
            bold=True,
        )

        save_btn = Button(
            text=fa("ذخیره"),
            font_name="Vazir",
            font_size=sp(15),
            background_normal="",
            background_color=COLOR_PRIMARY,
            color=COLOR_WHITE,
            bold=True,
        )

        btns.add_widget(cancel_btn)
        btns.add_widget(save_btn)
        content.add_widget(btns)

        self.add_widget(content)

        cancel_btn.bind(on_release=lambda x: self.dismiss())
        save_btn.bind(on_release=self._do_save)

    # ======================================
    # انتخاب پوشه
    # ======================================

    def _browse_folder(self, *args):
        from .folder_picker import pick_folder_via_tkinter

        current = self.folder_wrap.text.strip()
        if not current or not os.path.isdir(current):
            current = None

        folder = pick_folder_via_tkinter(initial_dir=current)

        if folder:
            self.folder_wrap.text = folder

    # ======================================
    # ذخیره
    # ======================================

    def _show_error(self, msg):
        self.error_label.text = fa(msg)

    def _do_save(self, *args):

        folder = self.folder_wrap.text.strip()
        name = self.name_wrap.text.strip()

        if not folder:
            self._show_error("پوشه را وارد کنید.")
            return

        if not name:
            self._show_error("نام فایل را وارد کنید.")
            return

        invalid = '<>:"/\\|?*'
        for ch in invalid:
            name = name.replace(ch, "_")

        try:
            os.makedirs(folder, exist_ok=True)
        except Exception as e:
            self._show_error(f"ساخت پوشه ناموفق: {e}")
            return

        if not name.endswith(self.file_extension):
            filename = name + self.file_extension
        else:
            filename = name

        filepath = os.path.join(folder, filename)

        if os.path.exists(filepath):
            base, ext = os.path.splitext(filename)
            ts = datetime.now().strftime("%H%M%S")
            filename = f"{base}_{ts}{ext}"
            filepath = os.path.join(folder, filename)

        self.dismiss()
        if self.on_save:
            self.on_save(filepath)


# ==========================================
# توابع عمومی
# ==========================================

def ask_save_path(
    title="ذخیره فایل",
    default_filename="",
    file_extension=".pdf",
    on_save=None,
):
    dialog = SaveDialog(
        title=title,
        default_filename=default_filename,
        file_extension=file_extension,
        on_save=on_save,
    )
    dialog.open()
    return dialog


def ask_open_after_save(on_yes, on_no=None):
    from .dialogs import confirm_dialog

    confirm_dialog(
        title="فایل ساخته شد",
        message="آیا می‌خواهید فایل را ببینید؟",
        confirm_text="بله، باز کن",
        cancel_text="نه",
        confirm_color=COLOR_PRIMARY,
        on_confirm=on_yes,
    )


# ==========================================
# انتخاب فایل ZIP
# ==========================================

def ask_open_zip(on_open=None):
    """
    دیالوگ انتخاب فایل ZIP برای بازیابی.
    روی دسکتاپ: با tkinter
    روی اندروید: به‌زودی
    """
    import platform

    if platform.system() == "Android":
        from .dialogs import info_dialog
        info_dialog(
            "به‌زودی",
            "این قابلیت در اندروید به‌زودی اضافه می‌شود."
        )
        return

    try:
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)

        zip_path = filedialog.askopenfilename(
            title="انتخاب فایل ZIP",
            filetypes=[
                ("ZIP files", "*.zip"),
                ("All files", "*.*"),
            ],
        )

        root.destroy()

        if zip_path and on_open:
            on_open(zip_path)

    except ImportError:
        from .dialogs import info_dialog
        info_dialog("خطا", "tkinter نصب نیست.")
    except Exception as e:
        from .dialogs import info_dialog
        info_dialog("خطا", f"خطا در باز کردن دیالوگ:\n{e}")
