# -*- coding: utf-8 -*-
"""
کلاس اصلی اپلیکیشن
"""

import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from kivy.uix.screenmanager import ScreenManager, SlideTransition

from kivymd.app import MDApp

from .screens.login import LoginScreen
from .screens.admin_menu import AdminMenuScreen
from .screens.operator_menu import OperatorMenuScreen
from .screens.base_data import BaseDataScreen
from .screens.backup import BackupScreen

# ═══════════════════════════════════════════
# صفحات جدید (سه فرم + قبض‌ها + صورتحساب + جستجو + گزارش + تنظیمات)
# ═══════════════════════════════════════════
from .screens.slaughters_list import SlaughtersListScreen
from .screens.counting_form import CountingFormScreen
from .screens.weighing_form import WeighingFormScreen
from .screens.daily_form import DailyFormScreen
from .screens.receipts import ReceiptsScreen
from .screens.invoices import InvoicesScreen
from .screens.admin_search import AdminSearchScreen
from .screens.admin_reports import AdminReportsScreen
from .screens.invoice_settings import InvoiceSettingsScreen

from database import initialize_database


class LoadingApp(MDApp):

    # کاربر جاری
    current_user = None

    # کشتار جاری
    current_slaughter_id = None

    # ردیف شمارش جاری (برای ویرایش از لیست کشتارها)
    current_counting_row_id = None

    def build(self):
        self.title = "سیستم توزین محصولات"
        self.theme_cls.primary_palette = "Teal"
        self.theme_cls.theme_style = "Light"

        # ── مقداردهی اولیه state ──
        self.current_user = None
        self.current_slaughter_id = None
        self.current_counting_row_id = None

        sm = ScreenManager(transition=SlideTransition())

        sm.add_widget(LoginScreen())
        sm.add_widget(AdminMenuScreen())
        sm.add_widget(OperatorMenuScreen())
        sm.add_widget(BaseDataScreen())
        sm.add_widget(BackupScreen())

        # ── سه فرم ──
        sm.add_widget(SlaughtersListScreen())
        sm.add_widget(CountingFormScreen())
        sm.add_widget(WeighingFormScreen())
        sm.add_widget(DailyFormScreen())

        # ── قبض‌های باسکول ──
        sm.add_widget(ReceiptsScreen())

        # ── صورتحساب کشتار ──
        sm.add_widget(InvoicesScreen())

        # ── جستجوی پیشرفته (ادمین) ──
        sm.add_widget(AdminSearchScreen())

        # ── گزارش‌گیری جامع (ادمین) ──
        sm.add_widget(AdminReportsScreen())

        # ── تنظیم نرخ‌های صورتحساب (ادمین) ──
        sm.add_widget(InvoiceSettingsScreen())

        return sm

    def on_start(self):
        # ── ساخت دیتابیس ──
        try:
            initialize_database()
        except Exception as e:
            print(f"DB ERROR: {e}")

        # ── بکاپ خودکار ──
        try:
            from database import auto_backup
            path = auto_backup()
            if path and not str(path).startswith("ERROR"):
                print(f"✅ auto backup: {path}")
        except Exception as e:
            print(f"Auto backup error: {e}")

        # ── مهاجرت رمزهای plain ──
        try:
            from functions import migrate_plain_passwords
            migrated = migrate_plain_passwords()
            if migrated > 0:
                print(f"🔒 {migrated} password(s) migrated to hash.")
        except Exception as e:
            print(f"Password migration error: {e}")

    def on_stop(self):
        """بکاپ قبل از بستن برنامه."""
        from database import before_exit_backup
        try:
            before_exit_backup()
        except Exception as e:
            print(f"Backup error: {e}")
