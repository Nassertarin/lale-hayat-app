# -*- coding: utf-8 -*-
"""
دیالوگ‌های سفارشی با پشتیبانی کامل از فارسی
"""

from kivy.metrics import dp, sp
from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.graphics import Color, Rectangle, RoundedRectangle
from kivy.utils import get_color_from_hex

from .fa import fa
from .theme import (
    COLOR_PRIMARY, COLOR_ERROR, COLOR_TEXT, COLOR_WHITE,
    COLOR_GRAY, COLOR_PRIMARY_DARK,
)
from .widgets import fa_label


# رنگ‌های دیالوگ
DIALOG_BG = [1, 1, 1, 1]                 # سفید
DIALOG_BORDER = get_color_from_hex("#1B9E8F")   # سبز تیره
DIALOG_TEXT = get_color_from_hex("#212121")     # متن تیره
DIALOG_TITLE = get_color_from_hex("#137a6f")    # عنوان سبز تیره


# ==========================================
# دیالوگ تایید
# ==========================================

def confirm_dialog(
    title,
    message,
    on_confirm,
    confirm_text="تایید",
    cancel_text="لغو",
    confirm_color=None,
):
    """
    دیالوگ تایید سفارشی با فونت فارسی.
    on_confirm: تابعی که وقتی کاربر تایید کرد صدا زده می‌شود.
    """

    if confirm_color is None:
        confirm_color = COLOR_ERROR

    # ---- محتوای اصلی ----
    content = BoxLayout(
        orientation="vertical",
        padding=dp(20),
        spacing=dp(15),
    )

    # پس‌زمینه‌ی سفید برای محتوا
    with content.canvas.before:
        Color(*DIALOG_BG)
        content._bg_rect = RoundedRectangle(
            pos=content.pos,
            size=content.size,
            radius=[dp(10)],
        )

    def _update_bg(instance, value):
        content._bg_rect.pos = instance.pos
        content._bg_rect.size = instance.size

    content.bind(pos=_update_bg, size=_update_bg)

    # ---- عنوان ----
    content.add_widget(fa_label(
        title,
        size=18,
        color=DIALOG_TITLE,
        height=40,
        bold=True,
    ))

    # ---- متن پیام ----
    content.add_widget(fa_label(
        message,
        size=14,
        color=DIALOG_TEXT,
        height=70,
    ))

    # ---- دکمه‌ها ----
    buttons = BoxLayout(
        orientation="horizontal",
        size_hint_y=None,
        height=dp(55),
        spacing=dp(10),
    )

    # دکمه‌ی لغو
    cancel_btn = Button(
        text=fa(cancel_text),
        font_name="Vazir",
        font_size=sp(15),
        background_normal="",
        background_color=[0.7, 0.7, 0.7, 1],
        color=COLOR_WHITE,
        bold=True,
    )

    # دکمه‌ی تایید
    confirm_btn = Button(
        text=fa(confirm_text),
        font_name="Vazir",
        font_size=sp(15),
        background_normal="",
        background_color=confirm_color,
        color=COLOR_WHITE,
        bold=True,
    )

    buttons.add_widget(cancel_btn)
    buttons.add_widget(confirm_btn)

    content.add_widget(buttons)

    # ---- Popup ----
    popup = Popup(
        title="",
        title_size=0,
        content=content,
        size_hint=(None, None),
        size=(dp(400), dp(300)),
        auto_dismiss=False,
        background="",                  # ← حذف پس‌زمینه‌ی پیش‌فرض تیره
        background_color=[0, 0, 0, 0.5],  # ← نیمه‌شفاف برای پشت
        separator_height=0,
    )

    # ---- رویدادها ----
    cancel_btn.bind(on_release=lambda x: popup.dismiss())
    confirm_btn.bind(
        on_release=lambda x: _do_confirm(popup, on_confirm)
    )

    popup.open()
    return popup


def _do_confirm(popup, on_confirm):
    popup.dismiss()
    if on_confirm:
        on_confirm()


# ==========================================
# دیالوگ اطلاعاتی
# ==========================================

def info_dialog(title, message, button_text="باشه"):
    """دیالوگ اطلاعاتی ساده (بدون تایید)"""

    content = BoxLayout(
        orientation="vertical",
        padding=dp(20),
        spacing=dp(15),
        size_hint_y=None,
    )
    content.bind(minimum_height=content.setter("height"))

    with content.canvas.before:
        Color(*DIALOG_BG)
        content._bg_rect = RoundedRectangle(
            pos=content.pos,
            size=content.size,
            radius=[dp(10)],
        )

    def _update_bg(instance, value):
        content._bg_rect.pos = instance.pos
        content._bg_rect.size = instance.size

    content.bind(pos=_update_bg, size=_update_bg)

    # عنوان
    content.add_widget(fa_label(
        title,
        size=18,
        color=DIALOG_TITLE,
        height=40,
        bold=True,
    ))

    # متن پیام — ارتفاع پویا بر اساس تعداد خطوط
    lines = message.count("\n") + 1
    # هر خط حدود ۲۵ پیکسل + ۳۰ پیکسل حاشیه
    dynamic_height = max(50, lines * 28 + 20)

    content.add_widget(fa_label(
        message,
        size=14,
        color=DIALOG_TEXT,
        height=dynamic_height,
    ))

    # دکمه
    ok_btn = Button(
        text=fa(button_text),
        font_name="Vazir",
        font_size=sp(15),
        size_hint_y=None,
        height=dp(50),
        background_normal="",
        background_color=COLOR_PRIMARY,
        color=COLOR_WHITE,
        bold=True,
    )

    content.add_widget(ok_btn)

    # ارتفاع Popup بر اساس محتوا
    popup_height = max(
        dp(240),
        40 + dynamic_height + 50 + 20 * 4
    )

    popup = Popup(
        title="",
        title_size=0,
        content=content,
        size_hint=(None, None),
        size=(dp(420), popup_height),
        auto_dismiss=False,
        background="",
        background_color=[0, 0, 0, 0.5],
        separator_height=0,
    )

    ok_btn.bind(on_release=lambda x: popup.dismiss())
    popup.open()
    return popup
