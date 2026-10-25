# -*- coding: utf-8 -*-
"""
ابزارهای ساخت ویجت با فونت فارسی
"""

from kivy.metrics import dp, sp
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.widget import Widget

from .fa import fa
from .theme import (
    COLOR_PRIMARY, COLOR_PRIMARY_DARK, COLOR_WHITE, COLOR_TEXT,
    COLOR_GRAY, COLOR_ERROR, COLOR_SUCCESS,
)


# ==========================================
# پایه
# ==========================================

def fa_label(
    text,
    size=16,
    color=None,
    height=30,
    bold=False,
    halign="center",
):
    if color is None:
        color = COLOR_TEXT

    lbl = Label(
        text=fa(text),
        font_name="Vazir",
        font_size=sp(size),
        color=color,
        bold=bold,
        halign=halign,
        valign="middle",
        size_hint_y=None,
        height=dp(height),
    )
    lbl.bind(size=lambda s, sz: setattr(s, "text_size", sz))
    return lbl


def fa_button(
    text,
    size=18,
    on_press=None,
    height=60,
    bg_color=None,
    text_color=None,
):
    if bg_color is None:
        bg_color = COLOR_PRIMARY
    if text_color is None:
        text_color = COLOR_WHITE

    btn = Button(
        text=fa(text),
        font_name="Vazir",
        font_size=sp(size),
        size_hint=(1, None),
        height=dp(height),
        background_normal="",
        background_color=bg_color,
        color=text_color,
        bold=True,
    )

    if on_press:
        btn.bind(on_release=on_press)

    return btn


def spacer(height=10):
    return Widget(size_hint_y=None, height=dp(height))


def fa_section_title(text, height=30):
    """عنوان بخش (مثلاً «محصول:»)، راست‌چین و پررنگ"""
    return fa_label(
        text,
        size=15,
        color=COLOR_PRIMARY_DARK,
        height=height,
        bold=True,
        halign="right",
    )


# ==========================================
# فیلد ورودی با فونت فارسی
# ==========================================

def fa_text_input(
    hint_text="",
    text="",
    password=False,
    input_filter=None,
    height=50,
):
    """
    فیلد ورودی فارسی با reshaper و bidi.

    خروجی: FaTextInput
    برای دسترسی به فیلد اصلی: wrapper.hidden
    برای گرفتن متن: wrapper.text
    برای ست کردن متن: wrapper.text = "..."
    """
    from .fa_input import FaTextInput

    wrapper = FaTextInput(
        hint_text=hint_text,
        text=text,
        password=password,
        input_filter=input_filter,
        height=height,
    )
    # سازگاری با کد قبلی که از .input_field.text استفاده می‌کرد
    wrapper.input_field = wrapper.hidden
    return wrapper


# ==========================================
# گروه انتخاب (Single Select)
# ==========================================

class SelectionGroup(BoxLayout):
    """
    گروهی از دکمه‌ها که فقط یکی می‌تونه انتخاب بشه.
    items: [(id, display_text), ...]
    on_change: تابعی که وقتی انتخاب عوض می‌شه صدا زده می‌شه
    """

    def __init__(self, items, on_change=None, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "vertical"
        self.spacing = dp(5)
        self.size_hint_y = None
        self.bind(minimum_height=self.setter("height"))

        self.on_change = on_change
        self.selected_id = None
        self.buttons = {}

        for item_id, name in items:
            btn = Button(
                text=fa(name),
                font_name="Vazir",
                font_size=sp(15),
                size_hint_y=None,
                height=dp(45),
                background_normal="",
                background_color=[0.92, 0.92, 0.92, 1],
                color=COLOR_TEXT,
            )
            btn.bind(on_release=lambda inst, iid=item_id: self._select(iid))
            self.buttons[item_id] = btn
            self.add_widget(btn)

    def _select(self, item_id):
        self.selected_id = item_id
        self._update_visual()
        if self.on_change:
            self.on_change(item_id)

    def _update_visual(self):
        for iid, btn in self.buttons.items():
            if iid == self.selected_id:
                btn.background_color = COLOR_PRIMARY
                btn.color = COLOR_WHITE
            else:
                btn.background_color = [0.92, 0.92, 0.92, 1]
                btn.color = COLOR_TEXT

    def set_selected(self, item_id, trigger=True):
        if item_id not in self.buttons:
            return
        self.selected_id = item_id
        self._update_visual()
        if trigger and self.on_change:
            self.on_change(item_id)

    def get_selected(self):
        return self.selected_id

    def clear(self):
        self.selected_id = None
        self._update_visual()


# ==========================================
# ردیف شمارنده سبد
# ==========================================

class BasketCounterRow(BoxLayout):
    """
    ردیف: [نام سبد]  [-]  [تعداد]  [+]
    """

    def __init__(self, basket_id, name, weight, on_change=None, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "horizontal"
        self.spacing = dp(6)
        self.size_hint_y = None
        self.height = dp(50)

        self.basket_id = basket_id
        self.weight = weight
        self.on_change = on_change
        self.count = 0

        name_lbl = Label(
            text=fa(name) + f"  ({weight:.1f} kg)",
            font_name="Vazir",
            font_size=sp(13),
            size_hint_x=0.45,
            halign="right",
            valign="middle",
        )
        name_lbl.bind(size=lambda s, sz: setattr(s, "text_size", sz))
        self.add_widget(name_lbl)

        self.minus_btn = Button(
            text="-",
            font_name="Vazir",
            font_size=sp(22),
            size_hint=(None, 1),
            width=dp(45),
            background_normal="",
            background_color=[0.88, 0.88, 0.88, 1],
            color=COLOR_TEXT,
        )
        self.minus_btn.bind(on_release=self._on_minus)
        self.add_widget(self.minus_btn)

        self.count_lbl = Label(
            text="0",
            font_name="Vazir",
            font_size=sp(17),
            size_hint_x=0.2,
            halign="center",
            valign="middle",
            color=COLOR_PRIMARY_DARK,
            bold=True,
        )
        self.count_lbl.bind(size=lambda s, sz: setattr(s, "text_size", sz))
        self.add_widget(self.count_lbl)

        self.plus_btn = Button(
            text="+",
            font_name="Vazir",
            font_size=sp(22),
            size_hint=(None, 1),
            width=dp(45),
            background_normal="",
            background_color=COLOR_PRIMARY,
            color=COLOR_WHITE,
        )
        self.plus_btn.bind(on_release=self._on_plus)
        self.add_widget(self.plus_btn)

    def _on_minus(self, *args):
        if self.count > 0:
            self.count -= 1
            self.count_lbl.text = str(self.count)
            if self.on_change:
                self.on_change(self.basket_id, self.count)

    def _on_plus(self, *args):
        self.count += 1
        self.count_lbl.text = str(self.count)
        if self.on_change:
            self.on_change(self.basket_id, self.count)

    def set_count(self, value):
        self.count = value
        self.count_lbl.text = str(value)

def fa_text_input_multiline(
    hint_text="",
    text="",
    height=100,
    min_height=100,
):
    """
    فیلد ورودی چندخطی فارسی (برای توضیحات و پاراگراف‌ها).
    """
    from .fa_input import FaTextInputMultiline

    return FaTextInputMultiline(
        hint_text=hint_text,
        text=text,
        height=height,
        min_height=min_height,
    )
