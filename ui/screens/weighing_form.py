# -*- coding: utf-8 -*-
"""
صفحه‌ی فرم ۲: توزین
"""

from kivy.metrics import dp, sp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.spinner import Spinner, SpinnerOption
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
    get_slaughter,
    get_weighing_form,
    save_weighing_form,
    complete_weighing_form,
    can_edit_weighing_form,
    get_products_by_category,
    is_within_edit_window,
    can_edit_form,
    admin_unlock_form,
    finalize_form,
    user_can_edit_locked,
)
from database import get_connection
from datetime import datetime


OPERATOR_EDIT_WINDOW_MINUTES = 15


class FaSpinnerOption(SpinnerOption):
    """گزینه‌ی Spinner با فونت فارسی."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.font_name = "Vazir"
        self.font_size = sp(13)
        self.color = [0.1, 0.1, 0.1, 1]
        self.background_normal = ""
        self.background_color = [1, 1, 1, 1]


class SelectableRow(ButtonBehavior, BoxLayout):
    """ردیف قابل کلیک برای انتخاب."""
    pass


class WeighingFormScreen(MDScreen):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "weighing_form"
        self.md_bg_color = COLOR_BG

        self.slaughter_id = None
        self.slaughter_info = None
        self.alayeshat_products = []

        self.plucked_rows = []
        self.alayeshat_rows = []

        self.completed_at = None
        self.locked_at = None
        self.is_editing = False

        self.plucked_widgets = {}
        self.alayeshat_widgets = {}
        self.plucked_row_frames = {}
        self.alayeshat_row_frames = {}

        self.plucked_selected_index = None
        self.alayeshat_selected_index = None

        self.info_label = None
        self.status_label = None
        self.plucked_container = None
        self.alayeshat_container = None
        self.calc_label = None
        self.msg_label = None
        self.actions_container = None
        self.live_weight_wrap = None

        self.add_plucked_btn = None
        self.add_alayeshat_btn = None
        self.del_plucked_btn = None
        self.del_alayeshat_btn = None

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
            "فرم توزین",
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

        live_card = MDCard(
            orientation="horizontal",
            padding=[dp(12), dp(6)],
            spacing=dp(10),
            size_hint_y=None,
            height=dp(48),
            elevation=2,
            radius=[dp(10)],
            md_bg_color=[1, 1, 1, 1],
        )

        self.live_weight_wrap = fa_text_input(
            hint_text="",
            input_filter="float",
            height=38,
        )
        self.live_weight_wrap.size_hint_x = 0.32
        self.live_weight_wrap.hidden.bind(text=self._on_live_weight_change)
        live_card.add_widget(self.live_weight_wrap)

        live_label = fa_label(
            "وزن زنده باسکول مبدا (kg):",
            size=13,
            color=COLOR_PRIMARY_DARK,
            bold=True,
            halign="right",
            height=38,
        )
        live_label.size_hint_x = 0.68
        live_card.add_widget(live_label)

        root.add_widget(live_card)

        scroll = ScrollView()

        content = BoxLayout(
            orientation="vertical",
            padding=dp(10),
            spacing=dp(8),
            size_hint_y=None,
        )
        content.bind(minimum_height=content.setter("height"))

        content.add_widget(fa_section_title("مرغ پرکنده:"))
        content.add_widget(self._make_plucked_header())

        self.plucked_container = BoxLayout(
            orientation="vertical",
            spacing=dp(0),
            size_hint_y=None,
        )
        self.plucked_container.bind(
            minimum_height=self.plucked_container.setter("height")
        )
        content.add_widget(self.plucked_container)

        plucked_btns = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(42),
            spacing=dp(8),
        )
        self.add_plucked_btn = fa_button(
            "+ افزودن گاری",
            size=13,
            height=42,
            bg_color=COLOR_SUCCESS,
            on_press=self.on_add_plucked_row,
        )
        plucked_btns.add_widget(self.add_plucked_btn)

        self.del_plucked_btn = fa_button(
            "حذف ردیف انتخاب‌شده",
            size=13,
            height=42,
            bg_color=COLOR_ERROR,
            on_press=self.on_delete_selected_plucked,
        )
        self.del_plucked_btn.disabled = True
        self.del_plucked_btn.opacity = 1.0
        plucked_btns.add_widget(self.del_plucked_btn)

        content.add_widget(plucked_btns)

        content.add_widget(spacer(8))
        content.add_widget(fa_section_title("آلایشات:"))
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
        self.add_alayeshat_btn = fa_button(
            "+ افزودن آلایشات",
            size=13,
            height=42,
            bg_color=COLOR_SUCCESS,
            on_press=self.on_add_alayeshat_row,
        )
        alayeshat_btns.add_widget(self.add_alayeshat_btn)

        self.del_alayeshat_btn = fa_button(
            "حذف ردیف انتخاب‌شده",
            size=13,
            height=42,
            bg_color=COLOR_ERROR,
            on_press=self.on_delete_selected_alayeshat,
        )
        self.del_alayeshat_btn.disabled = True
        self.del_alayeshat_btn.opacity = 1.0
        alayeshat_btns.add_widget(self.del_alayeshat_btn)

        content.add_widget(alayeshat_btns)

        content.add_widget(spacer(10))
        content.add_widget(fa_section_title("محاسبه:"))

        self.calc_label = fa_label(
            "—",
            size=13,
            color=COLOR_PRIMARY_DARK,
            height=80,
            bold=True,
        )
        content.add_widget(self.calc_label)

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
            height=dp(50),
            spacing=dp(8),
        )
        btns_row.add_widget(fa_button(
            "خروجی PDF",
            size=12, height=50,
            bg_color=COLOR_PRIMARY_DARK,
            on_press=self.on_export_pdf,
        ))
        btns_row.add_widget(fa_button(
            "خروجی Excel",
            size=12, height=50,
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
        """به‌روزرسانی خودکار UI برای مخفی کردن دکمه‌های ویرایش بعد از ۱۵ دقیقه."""
        try:
            if self.locked_at or (self.completed_at and not self.is_editing):
                self._update_actions()
        except Exception:
            pass

    def on_leave(self, *args):
        """توقف تایمر هنگام خروج از صفحه."""
        try:
            if self._clock_event:
                self._clock_event.cancel()
                self._clock_event = None
        except Exception:
            pass

    # ======================================
    # هدرهای ثابت
    # ======================================

    def _make_plucked_header(self):
        hdr = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(28),
            spacing=dp(4),
            padding=[dp(4), 0],
        )
        for txt in ["شماره گاری", "وزن خالی", "وزن پر", "خالص"]:
            hdr.add_widget(fa_label(
                txt, size=11, color=COLOR_PRIMARY_DARK,
                height=28, bold=True, halign="center",
            ))
        return hdr

    def _make_alayeshat_header(self):
        hdr = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(28),
            spacing=dp(4),
            padding=[dp(4), 0],
        )
        for txt in ["محصول", "وزن خالی", "وزن پر", "خالص"]:
            hdr.add_widget(fa_label(
                txt, size=11, color=COLOR_PRIMARY_DARK,
                height=28, bold=True, halign="center",
            ))
        return hdr

    # ======================================
    # بارگذاری
    # ======================================

    def on_pre_enter(self, *args):
        if not self._clock_event:
            self._clock_event = Clock.schedule_interval(self._auto_refresh, 30)

        from kivymd.app import MDApp
        app = MDApp.get_running_app()

        self.slaughter_id = getattr(app, "current_slaughter_id", None)

        if self.slaughter_id is None:
            self._show_error("خطا: کشتاری انتخاب نشده")
            return

        self.slaughter_info = get_slaughter(self.slaughter_id)
        if not self.slaughter_info:
            self._show_error("کشتار یافت نشد.")
            return

        try:
            all_alayeshat = get_products_by_category(
                "alayeshat", only_active=True
            )
            self.alayeshat_products = [
                p for p in all_alayeshat if p[2] is not None
            ]
        except Exception as e:
            self._show_error(f"خطا در لود آلایشات: {e}")
            return

        self.is_editing = False
        self.load_form()

    def load_form(self):

        form = get_weighing_form(self.slaughter_id)
        if not form:
            self._show_error("فرم توزین یافت نشد.")
            return

        self.completed_at = form.get("completed_at")
        self.locked_at = form.get("locked_at")

        si = self.slaughter_info
        info_text = (
            f"کشتار #{si['slaughter_number']} — "
            f"{si['day_name']} {si['form_date']}"
        )
        self.info_label.text = fa(info_text)

        live_w = form.get("live_weight", 0)
        self.live_weight_wrap.text = str(live_w) if live_w else ""

        if self.locked_at:
            self.status_label.text = fa("[ قفل شده - تایید نهایی ]")
            self.status_label.color = COLOR_SUCCESS
            self.live_weight_wrap.disabled = True
            self.live_weight_wrap.opacity = 0.6
        elif self.completed_at and not self.is_editing:
            self.status_label.text = fa("[ ثبت شده - منتظر تایید ]")
            self.status_label.color = COLOR_WARNING
            self.live_weight_wrap.disabled = True
            self.live_weight_wrap.opacity = 0.6
        elif self.is_editing:
            self.status_label.text = fa("[ در حال ویرایش ]")
            self.status_label.color = COLOR_PRIMARY_DARK
            self.live_weight_wrap.disabled = False
            self.live_weight_wrap.opacity = 1.0
        else:
            self.status_label.text = fa("[ در حال ثبت ]")
            self.status_label.color = COLOR_GRAY
            self.live_weight_wrap.disabled = False
            self.live_weight_wrap.opacity = 1.0

        self.plucked_rows = []
        for r in form["plucked_rows"]:
            self.plucked_rows.append({
                "row_id": r["row_id"],
                "cart_number": r["cart_number"],
                "is_bulk": r.get("is_bulk", False),
                "empty_weight": r["empty_weight"],
                "full_weight": r["full_weight"],
                "net_weight": r["net_weight"],
                "baskets": r.get("baskets", []),
            })

        if not self.plucked_rows:
            self.plucked_rows.append(self._empty_plucked_row())

        self.alayeshat_rows = []
        for r in form["alayeshat_rows"]:
            self.alayeshat_rows.append({
                "row_id": r["row_id"],
                "product_id": r["product_id"],
                "product_name": r["product_name"],
                "empty_weight": r["empty_weight"],
                "full_weight": r["full_weight"],
                "net_weight": r["net_weight"],
            })

        self.plucked_selected_index = None
        self.alayeshat_selected_index = None

        self.render_all()
        self._update_actions()

        is_readonly = bool(self.locked_at) or (bool(self.completed_at) and not self.is_editing)
        for btn in [self.add_plucked_btn, self.add_alayeshat_btn]:
            if btn:
                btn.disabled = is_readonly
                btn.opacity = 0.4 if is_readonly else 1.0
        for btn in [self.del_plucked_btn, self.del_alayeshat_btn]:
            if btn:
                btn.disabled = True
                btn.opacity = 1.0

    def _update_actions(self):

        try:
            from functions import is_within_edit_window
            from datetime import datetime as _dt
            _now = _dt.now().strftime("%Y-%m-%d %H:%M:%S")
            _within = is_within_edit_window(self.locked_at, 15) if self.locked_at else "N/A"
            print(f"[DEBUG] _update_actions:")
            print(f"    locked_at    = {self.locked_at!r}")
            print(f"    completed_at = {self.completed_at!r}")
            print(f"    now          = {_now}")
            print(f"    within_15    = {_within}")
            print(f"    can_unlock   = {user_can_edit_locked(app.current_user)}")
        except Exception as _e:
            print(f"[DEBUG] error: {_e}")
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

    def _empty_plucked_row(self):
        return {
            "row_id": None,
            "cart_number": "",
            "is_bulk": False,
            "empty_weight": "",
            "full_weight": "",
            "net_weight": "",
            "baskets": [],
        }

    def _empty_alayeshat_row(self):
        return {
            "row_id": None,
            "product_id": None,
            "product_name": "",
            "empty_weight": "",
            "full_weight": "",
            "net_weight": "",
        }

    # ======================================
    # رندر
    # ======================================

    def render_all(self):
        self.render_plucked_rows()
        self.render_alayeshat_rows()
        self.update_calc()

    def render_plucked_rows(self):
        self.plucked_container.clear_widgets()
        self.plucked_widgets = {}
        self.plucked_row_frames = {}
        if self.plucked_selected_index is not None and \
           self.plucked_selected_index >= len(self.plucked_rows):
            self.plucked_selected_index = None
        for i, row in enumerate(self.plucked_rows):
            self.plucked_container.add_widget(
                self._make_plucked_row_widget(i, row)
            )
        self._refresh_plucked_delete_btn()

    def render_alayeshat_rows(self):
        self.alayeshat_container.clear_widgets()
        self.alayeshat_widgets = {}
        self.alayeshat_row_frames = {}
        if self.alayeshat_selected_index is not None and \
           self.alayeshat_selected_index >= len(self.alayeshat_rows):
            self.alayeshat_selected_index = None
        for i, row in enumerate(self.alayeshat_rows):
            self.alayeshat_container.add_widget(
                self._make_alayeshat_row_widget(i, row)
            )
        self._refresh_alayeshat_delete_btn()

    def _refresh_plucked_delete_btn(self):
        if self.del_plucked_btn is None:
            return
        is_readonly = bool(self.locked_at) or (bool(self.completed_at) and not self.is_editing)
        can_del = (self.plucked_selected_index is not None) and not is_readonly
        self.del_plucked_btn.disabled = not can_del
        self.del_plucked_btn.opacity = 1.0

    def _refresh_alayeshat_delete_btn(self):
        if self.del_alayeshat_btn is None:
            return
        is_readonly = bool(self.locked_at) or (bool(self.completed_at) and not self.is_editing)
        can_del = (self.alayeshat_selected_index is not None) and not is_readonly
        self.del_alayeshat_btn.disabled = not can_del
        self.del_alayeshat_btn.opacity = 1.0

    def _paint_plucked_row(self, index, selected):
        frame = self.plucked_row_frames.get(index)
        if frame is None:
            return
        bg = [0.86, 0.92, 1.0, 1] if selected else [1, 1, 1, 1]
        if hasattr(frame, "_bg_color"):
            frame._bg_color.rgba = bg

    def _paint_alayeshat_row(self, index, selected):
        frame = self.alayeshat_row_frames.get(index)
        if frame is None:
            return
        bg = [0.86, 0.92, 1.0, 1] if selected else [1, 1, 1, 1]
        if hasattr(frame, "_bg_color"):
            frame._bg_color.rgba = bg

    def _on_select_plucked(self, index):
        if self.plucked_selected_index == index:
            self._paint_plucked_row(index, False)
            self.plucked_selected_index = None
        else:
            if self.plucked_selected_index is not None:
                self._paint_plucked_row(self.plucked_selected_index, False)
            self.plucked_selected_index = index
            self._paint_plucked_row(index, True)
        self._refresh_plucked_delete_btn()

    def _on_select_alayeshat(self, index):
        if self.alayeshat_selected_index == index:
            self._paint_alayeshat_row(index, False)
            self.alayeshat_selected_index = None
        else:
            if self.alayeshat_selected_index is not None:
                self._paint_alayeshat_row(self.alayeshat_selected_index, False)
            self.alayeshat_selected_index = index
            self._paint_alayeshat_row(index, True)
        self._refresh_alayeshat_delete_btn()

    def _make_plucked_row_widget(self, index, row):
        is_locked = bool(self.locked_at)
        is_saved = bool(self.completed_at) and not self.is_editing
        is_readonly = is_locked or is_saved

        row_frame = SelectableRow(
            orientation="horizontal",
            size_hint=(1, None),
            height=dp(46),
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

        row_frame.bind(on_release=lambda inst, i=index: self._on_select_plucked(i))

        self.plucked_widgets[index] = {}
        self.plucked_row_frames[index] = row_frame

        if is_readonly:
            for field in ["cart_number", "empty_weight", "full_weight"]:
                val = str(row.get(field, ""))
                row_frame.add_widget(fa_label(
                    val if val else "—",
                    size=12, color=COLOR_TEXT, height=42, halign="center",
                ))
            net_val = self._calc_row_net(row)
            row_frame.add_widget(fa_label(
                f"{net_val:,.2f}" if net_val else "—",
                size=12, color=COLOR_PRIMARY, height=42, bold=True,
            ))
        else:
            cart_wrap = fa_text_input(
                hint_text="", text=str(row.get("cart_number", "")), height=42
            )
            cart_wrap.hidden.bind(
                text=lambda inst, val, i=index: self._on_plucked_change(i, "cart_number", val)
            )
            self.plucked_widgets[index]["cart_number"] = cart_wrap
            row_frame.add_widget(cart_wrap)

            empty_wrap = fa_text_input(
                hint_text="", text=str(row.get("empty_weight", "")),
                input_filter="float", height=42
            )
            empty_wrap.hidden.bind(
                text=lambda inst, val, i=index: self._on_plucked_change(i, "empty_weight", val)
            )
            self.plucked_widgets[index]["empty_weight"] = empty_wrap
            row_frame.add_widget(empty_wrap)

            full_wrap = fa_text_input(
                hint_text="", text=str(row.get("full_weight", "")),
                input_filter="float", height=42
            )
            full_wrap.hidden.bind(
                text=lambda inst, val, i=index: self._on_plucked_change(i, "full_weight", val)
            )
            self.plucked_widgets[index]["full_weight"] = full_wrap
            row_frame.add_widget(full_wrap)

            net_lbl = fa_label("—", size=12, color=COLOR_PRIMARY, height=42, bold=True)
            self.plucked_widgets[index]["net_lbl"] = net_lbl

            empty_wrap.hidden.bind(
                text=lambda inst, val, i=index: self._update_plucked_net(i)
            )
            full_wrap.hidden.bind(
                text=lambda inst, val, i=index: self._update_plucked_net(i)
            )

            row_frame.add_widget(net_lbl)

            initial_net = self._calc_row_net(row)
            if initial_net > 0:
                net_lbl.text = f"{initial_net:,.2f}"
            else:
                net_lbl.text = "—"

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

    def _make_alayeshat_row_widget(self, index, row):
        is_locked = bool(self.locked_at)
        is_saved = bool(self.completed_at) and not self.is_editing
        is_readonly = is_locked or is_saved

        row_frame = SelectableRow(
            orientation="horizontal",
            size_hint=(1, None),
            height=dp(46),
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

        row_frame.bind(on_release=lambda inst, i=index: self._on_select_alayeshat(i))

        self.alayeshat_widgets[index] = {}
        self.alayeshat_row_frames[index] = row_frame

        product_names = [p[1] for p in self.alayeshat_products]
        current_name = row.get("product_name") or (product_names[0] if product_names else "")

        if is_readonly:
            row_frame.add_widget(fa_label(
                current_name if current_name else "—",
                size=12, color=COLOR_TEXT, height=42, halign="center",
            ))
            for field in ["empty_weight", "full_weight"]:
                val = str(row.get(field, ""))
                row_frame.add_widget(fa_label(
                    val if val else "—",
                    size=12, color=COLOR_TEXT, height=42, halign="center",
                ))
            net_val = self._calc_row_net(row)
            row_frame.add_widget(fa_label(
                f"{net_val:,.2f}" if net_val else "—",
                size=12, color=COLOR_PRIMARY, height=42, bold=True,
            ))
        else:
            spinner = Spinner(
                text=fa(current_name),
                values=[fa(n) for n in product_names],
                size_hint=(1, None),
                height=dp(42),
                background_normal="",
                background_color=[0.96, 0.96, 0.96, 1],
                color=[0.1, 0.1, 0.1, 1],
                font_name="Vazir",
                font_size=sp(12),
                option_cls=FaSpinnerOption,
            )
            spinner.bind(
                text=lambda inst, val, i=index: self._on_alayeshat_product_change(i, val)
            )
            self.alayeshat_widgets[index]["product_spinner"] = spinner
            row_frame.add_widget(spinner)

            if not row.get("product_id"):
                for p in self.alayeshat_products:
                    if p[1] == current_name:
                        row["product_id"] = p[0]
                        row["product_name"] = p[1]
                        break

            empty_wrap = fa_text_input(
                hint_text="", text=str(row.get("empty_weight", "")),
                input_filter="float", height=42
            )
            empty_wrap.hidden.bind(
                text=lambda inst, val, i=index: self._on_alayeshat_change(i, "empty_weight", val)
            )
            self.alayeshat_widgets[index]["empty_weight"] = empty_wrap
            row_frame.add_widget(empty_wrap)

            full_wrap = fa_text_input(
                hint_text="", text=str(row.get("full_weight", "")),
                input_filter="float", height=42
            )
            full_wrap.hidden.bind(
                text=lambda inst, val, i=index: self._on_alayeshat_change(i, "full_weight", val)
            )
            self.alayeshat_widgets[index]["full_weight"] = full_wrap
            row_frame.add_widget(full_wrap)

            net_lbl = fa_label("—", size=12, color=COLOR_PRIMARY, height=42, bold=True)
            self.alayeshat_widgets[index]["net_lbl"] = net_lbl

            empty_wrap.hidden.bind(
                text=lambda inst, val, i=index: self._update_alayeshat_net(i)
            )
            full_wrap.hidden.bind(
                text=lambda inst, val, i=index: self._update_alayeshat_net(i)
            )

            row_frame.add_widget(net_lbl)

            initial_net = self._calc_row_net(row)
            if initial_net > 0:
                net_lbl.text = f"{initial_net:,.2f}"
            else:
                net_lbl.text = "—"

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

    # ======================================
    # محاسبات
    # ======================================

    def _calc_row_net(self, row):
        try:
            e = float(row.get("empty_weight") or 0)
            f = float(row.get("full_weight") or 0)
        except (ValueError, TypeError):
            return 0.0
        return max(0.0, f - e)

    def _parse_float(self, val):
        if val is None or val == "":
            return 0.0
        try:
            return float(val)
        except (ValueError, TypeError):
            return 0.0

    def _update_alayeshat_net(self, index):
        if index not in self.alayeshat_widgets:
            return
        widgets = self.alayeshat_widgets[index]
        if "net_lbl" not in widgets:
            return

        e = self._parse_float(widgets["empty_weight"].text)
        f = self._parse_float(widgets["full_weight"].text)
        net = max(0.0, f - e)

        if net > 0:
            widgets["net_lbl"].text = f"{net:,.2f}"
        else:
            widgets["net_lbl"].text = "—"

    def _update_plucked_net(self, index):
        if index not in self.plucked_widgets:
            return
        widgets = self.plucked_widgets[index]
        if "net_lbl" not in widgets:
            return

        e = self._parse_float(widgets["empty_weight"].text)
        f = self._parse_float(widgets["full_weight"].text)
        net = max(0.0, f - e)

        if net > 0:
            widgets["net_lbl"].text = f"{net:,.2f}"
        else:
            widgets["net_lbl"].text = "—"
        self.update_calc()

    def _on_live_weight_change(self, instance, value):
        self.update_calc()

    def update_calc(self):
        total_net_plucked = 0.0

        for i, row in enumerate(self.plucked_rows):
            if not (self.completed_at or self.locked_at) or self.is_editing:
                widgets = self.plucked_widgets.get(i, {})
                if "full_weight" in widgets:
                    f = self._parse_float(widgets["full_weight"].text)
                    e = self._parse_float(widgets["empty_weight"].text)
                else:
                    f = self._parse_float(row.get("full_weight"))
                    e = self._parse_float(row.get("empty_weight"))
            else:
                f = self._parse_float(row.get("full_weight"))
                e = self._parse_float(row.get("empty_weight"))

            n = max(0.0, f - e)
            total_net_plucked += n

        live_weight = self._parse_float(self.live_weight_wrap.text) if hasattr(self, "live_weight_wrap") else 0.0

        if live_weight <= 0:
            self.calc_label.text = fa("—")
            return

        loss = (1 - (total_net_plucked / live_weight)) * 100

        text = (
            f"۱۰۰ × [ (وزن خالص پرکنده ÷ وزن زنده باسکول) - ۱ ] = درصد افت\n"
            f"۱۰۰ × [ ({total_net_plucked:,.2f} ÷ {live_weight:,.2f}) - ۱ ] = درصد افت\n"
            f"{loss:.2f}% = درصد افت"
        )
        self.calc_label.text = fa(text)

    # ======================================
    # تغییرات
    # ======================================

    def _on_plucked_change(self, index, field, value):
        if index < len(self.plucked_rows):
            self.plucked_rows[index][field] = value
            self.update_calc()

    def _on_alayeshat_change(self, index, field, value):
        if index < len(self.alayeshat_rows):
            self.alayeshat_rows[index][field] = value

    def _on_alayeshat_product_change(self, index, value):
        if index >= len(self.alayeshat_rows):
            return
        for p in self.alayeshat_products:
            if fa(p[1]) == value:
                self.alayeshat_rows[index]["product_id"] = p[0]
                self.alayeshat_rows[index]["product_name"] = p[1]
                break

    # ======================================
    # افزودن / حذف
    # ======================================

    def on_add_plucked_row(self, *args):
        if self.locked_at or (self.completed_at and not self.is_editing):
            return
        self._sync_plucked_widgets_to_rows()
        self.plucked_rows.append(self._empty_plucked_row())
        self.render_plucked_rows()

    def on_add_alayeshat_row(self, *args):
        if self.locked_at or (self.completed_at and not self.is_editing):
            return
        self._sync_alayeshat_widgets_to_rows()
        self.alayeshat_rows.append(self._empty_alayeshat_row())
        self.render_alayeshat_rows()

    def _sync_plucked_widgets_to_rows(self):
        for i, row in enumerate(self.plucked_rows):
            widgets = self.plucked_widgets.get(i, {})
            if "cart_number" in widgets:
                row["cart_number"] = widgets["cart_number"].text
            if "empty_weight" in widgets:
                row["empty_weight"] = widgets["empty_weight"].text
            if "full_weight" in widgets:
                row["full_weight"] = widgets["full_weight"].text

    def _sync_alayeshat_widgets_to_rows(self):
        for i, row in enumerate(self.alayeshat_rows):
            widgets = self.alayeshat_widgets.get(i, {})
            if "empty_weight" in widgets:
                row["empty_weight"] = widgets["empty_weight"].text
            if "full_weight" in widgets:
                row["full_weight"] = widgets["full_weight"].text

    def on_delete_selected_plucked(self, *args):
        if self.locked_at or (self.completed_at and not self.is_editing):
            return
        idx = self.plucked_selected_index
        if idx is None or idx >= len(self.plucked_rows):
            return
        self._sync_plucked_widgets_to_rows()
        self.plucked_rows.pop(idx)
        if not self.plucked_rows:
            self.plucked_rows.append(self._empty_plucked_row())
        self.plucked_selected_index = None
        self.render_plucked_rows()
        self.update_calc()

    def on_delete_selected_alayeshat(self, *args):
        if self.locked_at or (self.completed_at and not self.is_editing):
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

    # ======================================
    # جمع‌آوری داده‌ها
    # ======================================

    def _collect_plucked(self):
        result = []
        for i, row in enumerate(self.plucked_rows):
            if not (self.completed_at or self.locked_at) or self.is_editing:
                widgets = self.plucked_widgets.get(i, {})
                cart = str(widgets["cart_number"].text if "cart_number" in widgets else "").strip()
                e = self._parse_float(widgets["empty_weight"].text if "empty_weight" in widgets else row.get("empty_weight"))
                f = self._parse_float(widgets["full_weight"].text if "full_weight" in widgets else row.get("full_weight"))
            else:
                cart = str(row.get("cart_number") or "").strip()
                e = self._parse_float(row.get("empty_weight"))
                f = self._parse_float(row.get("full_weight"))

            if not cart and e == 0 and f == 0:
                continue
            result.append({
                "cart_number": cart,
                "is_bulk": row.get("is_bulk", False),
                "empty_weight": e,
                "full_weight": f,
            })
        return result

    def _collect_alayeshat(self):
        result = []
        for i, row in enumerate(self.alayeshat_rows):
            pid = row.get("product_id")

            if not pid and row.get("product_name"):
                for p in self.alayeshat_products:
                    if p[1] == row["product_name"]:
                        pid = p[0]
                        break

            if not pid:
                continue

            if not (self.completed_at or self.locked_at) or self.is_editing:
                widgets = self.alayeshat_widgets.get(i, {})
                e = self._parse_float(widgets["empty_weight"].text if "empty_weight" in widgets else row.get("empty_weight"))
                f = self._parse_float(widgets["full_weight"].text if "full_weight" in widgets else row.get("full_weight"))
            else:
                e = self._parse_float(row.get("empty_weight"))
                f = self._parse_float(row.get("full_weight"))

            if e == 0 and f == 0:
                continue

            result.append({
                "product_id": pid,
                "product_name": row.get("product_name", ""),
                "empty_weight": e,
                "full_weight": f,
            })
        return result

    # ======================================
    # ثبت اولیه
    # ======================================

    def on_submit(self, *args):
        plucked = self._collect_plucked()
        alayeshat = self._collect_alayeshat()
        live_weight = self._parse_float(self.live_weight_wrap.text)

        if not plucked:
            self._show_error("حداقل یک ردیف مرغ پرکنده لازم است.")
            return

        try:
            save_weighing_form(self.slaughter_id, plucked, alayeshat, live_weight)

            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE weighing_forms SET completed_at = ? WHERE slaughter_id = ?",
                (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), self.slaughter_id)
            )
            conn.commit()
            conn.close()

        except Exception as e:
            self._show_error(f"خطا در ثبت: {e}")
            return

        info_dialog(
            "ثبت موفق",
            "فرم توزین ثبت شد. اکنون می‌توانید آن را ویرایش، حذف یا نهایی کنید."
        )
        self.is_editing = False
        self.load_form()

    # ======================================
    # ویرایش
    # ======================================

    def on_edit(self, *args):
        if not self.completed_at:
            return

        from kivymd.app import MDApp
        app = MDApp.get_running_app()

        if not can_edit_form(self.completed_at, self.locked_at, app.current_user):
            info_dialog(
                "مهلت ویرایش تمام شده",
                "این فرم بیش از ۱۵ دقیقه پیش ثبت شده و دیگر قابل ویرایش نیست.",
            )
            return

        self.is_editing = True
        self.load_form()

    def on_save_edit(self, *args):
        plucked = self._collect_plucked()
        alayeshat = self._collect_alayeshat()
        live_weight = self._parse_float(self.live_weight_wrap.text)

        if not plucked:
            self._show_error("حداقل یک ردیف مرغ پرکنده لازم است.")
            return

        try:
            save_weighing_form(self.slaughter_id, plucked, alayeshat, live_weight)
        except Exception as e:
            self._show_error(f"خطا در ذخیره تغییرات: {e}")
            return

        info_dialog("ویرایش موفق", "تغییرات با موفقیت ذخیره شد.")
        self.is_editing = False
        self.load_form()

    def on_cancel_edit(self, *args):
        self.is_editing = False
        self.load_form()

    # ======================================
    # ثبت نهایی
    # ======================================

    def on_finalize(self, *args):
        confirm_dialog(
            title="ثبت نهایی فرم توزین",
            message=(
                "آیا از ثبت نهایی مطمئن هستید؟\n\n"
                "پس از ثبت نهایی، فرم کاملاً قفل شده و قابل ویرایش یا حذف نیست."
            ),
            confirm_text="تایید نهایی",
            cancel_text="لغو",
            confirm_color=COLOR_PRIMARY_DARK,
            on_confirm=self._do_finalize,
        )

    def _do_finalize(self):
        try:
            finalize_form("weighing_forms", "slaughter_id", self.slaughter_id)
        except Exception as e:
            self._show_error(f"خطا در ثبت نهایی: {e}")
            return

        info_dialog("تایید نهایی موفق", "فرم توزین قفل شد.")
        self.load_form()

    # ======================================
    # ویرایش ادمین
    # ======================================

    def on_admin_edit(self, *args):
        def do_unlock():
            try:
                admin_unlock_form("weighing_forms", "slaughter_id", self.slaughter_id)
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
                "پس از ویرایش، حتماً دوباره ثبت نهایی کنید."
            ),
            confirm_text="باز کن",
            cancel_text="لغو",
            confirm_color=COLOR_WARNING,
            on_confirm=do_unlock,
        )

    # ======================================
    # حذف کل فرم
    # ======================================

    def on_delete_entire_form(self, *args):
        def do_delete():
            try:
                conn = get_connection()
                cursor = conn.cursor()

                cursor.execute("SELECT form_id FROM weighing_forms WHERE slaughter_id = ?", (self.slaughter_id,))
                row = cursor.fetchone()
                if row:
                    form_id = row[0]
                    cursor.execute("DELETE FROM weighing_plucked_baskets WHERE row_id IN (SELECT row_id FROM weighing_plucked_rows WHERE form_id = ?)", (form_id,))
                    cursor.execute("DELETE FROM weighing_plucked_rows WHERE form_id = ?", (form_id,))
                    cursor.execute("DELETE FROM weighing_alayeshat_rows WHERE form_id = ?", (form_id,))

                    cursor.execute("""
                        UPDATE weighing_forms
                        SET total_full_weight = 0, total_net_weight = 0, loss_percent = 0, live_weight = 0,
                            completed_at = NULL, locked_at = NULL
                        WHERE form_id = ?
                    """, (form_id,))

                conn.commit()
                conn.close()

            except Exception as e:
                self._show_error(f"خطا در حذف: {e}")
                return

            info_dialog("حذف موفق", "فرم توزین پاک شد.")
            self.is_editing = False
            self.load_form()

        confirm_dialog(
            title="حذف فرم توزین",
            message="آیا از حذف کل اطلاعات این فرم مطمئن هستید؟\nاین عمل قابل بازگشت نیست.",
            confirm_text="حذف",
            cancel_text="لغو",
            confirm_color=COLOR_ERROR,
            on_confirm=do_delete,
        )

    # ======================================
    # خروجی‌ها
    # ======================================

    def on_export_pdf(self, *args):
        from ..helpers.file_dialog import ask_save_path, ask_open_after_save
        from ..helpers.file_utils import open_file
        from pdf_weighing import generate_weighing_pdf
        from datetime import datetime

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        si = self.slaughter_info
        safe_date = si["form_date"].replace("/", "-")
        default_name = f"weighing_{safe_date}_K{si['slaughter_number']}_{ts}"

        def do_save(filepath):
            try:
                result = generate_weighing_pdf(
                    slaughter_id=self.slaughter_id,
                    output_path=filepath,
                )
            except Exception as e:
                info_dialog("خطا در ساخت PDF", str(e))
                return

            info_dialog(
                "خروجی PDF ساخته شد",
                f"فایل ذخیره شد در:\n\n{result}",
            )

            ask_open_after_save(
                on_yes=lambda: open_file(result),
            )

        ask_save_path(
            title="ذخیره خروجی PDF",
            default_filename=default_name,
            file_extension=".pdf",
            on_save=do_save,
        )

    def on_export_csv(self, *args):
        from ..helpers.file_dialog import ask_save_path, ask_open_after_save
        from ..helpers.file_utils import open_file
        from pdf_weighing import generate_weighing_csv
        from datetime import datetime

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        si = self.slaughter_info
        safe_date = si["form_date"].replace("/", "-")
        default_name = f"weighing_{safe_date}_K{si['slaughter_number']}_{ts}"

        def do_save(filepath):
            try:
                result = generate_weighing_csv(
                    slaughter_id=self.slaughter_id,
                    output_path=filepath,
                )
            except Exception as e:
                info_dialog("خطا در ساخت Excel", str(e))
                return

            info_dialog(
                "خروجی Excel ساخته شد",
                f"فایل ذخیره شد در:\n\n{result}",
            )

            ask_open_after_save(
                on_yes=lambda: open_file(result),
            )

        ask_save_path(
            title="ذخیره خروجی Excel",
            default_filename=default_name,
            file_extension=".csv",
            on_save=do_save,
        )

    # ======================================
    # کمکی
    # ======================================

    def _show_error(self, text):
        self.msg_label.text = fa(text)
        self.msg_label.color = COLOR_ERROR

    def on_back(self, *args):
        self.manager.transition.direction = "right"
        self.manager.current = "slaughters_list"
