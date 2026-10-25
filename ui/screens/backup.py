# -*- coding: utf-8 -*-
"""
صفحه‌ی مدیریت بکاپ (فقط ادمین)
"""

from kivy.metrics import dp, sp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.button import Button

from kivymd.uix.screen import MDScreen
from kivymd.uix.card import MDCard

from ..helpers.fa import fa
from ..helpers.theme import (
    COLOR_BG, COLOR_PRIMARY, COLOR_PRIMARY_DARK, COLOR_GRAY,
    COLOR_ERROR, COLOR_SUCCESS, COLOR_TEXT, COLOR_WHITE, COLOR_WARNING,
)
from ..helpers.widgets import (
    fa_label, fa_button, spacer, fa_section_title,
)
from ..helpers.dialogs import confirm_dialog, info_dialog

from database import (
    list_backups, manual_backup, restore_backup,
    export_backup_zip, import_backup_zip,
    get_database_size, format_size, format_shamsi_datetime,
    BACKUP_TYPE_NAMES,
)


class BackupScreen(MDScreen):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "backup"
        self.md_bg_color = COLOR_BG

        self.list_container = None
        self.info_label = None

        self.build_ui()

    # ======================================
    # ساخت UI
    # ======================================

    def build_ui(self):

        root = BoxLayout(orientation="vertical")

        # ---------- هدر ----------
        header = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(55),
            padding=[dp(10), dp(8)],
            spacing=dp(10),
        )
        header.add_widget(fa_button(
            "بازگشت",
            size=14,
            height=40,
            bg_color=[0.6, 0.6, 0.6, 1],
            on_press=self.on_back,
        ))
        header.add_widget(fa_label(
            "مدیریت بکاپ",
            size=17,
            color=COLOR_PRIMARY_DARK,
            height=40,
            bold=True,
        ))
        root.add_widget(header)

        # ---------- اطلاعات ----------
        self.info_label = fa_label(
            "",
            size=13,
            color=COLOR_TEXT,
            height=50,
        )
        root.add_widget(self.info_label)

        # ---------- دکمه‌ها ----------
        btns = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(60),
            padding=[dp(10), dp(5)],
            spacing=dp(8),
        )
        btns.add_widget(fa_button(
            "بکاپ جدید",
            size=14,
            height=50,
            bg_color=COLOR_SUCCESS,
            on_press=self.do_manual_backup,
        ))
        btns.add_widget(fa_button(
            "خروجی ZIP",
            size=14,
            height=50,
            bg_color=COLOR_PRIMARY,
            on_press=self.do_export_zip,
        ))
        btns.add_widget(fa_button(
            "ورودی ZIP",
            size=14,
            height=50,
            bg_color=COLOR_PRIMARY_DARK,
            on_press=self.do_import_zip,
        ))
        root.add_widget(btns)

        # ---------- عنوان لیست ----------
        root.add_widget(fa_label(
            "بکاپ‌های موجود (جدیدترین اول):",
            size=13,
            color=COLOR_PRIMARY_DARK,
            height=30,
            bold=True,
            halign="right",
        ))

        # ---------- لیست ----------
        scroll = ScrollView()

        self.list_container = BoxLayout(
            orientation="vertical",
            padding=dp(10),
            spacing=dp(6),
            size_hint_y=None,
        )
        self.list_container.bind(
            minimum_height=self.list_container.setter("height")
        )

        scroll.add_widget(self.list_container)
        root.add_widget(scroll)

        self.add_widget(root)

    # ======================================
    # بارگذاری
    # ======================================

    def on_pre_enter(self, *args):
        self.refresh_list()

    def refresh_list(self):

        size = get_database_size()
        self.info_label.text = fa(
            f"حجم دیتابیس فعلی: {format_size(size)}"
        )

        self.list_container.clear_widgets()

        try:
            backups = list_backups()
        except Exception as e:
            self.list_container.add_widget(fa_label(
                f"خطا: {e}",
                size=13, color=COLOR_ERROR, height=40,
            ))
            return

        if not backups:
            self.list_container.add_widget(fa_label(
                "هیچ بکاپی وجود ندارد.",
                size=14, color=COLOR_GRAY, height=50,
            ))
            return

        for b in backups[:30]:
            self.list_container.add_widget(self._make_card(b))

        if len(backups) > 30:
            self.list_container.add_widget(fa_label(
                f"... و {len(backups) - 30} بکاپ قدیمی‌تر",
                size=12, color=COLOR_GRAY, height=30,
            ))

    # ======================================
    # کارت بکاپ
    # ======================================

    def _make_card(self, b):

        card = MDCard(
            orientation="horizontal",
            padding=dp(10),
            spacing=dp(8),
            size_hint=(1, None),
            height=dp(95),
            elevation=2,
            radius=[dp(10)],
            md_bg_color=[1, 1, 1, 1],
        )

        info = BoxLayout(orientation="vertical")

        btype = BACKUP_TYPE_NAMES.get(b["type"], b["type"])
        shamsi_dt = format_shamsi_datetime(b["mtime"])

        info.add_widget(fa_label(
            f"[{btype}]  {shamsi_dt}",
            size=12,
            color=COLOR_TEXT,
            height=22,
            bold=True,
            halign="right",
        ))

        info.add_widget(fa_label(
            f"حجم: {format_size(b['size'])}",
            size=11,
            color=COLOR_GRAY,
            height=18,
            halign="right",
        ))

        info.add_widget(fa_label(
            b["filename"],
            size=10,
            color=COLOR_GRAY,
            height=16,
            halign="right",
        ))

        card.add_widget(info)

        btns_box = BoxLayout(
            orientation="vertical",
            size_hint_x=None,
            width=dp(90),
            spacing=dp(4),
        )

        restore_btn = Button(
            text=fa("بازیابی"),
            font_name="Vazir",
            font_size=sp(12),
            background_normal="",
            background_color=COLOR_WARNING,
            color=COLOR_WHITE,
            bold=True,
        )
        restore_btn.bind(
            on_release=lambda x, f=b["filename"]: self.do_restore(f)
        )
        btns_box.add_widget(restore_btn)

        if b["type"] == "manual":
            del_btn = Button(
                text=fa("حذف"),
                font_name="Vazir",
                font_size=sp(11),
                background_normal="",
                background_color=COLOR_ERROR,
                color=COLOR_WHITE,
            )
            del_btn.bind(
                on_release=lambda x, f=b["filename"]:
                    self.confirm_delete_backup(f)
            )
            btns_box.add_widget(del_btn)

        card.add_widget(btns_box)
        return card

    # ======================================
    # بکاپ جدید
    # ======================================

    def do_manual_backup(self, *args):
        try:
            path = manual_backup()
        except Exception as e:
            info_dialog("خطا", f"ساخت بکاپ ناموفق:\n{e}")
            return

        if path and not str(path).startswith("ERROR"):
            info_dialog(
                "بکاپ ساخته شد",
                f"فایل بکاپ با موفقیت ذخیره شد.\n\n{path}",
            )
            self.refresh_list()
        else:
            info_dialog("خطا", f"بکاپ ساخته نشد:\n{path}")

    # ======================================
    # بازیابی
    # ======================================

    def do_restore(self, filename):
        confirm_dialog(
            title="بازیابی از بکاپ",
            message=(
                f"آیا از بازیابی از فایل زیر مطمئن هستید؟\n\n"
                f"{filename}\n\n"
                f"⚠️ دیتابیس فعلی جایگزین می‌شود.\n"
                f"(یک بکاپ ایمنی از وضعیت فعلی گرفته می‌شود)"
            ),
            confirm_text="بازیابی",
            cancel_text="لغو",
            confirm_color=COLOR_WARNING,
            on_confirm=lambda: self._perform_restore(filename),
        )

    def _perform_restore(self, filename):
        try:
            restore_backup(filename)
        except Exception as e:
            info_dialog("خطا", f"بازیابی ناموفق:\n{e}")
            return

        info_dialog(
            "بازیابی موفق",
            "دیتابیس با موفقیت بازیابی شد.\n\n"
            "⚠️ لطفاً برنامه را دوباره اجرا کنید.",
        )

    # ======================================
    # حذف بکاپ دستی
    # ======================================

    def confirm_delete_backup(self, filename):
        confirm_dialog(
            title="حذف بکاپ",
            message=f"آیا از حذف «{filename}» مطمئن هستید؟",
            confirm_text="حذف",
            cancel_text="لغو",
            confirm_color=COLOR_ERROR,
            on_confirm=lambda: self._do_delete(filename),
        )

    def _do_delete(self, filename):
        import os
        from database import BACKUP_DIR

        path = os.path.join(BACKUP_DIR, filename)

        try:
            os.remove(path)
            info_dialog("حذف موفق", "بکاپ حذف شد.")
            self.refresh_list()
        except Exception as e:
            info_dialog("خطا", f"حذف ناموفق:\n{e}")

    # ======================================
    # خروجی ZIP
    # ======================================

    def do_export_zip(self, *args):
        try:
            path = export_backup_zip()
        except Exception as e:
            info_dialog("خطا", f"ساخت ZIP ناموفق:\n{e}")
            return

        info_dialog(
            "خروجی ZIP ساخته شد",
            f"فایل ZIP ذخیره شد در:\n\n{path}\n\n"
            f"می‌توانید این فایل را به هرجایی بفرستید\n"
            f"(ایمیل، تلگرام، Google Drive، ...).",
        )

    # ======================================
    # ورودی ZIP
    # ======================================

    def do_import_zip(self, *args):
        from ..helpers.file_dialog import ask_open_zip

        def do_open(zip_path):
            if not zip_path:
                return

            confirm_dialog(
                title="بازیابی از ZIP",
                message=(
                    f"آیا از بازیابی از فایل زیر مطمئن هستید؟\n\n"
                    f"{zip_path}\n\n"
                    f"⚠️ دیتابیس فعلی جایگزین می‌شود."
                ),
                confirm_text="بازیابی",
                cancel_text="لغو",
                confirm_color=COLOR_WARNING,
                on_confirm=lambda: self._do_import_zip(zip_path),
            )

        ask_open_zip(on_open=do_open)

    def _do_import_zip(self, zip_path):
        try:
            import_backup_zip(zip_path)
        except Exception as e:
            info_dialog("خطا", f"بازیابی ناموفق:\n{e}")
            return

        info_dialog(
            "بازیابی موفق",
            "دیتابیس با موفقیت بازیابی شد.\n\n"
            "⚠️ لطفاً برنامه را دوباره اجرا کنید.",
        )

    # ======================================
    # بازگشت
    # ======================================

    def on_back(self, *args):
        from kivymd.app import MDApp
        app = MDApp.get_running_app()

        role = ""
        if app.current_user:
            role = str(app.current_user.get("role", "")).strip().lower()

        self.manager.transition.direction = "right"

        if role == "admin":
            self.manager.current = "admin"
        else:
            self.manager.current = "operator"
