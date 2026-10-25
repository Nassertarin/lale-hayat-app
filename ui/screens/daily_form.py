# -*- coding: utf-8 -*-
"""
فرم ۳: گزارش روزانه (یک فرم برای همه‌ی کشتارهای یک روز)
"""

from kivy.metrics import dp, sp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.widget import Widget
from kivy.graphics import Color, RoundedRectangle, Line
from kivy.uix.behaviors import ButtonBehavior
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
)
from ..helpers.dialogs import confirm_dialog, info_dialog

from functions import (
    get_work_day_shamsi,
    get_or_create_daily_form,
    get_available_carts_for_date,
    get_aggregated_alayeshat_for_date,
    save_daily_form_by_date,
    calc_carts_total,
    calc_morgh_row_waste,
    get_weighing_alayeshat_total_for_date,
    is_within_edit_window,
    can_edit_form,
    admin_unlock_form,
    finalize_form,
    user_can_edit_locked,
)
from database import get_connection
from datetime import datetime


class SelectableRow(ButtonBehavior, BoxLayout):
    """ردیف قابل کلیک برای انتخاب."""
    pass


class DailyFormScreen(MDScreen):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "daily_form"
        self.md_bg_color = COLOR_BG

        self.form_date = None
        self.day_name = None
        self.operator_id = None
        self.current_user = None

        self.available_carts = []
        self.aggregated_alayeshat = []

        self.packed_rows = []
        self.alayeshat_rows = []
        self.morgh_rows = []

        self.completed_at = None
        self.locked_at = None
        self.is_editing = False

        self.info_label = None
        self.status_label = None
        self.packed_container = None
        self.alayeshat_container = None
        self.alayeshat_msg_label = None
        self.morgh_container = None
        self.morgh_msg_label = None
        self.msg_label = None
        self.actions_container = None
        self.packed_msg_label = None

        self.carts_bar_container = None
        self.carts_bar_label = None

        self.packed_widgets = {}
        self.alayeshat_widgets = {}
        self.morgh_widgets = {}
        self.packed_row_frames = {}
        self.alayeshat_row_frames = {}
        self.morgh_row_frames = {}

        self.packed_selected_index = None
        self.alayeshat_selected_index = None
        self.morgh_selected_index = None

        self.packed_add_btn = None
        self.alayeshat_add_btn = None
        self.morgh_add_btn = None
        self.packed_del_btn = None
        self.alayeshat_del_btn = None
        self.morgh_del_btn = None

        self._clock_event = None

        self.build_ui()

    # ======================================
    # ساخت UI
    # ======================================

    def build_ui(self):
        root = BoxLayout(orientation="vertical")

        header = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(55),
            padding=[dp(10), dp(8)],
            spacing=dp(10),
        )
        header.add_widget(fa_button(
            "بازگشت",
            size=14,
            height=40,
            bg_color=[0.6, 0.6, 0.6, 1],
            on_press=self.on_back,
        ))
        header.add_widget(fa_label(
            "فرم گزارش روزانه",
            size=16,
            color=COLOR_PRIMARY_DARK,
            height=40,
            bold=True,
        ))
        root.add_widget(header)

        self.info_label = fa_label(
            "در حال بارگذاری...",
            size=12,
            color=COLOR_PRIMARY_DARK,
            height=30,
            bold=True,
        )
        root.add_widget(self.info_label)

        self.status_label = fa_label(
            "",
            size=12,
            color=COLOR_GRAY,
            height=25,
            bold=True,
        )
        root.add_widget(self.status_label)

        scroll = ScrollView()

        content = BoxLayout(
            orientation="vertical",
            padding=dp(10),
            spacing=dp(8),
            size_hint_y=None,
        )
        content.bind(minimum_height=content.setter("height"))

        content.add_widget(fa_section_title("مرغ پرکنده (مجموع گاری‌های امروز):"))

        packed_btns_top = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(42),
            spacing=dp(8),
        )
        self.packed_add_btn = fa_button(
            "+ افزودن خریدار",
            size=13,
            height=42,
            bg_color=COLOR_SUCCESS,
            on_press=self.on_add_packed_row,
        )
        packed_btns_top.add_widget(self.packed_add_btn)

        self.packed_del_btn = fa_button(
            "حذف ردیف انتخاب‌شده",
            size=13,
            height=42,
            bg_color=COLOR_ERROR,
            on_press=self.on_delete_selected_packed,
        )
        self.packed_del_btn.disabled = True
        self.packed_del_btn.opacity = 1.0
        packed_btns_top.add_widget(self.packed_del_btn)

        content.add_widget(packed_btns_top)

        carts_bar_box = BoxLayout(
            orientation="vertical",
            size_hint_y=None,
            height=dp(90),
            spacing=dp(4),
        )

        self.carts_bar_label = fa_label(
            "",
            size=11,
            color=COLOR_PRIMARY_DARK,
            height=dp(24),
            bold=True,
            halign="right",
        )
        carts_bar_box.add_widget(self.carts_bar_label)

        carts_scroll = ScrollView(
            size_hint_y=None, height=dp(52),
            do_scroll_x=True, do_scroll_y=False, bar_width=dp(2),
        )
        self.carts_bar_container = BoxLayout(
            orientation="horizontal",
            size_hint_x=None,
            height=dp(52),
            spacing=dp(4),
        )
        self.carts_bar_container.bind(
            minimum_width=self.carts_bar_container.setter("width")
        )
        carts_scroll.add_widget(self.carts_bar_container)

        carts_bar_box.add_widget(carts_scroll)
        content.add_widget(carts_bar_box)

        content.add_widget(self._make_packed_header())

        self.packed_container = BoxLayout(
            orientation="vertical",
            spacing=dp(0),
            size_hint_y=None,
        )
        self.packed_container.bind(
            minimum_height=self.packed_container.setter("height")
        )
        content.add_widget(self.packed_container)

        self.packed_msg_label = fa_label(
            "",
            size=12,
            color=COLOR_SUCCESS,
            height=dp(30),
        )
        content.add_widget(self.packed_msg_label)

        content.add_widget(spacer(8))
        content.add_widget(fa_section_title("آلایشات (توزیع بین مشتری‌ها):"))

        self.alayeshat_stock_label = fa_label(
            "",
            size=12,
            color=COLOR_PRIMARY_DARK,
            height=dp(40),
            bold=True,
        )
        content.add_widget(self.alayeshat_stock_label)

        content.add_widget(self._make_alayeshat_header())

        self.alayeshat_container = BoxLayout(
            orientation="vertical",
            spacing=dp(0),
            size_hint_y=None,
        )
        self.alayeshat_container.bind(
            minimum_height=self.alayeshat_container.setter("height")
        )
        content.add_widget(self.alayeshat_container)

        alayeshat_btns = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(42),
            spacing=dp(8),
        )
        self.alayeshat_add_btn = fa_button(
            "+ افزودن ردیف",
            size=13,
            height=42,
            bg_color=COLOR_SUCCESS,
            on_press=self.on_add_alayeshat_row,
        )
        alayeshat_btns.add_widget(self.alayeshat_add_btn)

        self.alayeshat_del_btn = fa_button(
            "حذف ردیف انتخاب‌شده",
            size=13,
            height=42,
            bg_color=COLOR_ERROR,
            on_press=self.on_delete_selected_alayeshat,
        )
        self.alayeshat_del_btn.disabled = True
        self.alayeshat_del_btn.opacity = 1.0
        alayeshat_btns.add_widget(self.alayeshat_del_btn)

        content.add_widget(alayeshat_btns)

        self.alayeshat_msg_label = fa_label(
            "",
            size=12,
            color=COLOR_SUCCESS,
            height=dp(60),
        )
        content.add_widget(self.alayeshat_msg_label)

        content.add_widget(spacer(8))
        content.add_widget(fa_section_title("مرغ اصلاحی:"))

        content.add_widget(self._make_morgh_header())

        self.morgh_container = BoxLayout(
            orientation="vertical",
            spacing=dp(0),
            size_hint_y=None,
        )
        self.morgh_container.bind(
            minimum_height=self.morgh_container.setter("height")
        )
        content.add_widget(self.morgh_container)

        morgh_btns = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(42),
            spacing=dp(8),
        )
        self.morgh_add_btn = fa_button(
            "+ افزودن ردیف",
            size=13,
            height=42,
            bg_color=COLOR_SUCCESS,
            on_press=self.on_add_morgh_row,
        )
        morgh_btns.add_widget(self.morgh_add_btn)

        self.morgh_del_btn = fa_button(
            "حذف ردیف انتخاب‌شده",
            size=13,
            height=42,
            bg_color=COLOR_ERROR,
            on_press=self.on_delete_selected_morgh,
        )
        self.morgh_del_btn.disabled = True
        self.morgh_del_btn.opacity = 1.0
        morgh_btns.add_widget(self.morgh_del_btn)

        content.add_widget(morgh_btns)

        self.morgh_msg_label = fa_label(
            "",
            size=12,
            color=COLOR_SUCCESS,
            height=dp(60),
        )
        content.add_widget(self.morgh_msg_label)

        content.add_widget(spacer(6))
        self.msg_label = fa_label(
            "",
            size=13,
            color=COLOR_ERROR,
            height=30,
        )
        content.add_widget(self.msg_label)

        content.add_widget(spacer(10))

        btns_row = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(55),
            spacing=dp(8),
        )
        btns_row.add_widget(fa_button(
            "خروجی PDF",
            size=13,
            height=50,
            bg_color=COLOR_PRIMARY_DARK,
            on_press=self.on_export_pdf,
        ))
        btns_row.add_widget(fa_button(
            "خروجی Excel",
            size=13,
            height=50,
            bg_color=COLOR_SUCCESS,
            on_press=self.on_export_csv,
        ))
        content.add_widget(btns_row)

        content.add_widget(spacer(20))

        scroll.add_widget(content)
        root.add_widget(scroll)

        self.actions_container = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(65),
            padding=[dp(10), dp(5)],
            spacing=dp(6),
        )
        root.add_widget(self.actions_container)

        self.add_widget(root)

        # ── به‌روزرسانی خودکار UI هر ۳۰ ثانیه ──
        self._clock_event = Clock.schedule_interval(self._auto_refresh, 30)

    def _auto_refresh(self, dt):
        try:
            if self.locked_at or (self.completed_at and not self.is_editing):
                self._update_actions()
        except Exception:
            pass

    def on_leave(self, *args):
        try:
            if self._clock_event:
                self._clock_event.cancel()
                self._clock_event = None
        except Exception:
            pass

    def _make_packed_header(self):
        hdr = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(26),
            spacing=dp(4),
            padding=[dp(4), 0],
        )
        for txt, sx in [("نام خریدار", 0.45), ("گاری‌های انتخاب‌شده", 0.35), ("جمع خالص", 0.20)]:
            lbl = fa_label(
                txt, size=11, color=COLOR_PRIMARY_DARK,
                height=26, bold=True, halign="center",
            )
            lbl.size_hint_x = sx
            hdr.add_widget(lbl)
        return hdr

    def _make_alayeshat_header(self):
        hdr = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(24),
            spacing=dp(4),
            padding=[dp(4), 0],
        )
        for txt in ["دل", "جگر", "سنگدان", "پا", "کله"]:
            hdr.add_widget(fa_label(
                txt, size=10, color=COLOR_PRIMARY_DARK,
                height=24, bold=True, halign="center",
            ))
        return hdr

    def _make_morgh_header(self):
        hdr = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(24),
            spacing=dp(2),
            padding=[dp(2), 0],
        )
        for txt in ["مرغ لکه", "قطعه", "سینه", "ران", "بال", "گردن", "کامل"]:
            hdr.add_widget(fa_label(
                txt, size=10, color=COLOR_PRIMARY_DARK,
                height=24, bold=True, halign="center",
            ))
        return hdr

    def on_pre_enter(self, *args):
        if not self._clock_event:
            self._clock_event = Clock.schedule_interval(self._auto_refresh, 30)

        from kivymd.app import MDApp
        app = MDApp.get_running_app()

        self.current_user = app.current_user
        if not self.current_user:
            self._show_error("نشست کاربر منقضی شده.")
            return

        self.operator_id = self.current_user["user_id"]

        shamsi, day_name = get_work_day_shamsi()
        self.form_date = shamsi
        self.day_name = day_name

        self.is_editing = False
        self.load_form()

    def load_form(self):
        try:
            form = get_or_create_daily_form(
                self.form_date, self.day_name, self.operator_id
            )
        except Exception as e:
            self._show_error(f"خطا در بارگذاری فرم: {e}")
            return

        if not form:
            self._show_error("فرم گزارش یافت نشد.")
            return

        self.completed_at = form.get("completed_at")
        self.locked_at = form.get("locked_at")

        self.info_label.text = fa(
            f"روز کاری: {self.day_name} {self.form_date}"
        )

        if self.locked_at:
            self.status_label.text = fa("[ قفل شده - تایید نهایی ]")
            self.status_label.color = COLOR_SUCCESS
        elif self.completed_at and not self.is_editing:
            self.status_label.text = fa("[ ثبت شده - منتظر تایید ]")
            self.status_label.color = COLOR_WARNING
        elif self.is_editing:
            self.status_label.text = fa("[ در حال ویرایش ]")
            self.status_label.color = COLOR_PRIMARY_DARK
        else:
            self.status_label.text = fa("[ در حال ثبت ]")
            self.status_label.color = COLOR_GRAY

        try:
            self.available_carts = get_available_carts_for_date(self.form_date)
        except Exception as e:
            self._show_error(f"خطا در لود گاری‌ها: {e}")
            self.available_carts = []

        try:
            self.aggregated_alayeshat = get_aggregated_alayeshat_for_date(self.form_date)
            self._update_alayeshat_stock_label()
        except Exception as e:
            self._show_error(f"خطا در لود آلایشات: {e}")
            self.aggregated_alayeshat = []

        self.packed_rows = []
        for r in form["packed_rows"]:
            self.packed_rows.append({
                "row_id": r["row_id"],
                "buyer_name": r["buyer_name"],
                "cart_ids": [c["plucked_row_id"] for c in r["carts"] if c["plucked_row_id"]],
                "total_net_weight": r["total_net_weight"],
            })
        if not self.packed_rows:
            self.packed_rows.append(self._empty_packed_row())

        self.alayeshat_rows = []
        for r in form["alayeshat_rows"]:
            self.alayeshat_rows.append({
                "row_id": r.get("row_id"),
                "customer_name": r.get("customer_name", ""),
                "del_weight": r.get("del_weight", ""),
                "jigar_weight": r.get("jigar_weight", ""),
                "sangdane_weight": r.get("sangdane_weight", ""),
                "pa_weight": r.get("pa_weight", ""),
                "kale_weight": r.get("kale_weight", ""),
            })
        if not self.alayeshat_rows:
            self.alayeshat_rows.append(self._empty_alayeshat_row())

        self.morgh_rows = []
        for r in form["morgh_rows"]:
            self.morgh_rows.append({
                "row_id": r["row_id"],
                "customer_name": r["customer_name"],
                "lake_weight": r["lake_weight"],
                "piece_weight": r["piece_weight"],
                "sine_weight": r["sine_weight"],
                "ran_weight": r["ran_weight"],
                "bal_weight": r["bal_weight"],
                "gardan_weight": r["gardan_weight"],
                "whole_weight": r["whole_weight"],
            })
        if not self.morgh_rows:
            self.morgh_rows.append(self._empty_morgh_row())

        self.packed_selected_index = None
        self.alayeshat_selected_index = None
        self.morgh_selected_index = None

        self.render_all()
        self._update_actions()

        is_locked = bool(self.locked_at)
        for btn in [self.packed_add_btn, self.alayeshat_add_btn, self.morgh_add_btn]:
            if btn:
                btn.disabled = is_locked
                btn.opacity = 0.4 if is_locked else 1.0
        for btn in [self.packed_del_btn, self.alayeshat_del_btn, self.morgh_del_btn]:
            if btn:
                btn.disabled = True
                btn.opacity = 1.0

        if self.completed_at:
            self.check_packed_discrepancy()

    def _update_alayeshat_stock_label(self):
        if not self.aggregated_alayeshat:
            self.alayeshat_stock_label.text = fa("موجودی: هیچ آلایشاتی در فرم‌های توزین ثبت نشده است.")
            return

        parts = []
        for item in self.aggregated_alayeshat:
            parts.append(f"{item['product_name']}: {item['total_net']:,.1f}")

        self.alayeshat_stock_label.text = fa("موجودی: " + " | ".join(parts))

    def _update_actions(self):
        self.actions_container.clear_widgets()

        from kivymd.app import MDApp
        app = MDApp.get_running_app()

        is_locked = bool(self.locked_at)
        is_saved = bool(self.completed_at) and not self.is_editing
        is_editing = self.is_editing

        if is_locked:
            can_unlock = user_can_edit_locked(app.current_user)
            within_window = is_within_edit_window(self.locked_at, 15)
            if can_unlock and within_window:
                self.actions_container.add_widget(fa_button(
                    "ویرایش (ادمین)",
                    size=13, height=55,
                    bg_color=COLOR_WARNING,
                    on_press=self.on_admin_edit,
                ))
            else:
                self.actions_container.add_widget(fa_label(
                    "این فرم تایید نهایی شده و قفل است.",
                    size=12, color=COLOR_GRAY, height=55, halign="center",
                ))
            return
        if is_editing:
            self.actions_container.add_widget(fa_button(
                "ذخیره تغییرات", size=13, height=55,
                bg_color=COLOR_PRIMARY,
                on_press=self.on_save_edit,
            ))
            self.actions_container.add_widget(fa_button(
                "انصراف", size=13, height=55,
                bg_color=[0.7, 0.7, 0.7, 1],
                on_press=self.on_cancel_edit,
            ))
            return

        if is_saved:
            if can_edit_form(self.completed_at, self.locked_at, app.current_user):
                self.actions_container.add_widget(fa_button(
                    "ویرایش", size=12, height=55,
                    bg_color=COLOR_WARNING,
                    on_press=self.on_edit,
                ))
                self.actions_container.add_widget(fa_button(
                    "حذف", size=12, height=55,
                    bg_color=COLOR_ERROR,
                    on_press=self.on_delete_entire_form,
                ))
                self.actions_container.add_widget(fa_button(
                    "ثبت نهایی", size=12, height=55,
                    bg_color=COLOR_PRIMARY_DARK,
                    on_press=self.on_finalize,
                ))
            else:
                self.actions_container.add_widget(fa_label(
                    "مهلت ویرایش/حذف تمام شده",
                    size=11, color=COLOR_GRAY, height=55, halign="center",
                ))
                self.actions_container.add_widget(fa_button(
                    "ثبت نهایی", size=12, height=55,
                    bg_color=COLOR_PRIMARY_DARK,
                    on_press=self.on_finalize,
                ))
            return

        self.actions_container.add_widget(fa_button(
            "ثبت", size=14, height=55,
            bg_color=COLOR_SUCCESS,
            on_press=self.on_submit,
        ))

    def _empty_packed_row(self):
        return {
            "row_id": None,
            "buyer_name": "",
            "cart_ids": [],
            "total_net_weight": 0.0,
        }

    def _empty_alayeshat_row(self):
        return {
            "row_id": None,
            "customer_name": "",
            "del_weight": "",
            "jigar_weight": "",
            "sangdane_weight": "",
            "pa_weight": "",
            "kale_weight": "",
        }

    def _empty_morgh_row(self):
        return {
            "row_id": None,
            "customer_name": "",
            "lake_weight": "",
            "piece_weight": "",
            "sine_weight": "",
            "ran_weight": "",
            "bal_weight": "",
            "gardan_weight": "",
            "whole_weight": "",
        }

    def render_all(self):
        self.render_packed_rows()
        self.render_alayeshat_rows()
        self.render_morgh_rows()
        self._render_carts_bar()

    def render_packed_rows(self):
        self.packed_container.clear_widgets()
        self.packed_widgets = {}
        self.packed_row_frames = {}
        if self.packed_selected_index is not None and \
           self.packed_selected_index >= len(self.packed_rows):
            self.packed_selected_index = None
        for i, row in enumerate(self.packed_rows):
            self.packed_container.add_widget(self._make_packed_row_widget(i, row))
        self._refresh_packed_delete_btn()

    def render_alayeshat_rows(self):
        self.alayeshat_container.clear_widgets()
        self.alayeshat_widgets = {}
        self.alayeshat_row_frames = {}
        if self.alayeshat_selected_index is not None and \
           self.alayeshat_selected_index >= len(self.alayeshat_rows):
            self.alayeshat_selected_index = None
        for i, row in enumerate(self.alayeshat_rows):
            self.alayeshat_container.add_widget(self._make_alayeshat_row_widget(i, row))
        self._refresh_alayeshat_delete_btn()
        self.check_alayeshat_discrepancy()

    def render_morgh_rows(self):
        self.morgh_container.clear_widgets()
        self.morgh_widgets = {}
        self.morgh_row_frames = {}
        if self.morgh_selected_index is not None and \
           self.morgh_selected_index >= len(self.morgh_rows):
            self.morgh_selected_index = None
        for i, row in enumerate(self.morgh_rows):
            self.morgh_container.add_widget(self._make_morgh_row_widget(i, row))
        self._refresh_morgh_delete_btn()
        self.check_morgh_discrepancy()

    def _render_carts_bar(self):
        if self.carts_bar_container is None:
            return

        self.carts_bar_container.clear_widgets()

        is_locked = bool(self.locked_at)
        active_idx = self.packed_selected_index

        used_by_other = {}
        for i, r in enumerate(self.packed_rows):
            if i == active_idx:
                continue
            for cid in r.get("cart_ids", []):
                used_by_other[cid] = i

        if is_locked:
            self.carts_bar_label.text = fa("گاری‌ها (فرم قفل شده):")
            self.carts_bar_label.color = COLOR_GRAY
        elif active_idx is None:
            self.carts_bar_label.text = fa("گاری‌ها: ابتدا یک ردیف را از جدول پایین انتخاب کنید")
            self.carts_bar_label.color = COLOR_ERROR
        else:
            buyer = self.packed_rows[active_idx].get("buyer_name") or f"ردیف {active_idx + 1}"
            self.carts_bar_label.text = fa(
                f"گاری‌ها برای: {buyer} — کلیک کنید تا انتخاب/لغو شود"
            )
            self.carts_bar_label.color = COLOR_PRIMARY_DARK

        if not self.available_carts:
            self.carts_bar_container.add_widget(fa_label(
                "هیچ گاری‌ای امروز ثبت نشده",
                size=11, color=COLOR_GRAY, height=dp(52),
            ))
            return

        active_selected = set()
        if active_idx is not None and active_idx < len(self.packed_rows):
            active_selected = set(self.packed_rows[active_idx].get("cart_ids", []))

        for cart in self.available_carts:
            cart_id = cart["row_id"]
            cart_num = cart["cart_number"]
            slaughter_num = cart.get("slaughter_number", "")
            display_text = f"گاری {cart_num} (کشتار {slaughter_num})"

            is_selected = cart_id in active_selected
            is_used_by_other = (cart_id in used_by_other) and (cart_id not in active_selected)

            if is_selected:
                bg = COLOR_PRIMARY
                fg = COLOR_WHITE
            elif is_used_by_other:
                bg = [0.85, 0.85, 0.85, 1]
                fg = [0.55, 0.55, 0.55, 1]
            else:
                bg = [0.92, 0.92, 0.92, 1]
                fg = COLOR_TEXT

            btn = Button(
                text=fa(display_text),
                font_name="Vazir", font_size=sp(11),
                size_hint=(None, 1), width=dp(130),
                background_normal="",
                background_color=bg,
                color=fg,
            )

            if is_used_by_other or is_locked or active_idx is None:
                btn.disabled = True
            else:
                btn.bind(
                    on_release=lambda x, cid=cart_id: self._toggle_cart_for_active(cid)
                )

            self.carts_bar_container.add_widget(btn)

    def _refresh_packed_delete_btn(self):
        if self.packed_del_btn is None:
            return
        is_locked = bool(self.locked_at)
        can_del = (self.packed_selected_index is not None) and not is_locked
        self.packed_del_btn.disabled = not can_del
        self.packed_del_btn.opacity = 1.0

    def _refresh_alayeshat_delete_btn(self):
        if self.alayeshat_del_btn is None:
            return
        is_locked = bool(self.locked_at)
        can_del = (self.alayeshat_selected_index is not None) and not is_locked
        self.alayeshat_del_btn.disabled = not can_del
        self.alayeshat_del_btn.opacity = 1.0

    def _refresh_morgh_delete_btn(self):
        if self.morgh_del_btn is None:
            return
        is_locked = bool(self.locked_at)
        can_del = (self.morgh_selected_index is not None) and not is_locked
        self.morgh_del_btn.disabled = not can_del
        self.morgh_del_btn.opacity = 1.0

    def _paint_row(self, frames, index, selected):
        frame = frames.get(index)
        if frame is None:
            return
        bg = [0.86, 0.92, 1.0, 1] if selected else [1, 1, 1, 1]
        if hasattr(frame, "_bg_color"):
            frame._bg_color.rgba = bg

    def _on_select_packed(self, index):
        self._sync_packed_widgets_to_rows()

        if self.packed_selected_index == index:
            self._paint_row(self.packed_row_frames, index, False)
            self.packed_selected_index = None
        else:
            if self.packed_selected_index is not None:
                self._paint_row(self.packed_row_frames, self.packed_selected_index, False)
            self.packed_selected_index = index
            self._paint_row(self.packed_row_frames, index, True)

        self._refresh_packed_delete_btn()
        self.render_packed_rows()
        self._render_carts_bar()

    def _on_select_alayeshat(self, index):
        self._sync_alayeshat_widgets_to_rows()
        if self.alayeshat_selected_index == index:
            self._paint_row(self.alayeshat_row_frames, index, False)
            self.alayeshat_selected_index = None
        else:
            if self.alayeshat_selected_index is not None:
                self._paint_row(self.alayeshat_row_frames, self.alayeshat_selected_index, False)
            self.alayeshat_selected_index = index
            self._paint_row(self.alayeshat_row_frames, index, True)
        self._refresh_alayeshat_delete_btn()

    def _on_select_morgh(self, index):
        self._sync_morgh_widgets_to_rows()
        if self.morgh_selected_index == index:
            self._paint_row(self.morgh_row_frames, index, False)
            self.morgh_selected_index = None
        else:
            if self.morgh_selected_index is not None:
                self._paint_row(self.morgh_row_frames, self.morgh_selected_index, False)
            self.morgh_selected_index = index
            self._paint_row(self.morgh_row_frames, index, True)
        self._refresh_morgh_delete_btn()

    def _make_packed_row_widget(self, index, row):
        is_locked = bool(self.locked_at)

        row_frame = SelectableRow(
            orientation="horizontal",
            size_hint=(1, None),
            height=dp(48),
            spacing=dp(4),
            padding=[dp(4), dp(2)],
        )
        with row_frame.canvas.before:
            row_frame._bg_color = Color(1, 1, 1, 1)
            row_frame._bg_rect = RoundedRectangle(
                pos=row_frame.pos, size=row_frame.size, radius=[dp(0)]
            )
        row_frame.bind(
            pos=lambda s, v: setattr(s._bg_rect, "pos", v),
            size=lambda s, v: setattr(s._bg_rect, "size", v),
        )
        row_frame.bind(on_release=lambda inst, i=index: self._on_select_packed(i))

        if self.packed_selected_index == index:
            row_frame._bg_color.rgba = [0.86, 0.92, 1.0, 1]

        self.packed_widgets[index] = {}
        self.packed_row_frames[index] = row_frame

        if is_locked:
            name_lbl = fa_label(
                row.get("buyer_name") or "—",
                size=12, color=COLOR_TEXT, height=42, bold=True, halign="center",
            )
            name_lbl.size_hint_x = 0.45
            row_frame.add_widget(name_lbl)
        else:
            name_wrap = fa_text_input(
                hint_text="نام خریدار",
                text=row.get("buyer_name", ""),
                height=42,
            )
            name_wrap.size_hint_x = 0.45
            name_wrap.hidden.bind(
                text=lambda inst, val, i=index: self._on_packed_change(i, "buyer_name", val)
            )
            self.packed_widgets[index]["buyer_name"] = name_wrap
            row_frame.add_widget(name_wrap)

        carts_text = self._carts_text_for_row(row)
        carts_lbl = fa_label(
            carts_text, size=11, color=COLOR_TEXT,
            height=42, halign="center",
        )
        carts_lbl.size_hint_x = 0.35
        row_frame.add_widget(carts_lbl)

        net_lbl = fa_label(
            f"{row.get('total_net_weight', 0):,.2f}",
            size=12, color=COLOR_PRIMARY, height=42, bold=True,
        )
        net_lbl.size_hint_x = 0.20
        row_frame.add_widget(net_lbl)

        with row_frame.canvas.after:
            Color(0.88, 0.88, 0.88, 1)
            row_frame._line = Line(
                points=[row_frame.x, row_frame.y, row_frame.right, row_frame.y],
                width=1,
            )
        row_frame.bind(
            pos=lambda s, v: setattr(s._line, "points",
                                      [v[0], v[1], v[0] + s.width, v[1]]),
            size=lambda s, v: setattr(s._line, "points",
                                      [s.x, s.y, s.x + s.width, s.y]),
        )
        return row_frame

    def _carts_text_for_row(self, row):
        ids = row.get("cart_ids", [])
        if not ids:
            return "—"
        num_by_id = {c["row_id"]: c["cart_number"] for c in self.available_carts}
        nums = [str(num_by_id.get(cid, "?")) for cid in ids]
        if len(nums) > 4:
            return "، ".join(nums[:3]) + f" +{len(nums) - 3}"
        return "، ".join(nums)

    def _make_alayeshat_row_widget(self, index, row):
        is_locked = bool(self.locked_at)

        row_frame = SelectableRow(
            orientation="vertical",
            size_hint=(1, None),
            height=dp(90),
            spacing=dp(2),
            padding=[dp(4), dp(4)],
        )
        with row_frame.canvas.before:
            row_frame._bg_color = Color(1, 1, 1, 1)
            row_frame._bg_rect = RoundedRectangle(
                pos=row_frame.pos, size=row_frame.size, radius=[dp(0)]
            )
        row_frame.bind(
            pos=lambda s, v: setattr(s._bg_rect, "pos", v),
            size=lambda s, v: setattr(s._bg_rect, "size", v),
        )
        row_frame.bind(on_release=lambda inst, i=index: self._on_select_alayeshat(i))

        if self.alayeshat_selected_index == index:
            row_frame._bg_color.rgba = [0.86, 0.92, 1.0, 1]

        self.alayeshat_widgets[index] = {}
        self.alayeshat_row_frames[index] = row_frame

        if is_locked:
            row_frame.add_widget(fa_label(
                row.get("customer_name") or "—",
                size=12, color=COLOR_TEXT, height=36, bold=True, halign="center",
            ))
        else:
            name_wrap = fa_text_input(
                hint_text="نام مشتری",
                text=row.get("customer_name", ""),
                height=36,
            )
            name_wrap.hidden.bind(
                text=lambda inst, val, i=index: self._on_alayeshat_change(i, "customer_name", val)
            )
            self.alayeshat_widgets[index]["customer_name"] = name_wrap
            row_frame.add_widget(name_wrap)

        fields = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(42),
            spacing=dp(4),
        )

        for field in ["del_weight", "jigar_weight", "sangdane_weight", "pa_weight", "kale_weight"]:
            val = str(row.get(field, ""))
            if is_locked:
                lbl_box = BoxLayout(size_hint_x=1, padding=(dp(4), dp(4)))
                with lbl_box.canvas.before:
                    Color(0.92, 0.92, 0.92, 1)
                    lbl_box.bg = RoundedRectangle(pos=lbl_box.pos, size=lbl_box.size, radius=[dp(4)])
                lbl_box.bind(
                    pos=lambda s, v: setattr(s.bg, 'pos', v),
                    size=lambda s, v: setattr(s.bg, 'size', v)
                )
                lbl_box.add_widget(fa_label(
                    text=val if val else "—",
                    size=12, color=COLOR_TEXT, height=42, halign="center",
                ))
                fields.add_widget(lbl_box)
            else:
                wrap = fa_text_input(
                    hint_text="", text=val, input_filter="float", height=42,
                )
                wrap.size_hint_x = 1
                wrap.hidden.bind(
                    text=lambda inst, val, i=index, f=field: self._on_alayeshat_change(i, f, val)
                )
                self.alayeshat_widgets[index][field] = wrap
                fields.add_widget(wrap)

        row_frame.add_widget(fields)

        with row_frame.canvas.after:
            Color(0.88, 0.88, 0.88, 1)
            row_frame._line = Line(
                points=[row_frame.x, row_frame.y, row_frame.right, row_frame.y],
                width=1,
            )
        row_frame.bind(
            pos=lambda s, v: setattr(s._line, "points",
                                      [v[0], v[1], v[0] + s.width, v[1]]),
            size=lambda s, v: setattr(s._line, "points",
                                      [s.x, s.y, s.x + s.width, s.y]),
        )
        return row_frame

    def _make_morgh_row_widget(self, index, row):
        is_locked = bool(self.locked_at)

        row_frame = SelectableRow(
            orientation="vertical",
            size_hint=(1, None),
            height=dp(80),
            spacing=dp(2),
            padding=[dp(2), dp(2)],
        )
        with row_frame.canvas.before:
            row_frame._bg_color = Color(1, 1, 1, 1)
            row_frame._bg_rect = RoundedRectangle(
                pos=row_frame.pos, size=row_frame.size, radius=[dp(0)]
            )
        row_frame.bind(
            pos=lambda s, v: setattr(s._bg_rect, "pos", v),
            size=lambda s, v: setattr(s._bg_rect, "size", v),
        )
        row_frame.bind(on_release=lambda inst, i=index: self._on_select_morgh(i))

        if self.morgh_selected_index == index:
            row_frame._bg_color.rgba = [0.86, 0.92, 1.0, 1]

        self.morgh_widgets[index] = {}
        self.morgh_row_frames[index] = row_frame

        if is_locked:
            row_frame.add_widget(fa_label(
                row.get("customer_name") or "—",
                size=12, color=COLOR_TEXT, height=32, bold=True, halign="center",
            ))
        else:
            name_wrap = fa_text_input(
                hint_text="نام مشتری",
                text=row.get("customer_name", ""),
                height=32,
            )
            name_wrap.hidden.bind(
                text=lambda inst, val, i=index: self._on_morgh_change(i, "customer_name", val)
            )
            self.morgh_widgets[index]["customer_name"] = name_wrap
            row_frame.add_widget(name_wrap)

        fields = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(40),
            spacing=dp(2),
            padding=[dp(0), 0],
        )

        for field in ["lake_weight", "piece_weight", "sine_weight", "ran_weight",
                      "bal_weight", "gardan_weight", "whole_weight"]:
            val = str(row.get(field, ""))
            if is_locked:
                lbl_box = BoxLayout(size_hint_x=1, padding=(dp(2), dp(4)))
                with lbl_box.canvas.before:
                    Color(0.92, 0.92, 0.92, 1)
                    lbl_box.bg = RoundedRectangle(pos=lbl_box.pos, size=lbl_box.size, radius=[dp(4)])
                lbl_box.bind(
                    pos=lambda s, v: setattr(s.bg, 'pos', v),
                    size=lambda s, v: setattr(s.bg, 'size', v)
                )
                lbl_box.add_widget(fa_label(
                    text=val if val else "—",
                    size=10, color=COLOR_TEXT, height=40, halign="center",
                ))
                fields.add_widget(lbl_box)
            else:
                wrap = fa_text_input(
                    hint_text="", text=val, input_filter="float", height=40,
                )
                wrap.size_hint_x = 1
                wrap.hidden.bind(
                    text=lambda inst, val, i=index, f=field: self._on_morgh_change(i, f, val)
                )
                self.morgh_widgets[index][field] = wrap
                fields.add_widget(wrap)

        row_frame.add_widget(fields)

        with row_frame.canvas.after:
            Color(0.88, 0.88, 0.88, 1)
            row_frame._line = Line(
                points=[row_frame.x, row_frame.y, row_frame.right, row_frame.y],
                width=1,
            )
        row_frame.bind(
            pos=lambda s, v: setattr(s._line, "points",
                                      [v[0], v[1], v[0] + s.width, v[1]]),
            size=lambda s, v: setattr(s._line, "points",
                                      [s.x, s.y, s.x + s.width, s.y]),
        )
        return row_frame

    def _on_packed_change(self, index, field, value):
        if index < len(self.packed_rows):
            self.packed_rows[index][field] = value
            if field == "buyer_name" and self.packed_selected_index == index:
                self._render_carts_bar()

    def _on_alayeshat_change(self, index, field, value):
        if index < len(self.alayeshat_rows):
            self.alayeshat_rows[index][field] = value
            self.check_alayeshat_discrepancy()

    def _on_morgh_change(self, index, field, value):
        if index < len(self.morgh_rows):
            self.morgh_rows[index][field] = value
            self.check_morgh_discrepancy()

    def _toggle_cart_for_active(self, cart_id):
        if self.locked_at:
            return
        idx = self.packed_selected_index
        if idx is None or idx >= len(self.packed_rows):
            return

        for j, r in enumerate(self.packed_rows):
            if j == idx:
                continue
            if cart_id in r.get("cart_ids", []):
                return

        row = self.packed_rows[idx]
        selected = row.get("cart_ids", [])
        if cart_id in selected:
            selected.remove(cart_id)
        else:
            selected.append(cart_id)
        row["cart_ids"] = selected
        row["total_net_weight"] = calc_carts_total(selected)
        self.render_packed_rows()
        self._render_carts_bar()

    def _parse_float(self, val):
        if val is None or val == "":
            return 0.0
        try:
            return float(val)
        except (ValueError, TypeError):
            return 0.0

    def check_packed_discrepancy(self):
        valid_cart_ids = {c["row_id"] for c in self.available_carts}

        selected_ids = []
        for row in self.packed_rows:
            selected_ids.extend(row.get("cart_ids", []))

        if not valid_cart_ids and not selected_ids:
            self.packed_msg_label.text = ""
            self.packed_msg_label.height = dp(30)
            return

        diffs = []

        invalid = [cid for cid in selected_ids if cid not in valid_cart_ids]
        if invalid:
            invalid_str = "، ".join(str(cid) for cid in invalid)
            diffs.append(f"گاری‌های انتخاب‌شده که در فرم توزین نیستند: {invalid_str}")

        seen = set()
        duplicates = []
        for cid in selected_ids:
            if cid in seen:
                duplicates.append(cid)
            seen.add(cid)

        if duplicates:
            num_by_id = {c["row_id"]: c["cart_number"] for c in self.available_carts}
            dup_str = "، ".join(
                f"گاری {num_by_id.get(cid, cid)}" for cid in set(duplicates)
            )
            diffs.append(f"گاری‌های تکراری در گزارش: {dup_str}")

        unassigned = [cid for cid in valid_cart_ids if cid not in selected_ids]
        if unassigned:
            num_by_id = {c["row_id"]: c["cart_number"] for c in self.available_carts}
            unassigned_str = "، ".join(
                f"گاری {num_by_id.get(cid, cid)}" for cid in unassigned
            )
            diffs.append(
                f"گاری‌های فرم توزین که در گزارش تخصیص داده نشده‌اند: {unassigned_str}"
            )

        if diffs:
            full_text = "مغایرت! " + " | ".join(diffs)
            self.packed_msg_label.text = fa(full_text)
            self.packed_msg_label.color = COLOR_ERROR
            char_count = len(full_text)
            lines_needed = max(2, char_count // 45 + 1)
            self.packed_msg_label.height = dp(20) * lines_needed + dp(20)
        else:
            self.packed_msg_label.text = fa("بدون مغایرت")
            self.packed_msg_label.color = COLOR_SUCCESS
            self.packed_msg_label.height = dp(30)

    def check_alayeshat_discrepancy(self):
        if not self.form_date:
            return

        total_assigned = {"دل": 0.0, "جگر": 0.0, "سنگدان": 0.0, "پا": 0.0, "کله": 0.0}
        has_any_value = False

        for r in self.alayeshat_rows:
            row_total = 0.0
            for key, name in [("del_weight", "دل"), ("jigar_weight", "جگر"), ("sangdane_weight", "سنگدان"), ("pa_weight", "پا"), ("kale_weight", "کله")]:
                w = self._parse_float(r.get(key))
                total_assigned[name] += w
                row_total += w
            if row_total > 0:
                has_any_value = True

        if not has_any_value:
            self.alayeshat_msg_label.text = ""
            return

        stock = {item["product_name"]: item["total_net"] for item in self.aggregated_alayeshat}

        diffs = []
        for name in ["دل", "جگر", "سنگدان", "پا", "کله"]:
            diff = total_assigned[name] - stock.get(name, 0.0)
            if abs(diff) > 0.01:
                diffs.append(f"{name}: توزیع {total_assigned[name]:,.2f} ≠ موجودی {stock.get(name, 0.0):,.2f} (اختلاف {diff:+,.2f})")

        if diffs:
            self.alayeshat_msg_label.text = fa("مغایرت!\n" + "\n".join(diffs))
            self.alayeshat_msg_label.color = COLOR_ERROR
        else:
            self.alayeshat_msg_label.text = fa("بدون مغایرت")
            self.alayeshat_msg_label.color = COLOR_SUCCESS

    def check_morgh_discrepancy(self):
        if not self.form_date:
            return

        details = []
        has_any_value = False

        for i, row in enumerate(self.morgh_rows):
            piece = self._parse_float(row.get("piece_weight"))
            sine = self._parse_float(row.get("sine_weight"))
            ran = self._parse_float(row.get("ran_weight"))
            bal = self._parse_float(row.get("bal_weight"))
            gardan = self._parse_float(row.get("gardan_weight"))

            total_parts = sine + ran + bal + gardan
            diff = piece - total_parts

            if piece == 0 and total_parts == 0:
                continue

            has_any_value = True

            if abs(diff) > 0.01:
                details.append(
                    f"ردیف {i+1}: قطعه {piece:,.2f} ≠ جمع اجزا {total_parts:,.2f} (اختلاف {diff:+,.2f})"
                )

        if not has_any_value:
            self.morgh_msg_label.text = ""
            return

        if details:
            self.morgh_msg_label.text = fa(
                "توجه: مغایرت در وزن قطعه!\n" + "\n".join(details)
            )
            self.morgh_msg_label.color = COLOR_ERROR
        else:
            self.morgh_msg_label.text = fa("بدون مغایرت")
            self.morgh_msg_label.color = COLOR_SUCCESS

    def _sync_packed_widgets_to_rows(self):
        for i, row in enumerate(self.packed_rows):
            widgets = self.packed_widgets.get(i, {})
            if "buyer_name" in widgets:
                row["buyer_name"] = widgets["buyer_name"].text

    def _sync_alayeshat_widgets_to_rows(self):
        for i, row in enumerate(self.alayeshat_rows):
            widgets = self.alayeshat_widgets.get(i, {})
            if "customer_name" in widgets:
                row["customer_name"] = widgets["customer_name"].text
            for f in ["del_weight", "jigar_weight", "sangdane_weight", "pa_weight", "kale_weight"]:
                if f in widgets:
                    row[f] = widgets[f].text

    def _sync_morgh_widgets_to_rows(self):
        for i, row in enumerate(self.morgh_rows):
            widgets = self.morgh_widgets.get(i, {})
            if "customer_name" in widgets:
                row["customer_name"] = widgets["customer_name"].text
            for f in ["lake_weight", "piece_weight", "sine_weight", "ran_weight",
                      "bal_weight", "gardan_weight", "whole_weight"]:
                if f in widgets:
                    row[f] = widgets[f].text

    def on_add_packed_row(self, *args):
        if self.locked_at:
            return
        self._sync_packed_widgets_to_rows()
        self.packed_rows.append(self._empty_packed_row())
        self.packed_selected_index = len(self.packed_rows) - 1
        self.render_packed_rows()
        self._render_carts_bar()
        new_idx = self.packed_selected_index
        w = self.packed_widgets.get(new_idx, {})
        if "buyer_name" in w:
            try:
                w["buyer_name"].hidden.focus = True
            except Exception:
                pass

    def on_add_alayeshat_row(self, *args):
        if self.locked_at:
            return
        self._sync_alayeshat_widgets_to_rows()
        self.alayeshat_rows.append(self._empty_alayeshat_row())
        self.alayeshat_selected_index = len(self.alayeshat_rows) - 1
        self.render_alayeshat_rows()
        new_idx = self.alayeshat_selected_index
        w = self.alayeshat_widgets.get(new_idx, {})
        if "customer_name" in w:
            try:
                w["customer_name"].hidden.focus = True
            except Exception:
                pass

    def on_add_morgh_row(self, *args):
        if self.locked_at:
            return
        self._sync_morgh_widgets_to_rows()
        self.morgh_rows.append(self._empty_morgh_row())
        self.morgh_selected_index = len(self.morgh_rows) - 1
        self.render_morgh_rows()
        new_idx = self.morgh_selected_index
        w = self.morgh_widgets.get(new_idx, {})
        if "customer_name" in w:
            try:
                w["customer_name"].hidden.focus = True
            except Exception:
                pass

    def on_delete_selected_packed(self, *args):
        if self.locked_at:
            return
        idx = self.packed_selected_index
        if idx is None or idx >= len(self.packed_rows):
            return
        self._sync_packed_widgets_to_rows()
        self.packed_rows.pop(idx)
        if not self.packed_rows:
            self.packed_rows.append(self._empty_packed_row())
        self.packed_selected_index = None
        self.render_packed_rows()
        self._render_carts_bar()

    def on_delete_selected_alayeshat(self, *args):
        if self.locked_at:
            return
        idx = self.alayeshat_selected_index
        if idx is None or idx >= len(self.alayeshat_rows):
            return
        self._sync_alayeshat_widgets_to_rows()
        self.alayeshat_rows.pop(idx)
        if not self.alayeshat_rows:
            self.alayeshat_rows.append(self._empty_alayeshat_row())
        self.alayeshat_selected_index = None
        self.render_alayeshat_rows()

    def on_delete_selected_morgh(self, *args):
        if self.locked_at:
            return
        idx = self.morgh_selected_index
        if idx is None or idx >= len(self.morgh_rows):
            return
        self._sync_morgh_widgets_to_rows()
        self.morgh_rows.pop(idx)
        if not self.morgh_rows:
            self.morgh_rows.append(self._empty_morgh_row())
        self.morgh_selected_index = None
        self.render_morgh_rows()

    def _collect_packed(self):
        result = []
        for row in self.packed_rows:
            buyer = str(row.get("buyer_name") or "").strip()
            cart_ids = row.get("cart_ids", [])
            if not buyer and not cart_ids:
                continue
            result.append({
                "buyer_name": buyer,
                "cart_row_ids": cart_ids,
            })
        return result

    def _collect_alayeshat(self):
        result = []
        for row in self.alayeshat_rows:
            name = str(row.get("customer_name") or "").strip()
            if not name:
                continue
            result.append({
                "customer_name": name,
                "del_weight": self._parse_float(row.get("del_weight")),
                "jigar_weight": self._parse_float(row.get("jigar_weight")),
                "sangdane_weight": self._parse_float(row.get("sangdane_weight")),
                "pa_weight": self._parse_float(row.get("pa_weight")),
                "kale_weight": self._parse_float(row.get("kale_weight")),
            })
        return result

    def _collect_morgh(self):
        result = []
        for row in self.morgh_rows:
            name = str(row.get("customer_name") or "").strip()
            if not name:
                continue
            result.append({
                "customer_name": name,
                "lake_weight": self._parse_float(row.get("lake_weight")),
                "piece_weight": self._parse_float(row.get("piece_weight")),
                "sine_weight": self._parse_float(row.get("sine_weight")),
                "ran_weight": self._parse_float(row.get("ran_weight")),
                "bal_weight": self._parse_float(row.get("bal_weight")),
                "gardan_weight": self._parse_float(row.get("gardan_weight")),
                "whole_weight": self._parse_float(row.get("whole_weight")),
            })
        return result

    def on_submit(self, *args):
        self._sync_packed_widgets_to_rows()
        self._sync_alayeshat_widgets_to_rows()
        self._sync_morgh_widgets_to_rows()

        packed = self._collect_packed()
        alayeshat = self._collect_alayeshat()
        morgh = self._collect_morgh()

        try:
            save_daily_form_by_date(self.form_date, packed, alayeshat, morgh)

            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE daily_forms SET completed_at = ? WHERE form_date = ?",
                (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), self.form_date)
            )
            conn.commit()
            conn.close()

        except Exception as e:
            self._show_error(f"خطا در ثبت: {e}")
            return

        self.load_form()
        self.check_packed_discrepancy()
        info_dialog("ثبت موفق", "فرم گزارش ثبت شد. اکنون می‌توانید آن را ویرایش، حذف یا نهایی کنید.")

    def on_edit(self, *args):
        if not self.completed_at:
            return

        from kivymd.app import MDApp
        app = MDApp.get_running_app()

        if not can_edit_form(self.completed_at, self.locked_at, app.current_user):
            info_dialog("مهلت ویرایش تمام شده", "این فرم بیش از ۱۵ دقیقه پیش ثبت شده و دیگر قابل ویرایش نیست.")
            return
        self.is_editing = True
        self.load_form()

    def on_save_edit(self, *args):
        self._sync_packed_widgets_to_rows()
        self._sync_alayeshat_widgets_to_rows()
        self._sync_morgh_widgets_to_rows()

        packed = self._collect_packed()
        alayeshat = self._collect_alayeshat()
        morgh = self._collect_morgh()

        try:
            save_daily_form_by_date(self.form_date, packed, alayeshat, morgh)
        except Exception as e:
            self._show_error(f"خطا در ذخیره تغییرات: {e}")
            return

        self.is_editing = False
        self.load_form()
        self.check_packed_discrepancy()
        info_dialog("ویرایش موفق", "تغییرات با موفقیت ذخیره شد.")

    def on_cancel_edit(self, *args):
        self.is_editing = False
        self.load_form()

    def on_finalize(self, *args):
        confirm_dialog(
            title="ثبت نهایی فرم گزارش",
            message="آیا از ثبت نهایی مطمئن هستید؟\n\nپس از ثبت نهایی، فرم کاملاً قفل شده و قابل ویرایش یا حذف نیست.",
            confirm_text="تایید نهایی",
            cancel_text="لغو",
            confirm_color=COLOR_PRIMARY_DARK,
            on_confirm=self._do_finalize,
        )

    def _do_finalize(self):
        try:
            finalize_form("daily_forms", "form_date", self.form_date)
        except Exception as e:
            self._show_error(f"خطا در ثبت نهایی: {e}")
            return

        info_dialog("تایید نهایی موفق", "فرم گزارش قفل شد.")
        self.load_form()

    def on_admin_edit(self, *args):
        def do_unlock():
            try:
                admin_unlock_form("daily_forms", "form_date", self.form_date)
                self.is_editing = False
                self.load_form()
                info_dialog(
                    "انجام شد",
                    "قفل فرم باز شد. حالا ۱۵ دقیقه فرصت ویرایش دارید.\n"
                    "بعد از ۱۵ دقیقه، دوباره قفل می‌شود."
                )
            except Exception as e:
                info_dialog("خطا", f"باز کردن قفل ناموفق:\n{e}")

        confirm_dialog(
            title="ویرایش فرم قفل‌شده",
            message=(
                "آیا از باز کردن قفل این فرم مطمئن هستید؟\n\n"
                "⚠️ پس از باز کردن قفل، ۱۵ دقیقه فرصت ویرایش دارید.\n"
                "بعد از آن، دوباره قفل می‌شود."
            ),
            confirm_text="باز کن",
            cancel_text="لغو",
            confirm_color=COLOR_WARNING,
            on_confirm=do_unlock,
        )

    def on_delete_entire_form(self, *args):
        def do_delete():
            try:
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT form_id FROM daily_forms WHERE form_date = ?", (self.form_date,))
                row = cursor.fetchone()
                if row:
                    form_id = row[0]
                    cursor.execute("DELETE FROM daily_packed_carts WHERE row_id IN (SELECT row_id FROM daily_packed_rows WHERE form_id = ?)", (form_id,))
                    cursor.execute("DELETE FROM daily_packed_rows WHERE form_id = ?", (form_id,))
                    cursor.execute("DELETE FROM daily_alayeshat_rows WHERE form_id = ?", (form_id,))
                    cursor.execute("DELETE FROM daily_morgh_rows WHERE form_id = ?", (form_id,))
                    cursor.execute("UPDATE daily_forms SET waste = 0, completed_at = NULL, locked_at = NULL WHERE form_id = ?", (form_id,))
                conn.commit()
                conn.close()
            except Exception as e:
                self._show_error(f"خطا در حذف: {e}")
                return
            info_dialog("حذف موفق", "فرم گزارش پاک شد.")
            self.load_form()

        confirm_dialog(
            title="حذف فرم گزارش",
            message="آیا از حذف کل اطلاعات این فرم مطمئن هستید؟\nاین عمل قابل بازگشت نیست.",
            confirm_text="حذف",
            cancel_text="لغو",
            confirm_color=COLOR_ERROR,
            on_confirm=do_delete,
        )

    def on_export_pdf(self, *args):
        from ..helpers.file_dialog import ask_save_path, ask_open_after_save
        from ..helpers.file_utils import open_file
        from pdf_daily import generate_daily_pdf
        from datetime import datetime

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_date = self.form_date.replace("/", "-")
        default_name = f"daily_{safe_date}_{ts}"

        def do_save(filepath):
            try:
                result = generate_daily_pdf(form_date=self.form_date, output_path=filepath)
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

    def on_export_csv(self, *args):
        from ..helpers.file_dialog import ask_save_path, ask_open_after_save
        from ..helpers.file_utils import open_file
        from pdf_daily import generate_daily_excel
        from datetime import datetime

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_date = self.form_date.replace("/", "-")
        default_name = f"daily_{safe_date}_{ts}"

        def do_save(filepath):
            try:
                result = generate_daily_excel(
                    form_date=self.form_date, output_path=filepath
                )
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

    def _show_error(self, text):
        self.msg_label.text = fa(text)
        self.msg_label.color = COLOR_ERROR

    def on_back(self, *args):
        self.manager.transition.direction = "right"
        self.manager.current = "slaughters_list"
