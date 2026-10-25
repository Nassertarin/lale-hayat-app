# -*- coding: utf-8 -*-
"""
صفحه‌ی صورتحساب کشتار روزانه (بر اساس تاریخ)
"""
import os
import textwrap
from datetime import datetime
from kivy.metrics import dp, sp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.graphics import Color, RoundedRectangle
from kivy.clock import Clock
from kivymd.uix.screen import MDScreen
from kivymd.uix.card import MDCard

from ..helpers.fa import fa
from ..helpers.theme import (
    COLOR_BG, COLOR_PRIMARY, COLOR_PRIMARY_DARK, COLOR_GRAY,
    COLOR_ERROR, COLOR_SUCCESS, COLOR_TEXT, COLOR_WHITE, COLOR_WARNING,
)
from ..helpers.widgets import (
    fa_label, fa_button, spacer, fa_text_input, fa_section_title, fa_text_input_multiline,
)
from ..helpers.dialogs import confirm_dialog, info_dialog
from ..helpers.shamsi_calendar import ShamsiCalendar
from functions import (
    get_work_day_shamsi, get_or_create_daily_invoice, save_daily_invoice,
    lock_daily_invoice, can_edit_daily_invoice, get_invoice_settings, delete_daily_invoice,
    get_invoice_prefill_data,
    can_edit_form, admin_unlock_form, finalize_form, user_can_edit_locked,is_within_edit_window,
)
from database import resolve_receipt_image


def fa_digits(text):
    if text is None:
        return ""
    s = str(text)
    mapping = {'0': '۰', '1': '۱', '2': '۲', '3': '۳', '4': '۴', '5': '۵', '6': '۶', '7': '۷', '8': '۸', '9': '۹', '.': '٫', ',': '٬'}
    return "".join(mapping.get(c, c) for c in s)


class InvoicesScreen(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "invoices"
        self.md_bg_color = COLOR_BG
        self.form_date = None
        self.day_name = None
        self.current_user = None
        self.is_admin = False
        self.invoice_data = None
        self._clock_event = None
        self.build_ui()

    def build_ui(self):
        root = BoxLayout(orientation="vertical")
        header = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(55), padding=[dp(10), dp(8)], spacing=dp(10))
        header.add_widget(fa_button("بازگشت", size=14, height=40, bg_color=[0.6, 0.6, 0.6, 1], on_press=self.on_back))
        header.add_widget(fa_label("صورتحساب کشتار روزانه", size=16, color=COLOR_PRIMARY_DARK, height=40, bold=True))
        root.add_widget(header)

        self.info_label = fa_label("در حال بارگذاری...", size=12, color=COLOR_PRIMARY_DARK, height=30, bold=True)
        root.add_widget(self.info_label)

        add_bar = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(55), padding=[dp(10), dp(5)], spacing=dp(8))
        self.main_btn = fa_button("ثبت / مشاهده صورتحساب کشتار", size=14, height=45, bg_color=COLOR_SUCCESS, on_press=self.on_open_form)
        add_bar.add_widget(self.main_btn)
        root.add_widget(add_bar)

        scroll = ScrollView()
        self.list_container = BoxLayout(orientation="vertical", padding=dp(10), spacing=dp(8), size_hint_y=None)
        self.list_container.bind(minimum_height=self.list_container.setter("height"))
        scroll.add_widget(self.list_container)
        root.add_widget(scroll)

        self.msg_label = fa_label("", size=13, color=COLOR_ERROR, height=30)
        root.add_widget(self.msg_label)
        self.add_widget(root)

        self._clock_event = Clock.schedule_interval(self._auto_refresh, 30)

    def _auto_refresh(self, dt):
        try:
            if self.invoice_data and (
                self.invoice_data.get("locked_at") or
                self.invoice_data.get("completed_at")
            ):
                self.refresh_list()
        except Exception:
            pass

    def on_leave(self, *args):
        try:
            if self._clock_event:
                self._clock_event.cancel()
                self._clock_event = None
        except Exception:
            pass

    def on_pre_enter(self, *args):
        if not self._clock_event:
            self._clock_event = Clock.schedule_interval(self._auto_refresh, 30)

        from kivymd.app import MDApp
        app = MDApp.get_running_app()
        self.current_user = app.current_user
        if not self.current_user:
            return
        role = str(self.current_user.get("role", "")).strip().lower()
        self.is_admin = (role == "admin")

        shamsi, day_name = get_work_day_shamsi()
        self.form_date = shamsi
        self.day_name = day_name

        self.info_label.text = fa(f"روز کاری: {self.day_name} {fa_digits(self.form_date)}")
        self.load_invoice()

    def load_invoice(self):
        try:
            self.invoice_data = get_or_create_daily_invoice(self.form_date, self.day_name, self.current_user["user_id"])
        except Exception as e:
            self._show_error(f"خطا: {e}")
            return

        if not self.invoice_data:
            self._show_error("صورتحساب یافت نشد.")
            return

        self.refresh_list()

    def refresh_list(self):
        self.list_container.clear_widgets()

        if not self.invoice_data:
            return

        from kivymd.app import MDApp
        app = MDApp.get_running_app()

        is_locked = bool(self.invoice_data.get("locked_at"))
        is_completed = bool(self.invoice_data.get("completed_at"))
        has_data = bool(self.invoice_data.get("created_at")) and (
            bool((self.invoice_data.get("invoice_number") or "").strip()) or
            (self.invoice_data.get("grand_total") or 0) > 0 or
            (self.invoice_data.get("total_weight") or 0) > 0
        )

        can_edit_time = can_edit_form(
            self.invoice_data.get("completed_at"),
            self.invoice_data.get("locked_at"),
            app.current_user,
        )

        card = MDCard(orientation="vertical", padding=dp(10), spacing=dp(6), size_hint=(1, None), elevation=2, radius=[dp(10)], md_bg_color=[0.85, 0.85, 0.85, 1] if is_locked else [1, 1, 1, 1])
        card.bind(minimum_height=card.setter("height"))

        row1 = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(28))
        row1.add_widget(fa_label(f"صورتحساب #{fa_digits(self.invoice_data.get('invoice_number') or '—')}", size=14, color=COLOR_PRIMARY, height=28, bold=True, halign="left"))
        row1.add_widget(fa_label(fa_digits(self.invoice_data.get("invoice_date") or "—"), size=12, color=COLOR_GRAY, height=28, halign="right"))
        card.add_widget(row1)

        grand_total = self.invoice_data.get("grand_total", 0) or 0
        row2 = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(30))
        row2.add_widget(fa_label(f"جمع کل: {fa_digits(f'{grand_total:,.0f}')} ریال", size=14, color=COLOR_PRIMARY_DARK, height=30, bold=True, halign="left"))
        card.add_widget(row2)

        if not has_data:
            card.add_widget(fa_label("[ اطلاعاتی ثبت نشده ]", size=11, color=COLOR_GRAY, height=20, bold=True))
        elif is_locked:
            card.add_widget(fa_label("[ قفل شده - تایید نهایی ]", size=11, color=COLOR_SUCCESS, height=20, bold=True))
        elif not is_completed:
            card.add_widget(fa_label("[ در انتظار ثبت نهایی ]", size=11, color=COLOR_WARNING, height=20, bold=True))

        desc = self.invoice_data.get("description", "") or ""
        if desc:
            notes_lines = textwrap.wrap(desc, width=60)
            if notes_lines:
                notes_box = BoxLayout(orientation="vertical", size_hint_y=None, padding=(dp(10), dp(10)), spacing=dp(2))
                notes_box.bind(minimum_height=notes_box.setter("height"))
                for line in notes_lines:
                    line_lbl = Label(text=fa(line), font_name="Vazir", font_size=sp(12), color=COLOR_TEXT, halign="right", valign="middle", size_hint_y=None, height=dp(22))
                    line_lbl.bind(size=lambda s, v: setattr(s, "text_size", v))
                    notes_box.add_widget(line_lbl)
                card.add_widget(notes_box)

        if has_data:
            btn_row = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(40), spacing=dp(6))
            if self.invoice_data.get("image_path"):
                full_path = resolve_receipt_image(self.invoice_data["image_path"])
                if full_path and os.path.exists(full_path):
                    btn_row.add_widget(fa_button("عکس", size=11, height=40, bg_color=COLOR_PRIMARY, on_press=lambda x, p=full_path: self.open_image(p)))

            btn_row.add_widget(fa_button("PDF", size=11, height=40, bg_color=COLOR_PRIMARY_DARK, on_press=lambda x: self.open_invoice_pdf()))
            btn_row.add_widget(fa_button("Excel", size=11, height=40, bg_color=COLOR_SUCCESS, on_press=lambda x: self.open_invoice_excel()))

            can_unlock = user_can_edit_locked(app.current_user)

            if is_locked:
                within_window = is_within_edit_window(self.invoice_data.get("locked_at"), 15)
                if can_unlock and within_window:
                    btn_row.add_widget(fa_button("ویرایش (ادمین)", size=11, height=40, bg_color=COLOR_WARNING, on_press=lambda x: self.on_admin_edit()))
                else:
                    btn_row.add_widget(fa_label(
                        "مهلت ویرایش (ادمین) تمام شده",
                        size=11, color=COLOR_GRAY, height=40, halign="center",
                    ))

            elif not is_locked and can_edit_time:
                btn_row.add_widget(fa_button("ویرایش", size=11, height=40, bg_color=COLOR_WARNING, on_press=lambda x: self.on_open_form()))
                btn_row.add_widget(fa_button("حذف", size=11, height=40, bg_color=COLOR_ERROR, on_press=lambda x: self.on_delete_invoice()))
                btn_row.add_widget(fa_button("ثبت نهایی", size=11, height=40, bg_color=COLOR_PRIMARY_DARK, on_press=lambda x: self.on_finalize_invoice()))
            elif not is_locked and is_completed and not can_edit_time:
                btn_row.add_widget(fa_label(
                    "مهلت ویرایش/حذف تمام شده",
                    size=11, color=COLOR_GRAY, height=40, halign="center",
                ))
                btn_row.add_widget(fa_button("ثبت نهایی", size=11, height=40, bg_color=COLOR_PRIMARY_DARK, on_press=lambda x: self.on_finalize_invoice()))
            card.add_widget(btn_row)

        self.list_container.add_widget(card)

    def on_admin_edit(self):
        def do_unlock():
            try:
                admin_unlock_form("daily_invoices", "form_date", self.form_date)
                self.load_invoice()
                info_dialog(
                    "انجام شد",
                    "قفل صورتحساب باز شد. حالا ۱۵ دقیقه فرصت ویرایش دارید.\n"
                    "بعد از ۱۵ دقیقه، دوباره قفل می‌شود."
                )
            except Exception as e:
                info_dialog("خطا", f"باز کردن قفل ناموفق:\n{e}")

        confirm_dialog(
            title="ویرایش صورتحساب قفل‌شده",
            message=(
                "آیا از باز کردن قفل این صورتحساب مطمئن هستید؟\n\n"
                "⚠️ پس از باز کردن قفل، ۱۵ دقیقه فرصت ویرایش دارید.\n"
                "بعد از آن، دوباره قفل می‌شود."
            ),
            confirm_text="باز کن",
            cancel_text="لغو",
            confirm_color=COLOR_WARNING,
            on_confirm=do_unlock,
        )

    def on_open_form(self, *args):
        self._show_form_dialog()

    def _show_form_dialog(self):
        invoice_data = self.invoice_data

        try:
            default_rates = get_invoice_settings()
        except Exception:
            default_rates = {}

        has_saved = bool(invoice_data.get("created_at")) and (
            bool((invoice_data.get("invoice_number") or "").strip()) or
            (invoice_data.get("grand_total") or 0) > 0
        )

        data = {}
        if has_saved:
            for k, v in invoice_data.items():
                data[k] = v if v is not None else ""
        else:
            prefill = get_invoice_prefill_data(self.form_date)
            data = {
                "w1_full":0,"w1_empty":0,"w1_net":0,"w1_qty":0,"w1_rate":0,"w1_amount":0,
                "w2_full":0,"w2_empty":0,"w2_net":0,"w2_qty":0,"w2_rate":0,"w2_amount":0,
                "w3_full":0,"w3_empty":0,"w3_net":0,"w3_qty":0,"w3_rate":0,"w3_amount":0,
                "w4_full":0,"w4_empty":0,"w4_net":0,"w4_qty":0,"w4_rate":0,"w4_amount":0,
                "w5_full":0,"w5_empty":0,"w5_net":0,"w5_qty":0,"w5_rate":0,"w5_amount":0,
                "total_weight":0, "total_amount":0,
                "c1_amount":0, "c1_rate":default_rates.get("c1_rate", 105000), "c1_total":0,
                "c2_amount":0, "c2_rate":default_rates.get("c2_rate", 24000), "c2_total":0,
                "e1_amount":0, "e1_rate":default_rates.get("e1_rate", 1300000), "e1_total":0,
                "e2_amount":0, "e2_rate":default_rates.get("e2_rate", 35000), "e2_total":0,
                "e3_amount":0, "e3_rate":default_rates.get("e3_rate", 33600), "e3_total":0,
                "e4_amount":0, "e4_rate":default_rates.get("e4_rate", 7000), "e4_total":0,
                "e5_amount":0, "e5_rate":default_rates.get("e5_rate", 13720), "e5_total":0,
                "e6_amount":0, "e6_rate":default_rates.get("e6_rate", 15220), "e6_total":0,
                "e7_amount":0, "e7_rate":default_rates.get("e7_rate", 60000), "e7_total":0,
                "e8_amount":0, "e8_rate":default_rates.get("e8_rate", 80), "e8_total":0,
                "e9_amount":0, "e9_rate":0, "e9_total":0,
                "vat_rate": 10, "vat_amount": 0, "grand_total": 0,
            }
            for i in range(1, 6):
                data[f"w{i}_full"] = prefill.get(f"w{i}_full", 0)
                data[f"w{i}_empty"] = prefill.get(f"w{i}_empty", 0)
                data[f"w{i}_net"] = prefill.get(f"w{i}_net", 0)
                data[f"w{i}_qty"] = prefill.get(f"w{i}_qty", "")
                data[f"w{i}_rate"] = prefill.get(f"w{i}_rate", 0)
                data[f"w{i}_amount"] = prefill.get(f"w{i}_amount", 0)
            data["total_weight"] = prefill.get("total_weight", 0)

        self.inputs = {}
        self.selected_image_path = None
        self.selected_date = str(data.get("invoice_date") or "")

        content = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(8), size_hint_y=None)
        content.bind(minimum_height=content.setter("height"))
        with content.canvas.before:
            Color(1, 1, 1, 1)
            content._bg = RoundedRectangle(pos=content.pos, size=content.size, radius=[dp(10)])
        content.bind(pos=lambda s, v: setattr(s._bg, "pos", v), size=lambda s, v: setattr(s._bg, "size", v))

        content.add_widget(fa_label("صورتحساب کشتار روزانه", size=16, color=COLOR_PRIMARY_DARK, height=35, bold=True))

        content.add_widget(fa_section_title("شماره صورتحساب:", height=22))
        num_wrap = fa_text_input(hint_text="شماره", text=str(data.get("invoice_number") or ""), height=45)
        content.add_widget(num_wrap)

        content.add_widget(fa_section_title("تاریخ:", height=22))
        date_btn = Button(text=fa(self.selected_date) if self.selected_date else fa("انتخاب تاریخ"), font_name="Vazir", font_size=sp(13), size_hint_y=None, height=dp(45), background_normal="", background_color=COLOR_PRIMARY if self.selected_date else [0.92, 0.92, 0.92, 1], color=COLOR_WHITE if self.selected_date else COLOR_TEXT)
        content.add_widget(date_btn)

        content.add_widget(spacer(10))
        content.add_widget(fa_label("جدول وزن‌کشی (از قبض‌های باسکول)", size=14, color=COLOR_PRIMARY_DARK, bold=True))

        header_row = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(25), spacing=dp(4))
        for txt in ["مبلغ", "فی", "خالص", "تعداد", "وزن خالی", "وزن پر", "ردیف"]:
            header_row.add_widget(fa_label(txt, size=10, color=COLOR_PRIMARY_DARK, bold=True, halign="center"))
        content.add_widget(header_row)

        for i in range(1, 6):
            row_box = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(40), spacing=dp(4))

            w_amt_lbl = fa_label("۰", size=11, color=COLOR_SUCCESS, bold=True)
            w_rate = fa_text_input(hint_text="", text=str(data.get(f"w{i}_rate") or ""), input_filter="float", height=40)
            w_net_lbl = fa_label(fa_digits(f"{data.get(f'w{i}_net') or 0:,.2f}"), size=11, color=COLOR_PRIMARY, bold=True)
            w_qty = fa_text_input(hint_text="", text=str(data.get(f"w{i}_qty") or ""), input_filter="float", height=40)

            full_val = data.get(f"w{i}_full") or 0
            empty_val = data.get(f"w{i}_empty") or 0
            w_full_lbl = fa_label(fa_digits(f"{full_val:,.2f}"), size=11, color=COLOR_TEXT, bold=True)
            w_empty_lbl = fa_label(fa_digits(f"{empty_val:,.2f}"), size=11, color=COLOR_TEXT, bold=True)

            row_lbl = fa_label(fa_digits(str(i)), size=11, halign="center", bold=True)

            self.inputs[f"w{i}_full_val"] = full_val
            self.inputs[f"w{i}_empty_val"] = empty_val
            self.inputs[f"w{i}_qty"] = w_qty
            self.inputs[f"w{i}_net_lbl"] = w_net_lbl
            self.inputs[f"w{i}_rate"] = w_rate
            self.inputs[f"w{i}_amt_lbl"] = w_amt_lbl

            w_qty.hidden.bind(text=lambda inst, val, idx=i: self._recalc_weight(idx))
            w_rate.hidden.bind(text=lambda inst, val, idx=i: self._recalc_weight(idx))

            row_box.add_widget(w_amt_lbl)
            row_box.add_widget(w_rate)
            row_box.add_widget(w_net_lbl)
            row_box.add_widget(w_qty)
            row_box.add_widget(w_empty_lbl)
            row_box.add_widget(w_full_lbl)
            row_box.add_widget(row_lbl)

            content.add_widget(row_box)

        self.total_weight_lbl = fa_label("۰", size=13, color=COLOR_PRIMARY_DARK, bold=True)
        content.add_widget(self.total_weight_lbl)

        content.add_widget(spacer(10))
        content.add_widget(fa_label("کشتار و بسته‌بندی", size=14, color=COLOR_PRIMARY_DARK, bold=True))

        row_c1 = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(45), spacing=dp(4))
        c1_total = fa_label("۰", size=12, color=COLOR_SUCCESS, bold=True)
        self.inputs["c1_total_lbl"] = c1_total
        c1_rate = fa_text_input(hint_text="فی", text=str(data.get("c1_rate") or 105000), input_filter="float", height=45)
        self.inputs["c1_rate"] = c1_rate
        c1_amt = fa_label("۰", size=12, halign="center")
        self.inputs["c1_amount_lbl"] = c1_amt

        row_c1.add_widget(c1_total)
        row_c1.add_widget(c1_rate)
        row_c1.add_widget(c1_amt)
        row_c1.add_widget(fa_label("کشتار مرغ گوشتی", size=12, halign="right"))

        c1_rate.hidden.bind(text=lambda inst, val: self._recalc_all())
        content.add_widget(row_c1)

        row_c2 = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(45), spacing=dp(4))
        c2_total = fa_label("۰", size=12, color=COLOR_SUCCESS, bold=True)
        self.inputs["c2_total_lbl"] = c2_total
        c2_rate = fa_text_input(hint_text="فی", text=str(data.get("c2_rate") or 24000), input_filter="float", height=45)
        self.inputs["c2_rate"] = c2_rate
        c2_amt = fa_text_input(hint_text="مقدار", text=str(data.get("c2_amount") or ""), input_filter="float", height=45)
        self.inputs["c2_amount"] = c2_amt

        row_c2.add_widget(c2_total)
        row_c2.add_widget(c2_rate)
        row_c2.add_widget(c2_amt)
        row_c2.add_widget(fa_label("بسته بندی مرغ گوشتی", size=12, halign="right"))

        c2_amt.hidden.bind(text=lambda inst, val: self._recalc_all())
        c2_rate.hidden.bind(text=lambda inst, val: self._recalc_all())
        content.add_widget(row_c2)

        content.add_widget(spacer(10))
        content.add_widget(fa_label("خلاصه فاکتور (کشتار و بسته‌بندی)", size=14, color=COLOR_PRIMARY_DARK, bold=True))

        self.base_lbl = fa_label("مبلغ پایه: ۰ ریال", size=13, bold=True)
        content.add_widget(self.base_lbl)

        self.vat_lbl = fa_label("ارزش افزوده (۱۰٪): ۰ ریال", size=13, bold=True)
        content.add_widget(self.vat_lbl)

        self.grand_total_lbl = fa_label("جمع کل: ۰ ریال", size=15, color=COLOR_PRIMARY_DARK, bold=True)
        content.add_widget(self.grand_total_lbl)

        content.add_widget(spacer(10))
        content.add_widget(fa_label("هزینه‌ها", size=14, color=COLOR_PRIMARY_DARK, bold=True))

        expense_names = [
            "هزینه یخ مازاد داخل خودرو",
            "بسته بندی دل و کگر و سنگدان",
            "قطعه بندی مرغ",
            "پاکسازی دل و کگر و سنگدان",
            "پوست گیری پای مرغ",
            "صدور مجوز",
            "پالمپ",
            "عوارض دامپزشکی"
        ]

        for i, name in enumerate(expense_names, start=1):
            row_e = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(45), spacing=dp(4))
            e_total = fa_label("۰", size=12, color=COLOR_SUCCESS, bold=True)
            rate_val = data.get(f"e{i}_rate")
            if not rate_val:
                rate_val = default_rates.get(f"e{i}_rate", "")
            e_rate = fa_text_input(hint_text="فی", text=str(rate_val or ""), input_filter="float", height=45)
            e_amt = fa_text_input(hint_text="مقدار", text=str(data.get(f"e{i}_amount") or ""), input_filter="float", height=45)

            self.inputs[f"e{i}_amount"] = e_amt
            self.inputs[f"e{i}_rate"] = e_rate
            self.inputs[f"e{i}_total_lbl"] = e_total

            e_amt.hidden.bind(text=lambda inst, val: self._recalc_all())
            e_rate.hidden.bind(text=lambda inst, val: self._recalc_all())

            row_e.add_widget(e_total)
            row_e.add_widget(e_rate)
            row_e.add_widget(e_amt)

            name_lbl = Label(
                text=fa(name),
                font_name="Vazir",
                font_size=sp(11),
                color=COLOR_TEXT,
                halign="right",
                valign="middle",
                size_hint=(None, 1),
                width=dp(130),
            )
            name_lbl.bind(size=lambda s, v: setattr(s, "text_size", v))
            row_e.add_widget(name_lbl)

            content.add_widget(row_e)

        content.add_widget(spacer(10))
        content.add_widget(fa_label("خلاصه فاکتور (فقط هزینه‌ها)", size=14, color=COLOR_PRIMARY_DARK, bold=True))

        self.exp_base_lbl = fa_label("جمع هزینه‌های مشمول: ۰ ریال", size=13, bold=True)
        content.add_widget(self.exp_base_lbl)

        self.exp_vat_lbl = fa_label("ارزش افزوده هزینه‌ها (۱۰٪): ۰ ریال", size=13, bold=True)
        content.add_widget(self.exp_vat_lbl)

        self.exp_avarez_lbl = fa_label("عوارض دامپزشکی: ۰ ریال", size=13, bold=True)
        content.add_widget(self.exp_avarez_lbl)

        self.exp_grand_total_lbl = fa_label("جمع کل هزینه‌ها: ۰ ریال", size=15, color=COLOR_PRIMARY_DARK, bold=True)
        content.add_widget(self.exp_grand_total_lbl)

        content.add_widget(spacer(6))
        content.add_widget(fa_section_title("توضیحات:", height=22))
        desc_wrap = fa_text_input_multiline(hint_text="توضیحات (اختیاری)", text=str(data.get("description") or ""), height=80, min_height=80)
        content.add_widget(desc_wrap)

        content.add_widget(spacer(6))
        content.add_widget(fa_label("عکس صورتحساب:", size=12, bold=True, halign="right"))
        preview_label = fa_label("عکس جدیدی انتخاب نشده", size=12, color=COLOR_GRAY, height=dp(30))
        content.add_widget(preview_label)

        img_btns = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(45), spacing=dp(6))
        def on_image_picked(path):
            if path:
                self.selected_image_path = path
                preview_label.text = fa(f"عکس: {os.path.basename(path)}")
                preview_label.color = COLOR_SUCCESS

        def take_camera(*args):
            from ..helpers.image_picker import pick_image, is_android
            if not is_android(): return
            pick_image(source="camera", on_result=on_image_picked)

        def pick_gallery(*args):
            from ..helpers.image_picker import pick_image
            pick_image(source="gallery", on_result=on_image_picked)

        img_btns.add_widget(fa_button("دوربین", size=12, height=45, bg_color=COLOR_PRIMARY, on_press=take_camera))
        img_btns.add_widget(fa_button("گالری", size=12, height=45, bg_color=COLOR_PRIMARY_DARK, on_press=pick_gallery))
        content.add_widget(img_btns)

        content.add_widget(spacer(10))
        btns = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(55), spacing=dp(8))
        cancel_btn = Button(text=fa("لغو"), font_name="Vazir", font_size=sp(14), background_normal="", background_color=[0.7, 0.7, 0.7, 1], color=COLOR_WHITE, bold=True)
        save_btn = Button(text=fa("ذخیره"), font_name="Vazir", font_size=sp(14), background_normal="", background_color=COLOR_SUCCESS, color=COLOR_WHITE, bold=True)
        btns.add_widget(cancel_btn)
        btns.add_widget(save_btn)
        content.add_widget(btns)

        inner_scroll = ScrollView()
        inner_scroll.add_widget(content)

        popup = Popup(title="", title_size=0, content=inner_scroll, size_hint=(None, None), size=(dp(520), dp(800)), auto_dismiss=False, background="", background_color=[0, 0, 0, 0.5], separator_height=0)
        cancel_btn.bind(on_release=lambda x: popup.dismiss())

        def open_calendar(*args):
            cal_content = BoxLayout(orientation="vertical", padding=dp(10), spacing=dp(5))
            with cal_content.canvas.before:
                Color(1, 1, 1, 1)
                cal_content._bg = RoundedRectangle(pos=cal_content.pos, size=cal_content.size, radius=[dp(10)])
            cal_content.bind(pos=lambda s, v: setattr(s._bg, "pos", v), size=lambda s, v: setattr(s._bg, "size", v))

            cal_content.add_widget(fa_label("انتخاب تاریخ", size=15, color=COLOR_PRIMARY_DARK, height=35, bold=True))
            def on_date_selected(date_str):
                self.selected_date = date_str
                date_btn.text = fa(date_str)
                date_btn.background_color = COLOR_PRIMARY
                date_btn.color = COLOR_WHITE
                calendar_popup.dismiss()

            cal = ShamsiCalendar(initial_date=self.selected_date or None, on_select=on_date_selected)
            cal_content.add_widget(cal)

            calendar_popup = Popup(title="", title_size=0, content=cal_content, size_hint=(None, None), size=(dp(400), dp(520)), auto_dismiss=True, background="", background_color=[0, 0, 0, 0.5], separator_height=0)
            calendar_popup.open()

        date_btn.bind(on_release=open_calendar)

        def do_save(*args):
            new_data = {}
            new_data["invoice_number"] = num_wrap.text.strip()
            new_data["invoice_date"] = self.selected_date
            new_data["description"] = desc_wrap.text

            if not new_data["invoice_number"]:
                new_data["invoice_number"] = f"INV-{self.form_date.replace('/', '')}"

            for i in range(1, 6):
                full_val = self.inputs.get(f"w{i}_full_val", 0)
                empty_val = self.inputs.get(f"w{i}_empty_val", 0)
                qty_val = self._p(self.inputs[f"w{i}_qty"].text)
                rate_val = self._p(self.inputs[f"w{i}_rate"].text)

                net_val = max(0, full_val - empty_val)
                amt_val = net_val * (qty_val if qty_val > 0 else 1) * rate_val

                new_data[f"w{i}_full"] = full_val
                new_data[f"w{i}_empty"] = empty_val
                new_data[f"w{i}_qty"] = qty_val
                new_data[f"w{i}_net"] = net_val
                new_data[f"w{i}_rate"] = rate_val
                new_data[f"w{i}_amount"] = amt_val

            new_data["total_weight"] = sum(new_data[f"w{i}_net"] for i in range(1,6))

            new_data["c1_amount"] = new_data["total_weight"]
            new_data["c1_rate"] = self._p(self.inputs["c1_rate"].text)
            new_data["c1_total"] = new_data["c1_amount"] * new_data["c1_rate"]

            new_data["c2_amount"] = self._p(self.inputs["c2_amount"].text)
            new_data["c2_rate"] = self._p(self.inputs["c2_rate"].text)
            new_data["c2_total"] = new_data["c2_amount"] * new_data["c2_rate"]

            for i in range(1, 9):
                new_data[f"e{i}_amount"] = self._p(self.inputs[f"e{i}_amount"].text)
                new_data[f"e{i}_rate"] = self._p(self.inputs[f"e{i}_rate"].text)
                new_data[f"e{i}_total"] = new_data[f"e{i}_amount"] * new_data[f"e{i}_rate"]

            base_total = new_data["c1_total"] + new_data["c2_total"]
            new_data["vat_rate"] = 10
            new_data["vat_amount"] = base_total * 0.1
            new_data["grand_total"] = base_total + new_data["vat_amount"]

            try:
                save_daily_invoice(self.form_date, new_data, self.selected_image_path)
            except Exception as e:
                info_dialog("خطا", f"ذخیره ناموفق:\n{e}")
                return

            popup.dismiss()
            info_dialog("ثبت موفق", "صورتحساب کشتار روزانه ذخیره شد.")
            self.load_invoice()

        save_btn.bind(on_release=do_save)
        self._recalc_all()
        popup.open()

    def _p(self, txt):
        try: return float(str(txt).strip()) if txt and str(txt).strip() else 0.0
        except: return 0.0

    def _recalc_weight(self, i):
        full = self.inputs.get(f"w{i}_full_val", 0)
        empty = self.inputs.get(f"w{i}_empty_val", 0)
        qty = self._p(self.inputs[f"w{i}_qty"].text)
        rate = self._p(self.inputs[f"w{i}_rate"].text)

        net = max(0, full - empty)
        amt = net * (qty if qty > 0 else 1) * rate

        self.inputs[f"w{i}_net_lbl"].text = fa_digits(f"{net:,.2f}")
        self.inputs[f"w{i}_amt_lbl"].text = fa_digits(f"{amt:,.0f}")
        self._recalc_all()

    def _recalc_all(self):
        try:
            total_weight = 0
            for i in range(1, 6):
                full = self.inputs.get(f"w{i}_full_val", 0)
                empty = self.inputs.get(f"w{i}_empty_val", 0)
                total_weight += max(0, full - empty)

            self.total_weight_lbl.text = fa(f"جمع وزن خالص: {fa_digits(f'{total_weight:,.2f}')} کیلوگرم")
            self.inputs["c1_amount_lbl"].text = fa_digits(f"{total_weight:,.2f}")

            c1_tot = total_weight * self._p(self.inputs["c1_rate"].text)
            self.inputs["c1_total_lbl"].text = fa_digits(f"{c1_tot:,.0f}")

            c2_tot = self._p(self.inputs["c2_amount"].text) * self._p(self.inputs["c2_rate"].text)
            self.inputs["c2_total_lbl"].text = fa_digits(f"{c2_tot:,.0f}")

            e_totals = []
            e_total = 0
            for i in range(1, 9):
                tot = self._p(self.inputs[f"e{i}_amount"].text) * self._p(self.inputs[f"e{i}_rate"].text)
                e_totals.append(tot)
                if f"e{i}_total_lbl" in self.inputs:
                    self.inputs[f"e{i}_total_lbl"].text = fa_digits(f"{tot:,.0f}")
                e_total += tot

            base = c1_tot + c2_tot
            vat = base * 0.1
            grand = base + vat

            self.base_lbl.text = fa(f"مبلغ پایه (کشتار + بسته‌بندی): {fa_digits(f'{base:,.0f}')} ریال")
            self.vat_lbl.text = fa(f"ارزش افزوده (۱۰٪): {fa_digits(f'{vat:,.0f}')} ریال")
            self.grand_total_lbl.text = fa(f"جمع کل: {fa_digits(f'{grand:,.0f}')} ریال")

            e_taxable_total = sum(e_totals[:7])
            e_avarez_total = e_totals[7] if len(e_totals) > 7 else 0.0

            exp_vat = e_taxable_total * 0.1
            exp_grand = e_taxable_total + exp_vat + e_avarez_total

            self.exp_base_lbl.text = fa(f"جمع هزینه‌های مشمول: {fa_digits(f'{e_taxable_total:,.0f}')} ریال")
            self.exp_vat_lbl.text = fa(f"ارزش افزوده هزینه‌ها (۱۰٪): {fa_digits(f'{exp_vat:,.0f}')} ریال")
            self.exp_avarez_lbl.text = fa(f"عوارض دامپزشکی: {fa_digits(f'{e_avarez_total:,.0f}')} ریال")
            self.exp_grand_total_lbl.text = fa(f"جمع کل هزینه‌ها: {fa_digits(f'{exp_grand:,.0f}')} ریال")

        except Exception as e:
            print(f"Error in calc: {e}")

    def on_finalize_invoice(self):
        confirm_dialog(title="ثبت نهایی", message="آیا مطمئن هستید؟", confirm_text="بله", cancel_text="لغو", confirm_color=COLOR_PRIMARY_DARK, on_confirm=self._do_finalize)

    def _do_finalize(self):
        try:
            finalize_form("daily_invoices", "form_date", self.form_date)
        except Exception as e:
            info_dialog("خطا", str(e))
            return
        info_dialog("تایید شد", "صورتحساب قفل شد.")
        self.load_invoice()

    def on_delete_invoice(self):
        def do_delete():
            try:
                delete_daily_invoice(self.form_date)
            except Exception as e:
                info_dialog("خطا", f"حذف ناموفق:\n{e}")
                return
            info_dialog("حذف موفق", "صورتحساب کشتار روزانه حذف شد.")
            self.load_invoice()

        confirm_dialog(
            title="حذف صورتحساب",
            message="آیا از حذف این صورتحساب مطمئن هستید؟\nاین عمل قابل بازگشت نیست.",
            confirm_text="حذف", cancel_text="لغو", confirm_color=COLOR_ERROR,
            on_confirm=do_delete,
        )

    def open_image(self, full_path):
        from ..helpers.file_utils import open_file
        if os.path.exists(full_path): open_file(full_path)

    def open_invoice_pdf(self):
        from ..helpers.file_dialog import ask_save_path, ask_open_after_save
        from ..helpers.file_utils import open_file
        try:
            from pdf_invoice import generate_daily_invoice_pdf
            from datetime import datetime
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_date = self.form_date.replace("/", "-")
            default_name = f"invoice_{safe_date}_{ts}"

            def do_save(filepath):
                try:
                    result = generate_daily_invoice_pdf(self.form_date, filepath)
                except Exception as e:
                    info_dialog("خطا در ساخت PDF", str(e))
                    return
                info_dialog("خروجی PDF ساخته شد", f"فایل ذخیره شد در:\n\n{result}")
                ask_open_after_save(on_yes=lambda: open_file(result))

            ask_save_path(
                title="ذخیره خروجی PDF",
                default_filename=default_name,
                file_extension=".pdf",
                on_save=do_save,
            )
        except Exception as e:
            info_dialog("خطا", str(e))

    def open_invoice_excel(self):
        from ..helpers.file_dialog import ask_save_path, ask_open_after_save
        from ..helpers.file_utils import open_file
        try:
            from pdf_invoice import generate_daily_invoice_excel
            from datetime import datetime
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_date = self.form_date.replace("/", "-")
            default_name = f"invoice_{safe_date}_{ts}"

            def do_save(filepath):
                try:
                    result = generate_daily_invoice_excel(self.form_date, filepath)
                except Exception as e:
                    info_dialog("خطا در ساخت Excel", str(e))
                    return
                info_dialog("خروجی Excel ساخته شد", f"فایل ذخیره شد در:\n\n{result}")
                ask_open_after_save(on_yes=lambda: open_file(result))

            ask_save_path(
                title="ذخیره خروجی Excel",
                default_filename=default_name,
                file_extension=".xlsx",
                on_save=do_save,
            )
        except Exception as e:
            info_dialog("خطا", str(e))

    def _show_error(self, text):
        self.msg_label.text = fa(text)
        self.msg_label.color = COLOR_ERROR

    def on_back(self, *args):
        self.manager.transition.direction = "right"
        self.manager.current = "slaughters_list"
