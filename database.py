# -*- coding: utf-8 -*-
"""
دیتابیس سیستم توزین — نسخه‌ی کامل (با صورتحساب روزانه)
"""

import sqlite3
import os
import shutil
import zipfile
from datetime import datetime, timedelta, time

def _get_base_dir():
    """Return a writable base directory for the app (Android-safe)."""
    import sys
    if hasattr(sys, "getandroidapilevel") or "ANDROID_ARGUMENT" in os.environ:
        from kivy.app import App
        app = App.get_running_app()
        if app:
            return app.user_data_dir
        return os.path.expanduser("~")
    return os.path.dirname(os.path.abspath(__file__))

BASE_DIR = _get_base_dir()

DB_NAME = os.path.join(BASE_DIR, "loading_system.db")
BACKUP_DIR = os.path.join(BASE_DIR, "backups")
REPORTS_DIR = os.path.join(BASE_DIR, "reports")
RECEIPTS_DIR = os.path.join(BASE_DIR, "receipts")

MAX_AUTO_BACKUPS = 7
MAX_BEFORE_EXIT_BACKUPS = 3
MAX_MANUAL_BACKUPS = 30
MAX_BEFORE_RESTORE_BACKUPS = 5


def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    return conn


def create_tables():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS products (
        product_id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_name TEXT NOT NULL,
        category TEXT NOT NULL,
        parent_id INTEGER,
        active INTEGER NOT NULL DEFAULT 1,
        FOREIGN KEY(parent_id) REFERENCES products(product_id) ON DELETE CASCADE
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS basket_types (
        basket_id INTEGER PRIMARY KEY AUTOINCREMENT,
        weight REAL NOT NULL UNIQUE CHECK(weight > 0),
        active INTEGER NOT NULL DEFAULT 1
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL,
        full_name TEXT NOT NULL,
        role TEXT NOT NULL,
        active INTEGER NOT NULL DEFAULT 1,
        failed_attempts INTEGER NOT NULL DEFAULT 0,
        locked_until TEXT,
        can_edit_locked INTEGER NOT NULL DEFAULT 0
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS loading_operations (
        operation_id INTEGER PRIMARY KEY AUTOINCREMENT,
        operation_datetime TEXT NOT NULL,
        operation_shamsi TEXT NOT NULL,
        product_id INTEGER NOT NULL,
        cart_number TEXT NOT NULL,
        before_weight REAL NOT NULL CHECK(before_weight >= 0),
        after_weight REAL NOT NULL CHECK(after_weight >= 0),
        net_product_weight REAL NOT NULL,
        user_id INTEGER NOT NULL,
        description TEXT,
        slaughter_id INTEGER,
        FOREIGN KEY(product_id) REFERENCES products(product_id),
        FOREIGN KEY(user_id) REFERENCES users(user_id),
        FOREIGN KEY(slaughter_id) REFERENCES slaughters(slaughter_id) ON DELETE SET NULL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS slaughters (
        slaughter_id INTEGER PRIMARY KEY AUTOINCREMENT,
        counting_row_id INTEGER NOT NULL UNIQUE,
        form_date TEXT NOT NULL,
        day_name TEXT NOT NULL,
        slaughter_number INTEGER NOT NULL,
        created_at TEXT NOT NULL,
        operator_id INTEGER NOT NULL,
        UNIQUE(form_date, slaughter_number),
        FOREIGN KEY(counting_row_id) REFERENCES counting_rows(row_id) ON DELETE CASCADE,
        FOREIGN KEY(operator_id) REFERENCES users(user_id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS counting_rows (
        row_id INTEGER PRIMARY KEY AUTOINCREMENT,
        form_date TEXT NOT NULL,
        day_name TEXT NOT NULL,
        row_num INTEGER NOT NULL,
        hook_count INTEGER NOT NULL DEFAULT 0,
        waste INTEGER NOT NULL DEFAULT 0,
        deaths INTEGER NOT NULL DEFAULT 0,
        pieces INTEGER NOT NULL DEFAULT 0,
        packed INTEGER NOT NULL DEFAULT 0,
        notes TEXT,
        created_at TEXT NOT NULL,
        completed_at TEXT,
        locked_at TEXT,
        operator_id INTEGER NOT NULL,
        UNIQUE(form_date, row_num),
        FOREIGN KEY(operator_id) REFERENCES users(user_id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS weighing_forms (
        form_id INTEGER PRIMARY KEY AUTOINCREMENT,
        slaughter_id INTEGER NOT NULL UNIQUE,
        total_full_weight REAL NOT NULL DEFAULT 0,
        total_net_weight REAL NOT NULL DEFAULT 0,
        loss_percent REAL NOT NULL DEFAULT 0,
        live_weight REAL NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL,
        completed_at TEXT,
        locked_at TEXT,
        FOREIGN KEY(slaughter_id) REFERENCES slaughters(slaughter_id) ON DELETE CASCADE
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS weighing_plucked_rows (
        row_id INTEGER PRIMARY KEY AUTOINCREMENT,
        form_id INTEGER NOT NULL,
        row_num INTEGER NOT NULL,
        cart_number TEXT,
        is_bulk INTEGER NOT NULL DEFAULT 0,
        empty_weight REAL NOT NULL DEFAULT 0,
        full_weight REAL NOT NULL DEFAULT 0,
        net_weight REAL NOT NULL DEFAULT 0,
        FOREIGN KEY(form_id) REFERENCES weighing_forms(form_id) ON DELETE CASCADE
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS weighing_plucked_baskets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        row_id INTEGER NOT NULL,
        basket_id INTEGER NOT NULL,
        count INTEGER NOT NULL DEFAULT 0,
        FOREIGN KEY(row_id) REFERENCES weighing_plucked_rows(row_id) ON DELETE CASCADE,
        FOREIGN KEY(basket_id) REFERENCES basket_types(basket_id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS weighing_alayeshat_rows (
        row_id INTEGER PRIMARY KEY AUTOINCREMENT,
        form_id INTEGER NOT NULL,
        row_num INTEGER NOT NULL,
        product_id INTEGER NOT NULL,
        empty_weight REAL NOT NULL DEFAULT 0,
        full_weight REAL NOT NULL DEFAULT 0,
        net_weight REAL NOT NULL DEFAULT 0,
        FOREIGN KEY(form_id) REFERENCES weighing_forms(form_id) ON DELETE CASCADE,
        FOREIGN KEY(product_id) REFERENCES products(product_id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS daily_forms (
        form_id INTEGER PRIMARY KEY AUTOINCREMENT,
        form_date TEXT NOT NULL UNIQUE,
        day_name TEXT NOT NULL,
        waste REAL NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL,
        completed_at TEXT,
        locked_at TEXT,
        operator_id INTEGER,
        FOREIGN KEY(operator_id) REFERENCES users(user_id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS daily_packed_rows (
        row_id INTEGER PRIMARY KEY AUTOINCREMENT,
        form_id INTEGER NOT NULL,
        row_num INTEGER NOT NULL,
        buyer_name TEXT NOT NULL,
        total_net_weight REAL NOT NULL DEFAULT 0,
        FOREIGN KEY(form_id) REFERENCES daily_forms(form_id) ON DELETE CASCADE
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS daily_packed_carts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        row_id INTEGER NOT NULL,
        cart_number TEXT NOT NULL,
        plucked_row_id INTEGER,
        FOREIGN KEY(row_id) REFERENCES daily_packed_rows(row_id) ON DELETE CASCADE,
        FOREIGN KEY(plucked_row_id) REFERENCES weighing_plucked_rows(row_id) ON DELETE SET NULL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS daily_alayeshat_rows (
        row_id INTEGER PRIMARY KEY AUTOINCREMENT,
        form_id INTEGER NOT NULL,
        row_num INTEGER NOT NULL,
        customer_name TEXT NOT NULL,
        product_id INTEGER NOT NULL,
        weight REAL NOT NULL DEFAULT 0,
        FOREIGN KEY(form_id) REFERENCES daily_forms(form_id) ON DELETE CASCADE,
        FOREIGN KEY(product_id) REFERENCES products(product_id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS daily_morgh_rows (
        row_id INTEGER PRIMARY KEY AUTOINCREMENT,
        form_id INTEGER NOT NULL,
        row_num INTEGER NOT NULL,
        customer_name TEXT NOT NULL,
        lake_weight REAL NOT NULL DEFAULT 0,
        piece_weight REAL NOT NULL DEFAULT 0,
        sine_weight REAL NOT NULL DEFAULT 0,
        ran_weight REAL NOT NULL DEFAULT 0,
        bal_weight REAL NOT NULL DEFAULT 0,
        gardan_weight REAL NOT NULL DEFAULT 0,
        whole_weight REAL NOT NULL DEFAULT 0,
        waste_weight REAL NOT NULL DEFAULT 0,
        FOREIGN KEY(form_id) REFERENCES daily_forms(form_id) ON DELETE CASCADE
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS slaughter_receipts (
        receipt_id INTEGER PRIMARY KEY AUTOINCREMENT,
        slaughter_id INTEGER NOT NULL,
        receipt_number TEXT,
        receipt_date TEXT,
        net_weight REAL NOT NULL DEFAULT 0,
        car_plate TEXT,
        driver_name TEXT,
        buyer_name TEXT,
        description TEXT,
        image_path TEXT,
        created_at TEXT NOT NULL,
        operator_id INTEGER NOT NULL,
        completed_at TEXT,
        locked_at TEXT,
        FOREIGN KEY(slaughter_id) REFERENCES slaughters(slaughter_id) ON DELETE CASCADE,
        FOREIGN KEY(operator_id) REFERENCES users(user_id)
    )
    """)

    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_receipts_slaughter
    ON slaughter_receipts(slaughter_id)
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS daily_invoices (
        invoice_id INTEGER PRIMARY KEY AUTOINCREMENT,
        form_date TEXT NOT NULL UNIQUE,
        day_name TEXT NOT NULL,
        invoice_number TEXT,
        invoice_date TEXT,
        w1_full REAL DEFAULT 0, w1_empty REAL DEFAULT 0, w1_net REAL DEFAULT 0, w1_qty REAL DEFAULT 0, w1_rate REAL DEFAULT 0, w1_amount REAL DEFAULT 0,
        w2_full REAL DEFAULT 0, w2_empty REAL DEFAULT 0, w2_net REAL DEFAULT 0, w2_qty REAL DEFAULT 0, w2_rate REAL DEFAULT 0, w2_amount REAL DEFAULT 0,
        w3_full REAL DEFAULT 0, w3_empty REAL DEFAULT 0, w3_net REAL DEFAULT 0, w3_qty REAL DEFAULT 0, w3_rate REAL DEFAULT 0, w3_amount REAL DEFAULT 0,
        w4_full REAL DEFAULT 0, w4_empty REAL DEFAULT 0, w4_net REAL DEFAULT 0, w4_qty REAL DEFAULT 0, w4_rate REAL DEFAULT 0, w4_amount REAL DEFAULT 0,
        w5_full REAL DEFAULT 0, w5_empty REAL DEFAULT 0, w5_net REAL DEFAULT 0, w5_qty REAL DEFAULT 0, w5_rate REAL DEFAULT 0, w5_amount REAL DEFAULT 0,
        total_weight REAL DEFAULT 0, total_amount REAL DEFAULT 0,
        c1_amount REAL DEFAULT 0, c1_rate REAL DEFAULT 0, c1_total REAL DEFAULT 0,
        c2_amount REAL DEFAULT 0, c2_rate REAL DEFAULT 0, c2_total REAL DEFAULT 0,
        e1_amount REAL DEFAULT 0, e1_rate REAL DEFAULT 0, e1_total REAL DEFAULT 0,
        e2_amount REAL DEFAULT 0, e2_rate REAL DEFAULT 0, e2_total REAL DEFAULT 0,
        e3_amount REAL DEFAULT 0, e3_rate REAL DEFAULT 0, e3_total REAL DEFAULT 0,
        e4_amount REAL DEFAULT 0, e4_rate REAL DEFAULT 0, e4_total REAL DEFAULT 0,
        e5_amount REAL DEFAULT 0, e5_rate REAL DEFAULT 0, e5_total REAL DEFAULT 0,
        e6_amount REAL DEFAULT 0, e6_rate REAL DEFAULT 0, e6_total REAL DEFAULT 0,
        e7_amount REAL DEFAULT 0, e7_rate REAL DEFAULT 0, e7_total REAL DEFAULT 0,
        e8_amount REAL DEFAULT 0, e8_rate REAL DEFAULT 0, e8_total REAL DEFAULT 0,
        e9_amount REAL DEFAULT 0, e9_rate REAL DEFAULT 0, e9_total REAL DEFAULT 0,
        vat_rate REAL DEFAULT 10,
        vat_amount REAL DEFAULT 0,
        grand_total REAL DEFAULT 0,
        description TEXT,
        image_path TEXT,
        created_at TEXT NOT NULL,
        operator_id INTEGER NOT NULL,
        completed_at TEXT,
        locked_at TEXT,
        FOREIGN KEY(operator_id) REFERENCES users(user_id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS invoice_settings (
        key TEXT PRIMARY KEY,
        value REAL NOT NULL DEFAULT 0
    )
    """)

    cursor.execute("SELECT COUNT(*) FROM invoice_settings")
    if cursor.fetchone()[0] == 0:
        defaults = [
            ('c1_rate', 105000),
            ('c2_rate', 24000),
            ('e1_rate', 1300000),
            ('e2_rate', 35000),
            ('e3_rate', 33600),
            ('e4_rate', 7000),
            ('e5_rate', 13720),
            ('e6_rate', 15220),
            ('e7_rate', 60000),
            ('e8_rate', 80),
        ]
        for k, v in defaults:
            cursor.execute("INSERT INTO invoice_settings (key, value) VALUES (?, ?)", (k, v))

    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_daily_invoices_date
    ON daily_invoices(form_date)
    """)

    conn.commit()
    conn.close()


def _migrate_daily_forms_if_needed():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(daily_forms)")
    cols = [row[1] for row in cursor.fetchall()]
    if not cols:
        conn.close()
        return False
    if "slaughter_id" not in cols:
        conn.close()
        return False
    print("⚠️  مهاجرت daily_forms به ساختار جدید...")
    try:
        cursor.execute("ALTER TABLE daily_forms RENAME TO daily_forms_old")
        cursor.execute("""
        CREATE TABLE daily_forms (
            form_id INTEGER PRIMARY KEY AUTOINCREMENT,
            form_date TEXT NOT NULL UNIQUE,
            day_name TEXT NOT NULL,
            waste REAL NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            completed_at TEXT,
            locked_at TEXT,
            operator_id INTEGER,
            FOREIGN KEY(operator_id) REFERENCES users(user_id)
        )
        """)
        cursor.execute("""
        INSERT INTO daily_forms (form_id, form_date, day_name, waste, created_at, completed_at, locked_at, operator_id)
        SELECT 
            old_df.form_id,
            s.form_date,
            s.day_name,
            old_df.waste,
            old_df.created_at,
            old_df.completed_at,
            old_df.locked_at,
            s.operator_id
        FROM daily_forms_old AS old_df
        JOIN slaughters s ON s.slaughter_id = old_df.slaughter_id
        GROUP BY s.form_date
        """)
        cursor.execute("DROP TABLE daily_forms_old")
        conn.commit()
        print("✅ مهاجرت daily_forms با موفقیت انجام شد.")
    except Exception as e:
        conn.rollback()
        print(f"❌ خطا در مهاجرت: {e}")
        conn.close()
        raise
    conn.close()
    return True


def _add_live_weight_if_needed():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(weighing_forms)")
    cols = [row[1] for row in cursor.fetchall()]
    if "live_weight" not in cols:
        try:
            cursor.execute("ALTER TABLE weighing_forms ADD COLUMN live_weight REAL NOT NULL DEFAULT 0")
            conn.commit()
            print("✅ ستون live_weight به weighing_forms اضافه شد.")
        except sqlite3.OperationalError as e:
            print(f"ℹ️  {e}")
    conn.close()


def _add_can_edit_locked_if_needed():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(users)")
    cols = [row[1] for row in cursor.fetchall()]
    if "can_edit_locked" not in cols:
        try:
            cursor.execute(
                "ALTER TABLE users ADD COLUMN can_edit_locked INTEGER NOT NULL DEFAULT 0"
            )
            conn.commit()
            print("✅ ستون can_edit_locked به users اضافه شد.")
        except sqlite3.OperationalError as e:
            print(f"ℹ️  {e}")
    conn.close()


def _remove_old_invoices_if_needed():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='slaughter_invoices'")
    if cursor.fetchone():
        print("⚠️  حذف جدول قدیمی slaughter_invoices...")
        cursor.execute("DROP TABLE slaughter_invoices")
        conn.commit()
        print("✅ جدول slaughter_invoices حذف شد.")
    conn.close()


def insert_initial_data():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""INSERT OR IGNORE INTO users (user_id, username, password, full_name, role) VALUES (1, 'admin', '1234', 'System Administrator', 'admin')""")
    for w in [2.1, 1.5]:
        cursor.execute("""INSERT OR IGNORE INTO basket_types (weight) VALUES (?)""", (w,))
    cursor.execute("SELECT COUNT(*) FROM products")
    count = cursor.fetchone()[0]
    if count == 0:
        cursor.execute("""INSERT INTO products (product_name, category, parent_id) VALUES ('مرغ پرکنده', 'plucked', NULL)""")
        cursor.execute("""INSERT INTO products (product_name, category, parent_id) VALUES ('مرغ کامل بسته‌بندی', 'whole_packed', NULL)""")
        cursor.execute("""INSERT INTO products (product_name, category, parent_id) VALUES ('آلایشات', 'alayeshat', NULL)""")
        alayeshat_id = cursor.lastrowid
        cursor.execute("""INSERT INTO products (product_name, category, parent_id) VALUES ('قطعه', 'piece', NULL)""")
        piece_id = cursor.lastrowid
        for name in ['دل', 'جگر', 'سنگدان', 'پا', 'کله']:
            cursor.execute("""INSERT INTO products (product_name, category, parent_id) VALUES (?, 'alayeshat', ?)""", (name, alayeshat_id))
        for name in ['سینه', 'ران', 'بال', 'گردن']:
            cursor.execute("""INSERT INTO products (product_name, category, parent_id) VALUES (?, 'piece', ?)""", (name, piece_id))
    conn.commit()
    conn.close()


def get_work_day(dt=None):
    if dt is None:
        dt = datetime.now()
    if dt.hour >= 12:
        return dt.date() + timedelta(days=1)
    return dt.date()


def get_work_day_shamsi():
    try:
        import jdatetime
        work_day = get_work_day()
        g_date = datetime.combine(work_day, time.min)
        sh = jdatetime.datetime.fromgregorian(datetime=g_date)
        shamsi_str = sh.strftime("%Y/%m/%d")
        DAY_NAMES = ["دوشنبه", "سه‌شنبه", "چهارشنبه", "پنجشنبه", "جمعه", "شنبه", "یکشنبه"]
        day_name = DAY_NAMES[work_day.weekday()]
        return shamsi_str, day_name
    except ImportError:
        work_day = get_work_day()
        return work_day.strftime("%Y/%m/%d"), ""


def get_report_range(work_day_date):
    start = datetime.combine(work_day_date - timedelta(days=1), time(hour=12))
    end = datetime.combine(work_day_date, time(hour=11, minute=59, second=59))
    return start, end


def is_within_edit_window(completed_at_str, minutes=15):
    if not completed_at_str:
        return True
    try:
        completed = datetime.strptime(completed_at_str, "%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        return False
    elapsed = datetime.now() - completed
    return elapsed.total_seconds() <= minutes * 60


def initialize_database():
    # On Android, seed the writable DB from the bundled assets DB on first run
    import sys as _sys
    if hasattr(_sys, "getandroidapilevel") or "ANDROID_ARGUMENT" in os.environ:
        if not os.path.exists(DB_NAME):
            _seed = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "assets", "loading_system.db"
            )
            if os.path.exists(_seed):
                try:
                    shutil.copy2(_seed, DB_NAME)
                    print(f"Seeded database from {_seed}")
                except Exception as e:
                    print(f"Seed copy failed: {e}")
    create_tables()
    _add_live_weight_if_needed()
    _add_can_edit_locked_if_needed()
    _migrate_daily_forms_if_needed()
    _remove_old_invoices_if_needed()
    insert_initial_data()
    print("Database initialized successfully.")


def generate_invoice_number(form_date):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        date_str = form_date.replace("/", "")
    except Exception:
        date_str = datetime.now().strftime("%Y%m%d")
    
    cursor.execute("SELECT COUNT(*) FROM daily_invoices WHERE form_date = ?", (form_date,))
    count = cursor.fetchone()[0]
    conn.close()
    
    counter = count + 1
    return f"INV-{date_str}-{counter:03d}"


# ==========================================
# بکاپ‌گیری و بازیابی
# ==========================================

def _get_backup_dir():
    os.makedirs(BACKUP_DIR, exist_ok=True)
    return BACKUP_DIR


def _get_reports_dir():
    os.makedirs(REPORTS_DIR, exist_ok=True)
    return REPORTS_DIR


def get_receipts_dir():
    os.makedirs(RECEIPTS_DIR, exist_ok=True)
    return RECEIPTS_DIR


def get_slaughter_receipts_dir(slaughter_id):
    d = os.path.join(get_receipts_dir(), str(slaughter_id))
    os.makedirs(d, exist_ok=True)
    return d


def save_receipt_image(slaughter_id, source_path):
    import uuid
    if not os.path.exists(source_path):
        raise ValueError(f"فایل عکس یافت نشد: {source_path}")
    ext = os.path.splitext(source_path)[1].lower() or ".jpg"
    filename = f"{uuid.uuid4().hex}{ext}"
    dst_dir = get_slaughter_receipts_dir(slaughter_id)
    dst = os.path.join(dst_dir, filename)
    shutil.copy2(source_path, dst)
    rel = os.path.relpath(dst, BASE_DIR)
    return rel


def resolve_receipt_image(rel_path):
    if not rel_path:
        return None
    if os.path.isabs(rel_path):
        return rel_path
    return os.path.join(BASE_DIR, rel_path)


def delete_receipt_image(rel_path):
    if not rel_path:
        return
    full = resolve_receipt_image(rel_path)
    if full and os.path.exists(full):
        try:
            os.remove(full)
        except OSError:
            pass


def delete_slaughter_receipts_folder(slaughter_id):
    d = os.path.join(get_receipts_dir(), str(slaughter_id))
    if os.path.isdir(d):
        try:
            shutil.rmtree(d)
        except OSError:
            pass


def delete_slaughter_full(slaughter_id):
    """
    حذف کامل یک کشتار با تمام وابستگی‌ها:
    - فرم شمارش
    - فرم توزین (به‌طور خودکار با CASCADE)
    - قبض‌ها
    - عکس‌های قبض‌ها
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT counting_row_id FROM slaughters WHERE slaughter_id = ?", (slaughter_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise ValueError("کشتار یافت نشد.")

    counting_row_id = row[0]

    # حذف عکس‌های قبض‌ها (فایل‌ها)
    cursor.execute("SELECT image_path FROM slaughter_receipts WHERE slaughter_id = ?", (slaughter_id,))
    for r in cursor.fetchall():
        if r[0]:
            try:
                delete_receipt_image(r[0])
            except Exception:
                pass

    # حذف کشتار (CASCADE باعث حذف weighing_forms، receipts و... می‌شود)
    cursor.execute("DELETE FROM slaughters WHERE slaughter_id = ?", (slaughter_id,))

    # حذف ردیف شمارش
    cursor.execute("DELETE FROM counting_rows WHERE row_id = ?", (counting_row_id,))

    conn.commit()
    conn.close()

    # حذف پوشه‌ی عکس‌های قبض
    try:
        delete_slaughter_receipts_folder(slaughter_id)
    except Exception:
        pass


# ==========================================
# بکاپ خودکار / دستی (بدون تغییر)
# ==========================================

def auto_backup():
    if not os.path.exists(DB_NAME):
        return None
    backup_dir = _get_backup_dir()
    try:
        import jdatetime
        today = jdatetime.date.today().strftime("%Y-%m-%d")
    except ImportError:
        today = datetime.now().strftime("%Y-%m-%d")
    prefix = f"auto_{today}"
    existing = [f for f in os.listdir(backup_dir) if f.startswith(prefix)]
    if existing:
        return None
    filename = f"auto_{today}.db"
    dst = os.path.join(backup_dir, filename)
    try:
        shutil.copy2(DB_NAME, dst)
    except OSError as error:
        return f"ERROR: {error}"
    _cleanup_old_backups("auto", MAX_AUTO_BACKUPS)
    return dst


def before_exit_backup():
    if not os.path.exists(DB_NAME):
        return None
    backup_dir = _get_backup_dir()
    try:
        import jdatetime
        ts = jdatetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    except ImportError:
        ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"before_exit_{ts}.db"
    dst = os.path.join(backup_dir, filename)
    try:
        shutil.copy2(DB_NAME, dst)
    except OSError:
        return None
    _cleanup_old_backups("before_exit", MAX_BEFORE_EXIT_BACKUPS)
    return dst


def manual_backup():
    if not os.path.exists(DB_NAME):
        return None
    backup_dir = _get_backup_dir()
    try:
        import jdatetime
        ts = jdatetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    except ImportError:
        ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"manual_{ts}.db"
    dst = os.path.join(backup_dir, filename)
    try:
        shutil.copy2(DB_NAME, dst)
    except OSError as error:
        return f"ERROR: {error}"
    _cleanup_old_backups("manual", MAX_MANUAL_BACKUPS)
    return dst


def _cleanup_old_backups(prefix, max_count):
    backup_dir = _get_backup_dir()
    if not os.path.isdir(backup_dir):
        return
    files = sorted([f for f in os.listdir(backup_dir) if f.startswith(f"{prefix}_") and f.endswith(".db")])
    while len(files) > max_count:
        old = files.pop(0)
        try:
            os.remove(os.path.join(backup_dir, old))
        except OSError:
            pass


def list_backups():
    backup_dir = _get_backup_dir()
    if not os.path.isdir(backup_dir):
        return []
    files = [f for f in os.listdir(backup_dir) if f.endswith(".db")]
    result = []
    for f in files:
        path = os.path.join(backup_dir, f)
        try:
            mtime = os.path.getmtime(path)
            size = os.path.getsize(path)
        except OSError:
            continue
        if f.startswith("auto_"):
            btype = "auto"
        elif f.startswith("before_exit_"):
            btype = "before_exit"
        elif f.startswith("manual_"):
            btype = "manual"
        elif f.startswith("before_restore_"):
            btype = "before_restore"
        else:
            btype = "other"
        result.append({"filename": f, "path": path, "size": size, "mtime": mtime, "type": btype})
    result.sort(key=lambda x: x["mtime"], reverse=True)
    return result


def format_size(num_bytes):
    if num_bytes < 1024:
        return f"{num_bytes} B"
    if num_bytes < 1024 * 1024:
        return f"{num_bytes / 1024:.1f} KB"
    return f"{num_bytes / (1024 * 1024):.2f} MB"


def format_shamsi_datetime(timestamp):
    try:
        import jdatetime
        dt = datetime.fromtimestamp(timestamp)
        sh = jdatetime.datetime.fromgregorian(datetime=dt)
        return sh.strftime("%Y/%m/%d - %H:%M")
    except ImportError:
        return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M")


BACKUP_TYPE_NAMES = {
    "auto": "خودکار",
    "before_exit": "قبل از خروج",
    "manual": "دستی",
    "before_restore": "ایمنی",
    "other": "سایر",
}


def restore_backup(backup_filename):
    backup_dir = _get_backup_dir()
    src = os.path.join(backup_dir, backup_filename)

    if not os.path.exists(src):
        raise ValueError(f"بکاپ «{backup_filename}» یافت نشد.")

    import gc
    gc.collect()

    if os.path.exists(DB_NAME):
        try:
            import jdatetime
            ts = jdatetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        except ImportError:
            ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

        safety = os.path.join(backup_dir, f"before_restore_{ts}.db")
        try:
            shutil.copy2(DB_NAME, safety)
        except OSError:
            pass

        _cleanup_old_backups("before_restore", MAX_BEFORE_RESTORE_BACKUPS)

    try:
        shutil.copy2(src, DB_NAME)
    except PermissionError:
        raise ValueError("خطا: فایل دیتابیس در حال استفاده است. لطفاً برنامه را ببندید و دوباره امتحان کنید.")
    except OSError as e:
        raise ValueError(f"خطا در بازیابی: {e}")

    return src


def export_backup_zip(output_path=None):
    if not os.path.exists(DB_NAME):
        raise ValueError("دیتابیس وجود ندارد.")
    if output_path is None:
        reports_dir = _get_reports_dir()
        try:
            import jdatetime
            ts = jdatetime.datetime.now().strftime("%Y-%m-%d_%H-%M")
        except ImportError:
            ts = datetime.now().strftime("%Y-%m-%d_%H-%M")
        filename = f"backup_{ts}.zip"
        output_path = os.path.join(reports_dir, filename)
    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(DB_NAME, "loading_system.db")
        receipts_dir = get_receipts_dir()
        for root, dirs, files in os.walk(receipts_dir):
            for f in files:
                full = os.path.join(root, f)
                rel = os.path.relpath(full, BASE_DIR)
                try:
                    zf.write(full, rel)
                except OSError:
                    pass
        db_size = os.path.getsize(DB_NAME)
        try:
            import jdatetime
            now_str = jdatetime.datetime.now().strftime("%Y/%m/%d - %H:%M")
        except ImportError:
            now_str = datetime.now().strftime("%Y/%m/%d - %H:%M")
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM slaughters")
            count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM slaughter_receipts")
            receipts_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM daily_invoices")
            invoices_count = cursor.fetchone()[0]
            conn.close()
        except Exception:
            count = 0
            receipts_count = 0
            invoices_count = 0
        info = (
            "سیستم توزین محصولات\n"
            "─────────────────────\n"
            f"تاریخ بکاپ: {now_str}\n"
            f"حجم دیتابیس: {format_size(db_size)}\n"
            f"تعداد کشتارها: {count}\n"
            f"تعداد قبض‌ها: {receipts_count}\n"
            f"تعداد صورتحساب‌ها: {invoices_count}\n"
            f"نسخه: 1.3\n"
        )
        zf.writestr("info.txt", info.encode("utf-8"))
    return output_path


def import_backup_zip(zip_path):
    if not os.path.exists(zip_path):
        raise ValueError(f"فایل ZIP یافت نشد: {zip_path}")
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            names = zf.namelist()
            if "loading_system.db" not in names:
                raise ValueError("فایل ZIP معتبر نیست.\n(loading_system.db در آن یافت نشد)")
    except zipfile.BadZipFile:
        raise ValueError("فایل ZIP خراب است.")
    if os.path.exists(DB_NAME):
        try:
            import jdatetime
            ts = jdatetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        except ImportError:
            ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        backup_dir = _get_backup_dir()
        safety = os.path.join(backup_dir, f"before_restore_{ts}.db")
        try:
            shutil.copy2(DB_NAME, safety)
        except OSError:
            pass
        _cleanup_old_backups("before_restore", MAX_BEFORE_RESTORE_BACKUPS)
    with zipfile.ZipFile(zip_path, "r") as zf:
        temp_dir = os.path.join(BASE_DIR, "temp_restore")
        os.makedirs(temp_dir, exist_ok=True)
        zf.extract("loading_system.db", temp_dir)
        for name in zf.namelist():
            if name.startswith("receipts/"):
                try:
                    zf.extract(name, temp_dir)
                except Exception:
                    pass
        extracted_db = os.path.join(temp_dir, "loading_system.db")
        try:
            test_conn = sqlite3.connect(extracted_db)
            test_conn.execute("SELECT COUNT(*) FROM users")
            test_conn.close()
        except sqlite3.DatabaseError as e:
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise ValueError(f"فایل دیتابیس داخل ZIP معتبر نیست:\n{e}")

        shutil.copy2(extracted_db, DB_NAME)
        extracted_receipts = os.path.join(temp_dir, "receipts")
        if os.path.isdir(extracted_receipts):
            if os.path.isdir(RECEIPTS_DIR):
                try:
                    shutil.rmtree(RECEIPTS_DIR)
                except OSError:
                    pass
            try:
                shutil.copytree(extracted_receipts, RECEIPTS_DIR)
            except OSError:
                pass
        try:
            shutil.rmtree(temp_dir)
        except OSError:
            pass
    return DB_NAME


def get_database_size():
    if not os.path.exists(DB_NAME):
        return 0
    return os.path.getsize(DB_NAME)


if __name__ == "__main__":
    initialize_database()
