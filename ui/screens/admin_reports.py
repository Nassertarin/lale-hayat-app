# -*- coding: utf-8 -*-
"""
صفحه‌ی گزارش‌گیری جامع (فقط ادمین)
"""
from datetime import datetime, timedelta
from kivy.metrics import dp, sp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
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
from ..helpers.widgets import fa_label, fa_button, spacer
from ..helpers.dialogs import info_dialog
from ..helpers.shamsi_calendar import ShamsiCalendar
from functions import (
    get_report_summary, get_report_details, get_work_day_shamsi,
    get_report_daily, get_report_operators, get_report_customers, get_report_products,
)


def fa_digits(text):
    if text is None: return ""
    s = str(text)
    mapping = {'0': '۰', '1': '۱', '2': '۲', '3': '۳', '4': '۴', '5': '۵', '6': '۶', '7': '۷', '8': '۸', '9': '۹', '.': '٫', ',': '٬'}
    return "".join(mapping.get(c, c) for c in s)


class AdminReportsScreen(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "admin_reports"
        self.md_bg_color = COLOR_BG

        self.date_from = ""
        self.date_to = ""
        self.active_preset = "today"
        self.active_tab = "slaughters"

        self.summary_container = None
        self.tab_content_container = None
        self.preset_label = None
        self.custom_date_box = None
        self.btn_from = None
        self.btn_to = None
        self.tab_buttons = {}

        self.build_ui()

    def build_ui(self):
        root_scroll = ScrollView()
        root = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(10), padding=[dp(10), dp(10)])
        root.bind(minimum_height=root.setter("height"))

        # ۱. هدر
        header = BoxLayout(
            orientation="horizontal", size_hint_y=None, height=dp(70), padding=[dp(5), dp(10)], spacing=dp(15)
        )
        header.add_widget(fa_button("بازگشت", size=14, height=50, bg_color=[0.6, 0.6, 0.6, 1], on_press=self.on_back))
        header.add_widget(fa_label("گزارش‌گیری جامع", size=18, color=COLOR_PRIMARY_DARK, height=50, bold=True))
        root.add_widget(header)

        # ۲. بازه
        preset_grid = GridLayout(cols=2, size_hint_y=None, spacing=dp(6))
        preset_grid.bind(minimum_height=preset_grid.setter("height"))
        
        preset_grid.add_widget(self._preset_btn("امروز", "today"))
        preset_grid.add_widget(self._preset_btn("۷ روز اخیر", "week"))
        preset_grid.add_widget(self._preset_btn("۳۰ روز اخیر", "month"))
        preset_grid.add_widget(self._preset_btn("همه سوابق", "all"))
        preset_grid.add_widget(self._preset_btn("بازه دلخواه", "custom"))
        root.add_widget(preset_grid)

        # ۳. بازه دلخواه
        self.custom_date_box = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(45), spacing=dp(6))
        self.btn_from = fa_button("از تاریخ", size=12, height=45, bg_color=COLOR_PRIMARY, on_press=lambda x: self.open_calendar("from"))
        self.btn_to = fa_button("تا تاریخ", size=12, height=45, bg_color=COLOR_PRIMARY, on_press=lambda x: self.open_calendar("to"))
        self.custom_date_box.add_widget(self.btn_from)
        self.custom_date_box.add_widget(self.btn_to)
        self.custom_date_box.opacity = 0
        self.custom_date_box.disabled = True
        root.add_widget(self.custom_date_box)

        # ۴. برچسب بازه
        self.preset_label = fa_label("", size=13, color=COLOR_GRAY, height=30)
        root.add_widget(self.preset_label)

        # ۵. خلاصه
        root.add_widget(fa_label("خلاصه آمار", size=15, color=COLOR_PRIMARY_DARK, bold=True, height=30, halign="right"))
        self.summary_container = BoxLayout(orientation="vertical", spacing=dp(6), size_hint_y=None)
        self.summary_container.bind(minimum_height=self.summary_container.setter("height"))
        root.add_widget(self.summary_container)

        # ۶. تب‌ها
        root.add_widget(spacer(10))
        root.add_widget(fa_label("گزارش‌های تفکیکی", size=15, color=COLOR_PRIMARY_DARK, bold=True, height=30, halign="right"))
        
        tabs_row = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(45), spacing=dp(4))
        for tab_id, tab_name in [
            ("slaughters", "کشتارها"),
            ("daily", "روزانه"),
            ("operators", "اپراتورها"),
            ("customers", "مشتری‌ها"),
            ("products", "محصولات"),
        ]:
            btn = Button(
                text=fa(tab_name), font_name="Vazir", font_size=sp(11),
                background_normal="", background_color=COLOR_PRIMARY if tab_id == "slaughters" else [0.9, 0.9, 0.9, 1],
                color=COLOR_WHITE if tab_id == "slaughters" else COLOR_TEXT,
            )
            btn.bind(on_release=lambda x, tid=tab_id: self.set_tab(tid))
            self.tab_buttons[tab_id] = btn
            tabs_row.add_widget(btn)
        root.add_widget(tabs_row)

        # ۷. محتوای تب
        self.tab_content_container = BoxLayout(orientation="vertical", spacing=dp(6), size_hint_y=None)
        self.tab_content_container.bind(minimum_height=self.tab_content_container.setter("height"))
        root.add_widget(self.tab_content_container)

        # ۸. دکمه‌های خروجی
        root.add_widget(spacer(10))
        export_row = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(55), spacing=dp(8))
        export_row.add_widget(fa_button("خروجی PDF", size=13, height=55, bg_color=COLOR_PRIMARY_DARK, on_press=self.on_export_pdf))
        export_row.add_widget(fa_button("خروجی Excel", size=13, height=55, bg_color=COLOR_SUCCESS, on_press=self.on_export_excel))
        root.add_widget(export_row)

        root.add_widget(spacer(20))

        root_scroll.add_widget(root)
        self.add_widget(root_scroll)

    def _preset_btn(self, text, preset):
        btn = Button(
            text=fa(text), font_name="Vazir", font_size=sp(13), 
            size_hint_y=None, height=dp(45), 
            background_normal="", background_color=[0.92, 0.92, 0.92, 1], color=COLOR_TEXT
        )
        btn.bind(on_release=lambda x: self.select_preset(preset))
        return btn

    def set_tab(self, tab_id):
        self.active_tab = tab_id
        for k, btn in self.tab_buttons.items():
            if k == tab_id:
                btn.background_color = COLOR_PRIMARY
                btn.color = COLOR_WHITE
            else:
                btn.background_color = [0.9, 0.9, 0.9, 1]
                btn.color = COLOR_TEXT
        self._refresh_tab_content()

    def select_preset(self, preset):
        if preset == "custom" and self.active_preset == "custom":
            self.select_preset("today")
            return

        self.active_preset = preset
        
        if preset == "custom":
            self.custom_date_box.opacity = 1
            self.custom_date_box.disabled = False
            if not self.date_from:
                today_shamsi, _ = get_work_day_shamsi()
                self.date_from = today_shamsi
                self.date_to = today_shamsi
                self.btn_from.text = fa(self.date_from)
                self.btn_to.text = fa(self.date_to)
                self._refresh_data()
            return
        else:
            self.custom_date_box.opacity = 0
            self.custom_date_box.disabled = True

        today_shamsi, _ = get_work_day_shamsi()
        
        try:
            import jdatetime
            today = jdatetime.datetime.strptime(today_shamsi, "%Y/%m/%d").date()
        except:
            today = datetime.now().date()

        if preset == "today":
            self.date_from = today_shamsi
            self.date_to = today_shamsi
        elif preset == "week":
            start = today - timedelta(days=7)
            self.date_from = start.strftime("%Y/%m/%d") if hasattr(start, 'strftime') else today_shamsi
            self.date_to = today_shamsi
        elif preset == "month":
            start = today - timedelta(days=30)
            self.date_from = start.strftime("%Y/%m/%d") if hasattr(start, 'strftime') else today_shamsi
            self.date_to = today_shamsi
        elif preset == "all":
            self.date_from = "1300/01/01"
            self.date_to = "1500/12/29"

        self.btn_from.text = fa(self.date_from)
        self.btn_to.text = fa(self.date_to)
        self._refresh_data()

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
            else:
                self.date_to = date_str
                self.btn_to.text = fa(date_str)
            popup.dismiss()
            self._refresh_data()

        cal = ShamsiCalendar(initial_date=initial or None, on_select=on_date)
        cal_content.add_widget(cal)
        popup = Popup(title="", title_size=0, content=cal_content, size_hint=(None, None), size=(dp(400), dp(520)), auto_dismiss=True, background="", background_color=[0, 0, 0, 0.5], separator_height=0)
        popup.open()

    def on_pre_enter(self, *args):
        self.select_preset("today")

    def _refresh_data(self):
        self.preset_label.text = fa("بازه انتخاب شده: " + self.date_from + " تا " + self.date_to)
        
        self.summary_container.clear_widgets()
        self.tab_content_container.clear_widgets()

        # خلاصه
        try:
            summary = get_report_summary(self.date_from, self.date_to)
        except Exception as e:
            self.summary_container.add_widget(fa_label("خطا: " + str(e), size=13, color=COLOR_ERROR, height=40))
            return

        card = MDCard(orientation="vertical", padding=dp(12), spacing=dp(4), size_hint=(1, None), elevation=2, radius=[dp(10)], md_bg_color=[1, 1, 1, 1])
        card.bind(minimum_height=card.setter("height"))
        
        card.add_widget(self._info_row("تعداد کشتارها", fa_digits(summary["slaughter_count"])))
        card.add_widget(self._info_row("مجموع پای قلاب", fa_digits(summary["total_hook"])))
        
        net_w = fa_digits("{:,.0f}".format(summary['total_net_weight']))
        card.add_widget(self._info_row("مجموع وزن خالص توزین", net_w + " کیلوگرم"))
        
        card.add_widget(self._info_row("تعداد قبض‌ها", fa_digits(summary["receipt_count"])))
        
        rec_w = fa_digits("{:,.0f}".format(summary['receipt_weight']))
        card.add_widget(self._info_row("مجموع وزن قبض‌ها", rec_w + " کیلوگرم"))
        
        card.add_widget(self._info_row("تعداد صورتحساب‌ها", fa_digits(summary["invoice_count"])))
        
        inv_t = fa_digits("{:,.0f}".format(summary['invoice_total']))
        card.add_widget(self._info_row("جمع کل مبالغ صورتحساب", inv_t + " ریال", highlight=True))
        
        self.summary_container.add_widget(card)

        # محتوای تب
        self._refresh_tab_content()

    def _refresh_tab_content(self):
        self.tab_content_container.clear_widgets()

        if self.active_tab == "slaughters":
            self._render_slaughters()
        elif self.active_tab == "daily":
            self._render_daily()
        elif self.active_tab == "operators":
            self._render_operators()
        elif self.active_tab == "customers":
            self._render_customers()
        elif self.active_tab == "products":
            self._render_products()

    def _render_slaughters(self):
        try:
            details = get_report_details(self.date_from, self.date_to)
        except Exception as e:
            self.tab_content_container.add_widget(fa_label("خطا: " + str(e), size=13, color=COLOR_ERROR, height=40))
            return

        if not details:
            self.tab_content_container.add_widget(fa_label("هیچ کشتاری در این بازه یافت نشد.", size=13, color=COLOR_GRAY, height=50))
            return

        for d in details:
            d_card = MDCard(orientation="vertical", padding=dp(10), spacing=dp(4), size_hint=(1, None), elevation=1, radius=[dp(10)], md_bg_color=[0.98, 0.98, 0.98, 1])
            d_card.bind(minimum_height=d_card.setter("height"))
            
            row1 = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(25))
            row1.add_widget(fa_label("کشتار #" + fa_digits(d['slaughter_number']), size=13, color=COLOR_PRIMARY, bold=True, halign="left"))
            row1.add_widget(fa_label(d['day_name'] + " " + fa_digits(d['form_date']), size=11, color=COLOR_GRAY, halign="right"))
            d_card.add_widget(row1)

            row2 = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(25))
            row2.add_widget(fa_label("پای قلاب: " + fa_digits(d['hook_count']), size=12, color=COLOR_TEXT))
            weight_val = fa_digits("{:,.0f}".format(d['net_weight']))
            row2.add_widget(fa_label("وزن خالص: " + weight_val, size=12, color=COLOR_TEXT))
            d_card.add_widget(row2)

            row3 = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(25))
            row3.add_widget(fa_label("قبض‌ها: " + fa_digits(d['receipt_count']), size=12, color=COLOR_WARNING))
            inv_val = fa_digits("{:,.0f}".format(d['invoice_total']))
            row3.add_widget(fa_label("صورتحساب: " + inv_val + " ریال", size=12, color=COLOR_ERROR))
            d_card.add_widget(row3)

            row4 = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(25))
            row4.add_widget(fa_label("گاری: " + fa_digits(d['cart_count']), size=11, color=COLOR_GRAY))
            p_w = fa_digits("{:,.0f}".format(d['plucked_weight']))
            row4.add_widget(fa_label("پرکنده: " + p_w, size=11, color=COLOR_GRAY))
            a_w = fa_digits("{:,.0f}".format(d['alayeshat_weight']))
            row4.add_widget(fa_label("آلایشات: " + a_w, size=11, color=COLOR_GRAY))
            d_card.add_widget(row4)

            if d['operator_name']:
                d_card.add_widget(fa_label("اپراتور: " + d['operator_name'], size=11, color=COLOR_GRAY, halign="right"))

            self.tab_content_container.add_widget(d_card)

    def _render_daily(self):
        try:
            rows = get_report_daily(self.date_from, self.date_to)
        except Exception as e:
            self.tab_content_container.add_widget(fa_label("خطا: " + str(e), size=13, color=COLOR_ERROR, height=40))
            return

        if not rows:
            self.tab_content_container.add_widget(fa_label("هیچ داده‌ای در این بازه نیست.", size=13, color=COLOR_GRAY, height=50))
            return

        for r in rows:
            card = MDCard(orientation="horizontal", padding=dp(12), spacing=dp(8), size_hint=(1, None), height=dp(60), elevation=1, radius=[dp(10)], md_bg_color=[1, 1, 1, 1])
            card.add_widget(fa_label(r['day_name'] + " " + fa_digits(r['form_date']), size=13, color=COLOR_PRIMARY, bold=True, halign="right"))
            card.add_widget(fa_label("کشتار: " + fa_digits(r['slaughter_count']), size=12, color=COLOR_TEXT))
            n_w = fa_digits("{:,.0f}".format(r['total_net']))
            card.add_widget(fa_label("وزن: " + n_w, size=12, color=COLOR_PRIMARY_DARK, bold=True))
            self.tab_content_container.add_widget(card)

    def _render_operators(self):
        try:
            rows = get_report_operators(self.date_from, self.date_to)
        except Exception as e:
            self.tab_content_container.add_widget(fa_label("خطا: " + str(e), size=13, color=COLOR_ERROR, height=40))
            return

        if not rows:
            self.tab_content_container.add_widget(fa_label("هیچ داده‌ای در این بازه نیست.", size=13, color=COLOR_GRAY, height=50))
            return

        for r in rows:
            card = MDCard(orientation="horizontal", padding=dp(12), spacing=dp(8), size_hint=(1, None), height=dp(60), elevation=1, radius=[dp(10)], md_bg_color=[1, 1, 1, 1])
            card.add_widget(fa_label(r['full_name'], size=13, color=COLOR_PRIMARY, bold=True, halign="right"))
            card.add_widget(fa_label("کشتار: " + fa_digits(r['slaughter_count']), size=12, color=COLOR_TEXT))
            n_w = fa_digits("{:,.0f}".format(r['total_net']))
            card.add_widget(fa_label("وزن: " + n_w, size=12, color=COLOR_PRIMARY_DARK, bold=True))
            self.tab_content_container.add_widget(card)

    def _render_customers(self):
        try:
            data = get_report_customers(self.date_from, self.date_to)
        except Exception as e:
            self.tab_content_container.add_widget(fa_label("خطا: " + str(e), size=13, color=COLOR_ERROR, height=40))
            return

        if not data["buyers"] and not data["alayeshat"]:
            self.tab_content_container.add_widget(fa_label("هیچ داده‌ای در این بازه نیست.", size=13, color=COLOR_GRAY, height=50))
            return

        if data["buyers"]:
            self.tab_content_container.add_widget(fa_label("خریداران (مرغ پرکنده)", size=13, color=COLOR_PRIMARY_DARK, bold=True, height=30, halign="right"))
            for r in data["buyers"]:
                card = MDCard(orientation="horizontal", padding=dp(12), spacing=dp(8), size_hint=(1, None), height=dp(50), elevation=1, radius=[dp(10)], md_bg_color=[1, 1, 1, 1])
                card.add_widget(fa_label(r['name'], size=13, color=COLOR_PRIMARY, bold=True, halign="right"))
                w_val = fa_digits("{:,.0f}".format(r['total_weight']))
                card.add_widget(fa_label("وزن: " + w_val, size=12, color=COLOR_PRIMARY_DARK, bold=True))
                self.tab_content_container.add_widget(card)

        if data["alayeshat"]:
            self.tab_content_container.add_widget(spacer(10))
            self.tab_content_container.add_widget(fa_label("مشتریان آلایشات", size=13, color=COLOR_PRIMARY_DARK, bold=True, height=30, halign="right"))
            for r in data["alayeshat"]:
                card = MDCard(orientation="horizontal", padding=dp(12), spacing=dp(8), size_hint=(1, None), height=dp(50), elevation=1, radius=[dp(10)], md_bg_color=[1, 1, 1, 1])
                card.add_widget(fa_label(r['name'], size=13, color=COLOR_PRIMARY, bold=True, halign="right"))
                w_val = fa_digits("{:,.0f}".format(r['total_weight']))
                card.add_widget(fa_label("وزن: " + w_val, size=12, color=COLOR_PRIMARY_DARK, bold=True))
                self.tab_content_container.add_widget(card)

    def _render_products(self):
        try:
            rows = get_report_products(self.date_from, self.date_to)
        except Exception as e:
            self.tab_content_container.add_widget(fa_label("خطا: " + str(e), size=13, color=COLOR_ERROR, height=40))
            return

        if not rows:
            self.tab_content_container.add_widget(fa_label("هیچ داده‌ای در این بازه نیست.", size=13, color=COLOR_GRAY, height=50))
            return

        for r in rows:
            card = MDCard(orientation="horizontal", padding=dp(12), spacing=dp(8), size_hint=(1, None), height=dp(50), elevation=1, radius=[dp(10)], md_bg_color=[1, 1, 1, 1])
            card.add_widget(fa_label(r['product_name'], size=13, color=COLOR_PRIMARY, bold=True, halign="right"))
            card.add_widget(fa_label("ردیف: " + fa_digits(r['row_count']), size=12, color=COLOR_TEXT))
            w_val = fa_digits("{:,.0f}".format(r['total_weight']))
            card.add_widget(fa_label("وزن: " + w_val, size=12, color=COLOR_PRIMARY_DARK, bold=True))
            self.tab_content_container.add_widget(card)

    def _info_row(self, label, value, highlight=False):
        row = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(28), spacing=dp(6))
        v_lbl = fa_label(str(value), size=14 if highlight else 13, color=COLOR_PRIMARY if highlight else COLOR_TEXT, height=28, bold=highlight, halign="left")
        v_lbl.size_hint_x = 0.55
        row.add_widget(v_lbl)
        l_lbl = fa_label(str(label), size=14 if highlight else 13, color=COLOR_PRIMARY_DARK if highlight else COLOR_GRAY, height=28, bold=highlight, halign="right")
        l_lbl.size_hint_x = 0.45
        row.add_widget(l_lbl)
        return row

    # ======================================
    # خروجی PDF و Excel
    # ======================================

    def on_export_pdf(self, *args):
        from ..helpers.file_dialog import ask_save_path, ask_open_after_save
        from ..helpers.file_utils import open_file
        from pdf_admin_report import generate_admin_report_pdf
        from datetime import datetime

        try:
            summary = get_report_summary(self.date_from, self.date_to)
            details = get_report_details(self.date_from, self.date_to)
            daily = get_report_daily(self.date_from, self.date_to)
            operators = get_report_operators(self.date_from, self.date_to)
            customers = get_report_customers(self.date_from, self.date_to)
            products = get_report_products(self.date_from, self.date_to)
        except Exception as e:
            info_dialog("خطا", "خطا در دریافت داده‌ها:\n" + str(e))
            return

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_name = "admin_report_" + self.date_from.replace('/', '-') + "_" + self.date_to.replace('/', '-') + "_" + ts

        def do_save(filepath):
            try:
                result = generate_admin_report_pdf(
                    summary, details, daily, operators, customers, products,
                    self.date_from, self.date_to, output_path=filepath
                )
            except Exception as e:
                info_dialog("خطا در ساخت PDF", str(e))
                return
            info_dialog("خروجی PDF ساخته شد", "فایل ذخیره شد در:\n\n" + result)
            ask_open_after_save(on_yes=lambda: open_file(result))

        ask_save_path(
            title="ذخیره خروجی PDF",
            default_filename=default_name,
            file_extension=".pdf",
            on_save=do_save,
        )

    def on_export_excel(self, *args):
        from ..helpers.file_dialog import ask_save_path, ask_open_after_save
        from ..helpers.file_utils import open_file
        from pdf_admin_report import generate_admin_report_excel
        from datetime import datetime

        try:
            summary = get_report_summary(self.date_from, self.date_to)
            details = get_report_details(self.date_from, self.date_to)
            daily = get_report_daily(self.date_from, self.date_to)
            operators = get_report_operators(self.date_from, self.date_to)
            customers = get_report_customers(self.date_from, self.date_to)
            products = get_report_products(self.date_from, self.date_to)
        except Exception as e:
            info_dialog("خطا", "خطا در دریافت داده‌ها:\n" + str(e))
            return

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_name = "admin_report_" + self.date_from.replace('/', '-') + "_" + self.date_to.replace('/', '-') + "_" + ts

        def do_save(filepath):
            try:
                result = generate_admin_report_excel(
                    summary, details, daily, operators, customers, products,
                    self.date_from, self.date_to, output_path=filepath
                )
            except Exception as e:
                info_dialog("خطا در ساخت Excel", str(e))
                return
            info_dialog("خروجی Excel ساخته شد", "فایل ذخیره شد در:\n\n" + result)
            ask_open_after_save(on_yes=lambda: open_file(result))

        ask_save_path(
            title="ذخیره خروجی Excel",
            default_filename=default_name,
            file_extension=".xlsx",
            on_save=do_save,
        )

    def on_back(self, *args):
        self.manager.transition.direction = "right"
        self.manager.current = "admin"
