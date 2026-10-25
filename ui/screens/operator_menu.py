# -*- coding: utf-8 -*-
"""
منوی اپراتور
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


class OperatorMenuScreen(MDScreen):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "operator"
        self.md_bg_color = COLOR_BG
        self.build_ui()

    def build_ui(self):

        root = AnchorLayout(anchor_x="center", anchor_y="center")

        card = MDCard(
            orientation="vertical",
            padding=dp(20),
            spacing=dp(10),
            size_hint=(None, None),
            size=(dp(400), dp(500)),
            pos_hint={"center_x": 0.5, "center_y": 0.5},
            elevation=3,
            radius=[dp(15)],
            md_bg_color=[1, 1, 1, 1],
        )

        card.add_widget(fa_label(
            "پنل اپراتور",
            size=22, color=COLOR_PRIMARY_DARK, height=40, bold=True,
        ))

        card.add_widget(spacer(4))

        self.welcome_label = fa_label(
            "", size=14, color=COLOR_GRAY, height=30,
        )
        card.add_widget(self.welcome_label)

        card.add_widget(spacer(20))

        card.add_widget(fa_button(
            "کشتارهای امروز",
            size=17, height=70,
            on_press=self.on_slaughters_list,
        ))

        card.add_widget(spacer(30))

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

    def on_slaughters_list(self, *args):
        self.manager.transition.direction = "left"
        self.manager.current = "slaughters_list"

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
