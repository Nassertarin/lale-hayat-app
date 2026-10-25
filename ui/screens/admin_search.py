# -*- coding: utf-8 -*-
"""
صفحه‌ی جستجوی پیشرفته (فقط ادمین)
"""
from kivy.metrics import dp, sp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.graphics import Color, RoundedRectangle

from kivymd.uix.screen import MDScreen
from kivymd.uix.card import MDCard

from ..helpers.fa import fa
from ..helpers.theme import (
    COLOR_BG, COLOR_PRIMARY, COLOR_PRIMARY_DARK, COLOR_GRAY,
    COLOR_ERROR, COLOR_SUCCESS, COLOR_TEXT, COLOR_WHITE, COLOR_WARNING,
)
from ..helpers.widgets import fa_label, fa_button, spacer, fa_text_input
from ..helpers.dialogs import info_dialog
from ..helpers.shamsi_calendar import ShamsiCalendar
from functions import admin_search


class AdminSearchScreen(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "admin_search"
        self.md_bg_color = COLOR_BG

        self.date_from = ""
        self.date_to = ""
        self.current_type = "all"
        self.text_query = ""

        self.results_container = None
        self.summary_label = None
        
        self.build_ui()

    def build_ui(self):
        root = BoxLayout(orientation="vertical")

        # هدر
        header = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(55), padding=[dp(10), dp(8)], spacing=dp(10))
        header.add_widget(fa_button("بازگشت", size=14, height=40, bg_color=[0.6, 0.6, 0.6, 1], on_press=self.on_back))
        header.add_widget(fa_label("جستجوی پیشرفته", size=16, color=COLOR_PRIMARY_DARK, height=40, bold=True))
        root.add_widget(header)

        # فیلترها (به صورت یک کارت)
        filter_card = MDCard(orientation="vertical", padding=dp(10), spacing=dp(6), size_hint_y=None, height=dp(260), elevation=1, radius=[dp(10)], md_bg_color=[1, 1, 1, 1])
        
        # ردیف تاریخ‌ها
        date_row = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(45), spacing=dp(6))
        self.btn_from = fa_button("از تاریخ", size=12, height=45, bg_color=COLOR_PRIMARY, on_press=lambda x: self.open_calendar("from"))
        self.btn_to = fa_button("تا تاریخ", size=12, height=45, bg_color=COLOR_PRIMARY, on_press=lambda x: self.open_calendar("to"))
        date_row.add_widget(self.btn_from)
        date_row.add_widget(self.btn_to)
        filter_card.add_widget(date_row)
        
        # فیلتر نوع (دو ردیف)
        self.type_btns = {}

        type_row1 = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(35), spacing=dp(4))
        for t_id, t_name in [("all", "همه"), ("slaughters", "کشتار"), ("receipts", "قبض")]:
            btn = Button(text=fa(t_name), font_name="Vazir", font_size=sp(11), background_normal="", background_color=COLOR_PRIMARY if t_id == "all" else [0.9, 0.9, 0.9, 1], color=COLOR_WHITE if t_id == "all" else COLOR_TEXT)
            btn.bind(on_release=lambda x, tid=t_id: self.set_type(tid))
            self.type_btns[t_id] = btn
            type_row1.add_widget(btn)
        filter_card.add_widget(type_row1)

        type_row2 = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(35), spacing=dp(4))
        for t_id, t_name in [("invoices", "صورتحساب"), ("daily_forms", "فرم گزارش")]:
            btn = Button(text=fa(t_name), font_name="Vazir", font_size=sp(11), background_normal="", background_color=[0.9, 0.9, 0.9, 1], color=COLOR_TEXT)
            btn.bind(on_release=lambda x, tid=t_id: self.set_type(tid))
            self.type_btns[t_id] = btn
            type_row2.add_widget(btn)
        filter_card.add_widget(type_row2)

        # فیلتر متنی
        self.text_input = fa_text_input(hint_text="جستجو در شماره، پلاک، نام...", height=45)
        # ── Enter برای جستجو ──
        self.text_input.hidden.bind(on_text_validate=self.do_search)
        filter_card.add_widget(self.text_input)

        # دکمه‌های اعمال و پاک کردن
        action_row = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(45), spacing=dp(6))
        search_btn = fa_button("اعمال فيلتر", size=13, height=45, bg_color=COLOR_SUCCESS, on_press=self.do_search)
        clear_btn = fa_button("برداشتن فيلتر", size=13, height=45, bg_color=COLOR_ERROR, on_press=self.clear_filters)
        action_row.add_widget(search_btn)
        action_row.add_widget(clear_btn)
        filter_card.add_widget(action_row)
        
        root.add_widget(filter_card)

        # خلاصه نتایج
        self.summary_label = fa_label("", size=13, color=COLOR_PRIMARY_DARK, height=30, bold=True)
        root.add_widget(self.summary_label)

        # لیست نتایج
        scroll = ScrollView()
        self.results_container = BoxLayout(orientation="vertical", padding=dp(10), spacing=dp(8), size_hint_y=None)
        self.results_container.bind(minimum_height=self.results_container.setter("height"))
        scroll.add_widget(self.results_container)
        root.add_widget(scroll)

        self.add_widget(root)
        
    def set_type(self, t_id):
        self.current_type = t_id
        for k, btn in self.type_btns.items():
            if k == t_id:
                btn.background_color = COLOR_PRIMARY
                btn.color = COLOR_WHITE
            else:
                btn.background_color = [0.9, 0.9, 0.9, 1]
                btn.color = COLOR_TEXT

    def open_calendar(self, which):
        initial = self.date_from if which == "from" else self.date_to
        cal_content = BoxLayout(orientation="vertical", padding=dp(10), spacing=dp(5))
        with cal_content.canvas.before:
            Color(1, 1, 1, 1)
            cal_content._bg = RoundedRectangle(pos=cal_content.pos, size=cal_content.size, radius=[dp(10)])
        cal_content.bind(pos=lambda s, v: setattr(s._bg, "pos", v), size=lambda s, v: setattr(s._bg, "size", v))

        cal_content.add_widget(fa_label("انتخاب تاریخ", size=15, color=COLOR_PRIMARY_DARK, height=35, bold=True))
        def on_date(date_str):
            if which == "from":
                self.date_from = date_str
                self.btn_from.text = fa(date_str)
                self.btn_from.background_color = COLOR_PRIMARY_DARK
            else:
                self.date_to = date_str
                self.btn_to.text = fa(date_str)
                self.btn_to.background_color = COLOR_PRIMARY_DARK
            popup.dismiss()

        cal = ShamsiCalendar(initial_date=initial or None, on_select=on_date)
        cal_content.add_widget(cal)
        popup = Popup(title="", title_size=0, content=cal_content, size_hint=(None, None), size=(dp(400), dp(520)), auto_dismiss=True, background="", background_color=[0, 0, 0, 0.5], separator_height=0)
        popup.open()

    def on_pre_enter(self, *args):
        self.results_container.clear_widgets()
        self.summary_label.text = fa("برای شروع جستجو، فیلترها را اعمال کنید.")
        self.do_search() # جستجوی اولیه با فیلترهای پیش‌فرض

    def clear_filters(self, *args):
        # پاک کردن تاریخ‌ها
        self.date_from = ""
        self.date_to = ""
        self.btn_from.text = fa("از تاریخ")
        self.btn_from.background_color = COLOR_PRIMARY
        self.btn_to.text = fa("تا تاریخ")
        self.btn_to.background_color = COLOR_PRIMARY
        
        # پاک کردن متن
        self.text_input.text = ""
        self.text_query = ""
        
        # ریست کردن نوع به "همه"
        self.set_type("all")
        
        # اجرای مجدد جستجو (بدون فیلتر)
        self.do_search()

    def do_search(self, *args):
        self.text_query = self.text_input.text.strip()
        self.results_container.clear_widgets()

        try:
            results = admin_search(
                query_type=self.current_type,
                date_from=self.date_from if self.date_from else None,
                date_to=self.date_to if self.date_to else None,
                text_query=self.text_query
            )
        except Exception as e:
            self.summary_label.text = fa(f"خطا: {e}")
            return

        if not results:
            self.summary_label.text = fa("هیچ نتیجه‌ای یافت نشد.")
            self.results_container.add_widget(fa_label("لیست خالی است.", size=14, color=COLOR_GRAY, height=60))
            return

        self.summary_label.text = fa(f"تعداد نتایج: {len(results)}")

        for r in results:
            card = MDCard(orientation="vertical", padding=dp(10), spacing=dp(4), size_hint=(1, None), height=dp(90), elevation=2, radius=[dp(10)], md_bg_color=[1, 1, 1, 1])
            
            color_type = COLOR_PRIMARY if r["type"] == "کشتار" else COLOR_WARNING if r["type"] == "قبض" else COLOR_ERROR
            
            row1 = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(25))
            row1.add_widget(fa_label(f"{r['type']} #{r['num']}", size=13, color=color_type, bold=True, halign="left"))
            row1.add_widget(fa_label(fa(r["date"]), size=11, color=COLOR_GRAY, halign="right"))
            card.add_widget(row1)

            row2 = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(25))
            row2.add_widget(fa_label(r["info1"], size=12, color=COLOR_TEXT, halign="left"))
            row2.add_widget(fa_label(r["info2"], size=12, color=COLOR_TEXT, halign="right"))
            card.add_widget(row2)

            if r["info3"]:
                card.add_widget(fa_label(r["info3"], size=11, color=COLOR_GRAY, halign="right"))

            self.results_container.add_widget(card)

    def on_back(self, *args):
        self.manager.transition.direction = "right"
        self.manager.current = "admin"
