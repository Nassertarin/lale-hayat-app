# -*- coding: utf-8 -*-
"""
صفحه‌ی مدیریت اطلاعات پایه (فقط ادمین)
"""

from kivy.metrics import dp, sp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.button import Button
from kivy.uix.spinner import Spinner, SpinnerOption
from kivy.uix.popup import Popup
from kivy.graphics import Color, RoundedRectangle

from kivymd.uix.screen import MDScreen
from kivymd.uix.card import MDCard

from ..helpers.fa import fa
from ..helpers.theme import (
    COLOR_BG, COLOR_PRIMARY, COLOR_PRIMARY_DARK, COLOR_GRAY,
    COLOR_ERROR, COLOR_SUCCESS, COLOR_TEXT, COLOR_WHITE, COLOR_WARNING,
)
from ..helpers.widgets import (
    fa_label, fa_button, spacer, fa_section_title, fa_text_input,
)
from ..helpers.dialogs import confirm_dialog, info_dialog

from functions import (
    get_products, add_product, update_product, delete_product,
    get_baskets, add_basket, update_basket, delete_basket,
    get_users, add_user, update_user, delete_user, unlock_user,
)


# ── نام‌های نمایشی دسته‌ها ──
CATEGORY_NAMES = {
    "plucked": "مرغ پرکنده",
    "whole_packed": "مرغ کامل بسته‌بندی",
    "alayeshat": "آلایشات",
    "piece": "قطعه",
    "general": "محصول اصلی",
}


# ── کلاس گزینه‌ی Spinner با فونت فارسی ──
class FaSpinnerOption(SpinnerOption):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.font_name = "Vazir"
        self.font_size = sp(13)
        self.color = [0.1, 0.1, 0.1, 1]
        self.background_normal = ""
        self.background_color = [1, 1, 1, 1]


class BaseDataScreen(MDScreen):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "base_data"
        self.md_bg_color = COLOR_BG

        self.current_category = None
        self.current_title = ""

        self.title_label = None
        self.list_container = None
        self.add_button = None
        self.category_bar = None
        self.category_buttons = {}

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
        self.title_label = fa_label(
            "مدیریت اطلاعات پایه",
            size=17,
            color=COLOR_PRIMARY_DARK,
            height=40,
            bold=True,
        )
        header.add_widget(self.title_label)
        root.add_widget(header)

        # ---------- نوار دسته‌ها ----------
        self.category_bar = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(65),
            padding=[dp(8), dp(5)],
            spacing=dp(6),
        )
        for text, cat in [
            ("محصولات", "products"),
            ("سبدها", "baskets"),
            ("کاربران", "users"),
        ]:
            btn = Button(
                text=fa(text),
                font_name="Vazir",
                font_size=sp(13),
                background_normal="",
                background_color=[0.92, 0.92, 0.92, 1],
                color=COLOR_TEXT,
                bold=True,
            )
            btn.bind(on_release=lambda x, c=cat: self.select_category(c))
            self.category_buttons[cat] = btn
            self.category_bar.add_widget(btn)

        root.add_widget(self.category_bar)

        # ---------- دکمه‌ی افزودن ----------
        add_bar = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(55),
            padding=[dp(10), dp(5)],
            spacing=dp(8),
        )
        self.add_button = fa_button(
            "افزودن مورد جدید",
            size=15,
            height=45,
            bg_color=COLOR_SUCCESS,
            on_press=self.on_add,
        )
        add_bar.add_widget(self.add_button)
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
    # ناوبری
    # ======================================

    def on_pre_enter(self, *args):
        if self.current_category is None:
            self.select_category("products")
        else:
            self.refresh_list()

    def select_category(self, category):

        self.current_category = category

        titles = {
            "products": "مدیریت محصولات",
            "baskets": "مدیریت انواع سبد",
            "users": "مدیریت کاربران",
        }
        self.current_title = titles.get(category, "")
        self.title_label.text = fa(self.current_title)

        for cat, btn in self.category_buttons.items():
            if cat == category:
                btn.background_color = COLOR_PRIMARY
                btn.color = COLOR_WHITE
            else:
                btn.background_color = [0.92, 0.92, 0.92, 1]
                btn.color = COLOR_TEXT

        self.refresh_list()

    # ======================================
    # بازسازی لیست
    # ======================================

    def refresh_list(self):

        self.list_container.clear_widgets()

        cat = self.current_category

        try:
            if cat == "products":
                self._render_products()
            elif cat == "baskets":
                self._render_baskets(get_baskets())
            elif cat == "users":
                self._render_users(get_users())
        except Exception as e:
            self.list_container.add_widget(fa_label(
                f"خطا: {e}",
                size=14, color=COLOR_ERROR, height=50,
            ))

    # ======================================
    # رندر محصولات (سلسله‌مراتبی)
    # ======================================

    def _render_products(self):
        """نمایش محصولات به‌صورت سلسله‌مراتبی."""

        # دسته‌های اصلی
        root_products = get_products(only_active=False, parent_id=0)

        if not root_products:
            self.list_container.add_widget(self._empty_msg())
            return

        for root in root_products:
            root_id = root[0]
            root_name = root[1]
            root_category = root[2]
            root_active = root[4]

            # کارت دسته‌ی اصلی
            self.list_container.add_widget(self._make_product_card(
                pid=root_id,
                name=root_name,
                category=root_category,
                active=bool(root_active),
                is_parent=True,
                on_edit=lambda x, r=root: self.edit_product(r),
            ))

            # زیرمجموعه‌ها
            subs = get_products(
                only_active=False, parent_id=root_id
            )
            for sub in subs:
                sub_id = sub[0]
                sub_name = sub[1]
                sub_category = sub[2]
                sub_active = sub[4]

                self.list_container.add_widget(self._make_product_card(
                    pid=sub_id,
                    name=sub_name,
                    category=sub_category,
                    active=bool(sub_active),
                    is_parent=False,
                    on_edit=lambda x, r=sub: self.edit_product(r),
                ))

    def _make_product_card(self, pid, name, category, active,
                           is_parent, on_edit):
        """ساخت کارت محصول."""

        card = MDCard(
            orientation="horizontal",
            padding=dp(12),
            spacing=dp(8),
            size_hint=(1, None),
            height=dp(70),
            elevation=2,
            radius=[dp(10)],
            md_bg_color=[1, 1, 1, 1],
            ripple_behavior=True,
        )

        info = BoxLayout(orientation="vertical")

        title_text = f"#{pid}  {'▶ ' if is_parent else '    '}{name}"

        info.add_widget(fa_label(
            title_text,
            size=14,
            color=COLOR_PRIMARY_DARK if is_parent else COLOR_TEXT,
            height=25,
            bold=is_parent,
            halign="right",
        ))

        subtitle = CATEGORY_NAMES.get(category, category)

        info.add_widget(fa_label(
            subtitle,
            size=12,
            color=COLOR_GRAY,
            height=20,
            halign="right",
        ))

        card.add_widget(info)

        status_box = BoxLayout(
            orientation="vertical",
            size_hint_x=None,
            width=dp(80),
        )
        if active:
            status_box.add_widget(fa_label(
                "فعال",
                size=13, color=COLOR_SUCCESS, height=25, bold=True,
            ))
        else:
            status_box.add_widget(fa_label(
                "غیرفعال",
                size=13, color=COLOR_ERROR, height=25, bold=True,
            ))
        card.add_widget(status_box)

        card.bind(on_release=on_edit)
        return card

    # ======================================
    # رندر سبدها
    # ======================================

    def _render_baskets(self, items):
        if not items:
            self.list_container.add_widget(self._empty_msg())
            return

        for row in items:
            bid, weight, active = row

            card = MDCard(
                orientation="horizontal",
                padding=dp(12),
                spacing=dp(8),
                size_hint=(1, None),
                height=dp(65),
                elevation=2,
                radius=[dp(10)],
                md_bg_color=[1, 1, 1, 1],
                ripple_behavior=True,
            )

            info = BoxLayout(orientation="vertical")
            info.add_widget(fa_label(
                f"سبد {weight:.2f} کیلوگرم",
                size=14,
                color=COLOR_TEXT,
                height=28,
                bold=True,
                halign="right",
            ))
            card.add_widget(info)

            status_box = BoxLayout(
                orientation="vertical",
                size_hint_x=None,
                width=dp(80),
            )
            if active:
                status_box.add_widget(fa_label(
                    "فعال",
                    size=13, color=COLOR_SUCCESS, height=25, bold=True,
                ))
            else:
                status_box.add_widget(fa_label(
                    "غیرفعال",
                    size=13, color=COLOR_ERROR, height=25, bold=True,
                ))
            card.add_widget(status_box)

            card.bind(
                on_release=lambda x, r=row: self.edit_basket(r)
            )

            self.list_container.add_widget(card)

    # ======================================
    # رندر کاربران
    # ======================================

    def _render_users(self, items):
        if not items:
            self.list_container.add_widget(self._empty_msg())
            return

        for row in items:
            uid = row[0]
            username = row[1]
            full_name = row[2]
            role = row[3]
            active = row[4]
            can_edit_locked = row[5] if len(row) > 5 else 0

            subtitle = f"{role}  •  نام کاربری: {username}"
            if can_edit_locked:
                subtitle += "  •  [ اجازه ویرایش قفل ]"

            card = MDCard(
                orientation="horizontal",
                padding=dp(12),
                spacing=dp(8),
                size_hint=(1, None),
                height=dp(75),
                elevation=2,
                radius=[dp(10)],
                md_bg_color=[1, 1, 1, 1],
                ripple_behavior=True,
            )

            info = BoxLayout(orientation="vertical")
            info.add_widget(fa_label(
                f"#{uid}  {full_name}",
                size=14,
                color=COLOR_TEXT,
                height=25,
                bold=True,
                halign="right",
            ))
            info.add_widget(fa_label(
                subtitle,
                size=12,
                color=COLOR_GRAY,
                height=20,
                halign="right",
            ))
            card.add_widget(info)

            status_box = BoxLayout(
                orientation="vertical",
                size_hint_x=None,
                width=dp(80),
            )
            if active:
                status_box.add_widget(fa_label(
                    "فعال",
                    size=13, color=COLOR_SUCCESS, height=25, bold=True,
                ))
            else:
                status_box.add_widget(fa_label(
                    "غیرفعال",
                    size=13, color=COLOR_ERROR, height=25, bold=True,
                ))
            card.add_widget(status_box)

            card.bind(
                on_release=lambda x, r=row: self.edit_user(r)
            )

            self.list_container.add_widget(card)

    def _empty_msg(self):
        return fa_label(
            "هیچ موردی ثبت نشده.",
            size=14, color=COLOR_GRAY, height=50,
        )

    # ======================================
    # دیالوگ پایه
    # ======================================

    def _make_popup(self, title, content_widgets, on_save, on_delete=None):

        content = BoxLayout(
            orientation="vertical",
            padding=dp(15),
            spacing=dp(10),
            size_hint_y=None,
        )
        content.bind(minimum_height=content.setter("height"))

        with content.canvas.before:
            Color(1, 1, 1, 1)
            content._bg = RoundedRectangle(
                pos=content.pos,
                size=content.size,
                radius=[dp(10)],
            )
        content.bind(
            pos=lambda s, v: setattr(s._bg, "pos", v),
            size=lambda s, v: setattr(s._bg, "size", v),
        )

        content.add_widget(fa_label(
            title,
            size=16,
            color=COLOR_PRIMARY_DARK,
            height=35,
            bold=True,
        ))

        for w in content_widgets:
            content.add_widget(w)

        content.add_widget(spacer(5))

        btns = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(55),
            spacing=dp(8),
        )

        cancel_btn = Button(
            text=fa("لغو"),
            font_name="Vazir",
            font_size=sp(14),
            background_normal="",
            background_color=[0.7, 0.7, 0.7, 1],
            color=COLOR_WHITE,
            bold=True,
        )

        save_btn = Button(
            text=fa("ذخیره"),
            font_name="Vazir",
            font_size=sp(14),
            background_normal="",
            background_color=COLOR_SUCCESS,
            color=COLOR_WHITE,
            bold=True,
        )

        delete_btn = None
        if on_delete:
            delete_btn = Button(
                text=fa("حذف"),
                font_name="Vazir",
                font_size=sp(14),
                background_normal="",
                background_color=COLOR_ERROR,
                color=COLOR_WHITE,
                bold=True,
            )
            btns.add_widget(delete_btn)

        btns.add_widget(cancel_btn)
        btns.add_widget(save_btn)
        content.add_widget(btns)

        num_children = len(content.children)
        base_spacing = content.spacing * max(0, num_children - 1)
        pad_vertical = content.padding[1] + content.padding[3]

        estimated_content_h = 0
        for w in content.children:
            estimated_content_h += getattr(w, "height", dp(50))

        total_h = estimated_content_h + base_spacing + pad_vertical

        popup_height = max(dp(320), min(dp(680), total_h + dp(20)))
        popup_width = dp(460)

        inner_scroll = ScrollView(
            size_hint=(1, 1),
            do_scroll_x=False,
        )
        inner_scroll.add_widget(content)

        popup = Popup(
            title="",
            title_size=0,
            content=inner_scroll,
            size_hint=(None, None),
            size=(popup_width, popup_height),
            auto_dismiss=False,
            background="",
            background_color=[0, 0, 0, 0.5],
            separator_height=0,
        )

        cancel_btn.bind(on_release=lambda x: popup.dismiss())

        def do_save(*args):
            result = on_save()
            if result:
                popup.dismiss()
                self.refresh_list()
                info_dialog(
                    "ثبت موفق",
                    "تغییرات با موفقیت ذخیره شد.",
                )

        save_btn.bind(on_release=do_save)

        if on_delete:
            def do_delete(*args):
                def confirmed():
                    result = on_delete()
                    if result:
                        self.refresh_list()
                        info_dialog(
                            "حذف موفق",
                            "مورد با موفقیت حذف شد.",
                        )
                popup.dismiss()
                confirm_dialog(
                    title="حذف",
                    message="آیا مطمئن هستید؟ این عمل قابل بازگشت نیست.",
                    confirm_text="حذف",
                    confirm_color=COLOR_ERROR,
                    on_confirm=confirmed,
                )
            delete_btn.bind(on_release=do_delete)

        popup.open()
        return popup

    # ======================================
    # افزودن
    # ======================================

    def on_add(self, *args):
        cat = self.current_category

        if cat is None:
            cat = "products"
            self.current_category = cat

        try:
            if cat == "products":
                self.add_product_ui()
            elif cat == "baskets":
                self.add_basket_ui()
            elif cat == "users":
                self.add_user_ui()
        except Exception as e:
            import traceback
            traceback.print_exc()
            info_dialog("خطای سیستمی", str(e))

    # ======================================
    # افزودن محصول (منطق جدید و ساده)
    # ======================================

    def add_product_ui(self):
        """
        افزودن محصول جدید:
        - نام
        - در کدام دسته قرار می‌گیرد؟ (یا هیچ‌کدام = محصول اصلی)
        """

        # ── ۱) نام ──
        name_label = fa_label(
            "نام محصول",
            size=13, color=COLOR_TEXT, height=25,
            bold=True, halign="right",
        )

        name_wrap = fa_text_input(hint_text="نام محصول")

        # ── ۲) دسته ──
        cat_label = fa_label(
            "در کدام دسته قرار می‌گیرد؟",
            size=13, color=COLOR_TEXT, height=25,
            bold=True, halign="right",
        )

        # گرفتن دسته‌های اصلی از دیتابیس
        root_products = get_products(only_active=False, parent_id=0)

        # نگاشت نام نمایشی → (category, parent_id)
        parent_map = {"هیچ‌کدام (محصول اصلی)": None}

        for rp in root_products:
            rp_id = rp[0]
            rp_name = rp[1]
            rp_category = rp[2]
            parent_map[rp_name] = {
                "category": rp_category,
                "parent_id": rp_id,
            }

        spinner_values = [fa(name) for name in parent_map.keys()]

        cat_spinner = Spinner(
            text=fa("هیچ‌کدام (محصول اصلی)"),
            values=spinner_values,
            size_hint_y=None,
            height=dp(45),
            background_normal="",
            background_color=[0.92, 0.92, 0.92, 1],
            color=[0.1, 0.1, 0.1, 1],
            font_name="Vazir",
            font_size=sp(13),
            option_cls=FaSpinnerOption,
        )

        # ── ذخیره ──
        def do_save():
            name = name_wrap.text.strip()
            if not name:
                info_dialog("خطا", "نام نمی‌تواند خالی باشد.")
                return False

            # پیدا کردن انتخاب کاربر
            selected_display = None
            for k in parent_map.keys():
                if fa(k) == cat_spinner.text:
                    selected_display = k
                    break

            if selected_display is None:
                selected_display = "هیچ‌کدام (محصول اصلی)"

            parent_info = parent_map[selected_display]

            if parent_info is None:
                # محصول اصلی
                category = "general"
                parent_id = None
            else:
                category = parent_info["category"]
                parent_id = parent_info["parent_id"]

            try:
                add_product(name, category, parent_id)
                return True
            except ValueError as e:
                info_dialog("خطا", str(e))
                return False

        self._make_popup(
            "افزودن محصول جدید",
            [name_label, name_wrap,
             cat_label, cat_spinner],
            do_save,
        )

    # ======================================
    # افزودن سبد (فقط وزنی)
    # ======================================

    def add_basket_ui(self):
        weight_wrap = fa_text_input(
            hint_text="وزن سبد (کیلوگرم)",
            input_filter="float",
        )

        def do_save():
            try:
                weight = float(weight_wrap.text.strip())
            except ValueError:
                info_dialog("خطا", "وزن نامعتبر است.")
                return False
            if weight <= 0:
                info_dialog("خطا", "وزن باید بزرگ‌تر از صفر باشد.")
                return False
            try:
                add_basket(weight)
                return True
            except ValueError as e:
                info_dialog("خطا", str(e))
                return False

        self._make_popup(
            "افزودن سبد جدید",
            [weight_wrap],
            do_save,
        )

    # ======================================
    # افزودن کاربر
    # ======================================

    def add_user_ui(self):
        username_wrap = fa_text_input(hint_text="نام کاربری")
        password_wrap = fa_text_input(hint_text="رمز عبور", password=True)
        full_name_wrap = fa_text_input(hint_text="نام کامل")
        role_wrap = fa_text_input(hint_text="عنوان شغلی")

        def do_save():
            u = username_wrap.text.strip()
            p = password_wrap.text.strip()
            f = full_name_wrap.text.strip()
            r = role_wrap.text.strip()
            if not u or not p or not f or not r:
                info_dialog("خطا", "همه‌ی فیلدها الزامی است.")
                return False
            try:
                add_user(u, p, f, r)
                return True
            except ValueError as e:
                info_dialog("خطا", str(e))
                return False

        self._make_popup(
            "افزودن کاربر جدید",
            [username_wrap, password_wrap, full_name_wrap, role_wrap],
            do_save,
        )

    # ======================================
    # ویرایش محصول
    # ======================================

    def edit_product(self, row):
        pid, name, category, parent_id, active = row

        name_wrap = fa_text_input(hint_text="نام محصول", text=name)

        active_var = {"value": bool(active)}
        active_label = fa_label(
            "وضعیت: فعال" if active else "وضعیت: غیرفعال",
            size=13, color=COLOR_TEXT, height=30,
        )
        toggle_btn = Button(
            text=fa("تغییر وضعیت"),
            font_name="Vazir",
            font_size=sp(13),
            size_hint_y=None,
            height=dp(40),
            background_normal="",
            background_color=COLOR_WARNING,
            color=COLOR_WHITE,
        )

        def toggle(*args):
            active_var["value"] = not active_var["value"]
            active_label.text = fa(
                "وضعیت: فعال" if active_var["value"]
                else "وضعیت: غیرفعال"
            )

        toggle_btn.bind(on_release=toggle)

        def do_save():
            new_name = name_wrap.text.strip()
            if not new_name:
                info_dialog("خطا", "نام نمی‌تواند خالی باشد.")
                return False
            try:
                update_product(
                    pid,
                    product_name=new_name,
                    active=1 if active_var["value"] else 0,
                )
                return True
            except ValueError as e:
                info_dialog("خطا", str(e))
                return False

        def do_delete():
            try:
                delete_product(pid)
                return True
            except ValueError as e:
                info_dialog("نمی‌توان حذف کرد", str(e))
                return False

        self._make_popup(
            f"ویرایش محصول #{pid}",
            [name_wrap, active_label, toggle_btn],
            do_save,
            on_delete=do_delete,
        )

    # ======================================
    # ویرایش سبد
    # ======================================

    def edit_basket(self, row):
        bid, weight, active = row

        weight_wrap = fa_text_input(
            hint_text="وزن سبد (کیلوگرم)",
            text=f"{weight:.2f}",
            input_filter="float",
        )

        active_var = {"value": bool(active)}
        active_label = fa_label(
            "وضعیت: فعال" if active else "وضعیت: غیرفعال",
            size=13, color=COLOR_TEXT, height=30,
        )
        active_btn = Button(
            text=fa("تغییر وضعیت"),
            font_name="Vazir",
            font_size=sp(13),
            size_hint_y=None,
            height=dp(40),
            background_normal="",
            background_color=COLOR_WARNING,
            color=COLOR_WHITE,
        )

        def toggle_active(*args):
            active_var["value"] = not active_var["value"]
            active_label.text = fa(
                "وضعیت: فعال" if active_var["value"]
                else "وضعیت: غیرفعال"
            )

        active_btn.bind(on_release=toggle_active)

        def do_save():
            try:
                new_weight = float(weight_wrap.text.strip())
            except ValueError:
                info_dialog("خطا", "وزن نامعتبر است.")
                return False
            if new_weight <= 0:
                info_dialog("خطا", "وزن باید بزرگ‌تر از صفر باشد.")
                return False
            try:
                update_basket(
                    bid,
                    weight=new_weight,
                    active=1 if active_var["value"] else 0,
                )
                return True
            except ValueError as e:
                info_dialog("خطا", str(e))
                return False

        def do_delete():
            try:
                delete_basket(bid)
                return True
            except ValueError as e:
                info_dialog("نمی‌توان حذف کرد", str(e))
                return False

        self._make_popup(
            f"ویرایش سبد {weight:.2f} kg",
            [weight_wrap, active_label, active_btn],
            do_save,
            on_delete=do_delete,
        )

    # ======================================
    # ویرایش کاربر
    # ======================================

    def edit_user(self, row):
        uid = row[0]
        username = row[1]
        full_name = row[2]
        role = row[3]
        active = row[4]
        can_edit_locked = row[5] if len(row) > 5 else 0

        username_label = fa_label(
            f"نام کاربری: {username}",
            size=13, color=COLOR_GRAY, height=30,
        )

        password_wrap = fa_text_input(
            hint_text="رمز عبور جدید (خالی = بدون تغییر)",
            password=True,
        )
        full_name_wrap = fa_text_input(hint_text="نام کامل", text=full_name)
        role_wrap = fa_text_input(hint_text="عنوان شغلی", text=role)

        active_var = {"value": bool(active)}
        active_label = fa_label(
            "وضعیت: فعال" if active else "وضعیت: غیرفعال",
            size=13, color=COLOR_TEXT, height=30,
        )
        active_btn = Button(
            text=fa("تغییر وضعیت"),
            font_name="Vazir",
            font_size=sp(13),
            size_hint_y=None,
            height=dp(40),
            background_normal="",
            background_color=COLOR_WARNING,
            color=COLOR_WHITE,
        )

        def toggle_active(*args):
            active_var["value"] = not active_var["value"]
            active_label.text = fa(
                "وضعیت: فعال" if active_var["value"]
                else "وضعیت: غیرفعال"
            )

        active_btn.bind(on_release=toggle_active)

        # ── can_edit_locked ──
        can_edit_var = {"value": bool(can_edit_locked)}
        can_edit_label = fa_label(
            "اجازه ویرایش فرم‌های قفل‌شده: " + ("بله" if can_edit_locked else "خیر"),
            size=13, color=COLOR_TEXT, height=30,
        )
        can_edit_btn = Button(
            text=fa("تغییر وضعیت"),
            font_name="Vazir",
            font_size=sp(13),
            size_hint_y=None,
            height=dp(40),
            background_normal="",
            background_color=COLOR_PRIMARY,
            color=COLOR_WHITE,
        )

        def toggle_can_edit(*args):
            can_edit_var["value"] = not can_edit_var["value"]
            can_edit_label.text = fa(
                "اجازه ویرایش فرم‌های قفل‌شده: " + ("بله" if can_edit_var["value"] else "خیر")
            )

        can_edit_btn.bind(on_release=toggle_can_edit)

        unlock_btn = Button(
            text=fa("باز کردن قفل حساب"),
            font_name="Vazir",
            font_size=sp(13),
            size_hint_y=None,
            height=dp(40),
            background_normal="",
            background_color=COLOR_PRIMARY,
            color=COLOR_WHITE,
        )

        def do_unlock(*args):
            unlock_user(uid)
            info_dialog("انجام شد", "قفل حساب باز شد.")

        unlock_btn.bind(on_release=do_unlock)

        def do_save():
            f = full_name_wrap.text.strip()
            r = role_wrap.text.strip()
            p = password_wrap.text.strip()

            if not f:
                info_dialog("خطا", "نام کامل نمی‌تواند خالی باشد.")
                return False

            try:
                update_user(
                    uid,
                    password=p if p else None,
                    full_name=f,
                    role=r,
                    active=1 if active_var["value"] else 0,
                    can_edit_locked=1 if can_edit_var["value"] else 0,
                )
                return True
            except ValueError as e:
                info_dialog("خطا", str(e))
                return False

        def do_delete():
            if username == "admin":
                info_dialog("خطا", "کاربر admin قابل حذف نیست.")
                return False
            try:
                delete_user(uid)
                return True
            except ValueError as e:
                info_dialog("نمی‌توان حذف کرد", str(e))
                return False

        self._make_popup(
            f"ویرایش کاربر #{uid}",
            [
                username_label,
                password_wrap,
                full_name_wrap,
                role_wrap,
                active_label, active_btn,
                can_edit_label, can_edit_btn,
                unlock_btn,
            ],
            do_save,
            on_delete=do_delete,
        )

    # ======================================
    # بازگشت
    # ======================================

    def on_back(self, *args):
        self.manager.transition.direction = "right"
        self.manager.current = "admin"
