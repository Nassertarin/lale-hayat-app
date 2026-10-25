# -*- coding: utf-8 -*-
"""
تقویم شمسی ساده برای Kivy
"""

from kivy.metrics import dp, sp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.label import Label

try:
    import jdatetime
    HAS_JDATETIME = True
except ImportError:
    HAS_JDATETIME = False

from .fa import fa
from .theme import (
    COLOR_PRIMARY, COLOR_PRIMARY_DARK, COLOR_GRAY,
    COLOR_TEXT, COLOR_WHITE, COLOR_BG,
)
from .widgets import fa_label


# ترتیب روزهای هفته (شنبه = 0 ... جمعه = 6)
WEEKDAYS_FA = ["ش", "ی", "د", "س", "چ", "پ", "ج"]

# نام ماه‌های شمسی
MONTHS_FA = [
    "فروردین", "اردیبهشت", "خرداد",
    "تیر", "مرداد", "شهریور",
    "مهر", "آبان", "آذر",
    "دی", "بهمن", "اسفند",
]


class ShamsiCalendar(BoxLayout):
    """
    تقویم شمسی ساده.

    با کلیک روی هر روز، on_select(date_str) صدا زده می‌شه.
    date_str مثل: "1404/07/15"
    """

    def __init__(self, initial_date=None, on_select=None, **kwargs):
        super().__init__(**kwargs)

        self.orientation = "vertical"
        self.spacing = dp(5)
        self.padding = dp(5)

        self.on_select = on_select

        # تاریخ نمایش‌داده‌شده (سال و ماه)
        if initial_date:
            try:
                y, m, d = initial_date.replace("-", "/").split("/")
                self.current_year = int(y)
                self.current_month = int(m)
                self.selected_day = int(d)
            except (ValueError, AttributeError):
                self._init_default()
        else:
            self._init_default()

        self.build_ui()

    def _init_default(self):
        if HAS_JDATETIME:
            today = jdatetime.date.today()
        else:
            from datetime import datetime
            today = datetime.now()
        self.current_year = today.year
        self.current_month = today.month
        self.selected_day = today.day

    # ======================================
    # ساخت UI
    # ======================================

    def build_ui(self):

        self.clear_widgets()

        # ---------- نوار بالای تقویم ----------
        nav = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(50),
            spacing=dp(5),
        )

        prev_btn = Button(
            text=fa("قبلی"),
            font_name="Vazir",
            font_size=sp(20),
            size_hint_x=None,
            width=dp(50),
            background_normal="",
            background_color=COLOR_PRIMARY,
            color=COLOR_WHITE,
        )
        prev_btn.bind(on_release=self.go_prev_month)

        self.month_label = fa_label(
            self._month_title(),
            size=16,
            color=COLOR_PRIMARY_DARK,
            height=50,
            bold=True,
        )

        next_btn = Button(
            text=fa("بعدی"),
            font_name="Vazir",
            font_size=sp(20),
            size_hint_x=None,
            width=dp(50),
            background_normal="",
            background_color=COLOR_PRIMARY,
            color=COLOR_WHITE,
        )
        next_btn.bind(on_release=self.go_next_month)

        nav.add_widget(prev_btn)
        nav.add_widget(self.month_label)
        nav.add_widget(next_btn)

        self.add_widget(nav)

        # ---------- ردیف نام روزهای هفته ----------
        weekdays = GridLayout(
            cols=7,
            size_hint_y=None,
            height=dp(35),
            spacing=dp(2),
        )

        for day_name in WEEKDAYS_FA:
            weekdays.add_widget(fa_label(
                day_name,
                size=13,
                color=COLOR_PRIMARY_DARK,
                height=35,
                bold=True,
            ))

        self.add_widget(weekdays)

        # ---------- شبکه‌ی روزها ----------
        self.days_grid = GridLayout(
            cols=7,
            size_hint_y=None,
            spacing=dp(2),
        )
        self.days_grid.bind(
            minimum_height=self.days_grid.setter("height")
        )

        self.add_widget(self.days_grid)

        # رندر روزها
        self.render_days()

        # ---------- دکمه‌ی «امروز» ----------
        today_btn = Button(
            text=fa("امروز"),
            font_name="Vazir",
            font_size=sp(14),
            size_hint_y=None,
            height=dp(40),
            background_normal="",
            background_color=[0.85, 0.85, 0.85, 1],
            color=COLOR_TEXT,
        )
        today_btn.bind(on_release=self.go_today)
        self.add_widget(today_btn)

    # ======================================
    # عنوان ماه
    # ======================================

    def _month_title(self):
        month_name = MONTHS_FA[self.current_month - 1]
        return f"{month_name}  {self.current_year}"

    # ======================================
    # رندر روزها
    # ======================================

    def render_days(self):

        self.days_grid.clear_widgets()

        # ---- محاسبه‌ی تعداد روزهای ماه ----
        days_in_month = self._days_in_month(
            self.current_year, self.current_month
        )

        # ---- محاسبه‌ی روز اول ماه (0=شنبه) ----
        first_weekday = self._first_weekday(
            self.current_year, self.current_month
        )

        # ---- روزهای خالی قبل از روز اول ----
        for _ in range(first_weekday):
            self.days_grid.add_widget(Label(
                text="",
                size_hint_y=None,
                height=dp(42),
            ))

        # ---- روزها ----
        for day in range(1, days_in_month + 1):

            btn = Button(
                text=str(day),
                font_name="Vazir",
                font_size=sp(15),
                size_hint_y=None,
                height=dp(42),
                background_normal="",
                background_color=[1, 1, 1, 1],
                color=COLOR_TEXT,
            )

            # روز انتخابی رو سبز کن
            if day == self.selected_day:
                btn.background_color = COLOR_PRIMARY
                btn.color = COLOR_WHITE

            btn.bind(
                on_release=lambda inst, d=day: self.select_day(d)
            )

            self.days_grid.add_widget(btn)

        # ---- روزهای خالی بعد ----
        total_cells = first_weekday + days_in_month
        remaining = (7 - (total_cells % 7)) % 7

        for _ in range(remaining):
            self.days_grid.add_widget(Label(
                text="",
                size_hint_y=None,
                height=dp(42),
            ))

    # ======================================
    # توابع کمکی تاریخ
    # ======================================

    def _days_in_month(self, year, month):
        """تعداد روزهای یک ماه شمسی"""

        if month <= 6:
            return 31
        if month <= 11:
            return 30

        # اسفند — سال کبیسه؟
        if self._is_leap_year(year):
            return 30
        return 29

    def _is_leap_year(self, year):
        """سال کبیسه شمسی؟"""

        if HAS_JDATETIME:
            try:
                return jdatetime.date(year, 12, 30).isvalid()
            except Exception:
                return False

        # الگوریتم تقریبی
        return (year - 1375) % 33 in (1, 5, 9, 13, 17, 22, 26, 30)

    def _first_weekday(self, year, month):
        """روز هفته‌ی اول ماه (0=شنبه)"""

        if HAS_JDATETIME:
            try:
                first_day = jdatetime.date(year, month, 1)
                # jdatetime: شنبه=0 ... جمعه=6
                return first_day.weekday()
            except Exception:
                return 0

        # fallback: میلادی
        from datetime import datetime
        try:
            first_day = datetime(year, month, 1)
            # datetime: دوشنبه=0 ... یکشنبه=6
            # تبدیل به شنبه=0
            wd = first_day.weekday()  # 0=Mon
            # شنبه = 5 در پایتون (Sat=5)
            # نقشه: Mon=0 → 2، Tue=1 → 3، Wed=2 → 4، Thu=3 → 5،
            #       Fri=4 → 6، Sat=5 → 0، Sun=6 → 1
            mapping = {0: 2, 1: 3, 2: 4, 3: 5, 4: 6, 5: 0, 6: 1}
            return mapping.get(wd, 0)
        except Exception:
            return 0

    # ======================================
    # ناوبری
    # ======================================

    def go_prev_month(self, *args):
        if self.current_month == 1:
            self.current_month = 12
            self.current_year -= 1
        else:
            self.current_month -= 1

        self.selected_day = None
        self.month_label.text = fa(self._month_title())
        self.render_days()

    def go_next_month(self, *args):
        if self.current_month == 12:
            self.current_month = 1
            self.current_year += 1
        else:
            self.current_month += 1

        self.selected_day = None
        self.month_label.text = fa(self._month_title())
        self.render_days()

    def go_today(self, *args):
        if HAS_JDATETIME:
            today = jdatetime.date.today()
        else:
            from datetime import datetime
            today = datetime.now()

        self.current_year = today.year
        self.current_month = today.month
        self.selected_day = today.day

        self.month_label.text = fa(self._month_title())
        self.render_days()

        # صدا زدن callback با تاریخ امروز
        date_str = (
            f"{self.current_year:04d}/"
            f"{self.current_month:02d}/"
            f"{self.selected_day:02d}"
        )
        if self.on_select:
            self.on_select(date_str)

    # ======================================
    # انتخاب روز
    # ======================================

    def select_day(self, day):
        self.selected_day = day
        self.render_days()

        date_str = (
            f"{self.current_year:04d}/"
            f"{self.current_month:02d}/"
            f"{day:02d}"
        )

        if self.on_select:
            self.on_select(date_str)
