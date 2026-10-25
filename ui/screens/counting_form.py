# -*- coding: utf-8 -*-
"""
صفحه‌ی فرم ۱: آماری شمارش مرغ
"""

import textwrap

from kivy.metrics import dp, sp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.graphics import Color, RoundedRectangle
from kivy.clock import Clock

from kivymd.uix.screen import MDScreen
from kivymd.uix.card import MDCard

from ..helpers.fa import fa
from ..helpers.theme import (
    COLOR_BG, COLOR_PRIMARY, COLOR_PRIMARY_DARK, COLOR_GRAY,
    COLOR_ERROR, COLOR_SUCCESS, COLOR_TEXT, COLOR_WHITE,
    COLOR_WARNING, COLOR_LIGHT_GRAY,
)
from ..helpers.widgets import (
    fa_label, fa_button, spacer, fa_text_input, fa_section_title,
    fa_text_input_multiline,
)
from ..helpers.dialogs import confirm_dialog, info_dialog

from functions import (
    get_work_day_shamsi,
    get_counting_rows,
    get_counting_row,
    add_counting_row,
    update_counting_row,
    delete_counting_row,
    complete_counting_row,
    is_within_edit_window,
    can_edit_form,
    admin_unlock_form,
    finalize_form,
    user_can_edit_locked,
)
from database import get_connection
from datetime import datetime


class CountingFormScreen(MDScreen):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "counting_form"
        self.md_bg_color = COLOR_BG

        self.form_date = None
        self.day_name = None
        self.operator_id = None

        self.rows = []
        self.row_widgets = {}

        self.info_label = None
        self.rows_container = None
        self.msg_label = None

        self._clock_event = None

        self.build_ui()

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
            "بازگشت", size=14, height=40,
            bg_color=[0.6, 0.6, 0.6, 1],
            on_press=self.on_back,
        ))
        header.add_widget(fa_label(
            "فرم آماری شمارش مرغ",
            size=16, color=COLOR_PRIMARY_DARK,
            height=40, bold=True,
        ))
        root.add_widget(header)

        self.info_label = fa_label(
            "در حال بارگذاری...",
            size=12, color=COLOR_PRIMARY_DARK,
            height=30, bold=True,
        )
        root.add_widget(self.info_label)

        scroll = ScrollView()
        content = BoxLayout(
            orientation="vertical",
            padding=dp(10),
            spacing=dp(8),
            size_hint_y=None,
        )
        content.bind(minimum_height=content.setter("height"))

        content.add_widget(fa_section_title("ردیف‌های شمارش:"))

        self.rows_container = BoxLayout(
            orientation="vertical",
            spacing=dp(8),
            size_hint_y=None,
        )
        self.rows_container.bind(
            minimum_height=self.rows_container.setter("height")
        )
        content.add_widget(self.rows_container)

        content.add_widget(fa_button(
            "+ افزودن ردیف جدید",
            size=13, height=42,
            bg_color=COLOR_SUCCESS,
            on_press=self.on_add_row,
        ))

        content.add_widget(spacer(6))
        self.msg_label = fa_label(
            "", size=13, color=COLOR_ERROR, height=30,
        )
        content.add_widget(self.msg_label)

        content.add_widget(spacer(20))
        scroll.add_widget(content)
        root.add_widget(scroll)
        self.add_widget(root)

        self._clock_event = Clock.schedule_interval(self._auto_refresh, 30)

    def _auto_refresh(self, dt):
        try:
            if self.rows and any(r.get("completed_at") for r in self.rows):
                self.render_rows()
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

        if not app.current_user:
            self._show_error("خطا: نشست کاربر منقضی شده.")
            return

        self.operator_id = app.current_user["user_id"]

        current_row_id = getattr(app, "current_counting_row_id", None)

        if current_row_id:
            self.load_specific_row(current_row_id)
            app.current_counting_row_id = None
            return

        result = get_work_day_shamsi()
        if isinstance(result, tuple):
            self.form_date, self.day_name = result
        else:
            self.form_date = result
            self.day_name = ""

        self.info_label.text = fa(
            f"تاریخ روز کاری: {self.form_date} — {self.day_name}"
        )

        self.load_rows()

    def load_specific_row(self, row_id):
        row = get_counting_row(row_id)
        if not row:
            self._show_error("ردیف یافت نشد.")
            return

        self.form_date = row["form_date"]
        self.day_name = row["day_name"]

        self.info_label.text = fa(
            f"تاریخ روز کاری: {self.form_date} — {self.day_name}"
        )

        self.rows = [{
            "row_id": row["row_id"],
            "row_num": row["row_num"],
            "hook_count": str(row["hook_count"]) if row["hook_count"] else "",
            "waste": str(row["waste"]) if row["waste"] else "",
            "deaths": str(row["deaths"]) if row["deaths"] else "",
            "packed": str(row["packed"]) if row["packed"] else "",
            "pieces": str(row["pieces"]) if row["pieces"] else "",
            "notes": row["notes"] or "",
            "completed_at": row["completed_at"],
            "locked_at": row["locked_at"],
            "is_editing": False,
        }]

        self.render_rows()

    def load_rows(self):
        rows_data = get_counting_rows(self.form_date)

        self.rows = []
        for r in rows_data:
            self.rows.append({
                "row_id": r["row_id"],
                "row_num": r["row_num"],
                "hook_count": str(r["hook_count"]) if r["hook_count"] else "",
                "waste": str(r["waste"]) if r["waste"] else "",
                "deaths": str(r["deaths"]) if r["deaths"] else "",
                "packed": str(r["packed"]) if r["packed"] else "",
                "pieces": str(r["pieces"]) if r["pieces"] else "",
                "notes": r["notes"] or "",
                "completed_at": r.get("completed_at"),
                "locked_at": r.get("locked_at"),
                "is_editing": False,
            })

        if not self.rows:
            self.rows.append(self._empty_row())

        self.render_rows()

    def _empty_row(self):
        return {
            "row_id": None,
            "row_num": 0,
            "hook_count": "",
            "waste": "",
            "deaths": "",
            "packed": "",
            "pieces": "",
            "notes": "",
            "completed_at": None,
            "locked_at": None,
            "is_editing": False,
        }

    def render_rows(self):
        self.rows_container.clear_widgets()
        self.row_widgets = {}
        for i, row in enumerate(self.rows):
            self.rows_container.add_widget(self._make_row_card(i, row))

    def _make_row_card(self, index, row):
        from kivymd.app import MDApp

        is_completed = row.get("completed_at") is not None
        is_finalized = row.get("locked_at") is not None
        is_editing = row.get("is_editing", False)

        app = MDApp.get_running_app()
        can_edit_time = can_edit_form(
            row.get("completed_at"),
            row.get("locked_at"),
            app.current_user,
        )

        is_readonly = (is_completed or is_finalized) and not is_editing

        if is_finalized:
            bg_color = [0.85, 0.85, 0.85, 1]
        elif is_completed:
            bg_color = [0.92, 0.98, 0.92, 1]
        else:
            bg_color = [0.98, 0.98, 0.98, 1]

        notes_val = row.get("notes", "") or ""
        notes_lines = textwrap.wrap(notes_val, width=70) if notes_val else []
        notes_height = max(dp(40), len(notes_lines) * dp(22) + dp(20))

        if is_readonly:
            base_height = dp(260) + notes_height
        else:
            base_height = dp(380)

        card = MDCard(
            orientation="vertical",
            padding=dp(10),
            spacing=dp(6),
            size_hint=(1, None),
            height=base_height,
            elevation=1,
            radius=[dp(8)],
            md_bg_color=bg_color,
        )

        top_row = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(35),
            spacing=dp(4),
        )
        top_row.add_widget(fa_label(
            f"ردیف {index + 1}",
            size=13, color=COLOR_PRIMARY_DARK,
            height=35, bold=True, halign="right",
        ))

        if is_finalized:
            top_row.add_widget(fa_label(
                "[ تایید نهایی شده - قفل ]",
                size=12, color=COLOR_SUCCESS,
                height=35, bold=True, halign="left",
            ))
        elif is_completed:
            top_row.add_widget(fa_label(
                "[ ثبت شده - منتظر تایید ]",
                size=12, color=COLOR_WARNING,
                height=35, bold=True, halign="left",
            ))
        card.add_widget(top_row)

        labels1 = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(20),
            spacing=dp(4),
        )
        for lbl in ["پای قلاب", "ضایعات", "تلفات", "پرکنده", "قطعه"]:
            labels1.add_widget(fa_label(
                lbl, size=10, color=COLOR_PRIMARY_DARK,
                height=20, bold=True, halign="center",
            ))
        card.add_widget(labels1)

        fields1 = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(45),
            spacing=dp(4),
        )

        self.row_widgets[index] = {}

        for field in ["hook_count", "waste", "deaths", "packed", "pieces"]:
            val = str(row.get(field, ""))
            if is_readonly:
                lbl_box = BoxLayout(size_hint=(1, 1), padding=(dp(4), dp(4)))
                with lbl_box.canvas.before:
                    Color(0.92, 0.92, 0.92, 1)
                    lbl_box.bg = RoundedRectangle(pos=lbl_box.pos, size=lbl_box.size, radius=[dp(6)])
                lbl_box.bind(pos=lambda s, v: setattr(s.bg, 'pos', v), size=lambda s, v: setattr(s.bg, 'size', v))
                lbl_box.add_widget(fa_label(text=val if val else "—", size=13, color=COLOR_TEXT, height=45, halign="center"))
                fields1.add_widget(lbl_box)
            else:
                wrap = fa_text_input(hint_text="", text=val, input_filter="int", height=45)
                wrap.hidden.bind(text=lambda inst, val, i=index: self._update_calc_row(i))
                self.row_widgets[index][field] = wrap
                fields1.add_widget(wrap)
        card.add_widget(fields1)

        calc_row = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(45),
            spacing=dp(10),
        )

        self.row_widgets[index]["packed_lbl"] = fa_label(
            "", size=12, color=COLOR_PRIMARY_DARK,
            height=45, bold=True, halign="right",
        )
        calc_row.add_widget(self.row_widgets[index]["packed_lbl"])

        self.row_widgets[index]["diff_lbl"] = fa_label(
            "", size=12,
            height=45, bold=True, halign="left",
        )
        calc_row.add_widget(self.row_widgets[index]["diff_lbl"])
        card.add_widget(calc_row)

        if is_readonly:
            notes_box = BoxLayout(
                orientation="vertical",
                size_hint_y=None,
                padding=(dp(10), dp(10)),
                spacing=dp(2),
            )
            notes_box.bind(minimum_height=notes_box.setter("height"))

            if notes_lines:
                for line in notes_lines:
                    line_lbl = Label(
                        text=fa(line),
                        font_name="Vazir",
                        font_size=sp(12),
                        color=COLOR_GRAY,
                        halign="right",
                        valign="middle",
                        size_hint_y=None,
                        height=dp(22),
                    )
                    line_lbl.bind(size=lambda s, v: setattr(s, "text_size", v))
                    notes_box.add_widget(line_lbl)
            else:
                empty_lbl = Label(
                    text=fa("بدون توضیحات"),
                    font_name="Vazir",
                    font_size=sp(12),
                    color=COLOR_GRAY,
                    halign="right",
                    size_hint_y=None,
                    height=dp(22),
                )
                empty_lbl.bind(size=lambda s, v: setattr(s, "text_size", v))
                notes_box.add_widget(empty_lbl)

            card.add_widget(notes_box)
        else:
            notes_input = fa_text_input_multiline(
                hint_text="توضیحات (اختیاری)",
                text=notes_val,
                height=120,
                min_height=120,
            )
            self.row_widgets[index]["notes"] = notes_input
            card.add_widget(notes_input)

        btn_row = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(42),
            spacing=dp(4),
        )

        if not is_completed:
            btn_row.add_widget(fa_button(
                "ثبت", size=13, height=42,
                bg_color=COLOR_SUCCESS,
                on_press=lambda x, i=index: self.on_submit(i),
            ))
            if len(self.rows) > 1:
                btn_row.add_widget(fa_button(
                    "حذف", size=13, height=42,
                    bg_color=COLOR_ERROR,
                    on_press=lambda x, i=index: self.on_delete_row(i),
                ))

        elif is_completed and not is_finalized and is_editing:
            btn_row.add_widget(fa_button(
                "ذخیره تغییرات", size=13, height=42,
                bg_color=COLOR_PRIMARY,
                on_press=lambda x, i=index: self.on_save_edit(i),
            ))
            btn_row.add_widget(fa_button(
                "انصراف", size=13, height=42,
                bg_color=[0.7, 0.7, 0.7, 1],
                on_press=lambda x, i=index: self.on_cancel_edit(i),
            ))

        elif is_completed and not is_finalized and not is_editing:
            if can_edit_time:
                btn_row.add_widget(fa_button(
                    "ویرایش", size=12, height=42,
                    bg_color=COLOR_WARNING,
                    on_press=lambda x, i=index: self.on_start_edit(i),
                ))
                btn_row.add_widget(fa_button(
                    "حذف", size=12, height=42,
                    bg_color=COLOR_ERROR,
                    on_press=lambda x, i=index: self.on_delete_row(i),
                ))
            else:
                btn_row.add_widget(fa_label(
                    "مهلت ویرایش/حذف تمام شده", size=11, color=COLOR_GRAY,
                    height=42, halign="center",
                ))

            btn_row.add_widget(fa_button(
                "ثبت نهایی", size=12, height=42,
                bg_color=COLOR_PRIMARY_DARK,
                on_press=lambda x, i=index: self.on_finalize(i),
            ))

        elif is_finalized:
            can_unlock = user_can_edit_locked(app.current_user)
            within_window = is_within_edit_window(row.get("locked_at"), 15)
            if can_unlock and within_window:
                btn_row.add_widget(fa_button(
                    "ویرایش (ادمین)", size=12, height=42,
                    bg_color=COLOR_WARNING,
                    on_press=lambda x, i=index: self.on_admin_edit(i),
                ))
            else:
                btn_row.add_widget(fa_label(
                    "این ردیف تایید نهایی شده و قفل است.", size=11, color=COLOR_GRAY,
                    height=42, halign="center",
                ))

        card.add_widget(btn_row)

        self._update_calc_row(index)
        return card

    def _parse_int(self, val):
        if val is None or val == "":
            return 0
        try:
            return int(float(val))
        except (ValueError, TypeError):
            return 0

    def _update_calc_row(self, index):
        if index not in self.row_widgets:
            return

        widgets = self.row_widgets[index]

        if "hook_count" in widgets:
            hc_txt = widgets["hook_count"].text.strip()
            w_txt = widgets["waste"].text.strip()
            d_txt = widgets["deaths"].text.strip()
            p_txt = widgets["packed"].text.strip()
            pieces_txt = widgets["pieces"].text.strip()

            is_complete = all([hc_txt, w_txt, d_txt, p_txt, pieces_txt])

            hc = self._parse_int(hc_txt)
            w = self._parse_int(w_txt)
            d = self._parse_int(d_txt)
            p = self._parse_int(p_txt)
            pieces = self._parse_int(pieces_txt)
        else:
            row = self.rows[index]
            hc = self._parse_int(row.get("hook_count"))
            w = self._parse_int(row.get("waste"))
            d = self._parse_int(row.get("deaths"))
            p = self._parse_int(row.get("packed"))
            pieces = self._parse_int(row.get("pieces"))
            is_complete = True

        if not is_complete:
            if "packed_lbl" in widgets:
                widgets["packed_lbl"].text = fa("بارگیری شده در ماشین: ---")
            if "diff_lbl" in widgets:
                widgets["diff_lbl"].text = fa("(لطفاً همه فیلدها را پر کنید)")
                widgets["diff_lbl"].color = COLOR_GRAY
            return

        packed_in_machine = hc + d
        diff = hc - w - pieces - p

        if diff == 0:
            diff_text = "بدون مغایرت"
            diff_color = COLOR_SUCCESS
        elif diff > 0:
            diff_text = f"مغایرت: {diff:+} (کمبود)"
            diff_color = COLOR_ERROR
        else:
            diff_text = f"مغایرت: {diff:+} (اضافه)"
            diff_color = COLOR_ERROR

        if "packed_lbl" in widgets:
            widgets["packed_lbl"].text = fa(f"بارگیری شده در ماشین: {packed_in_machine}")
        if "diff_lbl" in widgets:
            widgets["diff_lbl"].text = fa(diff_text)
            widgets["diff_lbl"].color = diff_color

    def on_add_row(self, *args):
        self.rows.append(self._empty_row())
        self.render_rows()

    def on_delete_row(self, index):
        if index >= len(self.rows):
            return
        row = self.rows[index]

        def do_delete():
            if row.get("row_id"):
                try:
                    delete_counting_row(row["row_id"])
                except Exception as e:
                    self._show_error(f"خطا در حذف: {e}")
                    return
            self.rows.pop(index)
            if not self.rows:
                self.rows.append(self._empty_row())
            self.load_rows()
            info_dialog("حذف موفق", "ردیف با موفقیت حذف شد.")

        confirm_dialog(
            title="حذف ردیف",
            message="آیا از حذف این ردیف مطمئن هستید؟\nاین عمل قابل بازگشت نیست.",
            confirm_text="حذف",
            cancel_text="لغو",
            confirm_color=COLOR_ERROR,
            on_confirm=do_delete,
        )

    def on_submit(self, index):
        if index >= len(self.rows):
            return

        widgets = self.row_widgets[index]
        data = {
            "hook_count": self._parse_int(widgets["hook_count"].text),
            "waste": self._parse_int(widgets["waste"].text),
            "deaths": self._parse_int(widgets["deaths"].text),
            "packed": self._parse_int(widgets["packed"].text),
            "pieces": self._parse_int(widgets["pieces"].text),
            "notes": widgets["notes"].text,
        }

        if data["hook_count"] == 0 and data["packed"] == 0:
            self._show_error("حداقل پای قلاب یا پرکنده را وارد کنید.")
            return

        try:
            row_id = self.rows[index].get("row_id")
            if not row_id:
                row_id = add_counting_row(
                    form_date=self.form_date,
                    day_name=self.day_name,
                    operator_id=self.operator_id,
                    data=data,
                )
            else:
                update_counting_row(row_id, data)

            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE counting_rows SET completed_at = ? WHERE row_id = ?",
                           (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), row_id))
            conn.commit()
            conn.close()

        except Exception as e:
            self._show_error(f"خطا در ثبت: {e}")
            return

        info_dialog("ثبت موفق", "ردیف با موفقیت ثبت شد. اکنون می‌توانید آن را ویرایش، حذف یا نهایی کنید.")
        self.load_rows()

    def on_start_edit(self, index):
        if index < len(self.rows):
            self.rows[index]["is_editing"] = True
            self.render_rows()

    def on_cancel_edit(self, index):
        if index < len(self.rows):
            self.rows[index]["is_editing"] = False
            self.load_rows()

    def on_save_edit(self, index):
        if index >= len(self.rows):
            return
        widgets = self.row_widgets[index]

        data = {
            "hook_count": self._parse_int(widgets["hook_count"].text),
            "waste": self._parse_int(widgets["waste"].text),
            "deaths": self._parse_int(widgets["deaths"].text),
            "packed": self._parse_int(widgets["packed"].text),
            "pieces": self._parse_int(widgets["pieces"].text),
            "notes": widgets["notes"].text,
        }

        row_id = self.rows[index].get("row_id")

        try:
            update_counting_row(row_id, data)
        except Exception as e:
            self._show_error(f"خطا در ذخیره تغییرات: {e}")
            return

        info_dialog("ویرایش موفق", "تغییرات با موفقیت ذخیره شد.")
        self.load_rows()

    def on_finalize(self, index):
        if index >= len(self.rows):
            return

        confirm_dialog(
            title=f"ثبت نهایی ردیف {index + 1}",
            message=(
                "آیا از ثبت نهایی مطمئن هستید؟\n\n"
                "پس از این مرحله، ردیف کاملاً قفل شده و قابل ویرایش یا حذف نیست.\n"
                "یک کشتار جدید نیز ایجاد می‌شود."
            ),
            confirm_text="تایید نهایی",
            cancel_text="لغو",
            confirm_color=COLOR_PRIMARY_DARK,
            on_confirm=lambda: self._do_finalize(index),
        )

    def _do_finalize(self, index):
        row = self.rows[index]
        row_id = row.get("row_id")

        try:
            slaughter_id = complete_counting_row(
                row_id=row_id,
                operator_id=self.operator_id,
            )
            finalize_form("counting_rows", "row_id", row_id)
        except Exception as e:
            self._show_error(f"خطا در ثبت نهایی: {e}")
            return

        info_dialog("تایید نهایی موفق", f"ردیف {index + 1} قفل شد و کشتار #{slaughter_id} ایجاد گردید.")
        self.load_rows()

    def on_admin_edit(self, index):
        row = self.rows[index]
        row_id = row.get("row_id")

        def do_unlock():
            try:
                admin_unlock_form("counting_rows", "row_id", row_id)
                self.load_rows()
                info_dialog(
                    "انجام شد",
                    "قفل باز شد. حالا ۱۵ دقیقه فرصت ویرایش دارید.\n"
                    "بعد از ۱۵ دقیقه، دوباره قفل می‌شود."
                )
            except Exception as e:
                info_dialog("خطا", f"باز کردن قفل ناموفق:\n{e}")

        confirm_dialog(
            title="ویرایش ردیف قفل‌شده",
            message=(
                "آیا از باز کردن قفل این ردیف مطمئن هستید؟\n\n"
                "⚠️ پس از باز کردن قفل، ۱۵ دقیقه فرصت ویرایش دارید.\n"
                "بعد از آن، دوباره قفل می‌شود."
            ),
            confirm_text="باز کن",
            cancel_text="لغو",
            confirm_color=COLOR_WARNING,
            on_confirm=do_unlock,
        )

    def _update_actions(self):
        pass

    def _show_error(self, text):
        self.msg_label.text = fa(text)
        self.msg_label.color = COLOR_ERROR

    def on_back(self, *args):
        self.manager.transition.direction = "right"
        self.manager.current = "slaughters_list"
