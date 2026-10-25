# -*- coding: utf-8 -*-
"""
صفحه ورود
"""

import os

from kivy.metrics import dp, sp
from kivy.core.window import Window
from kivy.uix.image import Image
from kivy.uix.anchorlayout import AnchorLayout

from kivymd.uix.screen import MDScreen
from kivymd.uix.card import MDCard

from ..helpers.fa import fa
from ..helpers.theme import (
    LOGO_PATH,
    COLOR_BG,
    COLOR_PRIMARY,
    COLOR_PRIMARY_DARK,
    COLOR_ERROR,
    COLOR_SUCCESS,
    COLOR_GRAY,
    COLOR_WHITE,
    COLOR_TEXT,
)
from ..helpers.widgets import fa_label, fa_button, spacer, fa_text_input

from functions import login as do_login_fn


class LoginScreen(MDScreen):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "login"
        self.md_bg_color = COLOR_BG
        self.build_ui()

    def build_ui(self):

        root = AnchorLayout(anchor_x="center", anchor_y="center")

        # اندازه‌ی کارت با توجه به اندازه‌ی پنجره
        card_w = min(dp(400), Window.width * 0.92)
        card_h = min(dp(680), Window.height * 0.96)

        card = MDCard(
            orientation="vertical",
            padding=dp(20),
            spacing=dp(8),
            size_hint=(None, None),
            size=(card_w, card_h),
            pos_hint={"center_x": 0.5, "center_y": 0.5},
            elevation=3,
            radius=[dp(15)],
            md_bg_color=[1, 1, 1, 1],
        )

        # ---- لوگو ----
        if os.path.exists(LOGO_PATH):
            card.add_widget(Image(
                source=LOGO_PATH,
                size_hint_y=None,
                height=dp(110),
            ))
        else:
            card.add_widget(spacer(20))

        # ---- عنوان ----
        card.add_widget(fa_label(
            "سیستم توزین محصولات",
            size=20, color=COLOR_PRIMARY_DARK, height=36, bold=True,
        ))

        # ---- زیرعنوان ----
        card.add_widget(fa_label(
            "کشتارگاه لعل حیات وسام",
            size=13, color=COLOR_GRAY, height=26,
        ))

        card.add_widget(spacer(8))

        # ---- برچسب نام کاربری ----
        card.add_widget(fa_label(
            "نام کاربری",
            size=14, color=COLOR_TEXT, height=24, halign="right",
        ))

        # ---- فیلد نام کاربری ----
        self.username_wrap = fa_text_input(
            hint_text="نام کاربری خود را وارد کنید",
            height=50,
        )
        card.add_widget(self.username_wrap)

        card.add_widget(spacer(4))

        # ---- برچسب رمز عبور ----
        card.add_widget(fa_label(
            "رمز عبور",
            size=14, color=COLOR_TEXT, height=24, halign="right",
        ))

        # ---- فیلد رمز عبور ----
        self.password_wrap = fa_text_input(
            hint_text="رمز عبور خود را وارد کنید",
            password=True,
            height=50,
        )
        card.add_widget(self.password_wrap)

        # ---- پیام ----
        self.message_label = fa_label(
            "", size=13, color=COLOR_ERROR, height=32,
        )
        card.add_widget(self.message_label)

        # ---- دکمه‌ی ورود ----
        card.add_widget(fa_button(
            "ورود",
            size=18,
            height=55,
            on_press=self.on_login,
        ))

        card.add_widget(spacer(4))

        root.add_widget(card)
        self.add_widget(root)

    # ======================================

    def show_message(self, text, is_error=True):
        self.message_label.text = fa(text)
        self.message_label.color = COLOR_ERROR if is_error else COLOR_SUCCESS

    def on_login(self, *args):

        username = self.username_wrap.text.strip()
        password = self.password_wrap.text.strip()

        if not username:
            self.show_message("لطفاً نام کاربری را وارد کنید.")
            return

        if not password:
            self.show_message("لطفاً رمز عبور را وارد کنید.")
            return

        self.show_message("در حال بررسی...", is_error=False)

        try:
            result = do_login_fn(username, password)
        except Exception as e:
            self.show_message(f"خطای سیستمی: {e}")
            return

        if not result["success"]:
            self.show_message(result["message"])
            return

        # ورود موفق
        user = result["user"]

        # ذخیره‌ی کاربر جاری در App
        app = self.get_app()
        app.current_user = {
            "user_id": user[0],
            "username": user[1],
            "full_name": user[3],
            "role": user[4],
            "can_edit_locked": bool(user[7]) if len(user) > 7 else False,
        }

        print(f"✅ LOGIN OK: user_id={user[0]}, role={user[4]}")

        # پاک کردن فیلدها برای دفعه‌ی بعد
        self.username_wrap.text = ""
        self.password_wrap.text = ""
        self.message_label.text = ""

        # رفتن به صفحه‌ی مناسب
        role = str(user[4]).strip().lower()
        if role == "admin":
            self.manager.transition.direction = "left"
            self.manager.current = "admin"
        else:
            self.manager.transition.direction = "left"
            self.manager.current = "operator"

    def get_app(self):
        from kivymd.app import MDApp
        return MDApp.get_running_app()
