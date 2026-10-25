# -*- coding: utf-8 -*-
"""
فیلد ورودی فارسی واقعی — با reshaper و bidi
"""

import re

from kivy.metrics import dp, sp
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.textinput import TextInput
from kivy.uix.label import Label
from kivy.graphics import Color, RoundedRectangle

from .fa import fa
from .theme import COLOR_PRIMARY, COLOR_TEXT

# رنگ‌ها
BG_NORMAL = [0.96, 0.96, 0.96, 1]
BG_FOCUS = [1, 1, 1, 1]
BORDER_NORMAL = [0.8, 0.8, 0.8, 1]
BORDER_FOCUS = COLOR_PRIMARY

# تشخیص حروف فارسی/عربی
_FA_RE = re.compile(r"[\u0600-\u06FF\uFB50-\uFDFF\uFE70-\uFEFF]")

def is_fa(text):
    """آیا متن شامل حروف فارسی/عربی است؟"""
    return bool(_FA_RE.search(text or ""))


class FaTextInput(FloatLayout):
    def __init__(self, hint_text="", text="", password=False, input_filter=None, height=50, **kwargs):
        super().__init__(**kwargs)
        self.size_hint_y = None
        self.height = dp(height)
        self.password = password
        self.hint_text = hint_text
        self.field_height = height
        self._focused = False

        with self.canvas.before:
            self._border_color = Color(*BORDER_NORMAL)
            self._border = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(8)])
            self._bg_color = Color(*BG_NORMAL)
            self._bg = RoundedRectangle(pos=(self.x + 1, self.y + 1), size=(self.width - 2, self.height - 2), radius=[dp(7)])

        self.bind(pos=self._update_graphics, size=self._update_graphics)

        self.hidden = TextInput(
            text=text, font_name="Vazir", font_size=sp(15), multiline=False, password=password, input_filter=input_filter,
            halign="right", padding=[dp(16), dp(14), dp(16), dp(14)], background_normal="", background_active="",
            background_color=[0, 0, 0, 0], foreground_color=[0, 0, 0, 0], cursor_color=COLOR_PRIMARY, cursor_width=dp(1.5),
            hint_text="", size_hint=(1, 1), pos_hint={"x": 0, "y": 0},
        )
        self.hidden.bind(text=self._on_text_change)
        self.hidden.bind(focus=self._on_focus_change)
        if text and not is_fa(text):
            self.hidden.halign = "left"

        self.display = Label(text="", font_name="Vazir", font_size=sp(15), halign="right", valign="middle", color=COLOR_TEXT, size_hint=(1, 1), pos_hint={"x": 0, "y": 0})
        self.display.bind(size=lambda inst, val: setattr(inst, "text_size", (inst.width - dp(32), inst.height)))
        self.display.bind(on_touch_down=self._on_display_touch)
        self.add_widget(self.hidden)
        self.add_widget(self.display)
        self._refresh_display()

    def _update_graphics(self, *args):
        self._border.pos = self.pos
        self._border.size = self.size
        self._bg.pos = (self.x + 1, self.y + 1)
        self._bg.size = (self.width - 2, self.height - 2)

    def _on_display_touch(self, instance, touch):
        if self.collide_point(*touch.pos):
            self.hidden.focus = True
        return False

    def _on_focus_change(self, instance, value):
        self._focused = value
        if value:
            self._border_color.rgba = BORDER_FOCUS
            self._bg_color.rgba = BG_FOCUS
            if self.display.text:
                self.display.color = COLOR_PRIMARY
        else:
            self._border_color.rgba = BORDER_NORMAL
            self._bg_color.rgba = BG_NORMAL
            if self.hidden.text:
                self.display.color = COLOR_TEXT

    def _on_text_change(self, instance, value):
        if self.password:
            self.hidden.halign = "left"
            self._refresh_display()
            return
        if value:
            self.hidden.halign = "right" if is_fa(value) else "left"
        else:
            self.hidden.halign = "right"
        self._refresh_display()
        
    def _refresh_display(self):
        raw = self.hidden.text
        if not raw:
            if self.hint_text:
                self.display.text = fa(self.hint_text)
                self.display.color = [0.55, 0.55, 0.55, 1]
                self.display.halign = "right"
            else:
                self.display.text = ""
            return
        if self.password:
            self.display.text = "*" * len(raw)
            self.display.halign = "left"
            self.display.color = COLOR_PRIMARY if self._focused else COLOR_TEXT
            return
        if is_fa(raw):
            self.display.text = fa(raw)
            self.display.halign = "right"
        else:
            self.display.text = raw
            self.display.halign = "left"
        self.display.color = COLOR_PRIMARY if self._focused else COLOR_TEXT

    @property
    def text(self):
        return self.hidden.text

    @text.setter
    def text(self, value):
        self.hidden.text = value or ""
        self._refresh_display()

    def focus(self):
        self.hidden.focus = True

    def get_text(self):
        return self.hidden.text


class FaTextInputMultiline(FloatLayout):
    def __init__(self, hint_text="", text="", height=100, min_height=100, **kwargs):
        super().__init__(**kwargs)
        self.size_hint_y = None
        self.height = dp(height)
        self.min_height = dp(min_height)
        self.hint_text = hint_text
        self._focused = False

        with self.canvas.before:
            self._border_color = Color(*BORDER_NORMAL)
            self._border = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(8)])
            self._bg_color = Color(*BG_NORMAL)
            self._bg = RoundedRectangle(pos=(self.x + 1, self.y + 1), size=(self.width - 2, self.height - 2), radius=[dp(7)])

        self.bind(pos=self._update_graphics, size=self._update_graphics)

        self.hidden = TextInput(
            text=text, font_name="Vazir", font_size=sp(14), multiline=True, halign="right",
            padding=[dp(16), dp(14), dp(16), dp(14)], background_normal="", background_active="",
            background_color=[0, 0, 0, 0], foreground_color=[0, 0, 0, 0], cursor_color=COLOR_PRIMARY, cursor_width=dp(1.5),
            hint_text="", size_hint=(1, 1), pos_hint={"x": 0, "y": 0},
        )
        self.hidden.bind(text=self._on_text_change)
        self.hidden.bind(focus=self._on_focus_change)

        self.display = Label(text="", font_name="Vazir", font_size=sp(14), halign="right", valign="top", color=COLOR_TEXT, size_hint=(1, 1), pos_hint={"x": 0, "y": 0})
        self.display.bind(size=lambda inst, val: setattr(inst, "text_size", (inst.width - dp(32), None)))
        self.display.bind(on_touch_down=self._on_display_touch)

        self.add_widget(self.hidden)
        self.add_widget(self.display)
        self._refresh_display()

    def _update_graphics(self, *args):
        self._border.pos = self.pos
        self._border.size = self.size
        self._bg.pos = (self.x + 1, self.y + 1)
        self._bg.size = (self.width - 2, self.height - 2)

    def _on_display_touch(self, instance, touch):
        if self.collide_point(*touch.pos):
            self.hidden.focus = True
        return False

    def _on_focus_change(self, instance, value):
        self._focused = value
        if value:
            self._border_color.rgba = BORDER_FOCUS
            self._bg_color.rgba = BG_FOCUS
            if self.display.text:
                self.display.color = COLOR_PRIMARY
        else:
            self._border_color.rgba = BORDER_NORMAL
            self._bg_color.rgba = BG_NORMAL
            if self.hidden.text:
                self.display.color = COLOR_TEXT

    def _on_text_change(self, instance, value):
        self._refresh_display()

    def _refresh_display(self):
        raw = self.hidden.text
        if not raw:
            if self.hint_text:
                self.display.text = fa(self.hint_text)
                self.display.color = [0.55, 0.55, 0.55, 1]
                self.display.halign = "right"
            else:
                self.display.text = ""
            return
        if is_fa(raw):
            self.display.text = fa(raw)
            self.display.halign = "right"
        else:
            self.display.text = raw
            self.display.halign = "left"
        self.display.color = COLOR_PRIMARY if self._focused else COLOR_TEXT

    @property
    def text(self):
        return self.hidden.text

    @text.setter
    def text(self, value):
        self.hidden.text = value or ""
        self._refresh_display()

    def focus(self):
        self.hidden.focus = True

    def get_text(self):
        return self.hidden.text


# ==========================================
# ویجت جدید: نمایش متن طولانی (بدون امکان تایپ) - حل قطعی مشکل ترتیب
# ==========================================
class FaLockedText(FloatLayout):
    """
    نمایش متن چندخطی به صورت فقط خواندنی، با حفظ ترتیب خطوط از بالا به پایین.
    برای جلوگیری از باگ Kivy در راست‌چین کردن خطوط، از halign='left' استفاده می‌کنیم
    و متن را با fa() از قبل آماده می‌کنیم تا شبیه راست‌چین شود.
    """
    def __init__(self, text="", height=50, font_size=14, **kwargs):
        super().__init__(**kwargs)
        self.size_hint_y = None
        self.height = dp(height)
        self._text = text

        self.ti = TextInput(
            text=fa(self._text),
            font_name="Vazir",
            font_size=sp(font_size),
            multiline=True,
            disabled=True,
            halign="left",               # <--- کلید حل مشکل (خطوط از بالا به پایین)
            padding=[dp(4), dp(4), dp(4), dp(4)],
            background_normal="",
            background_active="",
            background_color=[1, 1, 1, 0],
            foreground_color=COLOR_TEXT,
            cursor_color=[0, 0, 0, 0],
            size_hint=(1, 1),
            pos_hint={"x": 0, "y": 0},
        )
        
        self.add_widget(self.ti)

    def set_height(self, h):
        self.height = dp(h)
        self.ti.height = dp(h)
