# -*- coding: utf-8 -*-
"""
صفحه‌ی لیست کشتارهای امروز
"""

from datetime import datetime

from kivy.metrics import dp, sp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label

from kivymd.uix.screen import MDScreen
from kivymd.uix.card import MDCard

from ..helpers.fa import fa
from ..helpers.theme import (
    COLOR_BG, COLOR_PRIMARY, COLOR_PRIMARY_DARK, COLOR_GRAY,
    COLOR_ERROR, COLOR_SUCCESS, COLOR_TEXT, COLOR_WHITE,
    COLOR_WARNING,
)
from ..helpers.widgets import fa_label, fa_button, spacer
from ..helpers.dialogs import confirm_dialog, info_dialog

from functions import (
    get_work_day_shamsi,
    get_slaughters_by_date,
    get_slaughter,
    delete_slaughter,
    count_receipts,
    count_invoices,
    admin_unlock_form,
)


class SlaughtersListScreen(MDScreen):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "slaughters_list"
        self.md_bg_color = COLOR_BG

        self.current_form_date = ""
        self.current_day_name = ""
        self.is_daily_form_active = False
        self.is_invoice_active = False

        self.date_label = None
        self.list_container = None
        self.daily_form_btn = None
        self.daily_form_msg = None
        self.invoice_btn = None
        self.invoice_msg = None

        self.build_ui()

    # ======================================
    # ساخت UI
    # ======================================

    def build_ui(self):

        root = BoxLayout(orientation="vertical")

        # ---------- هدر ----------
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
            "کشتارهای امروز",
            size=17,
            color=COLOR_PRIMARY_DARK,
            height=40,
            bold=True,
        ))
        root.add_widget(header)

        # ---------- روز کاری ----------
        self.date_label = fa_label(
            "در حال بارگذاری...",
            size=14,
            color=COLOR_PRIMARY_DARK,
            height=35,
            bold=True,
        )
        root.add_widget(self.date_label)

        # ---------- دکمه‌ی فرم گزارش روزانه ----------
        daily_form_bar = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(55),
            padding=[dp(10), dp(5)],
            spacing=dp(8),
        )

        self.daily_form_btn = fa_button(
            "فرم گزارش روزانه (غير فعال)",
            size=14,
            height=45,
            bg_color=[0.7, 0.7, 0.7, 1],
            on_press=self.open_daily_form,
        )
        daily_form_bar.add_widget(self.daily_form_btn)
        root.add_widget(daily_form_bar)

        # ---------- پیام راهنما ----------
        self.daily_form_msg = fa_label(
            "ابتدا باید تمام کشتارها ثبت شوند.",
            size=12,
            color=COLOR_ERROR,
            height=25,
        )
        root.add_widget(self.daily_form_msg)

        # ---------- دکمه‌ی صورتحساب روزانه ----------
        invoice_bar = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(55),
            padding=[dp(10), dp(5)],
            spacing=dp(8),
        )

        self.invoice_btn = fa_button(
            "صورتحساب کشتار روزانه (غير فعال)",
            size=14,
            height=45,
            bg_color=[0.7, 0.7, 0.7, 1],
            on_press=self.open_invoices,
        )
        invoice_bar.add_widget(self.invoice_btn)
        root.add_widget(invoice_bar)

        # ---------- پیام راهنما ----------
        self.invoice_msg = fa_label(
            "با تکمیل فرم‌های توزین فعال می‌شود",
            size=12,
            color=COLOR_ERROR,
            height=25,
        )
        root.add_widget(self.invoice_msg)

        # ---------- دکمه‌ی افزودن کشتار ----------
        add_bar = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(55),
            padding=[dp(10), dp(5)],
            spacing=dp(8),
        )
        add_bar.add_widget(fa_button(
            "افزودن کشتار جدید",
            size=15,
            height=45,
            bg_color=COLOR_SUCCESS,
            on_press=self.on_add_slaughter,
        ))
        root.add_widget(add_bar)

        # ---------- لیست ----------
        scroll = ScrollView()

        self.list_container = BoxLayout(
            orientation="vertical",
            padding=dp(10),
            spacing=dp(8),
            size_hint_y=None,
        )
        self.list_container.bind(
            minimum_height=self.list_container.setter("height")
        )

        scroll.add_widget(self.list_container)
        root.add_widget(scroll)

        self.add_widget(root)

    # ======================================
    # بارگذاری
    # ======================================

    def on_pre_enter(self, *args):
        shamsi, day_name = get_work_day_shamsi()
        self.current_form_date = shamsi
        self.current_day_name = day_name

        self.date_label.text = fa(
            f"روز کاری: {day_name} {shamsi}"
        )

        self.refresh_list()

    def refresh_list(self):

        self.list_container.clear_widgets()

        try:
            slaughters = get_slaughters_by_date(self.current_form_date)
        except Exception as e:
            self.list_container.add_widget(fa_label(
                f"خطا: {e}",
                size=13,
                color=COLOR_ERROR,
                height=50,
            ))
            self._update_daily_btn_state(False)
            self._update_invoice_btn_state(False)
            return

        if not slaughters:
            empty_lbl = Label(
                text=fa("هيچ کشتاري براي امروز ثبت نشده است"),
                font_name="Vazir",
                font_size=sp(12),
                color=COLOR_GRAY,
                halign="center",
                valign="middle",
                size_hint_y=None,
                height=dp(15),
            )
            empty_lbl.bind(size=lambda s, v: setattr(s, "text_size", v))
            self.list_container.add_widget(empty_lbl)

            self._update_daily_btn_state(False)
            self._update_invoice_btn_state(False)
            return

        valid_slaughters = [s for s in slaughters if not s.get("is_pending", False)]

        all_weighing_completed = False
        if valid_slaughters:
            all_weighing_completed = all(
                s.get("weighing_completed", False)
                for s in valid_slaughters
            )

        self._update_daily_btn_state(all_weighing_completed)
        self._update_invoice_btn_state(all_weighing_completed)

        for s in slaughters:
            self.list_container.add_widget(self._make_card(s))

    def _update_daily_btn_state(self, is_enabled):
        self.is_daily_form_active = is_enabled

        if is_enabled:
            self.daily_form_btn.text = fa("فرم گزارش روزانه")
            self.daily_form_btn.background_color = COLOR_PRIMARY_DARK
            self.daily_form_msg.text = ""
        else:
            self.daily_form_btn.text = fa("فرم گزارش روزانه (غير فعال)")
            self.daily_form_btn.background_color = [0.6, 0.6, 0.6, 1]
            self.daily_form_msg.text = fa("با تکمیل تمام فرم‌های کشتار فعال می‌شود")

    def _update_invoice_btn_state(self, is_enabled):
        self.is_invoice_active = is_enabled

        if is_enabled:
            self.invoice_btn.text = fa("صورتحساب کشتار روزانه")
            self.invoice_btn.background_color = COLOR_SUCCESS
            self.invoice_msg.text = ""
        else:
            self.invoice_btn.text = fa("صورتحساب کشتار روزانه (غير فعال)")
            self.invoice_btn.background_color = [0.6, 0.6, 0.6, 1]
            self.invoice_msg.text = fa("با تکمیل فرم‌های توزین فعال می‌شود")

    # ======================================
    # کارت کشتار
    # ======================================

    def _make_card(self, s):
        is_pending = s.get("is_pending", False)

        if is_pending:
            return self._make_pending_card(s)
        return self._make_full_card(s)

    def _make_pending_card(self, s):
        card = MDCard(
            orientation="vertical",
            padding=dp(12),
            spacing=dp(6),
            size_hint=(1, None),
            height=dp(140),
            elevation=1,
            radius=[dp(10)],
            md_bg_color=[0.98, 0.98, 0.92, 1],
        )

        row1 = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(30),
        )
        row1.add_widget(fa_label(
            "ثبت موقت (منتظر تایید نهایی)",
            size=14,
            color=COLOR_WARNING,
            height=30,
            bold=True,
            halign="left",
        ))
        row1.add_widget(fa_label(
            f"ردیف {s['counting_row_id']}",
            size=12,
            color=COLOR_GRAY,
            height=30,
            halign="right",
        ))
        card.add_widget(row1)

        row2 = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(25),
        )
        row2.add_widget(fa_label(
            f"پای قلاب: {s['hook_count']:,}",
            size=12,
            color=COLOR_TEXT,
            height=25,
            halign="left",
        ))
        row2.add_widget(fa_label(
            f"بسته‌بندی: {s['packed']:,}",
            size=12,
            color=COLOR_TEXT,
            height=25,
            halign="right",
        ))
        card.add_widget(row2)

        row3 = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(40),
            spacing=dp(6),
        )
        row3.add_widget(fa_button(
            "ویرایش (بازگشت به فرم شمارش)",
            size=12,
            height=35,
            bg_color=COLOR_WARNING,
            on_press=lambda x: self.open_counting_form(
                s["counting_row_id"]
            ),
        ))
        card.add_widget(row3)

        return card

    # ======================================
    # وضعیت فرم شمارش
    # ======================================

    def _get_counting_status_text(self, s):
        if s.get("counting_locked_at"):
            return {
                "text": "فرم شمارش: تایید نهایی شده",
                "color": COLOR_SUCCESS,
            }
        elif s.get("counting_completed_at"):
            return {
                "text": "فرم شمارش: ثبت شده - منتظر تایید",
                "color": COLOR_WARNING,
            }
        else:
            return {
                "text": "فرم شمارش: در حال ثبت",
                "color": COLOR_GRAY,
            }

    def _get_weighing_status_text(self, s):
        if s.get("weighing_locked"):
            return {
                "text": "فرم توزین: تایید نهایی شده",
                "color": COLOR_SUCCESS,
            }
        elif s.get("weighing_completed"):
            return {
                "text": "فرم توزین: ثبت شده - منتظر تایید",
                "color": COLOR_WARNING,
            }
        else:
            return {
                "text": "فرم توزین: در انتظار",
                "color": COLOR_WARNING,
            }

    # ======================================
    # کارت کشتار کامل
    # ======================================

    def _make_full_card(self, s):

        card = MDCard(
            orientation="vertical",
            padding=dp(12),
            spacing=dp(6),
            size_hint=(1, None),
            elevation=2,
            radius=[dp(10)],
            md_bg_color=[1, 1, 1, 1],
        )
        card.bind(minimum_height=card.setter("height"))

        # ── ردیف ۱: شماره کشتار + پای قلاب ──
        row1 = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(30),
        )
        row1.add_widget(fa_label(
            f"کشتار #{s['slaughter_number']}",
            size=16,
            color=COLOR_PRIMARY,
            height=30,
            bold=True,
            halign="left",
        ))
        row1.add_widget(fa_label(
            f"پای قلاب: {s['hook_count']:,}",
            size=13,
            color=COLOR_TEXT,
            height=30,
            halign="right",
        ))
        card.add_widget(row1)

        # ── ردیف ۲: بسته‌بندی + درصد افت ──
        row2 = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(25),
        )
        row2.add_widget(fa_label(
            f"بسته‌بندی: {s['packed']:,}",
            size=12,
            color=COLOR_GRAY,
            height=25,
            halign="left",
        ))
        if s["loss_percent"]:
            row2.add_widget(fa_label(
                f"درصد افت: {s['loss_percent']:.2f}%",
                size=12,
                color=COLOR_PRIMARY_DARK,
                height=25,
                halign="right",
            ))
        card.add_widget(row2)

        # ── ردیف ۳: وضعیت فرم شمارش ──
        row3 = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(25),
        )
        counting_status = self._get_counting_status_text(s)
        row3.add_widget(fa_label(
            counting_status["text"],
            size=12,
            color=counting_status["color"],
            height=25,
            bold=True,
            halign="right",
        ))
        card.add_widget(row3)

        # ── ردیف ۴: وضعیت فرم توزین ──
        row4 = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(25),
        )
        weighing_status = self._get_weighing_status_text(s)
        row4.add_widget(fa_label(
            weighing_status["text"],
            size=12,
            color=weighing_status["color"],
            height=25,
            bold=True,
            halign="right",
        ))
        card.add_widget(row4)

        # ── فرم شمارش ──
        row_c_form = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(40),
            spacing=dp(4),
        )
        row_c_form.add_widget(fa_button(
            "فرم شمارش",
            size=11,
            height=35,
            bg_color=COLOR_PRIMARY,
            on_press=lambda x, rid=s["counting_row_id"]:
                self.open_counting_form(rid),
        ))
        row_c_form.add_widget(fa_button(
            "PDF شمارش",
            size=10,
            height=35,
            bg_color=COLOR_PRIMARY_DARK,
            on_press=lambda x, s=s: self.export_counting_pdf(s),
        ))
        row_c_form.add_widget(fa_button(
            "Excel شمارش",
            size=10,
            height=35,
            bg_color=COLOR_SUCCESS,
            on_press=lambda x, s=s: self.export_counting_excel(s),
        ))
        card.add_widget(row_c_form)

        # ── فرم توزین ──
        row_w_form = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(40),
            spacing=dp(4),
        )
        row_w_form.add_widget(fa_button(
            "فرم توزین",
            size=11,
            height=35,
            bg_color=COLOR_PRIMARY,
            on_press=lambda x, sid=s["slaughter_id"]:
                self.open_weighing(sid),
        ))

        if s["weighing_completed"]:
            row_w_form.add_widget(fa_button(
                "PDF توزین",
                size=10,
                height=35,
                bg_color=COLOR_PRIMARY_DARK,
                on_press=lambda x, s=s: self.export_weighing_pdf(s),
            ))
            row_w_form.add_widget(fa_button(
                "Excel توزین",
                size=10,
                height=35,
                bg_color=COLOR_SUCCESS,
                on_press=lambda x, s=s: self.export_weighing_excel(s),
            ))
        card.add_widget(row_w_form)

        # ── قبض‌های باسکول ──
        row_receipts = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(40),
            spacing=dp(4),
        )

        try:
            receipt_count = count_receipts(s["slaughter_id"])
        except Exception:
            receipt_count = 0

        row_receipts.add_widget(fa_button(
            f"قبض‌های باسکول ({receipt_count})",
            size=11,
            height=35,
            bg_color=COLOR_WARNING,
            on_press=lambda x, sid=s["slaughter_id"]:
                self.open_receipts(sid),
        ))
        card.add_widget(row_receipts)

        # ── دکمه‌های ادمین ──
        from kivymd.app import MDApp
        app = MDApp.get_running_app()
        user = app.current_user
        is_admin = user and str(user.get("role", "")).strip().lower() == "admin"

        if is_admin:
            admin_row = BoxLayout(
                orientation="horizontal",
                size_hint_y=None,
                height=dp(40),
                spacing=dp(4),
            )
            admin_row.add_widget(fa_button(
                "باز کردن قفل فرم‌ها",
                size=10, height=35,
                bg_color=COLOR_WARNING,
                on_press=lambda x, s=s: self.on_admin_unlock_all(s),
            ))
            admin_row.add_widget(fa_button(
                "حذف کامل کشتار",
                size=10, height=35,
                bg_color=COLOR_ERROR,
                on_press=lambda x, s=s: self.on_admin_delete_slaughter(s),
            ))
            card.add_widget(admin_row)

        return card

    # ======================================
    # باز کردن قفل همه‌ی فرم‌های یک کشتار (ادمین)
    # ======================================

    def on_admin_unlock_all(self, s):
        """
        باز کردن قفل همه‌ی فرم‌های این کشتار:
        - فرم شمارش (counting_rows)
        - فرم توزین (weighing_forms)
        - قبض‌ها (slaughter_receipts)

        با استفاده از admin_unlock_form که هم locked_at = NULL
        و هم completed_at = زمان حال (ریست مهلت ۱۵ دقیقه) را انجام می‌دهد.
        """
        def do_unlock():
            errors = []
            try:
                admin_unlock_form("counting_rows", "row_id", s["counting_row_id"])
            except Exception as e:
                errors.append(f"شمارش: {e}")
            try:
                admin_unlock_form("weighing_forms", "slaughter_id", s["slaughter_id"])
            except Exception as e:
                errors.append(f"توزین: {e}")
            try:
                admin_unlock_form("slaughter_receipts", "slaughter_id", s["slaughter_id"])
            except Exception as e:
                errors.append(f"قبض‌ها: {e}")

            if errors:
                info_dialog("خطا در باز کردن قفل", "\n".join(errors))
            else:
                info_dialog(
                    "انجام شد",
                    "قفل فرم‌های این کشتار باز شد.\n"
                    "حالا ۱۵ دقیقه فرصت ویرایش دارید.\n"
                    "بعد از ۱۵ دقیقه، دوباره قفل می‌شود."
                )
            self.refresh_list()

        confirm_dialog(
            title="باز کردن قفل فرم‌ها",
            message=(
                f"آیا از باز کردن قفل همه‌ی فرم‌های کشتار #{s['slaughter_number']} مطمئن هستید؟\n\n"
                "⚠️ پس از باز کردن قفل، ۱۵ دقیقه فرصت ویرایش دارید.\n"
                "بعد از آن، دوباره قفل می‌شود."
            ),
            confirm_text="باز کن",
            cancel_text="لغو",
            confirm_color=COLOR_WARNING,
            on_confirm=do_unlock,
        )

    def on_admin_delete_slaughter(self, s):
        """
        حذف کامل کشتار با تمام وابستگی‌ها (دو مرحله تأیید).
        فقط برای ادمین.
        """
        from database import delete_slaughter_full

        def confirm2():
            def do_delete():
                try:
                    delete_slaughter_full(s["slaughter_id"])
                    info_dialog("حذف موفق", f"کشتار #{s['slaughter_number']} با همه‌ی وابستگی‌ها حذف شد.")
                    self.refresh_list()
                except Exception as e:
                    info_dialog("خطا", f"حذف ناموفق:\n{e}")

            confirm_dialog(
                title="تأیید نهایی حذف",
                message=(
                    f"⚠️ این آخرین هشدار است!\n\n"
                    f"کشتار #{s['slaughter_number']} به‌طور کامل حذف می‌شود.\n"
                    f"همه‌ی فرم‌ها، قبض‌ها و عکس‌ها پاک می‌شوند.\n\n"
                    f"آیا مطمئن هستید؟"
                ),
                confirm_text="بله، حذف کن",
                cancel_text="لغو",
                confirm_color=COLOR_ERROR,
                on_confirm=do_delete,
            )

        confirm_dialog(
            title="حذف کشتار",
            message=(
                f"آیا از حذف کشتار #{s['slaughter_number']} مطمئن هستید؟\n\n"
                f"این عمل قابل بازگشت نیست."
            ),
            confirm_text="ادامه",
            cancel_text="لغو",
            confirm_color=COLOR_ERROR,
            on_confirm=confirm2,
        )

    # ======================================
    # ناوبری
    # ======================================

    def open_daily_form(self, *args):
        if not self.is_daily_form_active:
            info_dialog("دسترسی غیرفعال", "لطفاً ابتدا تمام فرم‌های توزین کشتارها را تکمیل کنید.")
            return

        self.manager.transition.direction = "left"
        self.manager.current = "daily_form"

    def open_invoices(self, *args):
        if not self.is_invoice_active:
            info_dialog("دسترسی غیرفعال", "لطفاً ابتدا تمام فرم‌های توزین کشتارها را تکمیل کنید.")
            return

        self.manager.transition.direction = "left"
        self.manager.current = "invoices"

    def on_add_slaughter(self, *args):
        from kivymd.app import MDApp
        app = MDApp.get_running_app()
        app.current_slaughter_id = None
        app.current_counting_row_id = None
        self.manager.transition.direction = "left"
        self.manager.current = "counting_form"

    def open_counting_form(self, row_id):
        from kivymd.app import MDApp
        app = MDApp.get_running_app()
        app.current_counting_row_id = row_id
        app.current_slaughter_id = None

        self.manager.transition.direction = "left"
        self.manager.current = "counting_form"

    def open_weighing(self, slaughter_id):
        from kivymd.app import MDApp
        app = MDApp.get_running_app()
        app.current_slaughter_id = slaughter_id

        self.manager.transition.direction = "left"
        self.manager.current = "weighing_form"

    def open_receipts(self, slaughter_id):
        from kivymd.app import MDApp
        app = MDApp.get_running_app()
        app.current_slaughter_id = slaughter_id

        self.manager.transition.direction = "left"
        self.manager.current = "receipts"

    # ======================================
    # خروجی‌های فرم شمارش
    # ======================================

    def export_counting_pdf(self, s):
        from ..helpers.file_dialog import ask_save_path, ask_open_after_save
        from ..helpers.file_utils import open_file
        from pdf_counting import generate_counting_pdf
        from datetime import datetime

        form_date = s.get("form_date") or self.current_form_date
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_date = form_date.replace("/", "-")
        default_name = f"counting_{safe_date}_{ts}"

        def do_save(filepath):
            try:
                result = generate_counting_pdf(
                    form_date=form_date,
                    output_path=filepath,
                )
            except Exception as e:
                info_dialog("خطا در ساخت PDF", str(e))
                return
            info_dialog(
                "خروجی PDF ساخته شد",
                f"فایل ذخیره شد در:\n\n{result}",
            )
            ask_open_after_save(on_yes=lambda: open_file(result))

        ask_save_path(
            title="ذخیره خروجی PDF (شمارش)",
            default_filename=default_name,
            file_extension=".pdf",
            on_save=do_save,
        )

    def export_counting_excel(self, s):
        from ..helpers.file_dialog import ask_save_path, ask_open_after_save
        from ..helpers.file_utils import open_file
        from pdf_counting import generate_counting_excel
        from datetime import datetime

        form_date = s.get("form_date") or self.current_form_date
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_date = form_date.replace("/", "-")
        default_name = f"counting_{safe_date}_{ts}"

        def do_save(filepath):
            try:
                result = generate_counting_excel(
                    form_date=form_date,
                    output_path=filepath,
                )
            except Exception as e:
                info_dialog("خطا در ساخت Excel", str(e))
                return
            info_dialog(
                "خروجی Excel ساخته شد",
                f"فایل ذخیره شد در:\n\n{result}",
            )
            ask_open_after_save(on_yes=lambda: open_file(result))

        ask_save_path(
            title="ذخیره خروجی Excel (شمارش)",
            default_filename=default_name,
            file_extension=".xlsx",
            on_save=do_save,
        )

    # ======================================
    # خروجی‌های فرم توزین
    # ======================================

    def export_weighing_pdf(self, s):
        from ..helpers.file_dialog import ask_save_path, ask_open_after_save
        from ..helpers.file_utils import open_file
        from pdf_weighing import generate_weighing_pdf
        from datetime import datetime

        slaughter_id = s["slaughter_id"]
        form_date = s.get("form_date") or self.current_form_date
        slaughter_number = s.get("slaughter_number", "")
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_date = form_date.replace("/", "-")
        default_name = f"weighing_{safe_date}_K{slaughter_number}_{ts}"

        def do_save(filepath):
            try:
                result = generate_weighing_pdf(
                    slaughter_id=slaughter_id,
                    output_path=filepath,
                )
            except Exception as e:
                info_dialog("خطا در ساخت PDF", str(e))
                return
            info_dialog(
                "خروجی PDF ساخته شد",
                f"فایل ذخیره شد در:\n\n{result}",
            )
            ask_open_after_save(on_yes=lambda: open_file(result))

        ask_save_path(
            title="ذخیره خروجی PDF (توزین)",
            default_filename=default_name,
            file_extension=".pdf",
            on_save=do_save,
        )

    def export_weighing_excel(self, s):
        from ..helpers.file_dialog import ask_save_path, ask_open_after_save
        from ..helpers.file_utils import open_file
        from pdf_weighing import generate_weighing_excel
        from datetime import datetime

        slaughter_id = s["slaughter_id"]
        form_date = s.get("form_date") or self.current_form_date
        slaughter_number = s.get("slaughter_number", "")
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_date = form_date.replace("/", "-")
        default_name = f"weighing_{safe_date}_K{slaughter_number}_{ts}"

        def do_save(filepath):
            try:
                result = generate_weighing_excel(
                    slaughter_id=slaughter_id,
                    output_path=filepath,
                )
            except Exception as e:
                info_dialog("خطا در ساخت Excel", str(e))
                return
            info_dialog(
                "خروجی Excel ساخته شد",
                f"فایل ذخیره شد در:\n\n{result}",
            )
            ask_open_after_save(on_yes=lambda: open_file(result))

        ask_save_path(
            title="ذخیره خروجی Excel (توزین)",
            default_filename=default_name,
            file_extension=".xlsx",
            on_save=do_save,
        )

    # ======================================
    # بازگشت (بر اساس نقش)
    # ======================================

    def on_back(self, *args):
        from kivymd.app import MDApp
        app = MDApp.get_running_app()

        role = ""
        if app.current_user:
            role = str(app.current_user.get("role", "")).strip().lower()

        self.manager.transition.direction = "right"

        if role == "admin":
            self.manager.current = "admin"
        else:
            self.manager.current = "operator"
