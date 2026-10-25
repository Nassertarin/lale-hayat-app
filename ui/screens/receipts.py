# -*- coding: utf-8 -*-
"""
صفحه‌ی قبض‌های باسکول یک کشتار
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
    COLOR_ERROR, COLOR_SUCCESS, COLOR_TEXT, COLOR_WHITE,
    COLOR_WARNING,
)
from ..helpers.widgets import (
    fa_label, fa_button, spacer, fa_text_input, fa_section_title,
    fa_text_input_multiline,
)
from ..helpers.dialogs import confirm_dialog, info_dialog
from ..helpers.shamsi_calendar import ShamsiCalendar

from functions import (
    get_slaughter, get_receipts, get_receipt, add_receipt,
    delete_receipt, update_receipt, lock_receipt, can_edit_receipt,
    can_edit_form, admin_unlock_form, finalize_form, user_can_edit_locked,
    is_within_edit_window,
)

from database import resolve_receipt_image


def parse_extra(description):
    if not description:
        return {
            "full": None, "empty": None,
            "name": "", "code": "", "scale_name": "",
            "text": "", "full_date": "", "full_time": "",
            "empty_date": "", "empty_time": "",
            "cost": "",
        }
    parts = {}
    text_parts = []
    for token in description.split("|"):
        if ":" in token:
            k, v = token.split(":", 1)
            k = k.strip().upper()
            if k in ("FULL", "EMPTY", "NAME", "CODE", "SCALE",
                     "FULL_DATE", "FULL_TIME", "EMPTY_DATE", "EMPTY_TIME", "COST"):
                parts[k] = v.strip()
                continue
        text_parts.append(token)

    if parts:
        try:
            full_v = float(parts["FULL"]) if parts.get("FULL") else None
        except (ValueError, TypeError):
            full_v = None
        try:
            empty_v = float(parts["EMPTY"]) if parts.get("EMPTY") else None
        except (ValueError, TypeError):
            empty_v = None
        return {
            "full": full_v,
            "empty": empty_v,
            "name": parts.get("NAME", ""),
            "code": parts.get("CODE", ""),
            "scale_name": parts.get("SCALE", ""),
            "full_date": parts.get("FULL_DATE", ""),
            "full_time": parts.get("FULL_TIME", ""),
            "empty_date": parts.get("EMPTY_DATE", ""),
            "empty_time": parts.get("EMPTY_TIME", ""),
            "cost": parts.get("COST", ""),
            "text": " | ".join(text_parts).strip(),
        }
    return {
        "full": None, "empty": None,
        "name": "", "code": "", "scale_name": "",
        "full_date": "", "full_time": "", "empty_date": "", "empty_time": "",
        "cost": "",
        "text": description,
    }


class ReceiptsScreen(MDScreen):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "receipts"
        self.md_bg_color = COLOR_BG

        self.slaughter_id = None
        self.slaughter_info = None
        self.is_admin = False
        self.current_user = None

        self.info_label = None
        self.list_container = None
        self.msg_label = None

        self.selected_image_path = None
        self.selected_date = ""

        self._clock_event = None

        self.build_ui()

    def build_ui(self):
        root = BoxLayout(orientation="vertical")

        header = BoxLayout(
            orientation="horizontal", size_hint_y=None,
            height=dp(55), padding=[dp(10), dp(8)], spacing=dp(10),
        )
        header.add_widget(fa_button(
            "بازگشت", size=14, height=40,
            bg_color=[0.6, 0.6, 0.6, 1], on_press=self.on_back,
        ))
        header.add_widget(fa_label(
            "قبض‌های باسکول", size=16,
            color=COLOR_PRIMARY_DARK, height=40, bold=True,
        ))
        root.add_widget(header)

        self.info_label = fa_label(
            "در حال بارگذاری...", size=12,
            color=COLOR_PRIMARY_DARK, height=30, bold=True,
        )
        root.add_widget(self.info_label)

        add_bar = BoxLayout(
            orientation="horizontal", size_hint_y=None,
            height=dp(55), padding=[dp(10), dp(5)], spacing=dp(8),
        )
        add_bar.add_widget(fa_button(
            "+ افزودن قبض جدید", size=14, height=45,
            bg_color=COLOR_SUCCESS, on_press=self.on_add_receipt,
        ))
        root.add_widget(add_bar)

        scroll = ScrollView()
        self.list_container = BoxLayout(
            orientation="vertical", padding=dp(10), spacing=dp(8),
            size_hint_y=None,
        )
        self.list_container.bind(
            minimum_height=self.list_container.setter("height")
        )
        scroll.add_widget(self.list_container)
        root.add_widget(scroll)

        self.msg_label = fa_label("", size=13, color=COLOR_ERROR, height=30)
        root.add_widget(self.msg_label)

        self.add_widget(root)

        self._clock_event = Clock.schedule_interval(self._auto_refresh, 30)

    def _auto_refresh(self, dt):
        try:
            if self.slaughter_id:
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
            self._show_error("نشست کاربر منقضی شده.")
            return

        role = str(self.current_user.get("role", "")).strip().lower()
        self.is_admin = (role == "admin")

        self.slaughter_id = getattr(app, "current_slaughter_id", None)
        if self.slaughter_id is None:
            self._show_error("کشتار انتخاب نشده.")
            return

        self.slaughter_info = get_slaughter(self.slaughter_id)
        if not self.slaughter_info:
            self._show_error("کشتار یافت نشد.")
            return

        si = self.slaughter_info
        self.info_label.text = fa(
            f"کشتار #{si['slaughter_number']} — "
            f"{si['day_name']} {si['form_date']}"
        )

        self.refresh_list()

    def refresh_list(self):
        self.list_container.clear_widgets()

        try:
            receipts = get_receipts(self.slaughter_id)
        except Exception as e:
            self._show_error(f"خطا در بارگذاری: {e}")
            return

        if not receipts:
            self.list_container.add_widget(fa_label(
                "هیچ قبضی برای این کشتار ثبت نشده.",
                size=14, color=COLOR_GRAY, height=60,
            ))
            return

        for r in receipts:
            self.list_container.add_widget(self._make_card(r))

    def _make_card(self, r):
        from kivymd.app import MDApp

        is_locked = bool(r.get("locked_at"))
        is_completed = bool(r.get("completed_at"))

        app = MDApp.get_running_app()

        can_edit_time = can_edit_form(
            r.get("completed_at"),
            r.get("locked_at"),
            app.current_user,
        )

        if is_locked:
            bg = [0.85, 0.85, 0.85, 1]
        elif is_completed:
            bg = [0.92, 0.98, 0.92, 1]
        else:
            bg = [1, 1, 1, 1]

        card = MDCard(
            orientation="vertical",
            padding=dp(10),
            spacing=dp(6),
            size_hint=(1, None),
            elevation=2,
            radius=[dp(10)],
            md_bg_color=bg,
        )
        card.bind(minimum_height=card.setter("height"))

        row1 = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(28))
        row1.add_widget(fa_label(
            f"قبض #{r['receipt_number'] or '—'}", size=14,
            color=COLOR_PRIMARY, height=28, bold=True, halign="left",
        ))
        row1.add_widget(fa_label(
            r["receipt_date"] or "—", size=12,
            color=COLOR_GRAY, height=28, halign="right",
        ))
        card.add_widget(row1)

        row2 = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(30))
        row2.add_widget(fa_label(
            f"وزن خالص: {r['net_weight']:,.2f} kg", size=14,
            color=COLOR_PRIMARY_DARK, height=30, bold=True, halign="left",
        ))
        if r["car_plate"]:
            row2.add_widget(fa_label(
                f"پلاک: {r['car_plate']}", size=12,
                color=COLOR_TEXT, height=30, halign="right",
            ))
        card.add_widget(row2)

        if is_locked:
            card.add_widget(fa_label(
                "[ قفل شده - تایید نهایی ]", size=11,
                color=COLOR_SUCCESS, height=20, bold=True,
            ))
        elif is_completed:
            card.add_widget(fa_label(
                "[ ثبت شده - منتظر تایید ]", size=11,
                color=COLOR_WARNING, height=20, bold=True,
            ))

        extra = []
        if r["driver_name"]: extra.append(f"راننده: {r['driver_name']}")
        if r["buyer_name"]: extra.append(f"مشتری: {r['buyer_name']}")
        if extra:
            card.add_widget(fa_label(
                "  |  ".join(extra), size=12, color=COLOR_GRAY,
                height=22, halign="right",
            ))

        parsed = parse_extra(r["description"])
        user_text = parsed.get("text", "")
        if user_text:
            lines = textwrap.wrap(user_text, width=60)
            final_desc = "\n".join([fa(line) for line in lines])

            desc_lbl = Label(
                text=final_desc,
                font_name="Vazir",
                font_size=sp(11),
                color=COLOR_GRAY,
                halign="right",
                valign="top",
                size_hint_y=None,
                text_size=(dp(400), None),
            )
            desc_lbl.bind(texture_size=lambda instance, value: setattr(instance, 'height', value[1]))

            def update_width(instance, value):
                instance.text_size = (value - dp(20), None)

            card.bind(width=update_width)
            card.add_widget(desc_lbl)

        btn_row_main = BoxLayout(
            orientation="horizontal", size_hint_y=None,
            height=dp(40), spacing=dp(6),
        )

        if r.get("image_path"):
            full_path = resolve_receipt_image(r["image_path"])
            if full_path and os.path.exists(full_path):
                btn_row_main.add_widget(fa_button(
                    "عکس", size=11, height=40, bg_color=COLOR_PRIMARY,
                    on_press=lambda x, p=full_path: self.open_image(p),
                ))

        btn_row_main.add_widget(fa_button(
            "PDF", size=11, height=40, bg_color=COLOR_PRIMARY_DARK,
            on_press=lambda x, rid=r["receipt_id"]: self.open_receipt_pdf(rid),
        ))
        card.add_widget(btn_row_main)

        can_unlock = user_can_edit_locked(app.current_user)


        if is_locked:
            within_window = is_within_edit_window(r.get("locked_at"), 15)
            if can_unlock and within_window:
                btn_row_admin = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(40), spacing=dp(6))
                btn_row_admin.add_widget(fa_button(
                    "ویرایش (ادمین)",
                    size=11, height=40,
                    bg_color=COLOR_WARNING,
                    on_press=lambda x, rid=r["receipt_id"]: self.on_admin_edit_receipt(rid),
                ))
                card.add_widget(btn_row_admin)
            else:
                card.add_widget(fa_label(
                    "مهلت ویرایش (ادمین) تمام شده",
                    size=11, color=COLOR_GRAY, height=dp(30), halign="center",
                ))

        elif not is_locked and can_edit_time:
            btn_row_status = BoxLayout(
                orientation="horizontal", size_hint_y=None,
                height=dp(40), spacing=dp(6),
            )
            btn_row_status.add_widget(fa_button(
                "ویرایش", size=12, height=40, bg_color=COLOR_WARNING,
                on_press=lambda x, rid=r["receipt_id"]: self.on_edit_receipt(rid),
            ))
            btn_row_status.add_widget(fa_button(
                "حذف", size=12, height=40, bg_color=COLOR_ERROR,
                on_press=lambda x, rid=r["receipt_id"]: self.on_delete_receipt(rid),
            ))
            btn_row_status.add_widget(fa_button(
                "ثبت نهایی", size=12, height=40, bg_color=COLOR_PRIMARY_DARK,
                on_press=lambda x, rid=r["receipt_id"]: self.on_finalize_receipt(rid),
            ))
            card.add_widget(btn_row_status)

        elif not is_locked and is_completed and not can_edit_time:
            btn_row_status = BoxLayout(
                orientation="horizontal", size_hint_y=None,
                height=dp(40), spacing=dp(6),
            )
            btn_row_status.add_widget(fa_label(
                "مهلت ویرایش/حذف تمام شده",
                size=11, color=COLOR_GRAY, height=40, halign="center",
            ))
            btn_row_status.add_widget(fa_button(
                "ثبت نهایی", size=12, height=40, bg_color=COLOR_PRIMARY_DARK,
                on_press=lambda x, rid=r["receipt_id"]: self.on_finalize_receipt(rid),
            ))
            card.add_widget(btn_row_status)

        elif not is_locked and not is_completed and self.is_admin:
            btn_row_admin = BoxLayout(
                orientation="horizontal", size_hint_y=None,
                height=dp(40), spacing=dp(6),
            )
            btn_row_admin.add_widget(fa_button(
                "حذف (مدیر)", size=12, height=40, bg_color=COLOR_ERROR,
                on_press=lambda x, rid=r["receipt_id"]: self.on_delete_receipt(rid),
            ))
            card.add_widget(btn_row_admin)

        return card

    def on_admin_edit_receipt(self, receipt_id):
        def do_unlock():
            try:
                admin_unlock_form("slaughter_receipts", "receipt_id", receipt_id)
                self.refresh_list()
                info_dialog(
                    "انجام شد",
                    "قفل قبض باز شد. حالا ۱۵ دقیقه فرصت ویرایش دارید.\n"
                    "بعد از ۱۵ دقیقه، دوباره قفل می‌شود."
                )
            except Exception as e:
                info_dialog("خطا", f"باز کردن قفل ناموفق:\n{e}")

        confirm_dialog(
            title="ویرایش قبض قفل‌شده",
            message=(
                "آیا از باز کردن قفل این قبض مطمئن هستید؟\n\n"
                "⚠️ پس از باز کردن قفل، ۱۵ دقیقه فرصت ویرایش دارید.\n"
                "بعد از آن، دوباره قفل می‌شود."
            ),
            confirm_text="باز کن",
            cancel_text="لغو",
            confirm_color=COLOR_WARNING,
            on_confirm=do_unlock,
        )

    def _show_time_picker(self, title, initial="", on_select=None):
        content = BoxLayout(orientation="vertical", padding=dp(10), spacing=dp(8))
        with content.canvas.before:
            Color(1, 1, 1, 1)
            content._bg = RoundedRectangle(pos=content.pos, size=content.size, radius=[dp(10)])
        content.bind(pos=lambda s, v: setattr(s._bg, "pos", v), size=lambda s, v: setattr(s._bg, "size", v))

        content.add_widget(fa_label(title, size=15, color=COLOR_PRIMARY_DARK, height=35, bold=True))

        hh, mm = "10", "00"
        if initial and ":" in initial:
            try:
                hh, mm = initial.split(":")[:2]
            except Exception:
                pass

        hh_wrap = fa_text_input(hint_text="ساعت (0-23)", text=hh, input_filter="int", height=45)
        mm_wrap = fa_text_input(hint_text="دقیقه (0-59)", text=mm, input_filter="int", height=45)

        row = BoxLayout(orientation="horizontal", spacing=dp(8), size_hint_y=None, height=45)
        row.add_widget(fa_label("ساعت:", size=12, color=COLOR_TEXT, height=45, halign="right"))
        row.add_widget(hh_wrap)
        row.add_widget(fa_label("دقیقه:", size=12, color=COLOR_TEXT, height=45, halign="right"))
        row.add_widget(mm_wrap)
        content.add_widget(row)

        btns = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(50), spacing=dp(8))
        cancel_btn = Button(text=fa("لغو"), font_name="Vazir", font_size=sp(13), background_normal="", background_color=[0.7, 0.7, 0.7, 1], color=COLOR_WHITE, bold=True)
        ok_btn = Button(text=fa("تایید"), font_name="Vazir", font_size=sp(13), background_normal="", background_color=COLOR_SUCCESS, color=COLOR_WHITE, bold=True)
        btns.add_widget(cancel_btn)
        btns.add_widget(ok_btn)
        content.add_widget(btns)

        popup = Popup(
            title="", title_size=0, content=content,
            size_hint=(None, None), size=(dp(300), dp(220)),
            auto_dismiss=False, background="", background_color=[0, 0, 0, 0.5], separator_height=0,
        )

        cancel_btn.bind(on_release=lambda x: popup.dismiss())

        def do_ok(*args):
            try:
                h = int(hh_wrap.text) if hh_wrap.text else 0
                m = int(mm_wrap.text) if mm_wrap.text else 0
                h = max(0, min(23, h))
                m = max(0, min(59, m))
                result = f"{h:02d}:{m:02d}"
            except ValueError:
                info_dialog("خطا", "ساعت/دقیقه نامعتبر است.")
                return
            popup.dismiss()
            if on_select:
                on_select(result)

        ok_btn.bind(on_release=do_ok)
        popup.open()

    def _show_date_picker(self, title, initial="", on_select=None):
        cal_content = BoxLayout(orientation="vertical", padding=dp(10), spacing=dp(5))
        with cal_content.canvas.before:
            Color(1, 1, 1, 1)
            cal_content._bg = RoundedRectangle(pos=cal_content.pos, size=cal_content.size, radius=[dp(10)])
        cal_content.bind(pos=lambda s, v: setattr(s._bg, "pos", v), size=lambda s, v: setattr(s._bg, "size", v))

        cal_content.add_widget(fa_label(title, size=15, color=COLOR_PRIMARY_DARK, height=35, bold=True))

        def on_date_selected(date_str):
            calendar_popup.dismiss()
            if on_select:
                on_select(date_str)

        cal = ShamsiCalendar(initial_date=initial or None, on_select=on_date_selected)
        cal_content.add_widget(cal)

        calendar_popup = Popup(
            title="", title_size=0, content=cal_content,
            size_hint=(None, None), size=(dp(400), dp(520)),
            auto_dismiss=True, background="", background_color=[0, 0, 0, 0.5], separator_height=0,
        )
        calendar_popup.open()

    def _show_form_dialog(self, receipt_data=None):
        is_edit = receipt_data is not None
        title = "ویرایش قبض" if is_edit else "افزودن قبض جدید"

        self.selected_image_path = None

        parsed = parse_extra(receipt_data.get("description", "")) if is_edit else {
            "full": None, "empty": None,
            "name": "", "code": "", "scale_name": "",
            "full_date": "", "full_time": "",
            "empty_date": "", "empty_time": "",
            "cost": "",
            "text": "",
        }

        self.selected_date = receipt_data.get("receipt_date", "") if is_edit else ""

        full_date = parsed.get("full_date", "") or self.selected_date
        full_time = parsed.get("full_time", "") or ""
        empty_date = parsed.get("empty_date", "") or self.selected_date
        empty_time = parsed.get("empty_time", "") or ""

        main_layout = BoxLayout(orientation="vertical")

        content = BoxLayout(
            orientation="vertical", padding=dp(12), spacing=dp(8),
            size_hint_y=None,
        )
        content.bind(minimum_height=content.setter("height"))

        with content.canvas.before:
            Color(1, 1, 1, 1)
            content._bg = RoundedRectangle(pos=content.pos, size=content.size, radius=[dp(10)])
        content.bind(
            pos=lambda s, v: setattr(s._bg, "pos", v),
            size=lambda s, v: setattr(s._bg, "size", v),
        )

        content.add_widget(fa_label(title, size=16, color=COLOR_PRIMARY_DARK, height=35, bold=True))

        content.add_widget(fa_section_title("نام باسکول:", height=22))
        scale_wrap = fa_text_input(hint_text="مثلاً باسکول مرکزی", text=parsed.get("scale_name", ""), height=45)
        content.add_widget(scale_wrap)

        content.add_widget(fa_section_title("شماره قبض:", height=22))
        num_wrap = fa_text_input(hint_text="شماره قبض", text=receipt_data.get("receipt_number", "") if is_edit else "", height=45)
        content.add_widget(num_wrap)

        content.add_widget(fa_section_title("تاریخ قبض (شمسی):", height=22))
        date_btn = Button(
            text=fa(self.selected_date) if self.selected_date else fa("انتخاب تاریخ از تقویم"),
            font_name="Vazir", font_size=sp(13), size_hint_y=None, height=dp(45),
            background_normal="",
            background_color=COLOR_PRIMARY if self.selected_date else [0.92, 0.92, 0.92, 1],
            color=COLOR_WHITE if self.selected_date else COLOR_TEXT,
        )
        content.add_widget(date_btn)

        def open_main_calendar(*args):
            def on_date(date_str):
                self.selected_date = date_str
                date_btn.text = fa(date_str)
                date_btn.background_color = COLOR_PRIMARY
                date_btn.color = COLOR_WHITE
            self._show_date_picker("انتخاب تاریخ قبض", self.selected_date, on_date)

        date_btn.bind(on_release=open_main_calendar)

        content.add_widget(fa_section_title("اطلاعات ردیف خالی:", height=22))

        content.add_widget(fa_section_title("وزن خالی (kg):", height=22))
        empty_val = str(parsed["empty"]) if parsed["empty"] is not None else ""
        empty_wrap = fa_text_input(hint_text="وزن خالی", text=empty_val, input_filter="float", height=45)
        content.add_widget(empty_wrap)

        content.add_widget(fa_section_title("تاریخ خالی:", height=22))
        empty_date_btn = Button(
            text=fa(empty_date) if empty_date else fa("انتخاب تاریخ"),
            font_name="Vazir", font_size=sp(13), size_hint_y=None, height=dp(45),
            background_normal="",
            background_color=COLOR_PRIMARY if empty_date else [0.92, 0.92, 0.92, 1],
            color=COLOR_WHITE if empty_date else COLOR_TEXT,
        )
        content.add_widget(empty_date_btn)

        def open_empty_date(*args):
            def on_date(date_str):
                nonlocal empty_date
                empty_date = date_str
                empty_date_btn.text = fa(date_str)
                empty_date_btn.background_color = COLOR_PRIMARY
                empty_date_btn.color = COLOR_WHITE
            self._show_date_picker("انتخاب تاریخ خالی", empty_date, on_date)

        empty_date_btn.bind(on_release=open_empty_date)

        content.add_widget(fa_section_title("ساعت خالی:", height=22))
        empty_time_btn = Button(
            text=fa(empty_time) if empty_time else fa("انتخاب ساعت"),
            font_name="Vazir", font_size=sp(13), size_hint_y=None, height=dp(45),
            background_normal="",
            background_color=COLOR_PRIMARY if empty_time else [0.92, 0.92, 0.92, 1],
            color=COLOR_WHITE if empty_time else COLOR_TEXT,
        )
        content.add_widget(empty_time_btn)

        def open_empty_time(*args):
            def on_time(time_str):
                nonlocal empty_time
                empty_time = time_str
                empty_time_btn.text = fa(time_str)
                empty_time_btn.background_color = COLOR_PRIMARY
                empty_time_btn.color = COLOR_WHITE
            self._show_time_picker("انتخاب ساعت خالی", empty_time, on_time)

        empty_time_btn.bind(on_release=open_empty_time)

        content.add_widget(fa_section_title("اطلاعات ردیف پر:", height=22))

        content.add_widget(fa_section_title("وزن پر (kg):", height=22))
        full_val = str(parsed["full"]) if parsed["full"] is not None else ""
        full_wrap = fa_text_input(hint_text="وزن پر", text=full_val, input_filter="float", height=45)
        content.add_widget(full_wrap)

        content.add_widget(fa_section_title("تاریخ پر:", height=22))
        full_date_btn = Button(
            text=fa(full_date) if full_date else fa("انتخاب تاریخ"),
            font_name="Vazir", font_size=sp(13), size_hint_y=None, height=dp(45),
            background_normal="",
            background_color=COLOR_PRIMARY if full_date else [0.92, 0.92, 0.92, 1],
            color=COLOR_WHITE if full_date else COLOR_TEXT,
        )
        content.add_widget(full_date_btn)

        def open_full_date(*args):
            def on_date(date_str):
                nonlocal full_date
                full_date = date_str
                full_date_btn.text = fa(date_str)
                full_date_btn.background_color = COLOR_PRIMARY
                full_date_btn.color = COLOR_WHITE
            self._show_date_picker("انتخاب تاریخ پر", full_date, on_date)

        full_date_btn.bind(on_release=open_full_date)

        content.add_widget(fa_section_title("ساعت پر:", height=22))
        full_time_btn = Button(
            text=fa(full_time) if full_time else fa("انتخاب ساعت"),
            font_name="Vazir", font_size=sp(13), size_hint_y=None, height=dp(45),
            background_normal="",
            background_color=COLOR_PRIMARY if full_time else [0.92, 0.92, 0.92, 1],
            color=COLOR_WHITE if full_time else COLOR_TEXT,
        )
        content.add_widget(full_time_btn)

        def open_full_time(*args):
            def on_time(time_str):
                nonlocal full_time
                full_time = time_str
                full_time_btn.text = fa(time_str)
                full_time_btn.background_color = COLOR_PRIMARY
                full_time_btn.color = COLOR_WHITE
            self._show_time_picker("انتخاب ساعت پر", full_time, on_time)

        full_time_btn.bind(on_release=open_full_time)

        content.add_widget(fa_section_title("نام کالا (اختیاری):", height=22))
        name_wrap = fa_text_input(hint_text="مرغ زنده", text=parsed["name"], height=45)
        content.add_widget(name_wrap)

        content.add_widget(fa_section_title("کد کالا (اختیاری):", height=22))
        code_wrap = fa_text_input(hint_text="مثلاً 001", text=parsed["code"], height=45)
        content.add_widget(code_wrap)

        content.add_widget(fa_section_title("پلاک ماشین:", height=22))
        plate_wrap = fa_text_input(hint_text="پلاک ماشین", text=receipt_data.get("car_plate", "") if is_edit else "", height=45)
        content.add_widget(plate_wrap)

        content.add_widget(fa_section_title("نام راننده (اختیاری):", height=22))
        driver_wrap = fa_text_input(hint_text="نام راننده", text=receipt_data.get("driver_name", "") if is_edit else "", height=45)
        content.add_widget(driver_wrap)

        content.add_widget(fa_section_title("نام مشتری (اختیاری):", height=22))
        buyer_wrap = fa_text_input(hint_text="نام مشتری", text=receipt_data.get("buyer_name", "") if is_edit else "", height=45)
        content.add_widget(buyer_wrap)

        content.add_widget(fa_section_title("هزینه توزین (اختیاری):", height=22))
        cost_wrap = fa_text_input(hint_text="مثلاً 50000", text=parsed.get("cost", ""), height=45)
        content.add_widget(cost_wrap)

        content.add_widget(fa_section_title("توضیحات (اختیاری):", height=22))
        desc_wrap = fa_text_input_multiline(
            hint_text="توضیحات", text=parsed.get("text", "") if is_edit else "", height=80, min_height=80,
        )
        content.add_widget(desc_wrap)

        content.add_widget(spacer(4))
        content.add_widget(fa_section_title("عکس قبض:", height=22))
        preview_label = fa_label("عکس جدیدی انتخاب نشده" if is_edit else "عکسی انتخاب نشده", size=12, color=COLOR_GRAY, height=dp(30))
        content.add_widget(preview_label)

        img_btns = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(45), spacing=dp(6))

        def on_image_picked(path):
            if path:
                self.selected_image_path = path
                preview_label.text = fa(f"عکس انتخاب شد:\n{os.path.basename(path)}")
                preview_label.color = COLOR_SUCCESS

        def take_camera(*args):
            from ..helpers.image_picker import pick_image, is_android
            if not is_android():
                info_dialog("توجه", "دوربین فقط در اندروید در دسترس است.")
                return
            pick_image(source="camera", on_result=on_image_picked)

        def pick_gallery(*args):
            from ..helpers.image_picker import pick_image
            pick_image(source="gallery", on_result=on_image_picked)

        img_btns.add_widget(fa_button("گرفتن عکس", size=12, height=45, bg_color=COLOR_PRIMARY, on_press=take_camera))
        img_btns.add_widget(fa_button("انتخاب از گالری", size=12, height=45, bg_color=COLOR_PRIMARY_DARK, on_press=pick_gallery))
        content.add_widget(img_btns)

        content.add_widget(spacer(6))

        btns = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(60),
            spacing=dp(8),
            padding=[dp(12), dp(6), dp(12), dp(12)]
        )
        cancel_btn = Button(text=fa("لغو"), font_name="Vazir", font_size=sp(14), background_normal="", background_color=[0.7, 0.7, 0.7, 1], color=COLOR_WHITE, bold=True)
        save_btn = Button(text=fa("ذخیره"), font_name="Vazir", font_size=sp(14), background_normal="", background_color=COLOR_SUCCESS, color=COLOR_WHITE, bold=True)
        btns.add_widget(cancel_btn)
        btns.add_widget(save_btn)

        inner_scroll = ScrollView()
        inner_scroll.add_widget(content)

        main_layout.add_widget(inner_scroll)
        main_layout.add_widget(btns)

        popup = Popup(
            title="", title_size=0, content=main_layout,
            size_hint=(None, None), size=(dp(460), dp(750)),
            auto_dismiss=False, background="", background_color=[0, 0, 0, 0.5], separator_height=0,
        )
        cancel_btn.bind(on_release=lambda x: popup.dismiss())

        def do_save(*args):
            num = num_wrap.text.strip()
            date = self.selected_date
            full_txt = full_wrap.text.strip()
            empty_txt = empty_wrap.text.strip()
            name_txt = name_wrap.text.strip()
            code_txt = code_wrap.text.strip()
            scale_txt = scale_wrap.text.strip()
            cost_txt = cost_wrap.text.strip()
            user_desc = desc_wrap.text.strip()

            if not self.selected_image_path and not num and not is_edit:
                info_dialog("خطا", "حداقل باید عکس قبض یا شماره قبض را وارد کنید.")
                return

            try:
                full = float(full_txt) if full_txt else 0.0
                empty = float(empty_txt) if empty_txt else 0.0
            except ValueError:
                info_dialog("خطا", "وزن‌ها نامعتبر هستند.")
                return

            net = max(0.0, full - empty)

            extra_str = ""
            if full or empty:
                extra_str = f"FULL:{full}|EMPTY:{empty}"
            if name_txt:
                extra_str += f"|NAME:{name_txt}"
            if code_txt:
                extra_str += f"|CODE:{code_txt}"
            if scale_txt:
                extra_str += f"|SCALE:{scale_txt}"
            if full_date:
                extra_str += f"|FULL_DATE:{full_date}"
            if full_time:
                extra_str += f"|FULL_TIME:{full_time}"
            if empty_date:
                extra_str += f"|EMPTY_DATE:{empty_date}"
            if empty_time:
                extra_str += f"|EMPTY_TIME:{empty_time}"
            if cost_txt:
                extra_str += f"|COST:{cost_txt}"
            if user_desc:
                if extra_str:
                    extra_str += "|" + user_desc
                else:
                    extra_str = user_desc

            try:
                if is_edit:
                    update_receipt(
                        receipt_id=receipt_data["receipt_id"],
                        receipt_number=num, receipt_date=date, net_weight=net,
                        car_plate=plate_wrap.text.strip(), driver_name=driver_wrap.text.strip(),
                        buyer_name=buyer_wrap.text.strip(), description=extra_str,
                    )
                else:
                    add_receipt(
                        slaughter_id=self.slaughter_id, operator_id=self.current_user["user_id"],
                        receipt_number=num, receipt_date=date, net_weight=net,
                        car_plate=plate_wrap.text.strip(), driver_name=driver_wrap.text.strip(),
                        buyer_name=buyer_wrap.text.strip(), description=extra_str,
                        image_source=self.selected_image_path,
                    )
            except Exception as e:
                info_dialog("خطا", f"ذخیره ناموفق:\n{e}")
                return

            popup.dismiss()
            info_dialog("ثبت موفق", "تغییرات با موفقیت ذخیره شد.")
            self.refresh_list()

        save_btn.bind(on_release=do_save)
        popup.open()

    def on_add_receipt(self, *args):
        self._show_form_dialog(None)

    def on_edit_receipt(self, receipt_id):
        r_data = get_receipt(receipt_id)
        if r_data:
            self._show_form_dialog(r_data)

    def on_finalize_receipt(self, receipt_id):
        confirm_dialog(
            title="ثبت نهایی قبض",
            message="آیا از ثبت نهایی مطمئن هستید؟\nپس از این مرحله، قبض قفل شده و قابل ویرایش نیست.",
            confirm_text="تایید نهایی", cancel_text="لغو", confirm_color=COLOR_PRIMARY_DARK,
            on_confirm=lambda: self._do_finalize(receipt_id),
        )

    def _do_finalize(self, receipt_id):
        try:
            finalize_form("slaughter_receipts", "receipt_id", receipt_id)
        except Exception as e:
            info_dialog("خطا", str(e))
            return
        info_dialog("تایید شد", "قبض قفل شد.")
        self.refresh_list()

    def on_delete_receipt(self, receipt_id):
        r_data = get_receipt(receipt_id)
        if not r_data:
            info_dialog("خطا", "قبض یافت نشد.")
            return

        from kivymd.app import MDApp
        app = MDApp.get_running_app()
        can_edit_time = can_edit_form(
            r_data.get("completed_at"),
            r_data.get("locked_at"),
            app.current_user,
        )
        if not can_edit_time and not self.is_admin:
            info_dialog("خطا", "زمان ویرایش/حذف این قبض به پایان رسیده است.")
            return

        confirm_dialog(
            title="حذف قبض", message="آیا از حذف این قبض مطمئن هستید؟\nعکس آن هم حذف می‌شود.",
            confirm_text="حذف", cancel_text="لغو", confirm_color=COLOR_ERROR,
            on_confirm=lambda: self._do_delete(receipt_id),
        )

    def _do_delete(self, receipt_id):
        try:
            delete_receipt(receipt_id)
        except Exception as e:
            info_dialog("خطا", f"حذف ناموفق:\n{e}")
            return
        info_dialog("حذف موفق", "قبض حذف شد.")
        self.refresh_list()

    def open_image(self, full_path):
        from ..helpers.file_utils import open_file
        if not os.path.exists(full_path):
            info_dialog("خطا", "فایل عکس یافت نشد.")
            return
        open_file(full_path)

    def open_receipt_pdf(self, receipt_id):
        from ..helpers.file_utils import open_file
        from functions import get_receipt
        from pdf_receipt import generate_receipt_pdf

        try:
            receipt_data = get_receipt(receipt_id)
            if not receipt_data:
                info_dialog("خطا", "اطلاعات قبض یافت نشد.")
                return

            slaughter_info = self.slaughter_info

            path = generate_receipt_pdf(
                receipt_data, slaughter_info,
            )

            if os.path.exists(path):
                open_file(path)
            else:
                info_dialog("خطا", "فایل PDF ساخته نشد.")

        except Exception as e:
            info_dialog("خطا در ساخت PDF", str(e))

    def _show_error(self, text):
        self.msg_label.text = fa(text)
        self.msg_label.color = COLOR_ERROR

    def on_back(self, *args):
        self.manager.transition.direction = "right"
        self.manager.current = "slaughters_list"
