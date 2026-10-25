# -*- coding: utf-8 -*-
"""
توابع سیستم توزین — نسخه‌ی کامل (صورتحساب روزانه)
"""

from datetime import datetime, timedelta
from database import get_connection
try:
    import jdatetime
    HAS_JDATETIME = True
except ImportError:
    HAS_JDATETIME = False
import csv, os, hashlib

def safe_float(value, default=0.0):
    if value is None or value == "":
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default

PBKDF2_ITERATIONS = 100_000
HASH_ALGO = "pbkdf2_sha256"

def hash_password(password):
    salt = os.urandom(16)
    h = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return f"{HASH_ALGO}${PBKDF2_ITERATIONS}${salt.hex()}${h.hex()}"

def verify_password(password, stored):
    if not stored:
        return False
    if "$" not in stored:
        return password == stored
    try:
        algo, iters, salt_hex, hash_hex = stored.split("$")
        if algo != HASH_ALGO:
            return False
        salt = bytes.fromhex(salt_hex)
        h = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, int(iters))
        return h.hex() == hash_hex
    except (ValueError, TypeError):
        return False

def is_hashed(stored):
    return stored is not None and "$" in stored

def get_shamsi_now():
    if HAS_JDATETIME:
        return jdatetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S")
    return datetime.now().strftime("%Y/%m/%d %H:%M:%S")

def get_shamsi_today():
    if HAS_JDATETIME:
        return jdatetime.date.today().strftime("%Y/%m/%d")
    return datetime.now().strftime("%Y/%m/%d")

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
        g_date = datetime.combine(work_day, datetime.min.time())
        sh = jdatetime.datetime.fromgregorian(datetime=g_date)
        shamsi_str = sh.strftime("%Y/%m/%d")
        DAY_NAMES = ["دوشنبه", "سه‌شنبه", "چهارشنبه", "پنجشنبه", "جمعه", "شنبه", "یکشنبه"]
        day_name = DAY_NAMES[work_day.weekday()]
        return shamsi_str, day_name
    except ImportError:
        work_day = get_work_day()
        return work_day.strftime("%Y/%m/%d"), ""

def is_within_edit_window(completed_at_str, minutes=15):
    if not completed_at_str:
        return True
    try:
        completed = datetime.strptime(completed_at_str, "%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        return False
    elapsed = datetime.now() - completed
    return elapsed.total_seconds() <= minutes * 60

def get_minutes_since(operation_datetime_str):
    try:
        op_time = datetime.strptime(operation_datetime_str, "%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        return 0
    elapsed = datetime.now() - op_time
    return int(elapsed.total_seconds() // 60)

def login(username, password):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT user_id, username, password, full_name, role, failed_attempts, locked_until, can_edit_locked "
        "FROM users WHERE username = ? AND active = 1",
        (username,)
    )
    user = cursor.fetchone()
    if user is None:
        conn.close()
        return {"success": False, "message": "کاربر یافت نشد."}
    user_id = user[0]; db_password = user[2]; user_role = user[4]; failed_attempts = user[5]; locked_until = user[6]
    is_admin = (str(user_role).strip().lower() == "admin")
    if not is_admin and locked_until:
        try:
            locked_time = datetime.strptime(locked_until, "%Y-%m-%d %H:%M:%S")
            if datetime.now() < locked_time:
                conn.close()
                return {"success": False, "message": f"حساب کاربری تا {locked_until} قفل است."}
        except (ValueError, TypeError): pass
    if verify_password(password, db_password):
        if not is_hashed(db_password):
            cursor.execute("UPDATE users SET password = ?, failed_attempts = 0, locked_until = NULL WHERE user_id = ?", (hash_password(password), user_id))
        else:
            cursor.execute("UPDATE users SET failed_attempts = 0, locked_until = NULL WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()
        return {"success": True, "user": user}
    if is_admin:
        conn.close()
        return {"success": False, "message": "رمز عبور اشتباه است."}
    failed_attempts += 1
    if failed_attempts >= 3:
        locked_until = (datetime.now() + timedelta(minutes=15)).strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("UPDATE users SET failed_attempts = ?, locked_until = ? WHERE user_id = ?", (failed_attempts, locked_until, user_id))
        conn.commit()
        conn.close()
        return {"success": False, "message": "حساب کاربری به مدت 15 دقیقه قفل شد."}
    else:
        cursor.execute("UPDATE users SET failed_attempts = ? WHERE user_id = ?", (failed_attempts, user_id))
        conn.commit()
        conn.close()
        return {"success": False, "message": f"رمز اشتباه است. تعداد خطا: {failed_attempts}/3"}

def add_user(username, password, full_name, role):
    conn = get_connection(); cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM users WHERE username = ?", (username,))
    if cursor.fetchone():
        conn.close()
        raise ValueError(f"کاربر «{username}» قبلاً ثبت شده است.")
    cursor.execute("INSERT INTO users (username, password, full_name, role) VALUES (?, ?, ?, ?)", (username, hash_password(password), full_name, role))
    conn.commit(); conn.close()

def update_user(user_id, password=None, full_name=None, role=None, active=None, can_edit_locked=None):
    conn = get_connection(); cursor = conn.cursor()
    cursor.execute("SELECT password, full_name, role, active, can_edit_locked FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    if row is None:
        conn.close(); raise ValueError("کاربر یافت نشد.")
    new_password = hash_password(password) if password is not None else row[0]
    new_full_name = full_name if full_name is not None else row[1]
    new_role = role if role is not None else row[2]
    new_active = active if active is not None else row[3]
    new_can_edit = can_edit_locked if can_edit_locked is not None else row[4]
    cursor.execute(
        "UPDATE users SET password = ?, full_name = ?, role = ?, active = ?, can_edit_locked = ? WHERE user_id = ?",
        (new_password, new_full_name, new_role, new_active, new_can_edit, user_id)
    )
    conn.commit(); conn.close()

def delete_user(user_id):
    conn = get_connection(); cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,))
    if not cursor.fetchone():
        conn.close(); raise ValueError("کاربر یافت نشد.")
    cursor.execute("SELECT COUNT(*) FROM counting_rows WHERE operator_id = ?", (user_id,))
    count = cursor.fetchone()[0]
    if count > 0:
        conn.close(); raise ValueError(f"این کاربر {count} سابقه‌ی شمارش دارد و قابل حذف نیست.\nبه‌جای حذف، آن را غیرفعال کنید.")
    cursor.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
    conn.commit(); conn.close()

def unlock_user(user_id):
    conn = get_connection(); cursor = conn.cursor()
    cursor.execute("UPDATE users SET failed_attempts = 0, locked_until = NULL WHERE user_id = ?", (user_id,))
    conn.commit(); conn.close()

def get_users(only_active=False):
    conn = get_connection(); cursor = conn.cursor()
    if only_active:
        cursor.execute("SELECT user_id, username, full_name, role, active, can_edit_locked FROM users WHERE active = 1")
    else:
        cursor.execute("SELECT user_id, username, full_name, role, active, can_edit_locked FROM users")
    rows = cursor.fetchall(); conn.close(); return rows

def user_can_edit_locked(user):
    """
    آیا کاربر می‌تواند فرم‌های قفل‌شده را ویرایش کند؟
    user: دیکشنری current_user
    """
    if not user:
        return False
    role = str(user.get("role", "")).strip().lower()
    if role == "admin":
        return True
    return bool(user.get("can_edit_locked", 0))

def migrate_plain_passwords():
    conn = get_connection(); cursor = conn.cursor()
    cursor.execute("SELECT user_id, password FROM users")
    rows = cursor.fetchall(); migrated = 0
    for user_id, pwd in rows:
        if not is_hashed(pwd):
            cursor.execute("UPDATE users SET password = ? WHERE user_id = ?", (hash_password(pwd), user_id))
            migrated += 1
    conn.commit(); conn.close(); return migrated

def add_product(product_name, category, parent_id=None):
    conn = get_connection(); cursor = conn.cursor()
    if parent_id is not None:
        cursor.execute("SELECT 1 FROM products WHERE product_name = ? AND category = ? AND parent_id = ?", (product_name, category, parent_id))
    else:
        cursor.execute("SELECT 1 FROM products WHERE product_name = ? AND category = ? AND parent_id IS NULL", (product_name, category))
    if cursor.fetchone():
        conn.close(); raise ValueError(f"محصول «{product_name}» قبلاً ثبت شده است.")
    cursor.execute("INSERT INTO products (product_name, category, parent_id) VALUES (?, ?, ?)", (product_name, category, parent_id))
    conn.commit(); conn.close()

def update_product(product_id, product_name=None, category=None, parent_id=None, active=None):
    conn = get_connection(); cursor = conn.cursor()
    cursor.execute("SELECT product_name, category, parent_id, active FROM products WHERE product_id = ?", (product_id,))
    row = cursor.fetchone()
    if row is None:
        conn.close(); raise ValueError("محصول یافت نشد.")
    new_name = product_name if product_name is not None else row[0]
    new_category = category if category is not None else row[1]
    new_parent = parent_id if parent_id is not None else row[2]
    new_active = active if active is not None else row[3]
    cursor.execute("UPDATE products SET product_name = ?, category = ?, parent_id = ?, active = ? WHERE product_id = ?", (new_name, new_category, new_parent, new_active, product_id))
    conn.commit(); conn.close()

def delete_product(product_id):
    conn = get_connection(); cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM products WHERE product_id = ?", (product_id,))
    if not cursor.fetchone():
        conn.close(); raise ValueError("محصول یافت نشد.")
    cursor.execute("SELECT COUNT(*) FROM weighing_alayeshat_rows WHERE product_id = ?", (product_id,))
    count1 = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM daily_alayeshat_rows WHERE product_id = ?", (product_id,))
    count2 = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM products WHERE parent_id = ?", (product_id,))
    count3 = cursor.fetchone()[0]
    total = count1 + count2
    if total > 0 or count3 > 0:
        conn.close(); raise ValueError(f"این محصول {total} سابقه و {count3} زیرمجموعه دارد و قابل حذف نیست.\nبه‌جای حذف، آن را غیرفعال کنید.")
    cursor.execute("DELETE FROM products WHERE product_id = ?", (product_id,))
    conn.commit(); conn.close()

def get_products(only_active=False, category=None, parent_id=None):
    conn = get_connection(); cursor = conn.cursor()
    conditions, params = [], []
    if only_active: conditions.append("active = 1")
    if category: conditions.append("category = ?"); params.append(category)
    if parent_id is not None:
        if parent_id == 0: conditions.append("parent_id IS NULL")
        else: conditions.append("parent_id = ?"); params.append(parent_id)
    query = "SELECT product_id, product_name, category, parent_id, active FROM products"
    if conditions: query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY product_id"
    cursor.execute(query, params)
    rows = cursor.fetchall(); conn.close(); return rows

def get_products_by_category(category, only_active=True):
    conn = get_connection(); cursor = conn.cursor()
    if only_active:
        cursor.execute("SELECT product_id, product_name, parent_id FROM products WHERE category = ? AND active = 1 ORDER BY product_id", (category,))
    else:
        cursor.execute("SELECT product_id, product_name, parent_id FROM products WHERE category = ? ORDER BY product_id", (category,))
    rows = cursor.fetchall(); conn.close(); return rows

def get_sub_products(parent_id, only_active=True):
    conn = get_connection(); cursor = conn.cursor()
    if only_active:
        cursor.execute("SELECT product_id, product_name, category FROM products WHERE parent_id = ? AND active = 1 ORDER BY product_id", (parent_id,))
    else:
        cursor.execute("SELECT product_id, product_name, category FROM products WHERE parent_id = ? ORDER BY product_id", (parent_id,))
    rows = cursor.fetchall(); conn.close(); return rows

def add_basket(weight):
    conn = get_connection(); cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM basket_types WHERE weight = ?", (weight,))
    if cursor.fetchone():
        conn.close(); raise ValueError(f"سبد با وزن {weight} قبلاً ثبت شده است.")
    cursor.execute("INSERT INTO basket_types (weight) VALUES (?)", (weight,))
    conn.commit(); conn.close()

def update_basket(basket_id, weight=None, active=None):
    conn = get_connection(); cursor = conn.cursor()
    cursor.execute("SELECT weight, active FROM basket_types WHERE basket_id = ?", (basket_id,))
    row = cursor.fetchone()
    if row is None:
        conn.close(); raise ValueError("سبد یافت نشد.")
    new_weight = weight if weight is not None else row[0]
    new_active = active if active is not None else row[1]
    cursor.execute("SELECT 1 FROM basket_types WHERE weight = ? AND basket_id != ?", (new_weight, basket_id))
    if cursor.fetchone():
        conn.close(); raise ValueError(f"سبد دیگری با وزن {new_weight} وجود دارد.")
    cursor.execute("UPDATE basket_types SET weight = ?, active = ? WHERE basket_id = ?", (new_weight, new_active, basket_id))
    conn.commit(); conn.close()

def delete_basket(basket_id):
    conn = get_connection(); cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM basket_types WHERE basket_id = ?", (basket_id,))
    if not cursor.fetchone():
        conn.close(); raise ValueError("سبد یافت نشد.")
    cursor.execute("SELECT COUNT(*) FROM weighing_plucked_baskets WHERE basket_id = ?", (basket_id,))
    count = cursor.fetchone()[0]
    if count > 0:
        conn.close(); raise ValueError(f"این سبد در {count} عملیات استفاده شده و قابل حذف نیست.\nبه‌جای حذف، آن را غیرفعال کنید.")
    cursor.execute("DELETE FROM basket_types WHERE basket_id = ?", (basket_id,))
    conn.commit(); conn.close()

def get_baskets(only_active=False):
    conn = get_connection(); cursor = conn.cursor()
    if only_active:
        cursor.execute("SELECT basket_id, weight, active FROM basket_types WHERE active = 1 ORDER BY weight")
    else:
        cursor.execute("SELECT basket_id, weight, active FROM basket_types ORDER BY weight")
    rows = cursor.fetchall(); conn.close(); return rows

def get_slaughter(slaughter_id):
    conn = get_connection(); cursor = conn.cursor()
    cursor.execute("""
        SELECT s.slaughter_id, s.form_date, s.day_name, s.slaughter_number, s.created_at, s.operator_id, s.counting_row_id, u.full_name AS operator_name, cr.completed_at AS counting_completed, wf.completed_at AS weighing_completed, df.completed_at AS daily_completed
        FROM slaughters s
        LEFT JOIN users u ON u.user_id = s.operator_id
        LEFT JOIN counting_rows cr ON cr.row_id = s.counting_row_id
        LEFT JOIN weighing_forms wf ON wf.slaughter_id = s.slaughter_id
        LEFT JOIN daily_forms df ON df.form_date = s.form_date
        WHERE s.slaughter_id = ?
    """, (slaughter_id,))
    row = cursor.fetchone(); conn.close()
    if not row: return None
    return {
        "slaughter_id": row[0], "form_date": row[1], "day_name": row[2], "slaughter_number": row[3], "created_at": row[4], "operator_id": row[5], "counting_row_id": row[6], "operator_name": row[7] or "", "counting_completed": bool(row[8]), "weighing_completed": bool(row[9]), "daily_completed": bool(row[10]),
    }

def get_slaughters_by_date(form_date):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT s.slaughter_id, s.slaughter_number, s.created_at, s.operator_id, 
               u.full_name AS operator_name, cr.hook_count, cr.packed, 
               wf.completed_at AS weighing_completed, 
               wf.locked_at AS weighing_locked,
               df.completed_at AS daily_completed, 
               wf.loss_percent, df.waste, cr.row_id AS counting_row_id, 
               cr.completed_at AS counting_completed_at, 
               cr.locked_at AS counting_locked_at
        FROM slaughters s
        LEFT JOIN users u ON u.user_id = s.operator_id
        LEFT JOIN counting_rows cr ON cr.row_id = s.counting_row_id
        LEFT JOIN weighing_forms wf ON wf.slaughter_id = s.slaughter_id
        LEFT JOIN daily_forms df ON df.form_date = s.form_date
        WHERE s.form_date = ?
        ORDER BY s.slaughter_number
    """, (form_date,))
    rows = cursor.fetchall()
    conn.close()
    return [
        {
            "slaughter_id": r[0], 
            "slaughter_number": r[1], 
            "created_at": r[2], 
            "operator_id": r[3], 
            "operator_name": r[4] or "", 
            "hook_count": r[5] or 0, 
            "packed": r[6] or 0, 
            "weighing_completed": bool(r[7]), 
            "weighing_locked": bool(r[8]),
            "daily_completed": bool(r[9]), 
            "loss_percent": safe_float(r[10]), 
            "waste": safe_float(r[11]), 
            "counting_row_id": r[12], 
            "counting_completed_at": r[13], 
            "counting_locked_at": r[14], 
            "is_pending": False,
        } for r in rows
    ]

def delete_slaughter(slaughter_id):
    from database import delete_slaughter_receipts_folder
    conn = get_connection(); cursor = conn.cursor()
    cursor.execute("SELECT counting_row_id FROM slaughters WHERE slaughter_id = ?", (slaughter_id,))
    row = cursor.fetchone()
    if not row:
        conn.close(); raise ValueError("کشتار یافت نشد.")
    cursor.execute("DELETE FROM counting_rows WHERE row_id = ?", (row[0],))
    conn.commit(); conn.close()
    delete_slaughter_receipts_folder(slaughter_id)

def get_counting_rows(form_date):
    conn = get_connection(); cursor = conn.cursor()
    cursor.execute("SELECT row_id, row_num, hook_count, waste, deaths, pieces, packed, notes, completed_at, locked_at FROM counting_rows WHERE form_date = ? ORDER BY row_num", (form_date,))
    rows = cursor.fetchall(); conn.close()
    return [{"row_id": r[0], "row_num": r[1], "hook_count": r[2] or 0, "waste": r[3] or 0, "deaths": r[4] or 0, "pieces": r[5] or 0, "packed": r[6] or 0, "notes": r[7] or "", "completed_at": r[8], "locked_at": r[9]} for r in rows]

def get_counting_row(row_id):
    conn = get_connection(); cursor = conn.cursor()
    cursor.execute("SELECT row_id, form_date, day_name, row_num, hook_count, waste, deaths, pieces, packed, notes, created_at, completed_at, locked_at, operator_id FROM counting_rows WHERE row_id = ?", (row_id,))
    r = cursor.fetchone(); conn.close()
    if not r: return None
    return {"row_id": r[0], "form_date": r[1], "day_name": r[2], "row_num": r[3], "hook_count": r[4] or 0, "waste": r[5] or 0, "deaths": r[6] or 0, "pieces": r[7] or 0, "packed": r[8] or 0, "notes": r[9] or "", "created_at": r[10], "completed_at": r[11], "locked_at": r[12], "operator_id": r[13]}

def add_counting_row(form_date, day_name, operator_id, data):
    conn = get_connection(); cursor = conn.cursor()
    cursor.execute("SELECT COALESCE(MAX(row_num), 0) + 1 FROM counting_rows WHERE form_date = ?", (form_date,))
    next_num = cursor.fetchone()[0]
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
        INSERT INTO counting_rows (form_date, day_name, row_num, hook_count, waste, deaths, pieces, packed, notes, created_at, operator_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (form_date, day_name, next_num, int(safe_float(data.get("hook_count", 0))), int(safe_float(data.get("waste", 0))), int(safe_float(data.get("deaths", 0))), int(safe_float(data.get("pieces", 0))), int(safe_float(data.get("packed", 0))), data.get("notes", ""), now, operator_id))
    row_id = cursor.lastrowid
    conn.commit(); conn.close()
    return row_id

def update_counting_row(row_id, data):
    conn = get_connection(); cursor = conn.cursor()
    cursor.execute("""
        UPDATE counting_rows SET hook_count = ?, waste = ?, deaths = ?, pieces = ?, packed = ?, notes = ? WHERE row_id = ?
    """, (int(safe_float(data.get("hook_count", 0))), int(safe_float(data.get("waste", 0))), int(safe_float(data.get("deaths", 0))), int(safe_float(data.get("pieces", 0))), int(safe_float(data.get("packed", 0))), data.get("notes", ""), row_id))
    conn.commit(); conn.close()

def delete_counting_row(row_id):
    conn = get_connection(); cursor = conn.cursor()
    cursor.execute("SELECT form_date FROM counting_rows WHERE row_id = ?", (row_id,))
    row = cursor.fetchone()
    if not row:
        conn.close(); raise ValueError("ردیف یافت نشد.")
    form_date = row[0]
    cursor.execute("DELETE FROM counting_rows WHERE row_id = ?", (row_id,))
    cursor.execute("SELECT row_id FROM counting_rows WHERE form_date = ? ORDER BY row_num", (form_date,))
    remaining = cursor.fetchall()
    for i, (rid,) in enumerate(remaining, start=1):
        cursor.execute("UPDATE counting_rows SET row_num = ? WHERE row_id = ?", (i, rid))
    conn.commit(); conn.close()

def complete_counting_row(row_id, operator_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT form_date, day_name, locked_at FROM counting_rows WHERE row_id = ?", (row_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise ValueError("ردیف یافت نشد.")
    form_date, day_name, locked_at = row

    # بررسی اینکه آیا قبلاً کشتاری برای این ردیف ساخته شده یا نه
    cursor.execute("SELECT slaughter_id FROM slaughters WHERE counting_row_id = ?", (row_id,))
    existing = cursor.fetchone()

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if existing:
        # کشتار قبلاً ساخته شده → فقط قفل را دوباره فعال کن
        slaughter_id = existing[0]
        cursor.execute("UPDATE counting_rows SET locked_at = ? WHERE row_id = ?", (now, row_id))
        conn.commit()
        conn.close()
        return slaughter_id

    # کشتار جدید
    cursor.execute("SELECT COALESCE(MAX(slaughter_number), 0) + 1 FROM slaughters WHERE form_date = ?", (form_date,))
    next_num = cursor.fetchone()[0]

    cursor.execute("INSERT INTO slaughters (counting_row_id, form_date, day_name, slaughter_number, created_at, operator_id) VALUES (?, ?, ?, ?, ?, ?)", (row_id, form_date, day_name, next_num, now, operator_id))
    slaughter_id = cursor.lastrowid
    cursor.execute("UPDATE counting_rows SET locked_at = ? WHERE row_id = ?", (now, row_id))
    cursor.execute("INSERT INTO weighing_forms (slaughter_id, created_at) VALUES (?, ?)", (slaughter_id, now))
    conn.commit()
    conn.close()
    return slaughter_id

def get_weighing_form(slaughter_id):
    conn = get_connection(); cursor = conn.cursor()
    cursor.execute("SELECT form_id, total_full_weight, total_net_weight, loss_percent, completed_at, locked_at, created_at, live_weight FROM weighing_forms WHERE slaughter_id = ?", (slaughter_id,))
    row = cursor.fetchone()
    if not row:
        conn.close(); return None
    form_id = row[0]
    result = {
        "form_id": form_id, "slaughter_id": slaughter_id, "total_full_weight": safe_float(row[1]), "total_net_weight": safe_float(row[2]), "loss_percent": safe_float(row[3]), "completed_at": row[4], "locked_at": row[5], "created_at": row[6], "live_weight": safe_float(row[7]), "plucked_rows": [], "alayeshat_rows": [],
    }
    cursor.execute("SELECT row_id, row_num, cart_number, is_bulk, empty_weight, full_weight, net_weight FROM weighing_plucked_rows WHERE form_id = ? ORDER BY row_num", (form_id,))
    for r in cursor.fetchall():
        row_id = r[0]
        cursor2 = conn.cursor()
        cursor2.execute("SELECT wb.basket_id, bt.weight, wb.count FROM weighing_plucked_baskets wb JOIN basket_types bt ON bt.basket_id = wb.basket_id WHERE wb.row_id = ?", (row_id,))
        baskets = cursor2.fetchall()
        cursor2.close()
        result["plucked_rows"].append({
            "row_id": row_id, "row_num": r[1], "cart_number": r[2] or "", "is_bulk": bool(r[3]), "empty_weight": safe_float(r[4]), "full_weight": safe_float(r[5]), "net_weight": safe_float(r[6]),
            "baskets": [{"basket_id": b[0], "weight": safe_float(b[1]), "count": b[2]} for b in baskets],
        })
    cursor.execute("SELECT war.row_id, war.row_num, war.product_id, p.product_name, war.empty_weight, war.full_weight, war.net_weight FROM weighing_alayeshat_rows war JOIN products p ON p.product_id = war.product_id WHERE war.form_id = ? ORDER BY war.row_num", (form_id,))
    for r in cursor.fetchall():
        result["alayeshat_rows"].append({"row_id": r[0], "row_num": r[1], "product_id": r[2], "product_name": r[3], "empty_weight": safe_float(r[4]), "full_weight": safe_float(r[5]), "net_weight": safe_float(r[6])})
    conn.close(); return result

def save_weighing_form(slaughter_id, plucked_rows, alayeshat_rows, live_weight=0.0):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT form_id FROM weighing_forms WHERE slaughter_id = ?", (slaughter_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise ValueError("فرم توزین یافت نشد.")
    
    form_id = row[0]

    cursor.execute("DELETE FROM weighing_plucked_baskets WHERE row_id IN (SELECT row_id FROM weighing_plucked_rows WHERE form_id = ?)", (form_id,))
    cursor.execute("DELETE FROM weighing_plucked_rows WHERE form_id = ?", (form_id,))
    cursor.execute("DELETE FROM weighing_alayeshat_rows WHERE form_id = ?", (form_id,))

    total_full, total_net, total_net_plucked = 0.0, 0.0, 0.0
    
    for i, row_data in enumerate(plucked_rows, start=1):
        empty_w = safe_float(row_data.get("empty_weight", 0))
        full_w = safe_float(row_data.get("full_weight", 0))
        net_w = max(0.0, full_w - empty_w)
        is_bulk = 1 if row_data.get("is_bulk") else 0
        total_full += full_w
        total_net += net_w
        total_net_plucked += net_w
        cursor.execute("""
            INSERT INTO weighing_plucked_rows 
            (form_id, row_num, cart_number, is_bulk, empty_weight, full_weight, net_weight) 
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (form_id, i, row_data.get("cart_number", ""), is_bulk, empty_w, full_w, net_w))
        plucked_row_id = cursor.lastrowid
        for b in row_data.get("baskets", []):
            cursor.execute("""
                INSERT INTO weighing_plucked_baskets (row_id, basket_id, count) 
                VALUES (?, ?, ?)
            """, (plucked_row_id, b["basket_id"], b["count"]))

    for i, row_data in enumerate(alayeshat_rows, start=1):
        empty_w = safe_float(row_data.get("empty_weight", 0))
        full_w = safe_float(row_data.get("full_weight", 0))
        net_w = max(0.0, full_w - empty_w)
        
        pid = row_data.get("product_id")
        
        if not pid:
            product_name = row_data.get("product_name", "")
            if product_name:
                cursor.execute("""
                    SELECT product_id FROM products 
                    WHERE product_name = ? AND category = 'alayeshat' 
                    LIMIT 1
                """, (product_name,))
                p_row = cursor.fetchone()
                if p_row:
                    pid = p_row[0]
        
        if not pid:
            continue
        
        cursor.execute("""
            INSERT INTO weighing_alayeshat_rows 
            (form_id, row_num, product_id, empty_weight, full_weight, net_weight) 
            VALUES (?, ?, ?, ?, ?, ?)
        """, (form_id, i, pid, empty_w, full_w, net_w))

    loss_percent = 0.0
    if live_weight > 0:
        loss_ratio = 1 - (total_net_plucked / live_weight)
        loss_percent = round(loss_ratio * 100, 5)
    cursor.execute("""
        UPDATE weighing_forms 
        SET total_full_weight = ?, total_net_weight = ?, loss_percent = ?, live_weight = ? 
        WHERE form_id = ?
    """, (round(total_full, 2), round(total_net, 2), loss_percent, round(live_weight, 2), form_id))

    conn.commit()
    conn.close()
    
    return {
        "total_full": round(total_full, 2),
        "total_net": round(total_net, 2),
        "loss_percent": loss_percent,
        "live_weight": round(live_weight, 2),
    }

def complete_weighing_form(slaughter_id):
    conn = get_connection(); cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("UPDATE weighing_forms SET completed_at = ? WHERE slaughter_id = ?", (now, slaughter_id))
    conn.commit(); conn.close()

def can_edit_weighing_form(slaughter_id, user_role):
    if user_role == "admin": return True
    conn = get_connection(); cursor = conn.cursor()
    cursor.execute("SELECT completed_at FROM weighing_forms WHERE slaughter_id = ?", (slaughter_id,))
    row = cursor.fetchone(); conn.close()
    if not row or not row[0]: return True
    return is_within_edit_window(row[0], 15)

def get_daily_form_by_date(form_date):
    conn = get_connection(); cursor = conn.cursor()
    cursor.execute("SELECT form_id, waste, completed_at, locked_at, created_at FROM daily_forms WHERE form_date = ?", (form_date,))
    row = cursor.fetchone()
    if not row:
        conn.close(); return None
    form_id = row[0]
    result = {
        "form_id": form_id, "form_date": form_date, "waste": safe_float(row[1]), "completed_at": row[2], "locked_at": row[3], "created_at": row[4], "packed_rows": [], "alayeshat_rows": [], "morgh_rows": [],
    }
    cursor.execute("SELECT row_id, row_num, buyer_name, total_net_weight FROM daily_packed_rows WHERE form_id = ? ORDER BY row_num", (form_id,))
    for r in cursor.fetchall():
        row_id = r[0]
        cursor2 = conn.cursor()
        cursor2.execute("SELECT cart_number, plucked_row_id FROM daily_packed_carts WHERE row_id = ?", (row_id,))
        carts = cursor2.fetchall(); cursor2.close()
        result["packed_rows"].append({"row_id": row_id, "row_num": r[1], "buyer_name": r[2] or "", "total_net_weight": safe_float(r[3]), "carts": [{"cart_number": c[0], "plucked_row_id": c[1]} for c in carts]})
    
    cursor.execute("""
        SELECT dar.customer_name, p.product_name, dar.weight, dar.row_num 
        FROM daily_alayeshat_rows dar 
        JOIN products p ON p.product_id = dar.product_id 
        WHERE dar.form_id = ? ORDER BY dar.row_num
    """, (form_id,))
    
    grouped_alayeshat = {}
    for r in cursor.fetchall():
        customer = r[0]
        product = r[1]
        weight = safe_float(r[2])
        row_num = r[3]
        
        if customer not in grouped_alayeshat:
            grouped_alayeshat[customer] = {
                "row_id": None, 
                "row_num": row_num, 
                "customer_name": customer, 
                "del_weight": "",
                "jigar_weight": "",
                "sangdane_weight": "",
                "pa_weight": "",
                "kale_weight": ""
            }
        
        if product == "دل":
            grouped_alayeshat[customer]["del_weight"] = weight
        elif product == "جگر":
            grouped_alayeshat[customer]["jigar_weight"] = weight
        elif product == "سنگدان":
            grouped_alayeshat[customer]["sangdane_weight"] = weight
        elif product == "پا":
            grouped_alayeshat[customer]["pa_weight"] = weight
        elif product == "کله":
            grouped_alayeshat[customer]["kale_weight"] = weight
            
    result["alayeshat_rows"] = list(grouped_alayeshat.values())

    cursor.execute("SELECT row_id, row_num, customer_name, lake_weight, piece_weight, sine_weight, ran_weight, bal_weight, gardan_weight, whole_weight, waste_weight FROM daily_morgh_rows WHERE form_id = ? ORDER BY row_num", (form_id,))
    for r in cursor.fetchall():
        result["morgh_rows"].append({"row_id": r[0], "row_num": r[1], "customer_name": r[2] or "", "lake_weight": safe_float(r[3]), "piece_weight": safe_float(r[4]), "sine_weight": safe_float(r[5]), "ran_weight": safe_float(r[6]), "bal_weight": safe_float(r[7]), "gardan_weight": safe_float(r[8]), "whole_weight": safe_float(r[9]), "waste_weight": safe_float(r[10])})
    conn.close(); return result

def get_or_create_daily_form(form_date, day_name, operator_id=None):
    conn = get_connection(); cursor = conn.cursor()
    cursor.execute("SELECT form_id FROM daily_forms WHERE form_date = ?", (form_date,))
    row = cursor.fetchone()
    if row:
        form_id = row[0]
    else:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("INSERT INTO daily_forms (form_date, day_name, created_at, operator_id) VALUES (?, ?, ?, ?)", (form_date, day_name, now, operator_id))
        form_id = cursor.lastrowid
        conn.commit()
    conn.close()
    return get_daily_form_by_date(form_date)

def get_available_carts_for_date(form_date):
    conn = get_connection(); cursor = conn.cursor()
    cursor.execute("""
        SELECT wpr.row_id, wpr.cart_number, wpr.net_weight, s.slaughter_number
        FROM weighing_plucked_rows wpr 
        JOIN weighing_forms wf ON wf.form_id = wpr.form_id 
        JOIN slaughters s ON s.slaughter_id = wf.slaughter_id
        WHERE s.form_date = ? 
        ORDER BY s.slaughter_number, wpr.row_num
    """, (form_date,))
    rows = cursor.fetchall(); conn.close()
    
    result = []
    for r in rows:
        result.append({
            "row_id": r[0], 
            "cart_number": r[1] or "", 
            "net_weight": safe_float(r[2]),
            "slaughter_number": r[3]
        })
    return result

def get_aggregated_alayeshat_for_date(form_date):
    conn = get_connection(); cursor = conn.cursor()
    cursor.execute("""
        SELECT p.product_id, p.product_name, SUM(war.net_weight) as total_net
        FROM weighing_alayeshat_rows war
        JOIN weighing_forms wf ON wf.form_id = war.form_id
        JOIN slaughters s ON s.slaughter_id = wf.slaughter_id
        JOIN products p ON p.product_id = war.product_id
        WHERE s.form_date = ?
        GROUP BY p.product_id
        ORDER BY p.product_id
    """, (form_date,))
    rows = cursor.fetchall(); conn.close()
    return [{"product_id": r[0], "product_name": r[1], "total_net": safe_float(r[2])} for r in rows]

def calc_carts_total(cart_row_ids):
    if not cart_row_ids: return 0.0
    conn = get_connection(); cursor = conn.cursor()
    placeholders = ",".join("?" * len(cart_row_ids))
    cursor.execute(f"SELECT COALESCE(SUM(net_weight), 0) FROM weighing_plucked_rows WHERE row_id IN ({placeholders})", cart_row_ids)
    total = safe_float(cursor.fetchone()[0]); conn.close(); return round(total, 2)

def calc_morgh_row_waste(lake, piece, whole):
    waste = (safe_float(lake) - safe_float(piece) - safe_float(whole))
    return round(waste, 2) if waste > 0 else 0.0

def save_daily_form_by_date(form_date, packed_rows, alayeshat_rows, morgh_rows):
    conn = get_connection(); cursor = conn.cursor()
    cursor.execute("SELECT form_id FROM daily_forms WHERE form_date = ?", (form_date,))
    row = cursor.fetchone()
    if not row:
        conn.close(); raise ValueError("فرم گزارش یافت نشد.")
    form_id = row[0]
    
    cursor.execute("DELETE FROM daily_packed_carts WHERE row_id IN (SELECT row_id FROM daily_packed_rows WHERE form_id = ?)", (form_id,))
    cursor.execute("DELETE FROM daily_packed_rows WHERE form_id = ?", (form_id,))
    cursor.execute("DELETE FROM daily_alayeshat_rows WHERE form_id = ?", (form_id,))
    cursor.execute("DELETE FROM daily_morgh_rows WHERE form_id = ?", (form_id,))
    
    for i, pr in enumerate(packed_rows, start=1):
        cart_ids = pr.get("cart_row_ids", [])
        total = calc_carts_total(cart_ids)
        cursor.execute("INSERT INTO daily_packed_rows (form_id, row_num, buyer_name, total_net_weight) VALUES (?, ?, ?, ?)", (form_id, i, pr.get("buyer_name", ""), total))
        packed_row_id = cursor.lastrowid
        for cid in cart_ids:
            cursor.execute("SELECT cart_number FROM weighing_plucked_rows WHERE row_id = ?", (cid,))
            c = cursor.fetchone()
            if c: cursor.execute("INSERT INTO daily_packed_carts (row_id, cart_number, plucked_row_id) VALUES (?, ?, ?)", (packed_row_id, c[0], cid))
            
    for i, row_data in enumerate(alayeshat_rows, start=1):
        customer_name = row_data.get("customer_name", "")
        for product_name, weight_key in [("دل", "del_weight"), ("جگر", "jigar_weight"), ("سنگدان", "sangdane_weight"), ("پا", "pa_weight"), ("کله", "kale_weight")]:
            weight = safe_float(row_data.get(weight_key, 0))
            if weight <= 0: continue
            cursor.execute("SELECT product_id FROM products WHERE product_name = ? AND category = 'alayeshat' LIMIT 1", (product_name,))
            p_row = cursor.fetchone()
            if not p_row:
                conn.close(); raise ValueError(f"محصول «{product_name}» در دیتابیس یافت نشد. لطفاً آن را در اطلاعات پایه ثبت کنید.")
            product_id = p_row[0]
            cursor.execute("INSERT INTO daily_alayeshat_rows (form_id, row_num, customer_name, product_id, weight) VALUES (?, ?, ?, ?, ?)", (form_id, i, customer_name, product_id, weight))

    for i, row_data in enumerate(morgh_rows, start=1):
        waste = calc_morgh_row_waste(row_data.get("lake_weight", 0), row_data.get("piece_weight", 0), row_data.get("whole_weight", 0))
        cursor.execute("""
            INSERT INTO daily_morgh_rows (form_id, row_num, customer_name, lake_weight, piece_weight, sine_weight, ran_weight, bal_weight, gardan_weight, whole_weight, waste_weight)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (form_id, i, row_data.get("customer_name", ""), safe_float(row_data.get("lake_weight", 0)), safe_float(row_data.get("piece_weight", 0)), safe_float(row_data.get("sine_weight", 0)), safe_float(row_data.get("ran_weight", 0)), safe_float(row_data.get("bal_weight", 0)), safe_float(row_data.get("gardan_weight", 0)), safe_float(row_data.get("whole_weight", 0)), waste))
    
    cursor.execute("SELECT COALESCE(SUM(waste_weight), 0) FROM daily_morgh_rows WHERE form_id = ?", (form_id,))
    waste_total = safe_float(cursor.fetchone()[0])
    cursor.execute("UPDATE daily_forms SET waste = ? WHERE form_id = ?", (waste_total, form_id))
    
    conn.commit(); conn.close()
    return {"waste": waste_total}

def complete_daily_form_by_date(form_date):
    conn = get_connection(); cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("UPDATE daily_forms SET completed_at = ? WHERE form_date = ?", (now, form_date))
    conn.commit(); conn.close()

def can_edit_daily_form_by_date(form_date, user_role):
    if user_role == "admin": return True
    conn = get_connection(); cursor = conn.cursor()
    cursor.execute("SELECT completed_at FROM daily_forms WHERE form_date = ?", (form_date,))
    row = cursor.fetchone(); conn.close()
    if not row or not row[0]: return True
    return is_within_edit_window(row[0], 15)

def get_weighing_alayeshat_total_for_date(form_date):
    conn = get_connection(); cursor = conn.cursor()
    cursor.execute("""
        SELECT COALESCE(SUM(war.net_weight), 0) 
        FROM weighing_alayeshat_rows war 
        JOIN weighing_forms wf ON wf.form_id = war.form_id 
        JOIN slaughters s ON s.slaughter_id = wf.slaughter_id
        WHERE s.form_date = ?
    """, (form_date,))
    row = cursor.fetchone(); conn.close()
    return safe_float(row[0]) if row else 0.0

def add_receipt(slaughter_id, operator_id, receipt_number="", receipt_date="", net_weight=0.0, car_plate="", driver_name="", buyer_name="", description="", image_source=None):
    from database import save_receipt_image
    conn = get_connection(); cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM slaughters WHERE slaughter_id = ?", (slaughter_id,))
    if not cursor.fetchone():
        conn.close(); raise ValueError("کشتار یافت نشد.")
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    image_path = None
    if image_source:
        try: image_path = save_receipt_image(slaughter_id, image_source)
        except Exception as e:
            conn.close(); raise ValueError(f"ذخیره عکس ناموفق: {e}")
    cursor.execute("""
        INSERT INTO slaughter_receipts (slaughter_id, receipt_number, receipt_date, net_weight, car_plate, driver_name, buyer_name, description, image_path, created_at, operator_id, completed_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (slaughter_id, receipt_number.strip() if receipt_number else "", receipt_date.strip() if receipt_date else "", safe_float(net_weight), car_plate.strip() if car_plate else "", driver_name.strip() if driver_name else "", buyer_name.strip() if buyer_name else "", description.strip() if description else "", image_path, now, operator_id, now))
    receipt_id = cursor.lastrowid
    conn.commit(); conn.close()
    return receipt_id

def get_receipts(slaughter_id):
    conn = get_connection(); cursor = conn.cursor()
    cursor.execute("""
        SELECT r.receipt_id, r.slaughter_id, r.receipt_number, r.receipt_date, r.net_weight, r.car_plate, r.driver_name, r.buyer_name, r.description, r.image_path, r.created_at, r.operator_id, r.completed_at, r.locked_at, u.full_name AS operator_name
        FROM slaughter_receipts r LEFT JOIN users u ON u.user_id = r.operator_id WHERE r.slaughter_id = ? ORDER BY r.receipt_id DESC
    """, (slaughter_id,))
    rows = cursor.fetchall(); conn.close()
    return [{"receipt_id": r[0], "slaughter_id": r[1], "receipt_number": r[2] or "", "receipt_date": r[3] or "", "net_weight": safe_float(r[4]), "car_plate": r[5] or "", "driver_name": r[6] or "", "buyer_name": r[7] or "", "description": r[8] or "", "image_path": r[9], "created_at": r[10], "operator_id": r[11], "completed_at": r[12], "locked_at": r[13], "operator_name": r[14] or ""} for r in rows]

def get_receipt(receipt_id):
    conn = get_connection(); cursor = conn.cursor()
    cursor.execute("""
        SELECT receipt_id, slaughter_id, receipt_number, receipt_date, net_weight, car_plate, driver_name, buyer_name, description, image_path, created_at, operator_id, completed_at, locked_at
        FROM slaughter_receipts WHERE receipt_id = ?
    """, (receipt_id,))
    r = cursor.fetchone(); conn.close()
    if not r: return None
    return {"receipt_id": r[0], "slaughter_id": r[1], "receipt_number": r[2] or "", "receipt_date": r[3] or "", "net_weight": safe_float(r[4]), "car_plate": r[5] or "", "driver_name": r[6] or "", "buyer_name": r[7] or "", "description": r[8] or "", "image_path": r[9], "created_at": r[10], "operator_id": r[11], "completed_at": r[12], "locked_at": r[13]}

def update_receipt(receipt_id, **fields):
    allowed = {"receipt_number", "receipt_date", "net_weight", "car_plate", "driver_name", "buyer_name", "description"}
    updates = []; params = []
    for key, value in fields.items():
        if key not in allowed: continue
        if key == "net_weight": value = safe_float(value)
        elif isinstance(value, str): value = value.strip()
        updates.append(f"{key} = ?"); params.append(value)
    if not updates: return
    params.append(receipt_id)
    conn = get_connection(); cursor = conn.cursor()
    cursor.execute(f"UPDATE slaughter_receipts SET {', '.join(updates)} WHERE receipt_id = ?", params)
    conn.commit(); conn.close()

def delete_receipt(receipt_id):
    from database import delete_receipt_image
    receipt = get_receipt(receipt_id)
    if not receipt: raise ValueError("قبض یافت نشد.")
    conn = get_connection(); cursor = conn.cursor()
    cursor.execute("DELETE FROM slaughter_receipts WHERE receipt_id = ?", (receipt_id,))
    conn.commit(); conn.close()
    if receipt.get("image_path"): delete_receipt_image(receipt["image_path"])

def lock_receipt(receipt_id):
    conn = get_connection(); cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("UPDATE slaughter_receipts SET locked_at = ? WHERE receipt_id = ?", (now, receipt_id))
    conn.commit(); conn.close()

def can_edit_receipt(receipt_data):
    if receipt_data.get("locked_at"): return False
    if not receipt_data.get("completed_at"): return True
    return is_within_edit_window(receipt_data["completed_at"], 15)

def count_receipts(slaughter_id):
    conn = get_connection(); cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM slaughter_receipts WHERE slaughter_id = ?", (slaughter_id,))
    n = cursor.fetchone()[0]; conn.close(); return n

# ==========================================
# صورتحساب روزانه (بر اساس تاریخ)
# ==========================================

def get_daily_invoice(form_date):
    conn = get_connection(); cursor = conn.cursor()
    cursor.execute("SELECT * FROM daily_invoices WHERE form_date = ?", (form_date,))
    columns = [description[0] for description in cursor.description]
    row = cursor.fetchone(); conn.close()
    if not row: return None
    return dict(zip(columns, row))

def get_or_create_daily_invoice(form_date, day_name, operator_id=None):
    conn = get_connection(); cursor = conn.cursor()
    cursor.execute("SELECT invoice_id FROM daily_invoices WHERE form_date = ?", (form_date,))
    row = cursor.fetchone()
    if not row:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            INSERT INTO daily_invoices (form_date, day_name, created_at, operator_id)
            VALUES (?, ?, ?, ?)
        """, (form_date, day_name, now, operator_id))
        conn.commit()
    conn.close()
    return get_daily_invoice(form_date)

def save_daily_invoice(form_date, data, image_source=None):
    from database import save_receipt_image
    conn = get_connection(); cursor = conn.cursor()
    cursor.execute("SELECT invoice_id, completed_at FROM daily_invoices WHERE form_date = ?", (form_date,))
    row = cursor.fetchone()
    if not row:
        conn.close(); raise ValueError("فرم صورتحساب روزانه یافت نشد.")

    current_completed_at = row[1]

    image_path = None
    if image_source:
        try:
            image_path = save_receipt_image(0, image_source)
        except Exception as e:
            conn.close(); raise ValueError(f"ذخیره عکس ناموفق: {e}")

    fields = ["invoice_number", "invoice_date", "description"]
    params = [data.get("invoice_number", ""), data.get("invoice_date", ""), data.get("description", "")]

    if image_path:
        fields.append("image_path")
        params.append(image_path)

    for i in range(1, 6):
        fields += [f"w{i}_full", f"w{i}_empty", f"w{i}_qty", f"w{i}_net", f"w{i}_rate", f"w{i}_amount"]
        params += [
            data.get(f"w{i}_full", 0), data.get(f"w{i}_empty", 0),
            data.get(f"w{i}_qty", 0), data.get(f"w{i}_net", 0),
            data.get(f"w{i}_rate", 0), data.get(f"w{i}_amount", 0)
        ]

    fields += ["total_weight", "total_amount"]
    params += [data.get("total_weight", 0), data.get("total_amount", 0)]

    fields += ["c1_amount", "c1_rate", "c1_total"]
    params += [data.get("c1_amount", 0), data.get("c1_rate", 0), data.get("c1_total", 0)]

    fields += ["c2_amount", "c2_rate", "c2_total"]
    params += [data.get("c2_amount", 0), data.get("c2_rate", 0), data.get("c2_total", 0)]

    for i in range(1, 10):
        fields += [f"e{i}_amount", f"e{i}_rate", f"e{i}_total"]
        params += [data.get(f"e{i}_amount", 0), data.get(f"e{i}_rate", 0), data.get(f"e{i}_total", 0)]

    fields += ["vat_rate", "vat_amount", "grand_total"]
    params += [data.get("vat_rate", 10), data.get("vat_amount", 0), data.get("grand_total", 0)]

    # اگر این اولین ذخیره است (completed_at خالی) → completed_at = now
    # اگر قبلاً ست شده → دست نزن (admin_unlock_form مسئول ریست است)
    if not current_completed_at:
        fields.append("completed_at")
        params.append(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    set_clause = ", ".join([f"{f} = ?" for f in fields])
    params.append(form_date)

    try:
        cursor.execute(f"UPDATE daily_invoices SET {set_clause} WHERE form_date = ?", params)
        conn.commit()
    except Exception as e:
        conn.rollback()
        conn.close()
        raise ValueError(f"خطا در ذخیره: {e}")

    conn.close()
    return get_daily_invoice(form_date)

def lock_daily_invoice(form_date):
    conn = get_connection(); cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("UPDATE daily_invoices SET completed_at = ?, locked_at = ? WHERE form_date = ?", (now, now, form_date))
    conn.commit(); conn.close()

def delete_daily_invoice(form_date):
    conn = get_connection(); cursor = conn.cursor()
    cursor.execute("DELETE FROM daily_invoices WHERE form_date = ?", (form_date,))
    conn.commit(); conn.close()

def can_edit_daily_invoice(form_date, user_role):
    if user_role == "admin": return True
    conn = get_connection(); cursor = conn.cursor()
    cursor.execute("SELECT completed_at FROM daily_invoices WHERE form_date = ?", (form_date,))
    row = cursor.fetchone(); conn.close()
    if not row or not row[0]: return True
    return is_within_edit_window(row[0], 15)

def count_invoices(form_date):
    conn = get_connection(); cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM daily_invoices WHERE form_date = ?", (form_date,))
    n = cursor.fetchone()[0]; conn.close(); return n

def get_invoice_settings():
    conn = get_connection(); cursor = conn.cursor()
    cursor.execute("SELECT key, value FROM invoice_settings")
    rows = cursor.fetchall(); conn.close()
    return {r[0]: safe_float(r[1]) for r in rows}

def update_invoice_setting(key, value):
    conn = get_connection(); cursor = conn.cursor()
    cursor.execute("INSERT INTO invoice_settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value", (key, safe_float(value)))
    conn.commit(); conn.close()

def get_receipt_weights_for_date(form_date):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT r.receipt_id, r.receipt_number, r.net_weight, r.description
        FROM slaughter_receipts r
        JOIN slaughters s ON s.slaughter_id = r.slaughter_id
        WHERE s.form_date = ?
        ORDER BY r.receipt_id
    """, (form_date,))
    rows = cursor.fetchall()
    conn.close()

    result = []
    for r in rows:
        full = 0.0
        empty = 0.0
        desc = r[3] or ""
        for token in desc.split("|"):
            if ":" in token:
                k, v = token.split(":", 1)
                k = k.strip().upper()
                try:
                    val = float(v.strip())
                except ValueError:
                    continue
                if k == "FULL":
                    full = val
                elif k == "EMPTY":
                    empty = val

        if full == 0 and empty == 0:
            full = r[2] or 0.0

        result.append({
            "receipt_id": r[0],
            "receipt_number": r[1] or "",
            "full_weight": full,
            "empty_weight": empty,
            "net_weight": (full - empty) if (full or empty) else (r[2] or 0.0),
        })
    return result


def get_invoice_prefill_data(form_date):
    receipts = get_receipt_weights_for_date(form_date)
    prefill = {"total_weight": 0, "rows": []}
    for i, r in enumerate(receipts[:5], start=1):
        net = max(0.0, r["full_weight"] - r["empty_weight"])
        prefill[f"w{i}_full"] = r["full_weight"]
        prefill[f"w{i}_empty"] = r["empty_weight"]
        prefill[f"w{i}_net"] = net
        prefill[f"w{i}_qty"] = ""
        prefill[f"w{i}_rate"] = 0
        prefill[f"w{i}_amount"] = 0
        prefill["total_weight"] += net
        prefill["rows"].append(r)
    return prefill

# ==========================================
# گزارش‌گیری جامع
# ==========================================

def get_report_summary(date_from, date_to):
    """خلاصه‌ی آمار بر اساس form_date (تاریخ روز کاری، نه تاریخ دستی)."""
    conn = get_connection()
    cursor = conn.cursor()

    # کشتارها
    cursor.execute("""
        SELECT COUNT(DISTINCT s.slaughter_id),
               COALESCE(SUM(cr.hook_count), 0),
               COALESCE(SUM(wf.total_net_weight), 0)
        FROM slaughters s
        LEFT JOIN counting_rows cr ON cr.row_id = s.counting_row_id
        LEFT JOIN weighing_forms wf ON wf.slaughter_id = s.slaughter_id
        WHERE s.form_date >= ? AND s.form_date <= ?
    """, (date_from, date_to))
    s_count, s_hook, s_net = cursor.fetchone()

    # قبض‌ها (بر اساس form_date کشتار، نه receipt_date دستی)
    cursor.execute("""
        SELECT COUNT(r.receipt_id), COALESCE(SUM(r.net_weight), 0)
        FROM slaughter_receipts r
        JOIN slaughters s ON s.slaughter_id = r.slaughter_id
        WHERE s.form_date >= ? AND s.form_date <= ?
    """, (date_from, date_to))
    r_count, r_weight = cursor.fetchone()

    # صورتحساب‌ها (بر اساس form_date، نه invoice_date دستی)
    cursor.execute("""
        SELECT COUNT(i.invoice_id), COALESCE(SUM(i.grand_total), 0)
        FROM daily_invoices i
        WHERE i.form_date >= ? AND i.form_date <= ?
          AND (i.invoice_number IS NOT NULL AND i.invoice_number != '')
    """, (date_from, date_to))
    i_count, i_total = cursor.fetchone()

    conn.close()
    return {
        "slaughter_count": s_count,
        "total_hook": s_hook,
        "total_net_weight": safe_float(s_net),
        "receipt_count": r_count,
        "receipt_weight": safe_float(r_weight),
        "invoice_count": i_count,
        "invoice_total": safe_float(i_total),
    }


def get_report_details(date_from, date_to):
    """گزارش تفکیکی کشتارها با جزئیات کامل."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            s.slaughter_id,
            s.slaughter_number,
            s.form_date,
            s.day_name,
            u.full_name AS operator_name,
            cr.hook_count,
            cr.packed,
            wf.total_net_weight,
            wf.loss_percent,
            (SELECT COUNT(*) FROM slaughter_receipts r WHERE r.slaughter_id = s.slaughter_id) as receipt_count,
            (SELECT COALESCE(SUM(net_weight), 0) FROM slaughter_receipts r WHERE r.slaughter_id = s.slaughter_id) as receipt_weight,
            (SELECT COALESCE(SUM(grand_total), 0) FROM daily_invoices i WHERE i.form_date = s.form_date) as invoice_total,
            -- تعداد گاری
            (SELECT COUNT(*) FROM weighing_plucked_rows wpr 
             JOIN weighing_forms wf2 ON wf2.form_id = wpr.form_id 
             WHERE wf2.slaughter_id = s.slaughter_id) as cart_count,
            -- مجموع وزن پرکنده
            (SELECT COALESCE(SUM(net_weight), 0) FROM weighing_plucked_rows wpr 
             JOIN weighing_forms wf2 ON wf2.form_id = wpr.form_id 
             WHERE wf2.slaughter_id = s.slaughter_id) as plucked_weight,
            -- مجموع آلایشات
            (SELECT COALESCE(SUM(net_weight), 0) FROM weighing_alayeshat_rows war 
             JOIN weighing_forms wf2 ON wf2.form_id = war.form_id 
             WHERE wf2.slaughter_id = s.slaughter_id) as alayeshat_weight
        FROM slaughters s
        LEFT JOIN users u ON u.user_id = s.operator_id
        LEFT JOIN counting_rows cr ON cr.row_id = s.counting_row_id
        LEFT JOIN weighing_forms wf ON wf.slaughter_id = s.slaughter_id
        WHERE s.form_date >= ? AND s.form_date <= ?
        ORDER BY s.form_date DESC, s.slaughter_number DESC
    """, (date_from, date_to))
    rows = cursor.fetchall()
    conn.close()
    return [
        {
            "slaughter_id": r[0],
            "slaughter_number": r[1],
            "form_date": r[2],
            "day_name": r[3],
            "operator_name": r[4] or "",
            "hook_count": r[5] or 0,
            "packed": r[6] or 0,
            "net_weight": safe_float(r[7]),
            "loss_percent": safe_float(r[8]),
            "receipt_count": r[9],
            "receipt_weight": safe_float(r[10]),
            "invoice_total": safe_float(r[11]),
            "cart_count": r[12],
            "plucked_weight": safe_float(r[13]),
            "alayeshat_weight": safe_float(r[14]),
        } for r in rows
    ]


def get_report_daily(date_from, date_to):
    """گزارش تفکیکی روزانه."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            s.form_date,
            s.day_name,
            COUNT(DISTINCT s.slaughter_id) as slaughter_count,
            COALESCE(SUM(cr.hook_count), 0) as total_hook,
            COALESCE(SUM(wf.total_net_weight), 0) as total_net
        FROM slaughters s
        LEFT JOIN counting_rows cr ON cr.row_id = s.counting_row_id
        LEFT JOIN weighing_forms wf ON wf.slaughter_id = s.slaughter_id
        WHERE s.form_date >= ? AND s.form_date <= ?
        GROUP BY s.form_date
        ORDER BY s.form_date DESC
    """, (date_from, date_to))
    rows = cursor.fetchall()
    conn.close()
    return [
        {
            "form_date": r[0],
            "day_name": r[1],
            "slaughter_count": r[2],
            "total_hook": r[3],
            "total_net": safe_float(r[4]),
        } for r in rows
    ]


def get_report_operators(date_from, date_to):
    """گزارش تفکیکی اپراتورها."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            u.user_id,
            u.full_name,
            u.username,
            COUNT(DISTINCT s.slaughter_id) as slaughter_count,
            COALESCE(SUM(cr.hook_count), 0) as total_hook,
            COALESCE(SUM(wf.total_net_weight), 0) as total_net
        FROM slaughters s
        LEFT JOIN users u ON u.user_id = s.operator_id
        LEFT JOIN counting_rows cr ON cr.row_id = s.counting_row_id
        LEFT JOIN weighing_forms wf ON wf.slaughter_id = s.slaughter_id
        WHERE s.form_date >= ? AND s.form_date <= ?
        GROUP BY u.user_id
        ORDER BY total_net DESC
    """, (date_from, date_to))
    rows = cursor.fetchall()
    conn.close()
    return [
        {
            "user_id": r[0],
            "full_name": r[1] or "—",
            "username": r[2] or "—",
            "slaughter_count": r[3],
            "total_hook": r[4],
            "total_net": safe_float(r[5]),
        } for r in rows
    ]


def get_report_customers(date_from, date_to):
    """گزارش تفکیکی مشتری‌ها (خریداران + مشتریان آلایشات)."""
    conn = get_connection()
    cursor = conn.cursor()

    # خریداران (مرغ پرکنده)
    cursor.execute("""
        SELECT 
            dpr.buyer_name,
            COUNT(DISTINCT dpr.row_id) as row_count,
            COALESCE(SUM(dpr.total_net_weight), 0) as total_weight
        FROM daily_packed_rows dpr
        JOIN daily_forms d ON d.form_id = dpr.form_id
        WHERE d.form_date >= ? AND d.form_date <= ?
          AND dpr.buyer_name IS NOT NULL AND dpr.buyer_name != ''
        GROUP BY dpr.buyer_name
        ORDER BY total_weight DESC
    """, (date_from, date_to))
    buyers = cursor.fetchall()

    # مشتریان آلایشات
    cursor.execute("""
        SELECT 
            dar.customer_name,
            COUNT(DISTINCT dar.row_id) as row_count,
            COALESCE(SUM(dar.weight), 0) as total_weight
        FROM daily_alayeshat_rows dar
        JOIN daily_forms d ON d.form_id = dar.form_id
        WHERE d.form_date >= ? AND d.form_date <= ?
          AND dar.customer_name IS NOT NULL AND dar.customer_name != ''
        GROUP BY dar.customer_name
        ORDER BY total_weight DESC
    """, (date_from, date_to))
    alayeshat = cursor.fetchall()

    conn.close()

    return {
        "buyers": [
            {
                "name": r[0],
                "row_count": r[1],
                "total_weight": safe_float(r[2]),
            } for r in buyers
        ],
        "alayeshat": [
            {
                "name": r[0],
                "row_count": r[1],
                "total_weight": safe_float(r[2]),
            } for r in alayeshat
        ],
    }


def get_report_products(date_from, date_to):
    """گزارش تفکیکی محصولات (آلایشات)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            p.product_name,
            COUNT(DISTINCT war.row_id) as row_count,
            COALESCE(SUM(war.net_weight), 0) as total_weight
        FROM weighing_alayeshat_rows war
        JOIN weighing_forms wf ON wf.form_id = war.form_id
        JOIN slaughters s ON s.slaughter_id = wf.slaughter_id
        JOIN products p ON p.product_id = war.product_id
        WHERE s.form_date >= ? AND s.form_date <= ?
        GROUP BY p.product_id
        ORDER BY total_weight DESC
    """, (date_from, date_to))
    rows = cursor.fetchall()
    conn.close()
    return [
        {
            "product_name": r[0],
            "row_count": r[1],
            "total_weight": safe_float(r[2]),
        } for r in rows
    ]

# ==========================================
# جستجوی پیشرفته (ادمین) — با فرم گزارش روزانه
# ==========================================

def admin_search(query_type="all", date_from=None, date_to=None, text_query=""):
    conn = get_connection(); cursor = conn.cursor()
    results = []
    text_query = text_query.strip() if text_query else ""
    text_param = f"%{text_query}%" if text_query else None

    date_cond_s = ""; date_cond_r = ""; date_cond_i = ""; date_cond_d = ""
    params_s = []; params_r = []; params_i = []; params_d = []

    if date_from:
        date_cond_s += " AND s.form_date >= ?"
        date_cond_r += " AND r.receipt_date >= ?"
        date_cond_i += " AND i.form_date >= ?"
        date_cond_d += " AND d.form_date >= ?"
        params_s.append(date_from); params_r.append(date_from)
        params_i.append(date_from); params_d.append(date_from)
    if date_to:
        date_cond_s += " AND s.form_date <= ?"
        date_cond_r += " AND r.receipt_date <= ?"
        date_cond_i += " AND i.form_date <= ?"
        date_cond_d += " AND d.form_date <= ?"
        params_s.append(date_to); params_r.append(date_to)
        params_i.append(date_to); params_d.append(date_to)

    # ── کشتارها ──
    if query_type in ("all", "slaughters"):
        sql_s = f"""
            SELECT 'slaughter' as type, s.slaughter_id as id,
                   s.slaughter_number as num, s.form_date as date,
                   u.full_name as info1, cr.hook_count as info2, '' as info3
            FROM slaughters s
            LEFT JOIN users u ON u.user_id = s.operator_id
            LEFT JOIN counting_rows cr ON cr.row_id = s.counting_row_id
            WHERE 1=1 {date_cond_s}
        """
        if text_param:
            sql_s += " AND (CAST(s.slaughter_number AS TEXT) LIKE ? OR u.full_name LIKE ?)"
            cursor.execute(sql_s, params_s + [text_param, text_param])
        else:
            cursor.execute(sql_s, params_s)
        for r in cursor.fetchall():
            results.append({
                "type": "کشتار", "id": r[1], "num": r[2], "date": r[3],
                "info1": r[4] or "", "info2": f"پای قلاب: {r[5]}", "info3": "",
            })

    # ── قبض‌ها ──
    if query_type in ("all", "receipts"):
        sql_r = f"""
            SELECT 'receipt' as type, r.receipt_id as id,
                   r.receipt_number as num, r.receipt_date as date,
                   r.car_plate as info1, r.net_weight as info2, r.buyer_name as info3
            FROM slaughter_receipts r
            WHERE 1=1 {date_cond_r}
        """
        if text_param:
            sql_r += " AND (r.receipt_number LIKE ? OR r.car_plate LIKE ? OR r.driver_name LIKE ? OR r.buyer_name LIKE ? OR r.description LIKE ?)"
            cursor.execute(sql_r, params_r + [text_param] * 5)
        else:
            cursor.execute(sql_r, params_r)
        for r in cursor.fetchall():
            results.append({
                "type": "قبض", "id": r[1], "num": r[2] or "—", "date": r[3] or "—",
                "info1": f"پلاک: {r[4] or '—'}", "info2": f"وزن: {r[5]}", "info3": r[6] or "",
            })

    # ── صورتحساب‌ها ──
    if query_type in ("all", "invoices"):
        sql_i = f"""
            SELECT 'invoice' as type, i.invoice_id as id,
                   i.invoice_number as num, i.form_date as date,
                   i.grand_total as info1, i.description as info2, '' as info3
            FROM daily_invoices i
            WHERE 1=1 {date_cond_i}
        """
        if text_param:
            sql_i += " AND (i.invoice_number LIKE ? OR i.description LIKE ?)"
            cursor.execute(sql_i, params_i + [text_param, text_param])
        else:
            cursor.execute(sql_i, params_i)
        for r in cursor.fetchall():
            desc = r[5] if r[5] else ""
            results.append({
                "type": "صورتحساب", "id": r[1], "num": r[2] or "—", "date": r[3] or "—",
                "info1": f"جمع: {r[4]:,.0f} ریال",
                "info2": (desc[:40] + "..." if len(desc) > 40 else desc),
                "info3": "",
            })

    # ── فرم‌های گزارش روزانه (نام خریدار و مشتری‌ها) ──
    if query_type in ("all", "daily_forms"):
        # ۱) نام خریدار در مرغ پرکنده
        sql_dp = f"""
            SELECT 'packed' as subtype, dpr.buyer_name as name,
                   d.form_date as date, dpr.total_net_weight as weight, dpr.row_num as row_num
            FROM daily_packed_rows dpr
            JOIN daily_forms d ON d.form_id = dpr.form_id
            WHERE 1=1 {date_cond_d}
        """
        if text_param:
            sql_dp += " AND dpr.buyer_name LIKE ?"
            cursor.execute(sql_dp, params_d + [text_param])
        else:
            cursor.execute(sql_dp, params_d)
        for r in cursor.fetchall():
            results.append({
                "type": "فرم گزارش", "id": None, "num": f"خریدار: {r[1]}", "date": r[2],
                "info1": f"مرغ پرکنده — ردیف {r[4]}",
                "info2": f"وزن: {r[3]:,.2f} کیلوگرم",
                "info3": "فرم گزارش روزانه",
            })

        # ۲) نام مشتری در آلایشات
        sql_da = f"""
            SELECT 'alayeshat' as subtype, dar.customer_name as name,
                   d.form_date as date, dar.weight as weight, dar.row_num as row_num
            FROM daily_alayeshat_rows dar
            JOIN daily_forms d ON d.form_id = dar.form_id
            WHERE 1=1 {date_cond_d}
        """
        if text_param:
            sql_da += " AND dar.customer_name LIKE ?"
            cursor.execute(sql_da, params_d + [text_param])
        else:
            cursor.execute(sql_da, params_d)
        for r in cursor.fetchall():
            results.append({
                "type": "فرم گزارش", "id": None, "num": f"مشتری: {r[1]}", "date": r[2],
                "info1": f"آلایشات — ردیف {r[4]}",
                "info2": f"وزن: {r[3]:,.2f} کیلوگرم",
                "info3": "فرم گزارش روزانه",
            })

        # ۳) نام مشتری در مرغ اصلاحی
        sql_dm = f"""
            SELECT 'morgh' as subtype, dmr.customer_name as name,
                   d.form_date as date, dmr.whole_weight as whole, dmr.row_num as row_num
            FROM daily_morgh_rows dmr
            JOIN daily_forms d ON d.form_id = dmr.form_id
            WHERE 1=1 {date_cond_d}
        """
        if text_param:
            sql_dm += " AND dmr.customer_name LIKE ?"
            cursor.execute(sql_dm, params_d + [text_param])
        else:
            cursor.execute(sql_dm, params_d)
        for r in cursor.fetchall():
            results.append({
                "type": "فرم گزارش", "id": None, "num": f"مشتری: {r[1]}", "date": r[2],
                "info1": f"مرغ اصلاحی — ردیف {r[4]}",
                "info2": f"وزن کامل: {r[3]:,.2f} کیلوگرم",
                "info3": "فرم گزارش روزانه",
            })

    conn.close()
    results.sort(key=lambda x: x["date"] or "", reverse=True)
    return results

# ==========================================
# مدیریت قفل و مهلت ویرایش فرم‌ها
# ==========================================

def can_edit_form(completed_at, locked_at, user):
    """
    آیا کاربر می‌تواند این فرم را ویرایش کند؟

    - اگر هیچ‌کدام از completed_at و locked_at ست نشده باشند → فرم جدید است، ویرایش آزاد.
    - اگر locked_at ست شده باشد → قفل نهایی است؛ فقط از طریق دکمه «ویرایش (ادمین)».
    - اگر completed_at ست شده ولی locked_at نه → مهلت ۱۵ دقیقه از completed_at.
    """
    if not completed_at and not locked_at:
        return True
    if locked_at:
        return False
    return is_within_edit_window(completed_at, 15)


def admin_unlock_form(table, id_column, id_value):
    """
    باز کردن قفل توسط ادمین + ریست مهلت ۱۵ دقیقه.

    - locked_at = NULL
    - completed_at = زمان حال (مهلت از این لحظه دوباره شروع می‌شود)

    table: نام جدول (مثلاً "weighing_forms")
    id_column: نام ستون کلید (مثلاً "slaughter_id")
    id_value: مقدار کلید
    """
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        f"UPDATE {table} SET locked_at = NULL, completed_at = ? WHERE {id_column} = ?",
        (now, id_value)
    )
    conn.commit()
    conn.close()


def finalize_form(table, id_column, id_value):
    """
    ثبت نهایی: قفل + ریست completed_at.

    - locked_at = زمان حال
    - completed_at = زمان حال (تا اگر بعداً ادمین قفل را باز کرد، مهلت از این لحظه حساب شود)
    """
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        f"UPDATE {table} SET locked_at = ?, completed_at = ? WHERE {id_column} = ?",
        (now, now, id_value)
    )
    conn.commit()
    conn.close()
