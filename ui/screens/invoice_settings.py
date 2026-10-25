# -*- coding: utf-8 -*-
"""
صفحه تنظیم نرخ‌های پیش‌فرض صورتحساب
"""
from kivy.metrics import dp, sp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView

from kivymd.uix.screen import MDScreen
from kivymd.uix.card import MDCard

from ..helpers.fa import fa
from ..helpers.theme import (
    COLOR_BG, COLOR_PRIMARY, COLOR_PRIMARY_DARK, COLOR_GRAY,
    COLOR_ERROR, COLOR_SUCCESS, COLOR_TEXT, COLOR_WHITE,
)
from ..helpers.widgets import fa_label, fa_button, spacer, fa_text_input, fa_section_title
from ..helpers.dialogs import info_dialog
from functions import get_invoice_settings, update_invoice_setting


class InvoiceSettingsScreen(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "invoice_settings"
        self.md_bg_color = COLOR_BG

        self.settings_inputs = {}
        self.build_ui()

    def build_ui(self):
        root = BoxLayout(orientation="vertical")

        # هدر
        header = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(55), padding=[dp(10), dp(8)], spacing=dp(10))
        header.add_widget(fa_button("بازگشت", size=14, height=40, bg_color=[0.6, 0.6, 0.6, 1], on_press=self.on_back))
        header.add_widget(fa_label("تنظیم نرخ‌های صورتحساب", size=16, color=COLOR_PRIMARY_DARK, height=40, bold=True))
        root.add_widget(header)

        scroll = ScrollView()
        content = BoxLayout(orientation="vertical", padding=dp(10), spacing=dp(10), size_hint_y=None)
        content.bind(minimum_height=content.setter("height"))

        content.add_widget(fa_label(
            "مقادیر زیر به عنوان نرخ پیش‌فرض در فرم صورتحساب استفاده می‌شوند.",
            size=13, color=COLOR_GRAY, height=40, halign="center"
        ))

        # لیست آیتم‌ها
        items = [
            ("c1_rate", "کشتار مرغ گوشتی"),
            ("c2_rate", "بسته بندی مرغ گوشتی"),
            ("e1_rate", "هزینه یخ مازاد داخل خودرو"),
            ("e2_rate", "بسته بندی دل و کگر و سنگدان"),
            ("e3_rate", "قطعه بندی مرغ"),
            ("e4_rate", "پاکسازی دل و کگر و سنگدان"),
            ("e5_rate", "پوست گیری پای مرغ"),
            ("e6_rate", "صدور مجوز"),
            ("e7_rate", "پالمپ"),
            ("e8_rate", "عوارض دامپزشکی"),
        ]

        # خواندن مقادیر فعلی
        try:
            current_settings = get_invoice_settings()
        except Exception as e:
            info_dialog("خطا", str(e))
            current_settings = {}

        for key, name in items:
            row = MDCard(orientation="horizontal", padding=dp(10), spacing=dp(10), size_hint_y=None, height=dp(70), elevation=1, radius=[dp(10)], md_bg_color=[1, 1, 1, 1])
            
            lbl = fa_label(name, size=13, color=COLOR_TEXT, halign="right", height=50)
            lbl.size_hint_x = 0.6
            row.add_widget(lbl)

            inp = fa_text_input(hint_text="نرخ", text=str(current_settings.get(key, 0)), input_filter="float", height=50)
            inp.size_hint_x = 0.4
            self.settings_inputs[key] = inp
            row.add_widget(inp)

            content.add_widget(row)

        content.add_widget(spacer(20))

        save_btn = fa_button("ذخیره تمام تنظیمات", size=15, height=55, bg_color=COLOR_SUCCESS, on_press=self.on_save)
        content.add_widget(save_btn)

        content.add_widget(spacer(20))
        scroll.add_widget(content)
        root.add_widget(scroll)
        self.add_widget(root)

    def on_save(self, *args):
        try:
            for key, inp in self.settings_inputs.items():
                val = float(inp.text.strip()) if inp.text.strip() else 0.0
                update_invoice_setting(key, val)
        except Exception as e:
            info_dialog("خطا", f"ذخیره ناموفق:\n{e}")
            return
        
        info_dialog("ثبت موفق", "تنظیمات نرخ‌ها با موفقیت ذخیره شد.")

    def on_back(self, *args):
        self.manager.transition.direction = "right"
        self.manager.current = "admin"
