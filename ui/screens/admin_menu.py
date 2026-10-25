# -*- coding: utf-8 -*-
"""
منوی ادمین
"""

from kivy.metrics import dp
from kivy.uix.anchorlayout import AnchorLayout

from kivymd.uix.screen import MDScreen
from kivymd.uix.card import MDCard

from ..helpers.fa import fa
from ..helpers.theme import (
    COLOR_BG,
    COLOR_PRIMARY_DARK,
    COLOR_GRAY,
    COLOR_ERROR,
)
from ..helpers.widgets import fa_label, fa_button, spacer


class AdminMenuScreen(MDScreen):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "admin"
        self.md_bg_color = COLOR_BG
        self.build_ui()

    def build_ui(self):

        root = AnchorLayout(anchor_x="center", anchor_y="center")

        card = MDCard(
            orientation="vertical",
            padding=dp(20),
            spacing=dp(10),
            size_hint=(None, None),
            size=(dp(400), dp(880)),
            pos_hint={"center_x": 0.5, "center_y": 0.5},
            elevation=3,
            radius=[dp(15)],
            md_bg_color=[1, 1, 1, 1],
        )

        card.add_widget(fa_label(
            "پنل مدیریت",
            size=22, color=COLOR_PRIMARY_DARK, height=40, bold=True,
        ))

        card.add_widget(spacer(4))

        self.welcome_label = fa_label(
            "", size=14, color=COLOR_GRAY, height=30,
        )
        card.add_widget(self.welcome_label)

        card.add_widget(spacer(15))

        card.add_widget(fa_button(
            "کشتارهای امروز",
            size=16, height=60,
            on_press=self.on_slaughters_list,
        ))

        card.add_widget(spacer(4))

        card.add_widget(fa_button(
            "مدیریت اطلاعات پایه",
            size=15, height=55,
            on_press=self.on_base_data,
        ))
        
        card.add_widget(fa_button(
            "جستجوی پیشرفته",
            size=15, height=55,
            on_press=self.on_search,
        ))

        card.add_widget(fa_button(
            "گزارش‌گیری جامع",
            size=15, height=55,
            on_press=self.on_reports,
        ))

        card.add_widget(fa_button(
            "تنظیم نرخ‌های صورتحساب",
            size=15, height=55,
            on_press=self.on_invoice_settings,
        ))

        card.add_widget(fa_button(
            "مدیریت بکاپ",
            size=15, height=55,
            on_press=self.on_backup,
        ))

        card.add_widget(spacer(20))

        card.add_widget(fa_button(
            "خروج از حساب",
            size=15, height=50,
            bg_color=COLOR_ERROR,
            on_press=self.on_logout,
        ))

        root.add_widget(card)
        self.add_widget(root)

    # ======================================

    def on_pre_enter(self, *args):
        from kivymd.app import MDApp
        app = MDApp.get_running_app()
        if app.current_user:
            self.welcome_label.text = fa(
                f"خوش آمدید {app.current_user['full_name']}"
            )

    # ======================================

    def on_slaughters_list(self, *args):
        self.manager.transition.direction = "left"
        self.manager.current = "slaughters_list"

    def on_base_data(self, *args):
        self.manager.transition.direction = "left"
        self.manager.current = "base_data"

    def on_search(self, *args):
        self.manager.transition.direction = "left"
        self.manager.current = "admin_search"

    def on_reports(self, *args):
        self.manager.transition.direction = "left"
        self.manager.current = "admin_reports"

    def on_invoice_settings(self, *args):
        self.manager.transition.direction = "left"
        self.manager.current = "invoice_settings"

    def on_backup(self, *args):
        self.manager.transition.direction = "left"
        self.manager.current = "backup"

    def on_logout(self, *args):
        # بکاپ قبل از خروج
        from database import before_exit_backup
        try:
            before_exit_backup()
        except Exception:
            pass

        from kivymd.app import MDApp
        MDApp.get_running_app().current_user = None
        self.manager.transition.direction = "right"
        self.manager.current = "login"
