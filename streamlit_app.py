"""
Business Analyzer – All Milestones (1, 2, 3)
---------------------------------------------
A comprehensive business management tool with:
- Authentication & user management (JWT + bcrypt)
- Business profiles & transaction logging
- Inventory tracking & COGS calculation
- Advanced analytics: interactive charts, category breakdowns,
  AI-based forecasting using Prophet (with linear regression fallback)

Author: Final Year Project
"""

import streamlit as st
import pandas as pd
import sqlite3
import numpy as np
import bcrypt
import jwt
from datetime import datetime, timedelta
from contextlib import contextmanager
import os
import plotly.express as px
import plotly.graph_objects as go

# -----------------------------------------------------------------------------
# FIX 1: Use absolute paths for database files
#        This ensures the files are found on Streamlit Cloud.
# -----------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
USER_DB = os.path.join(BASE_DIR, 'USER.db')
BUSINESS_DB = os.path.join(BASE_DIR, 'BUSINESS.db')
SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'your-secret-key-change-in-production')
JWT_ALGORITHM = 'HS256'

# -----------------------------------------------------------------------------
# Custom CSS for a modern, clean look (no emojis, just style)
# -----------------------------------------------------------------------------
def apply_custom_css():
    st.markdown("""
        <style>
        /* Main container */
        .main {
            padding: 0rem 1rem;
        }
        /* Headers */
        h1, h2, h3 {
            color: #1E3A5F;
            font-weight: 500;
            border-bottom: 2px solid #f0f2f6;
            padding-bottom: 0.3rem;
        }
        /* Buttons */
        .stButton > button {
            border-radius: 8px;
            border: none;
            background: linear-gradient(135deg, #1E3A5F 0%, #2B4C7C 100%);
            color: white;
            padding: 0.5rem 1rem;
            font-weight: 500;
            transition: all 0.3s ease;
        }
        .stButton > button:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }
        /* Metrics */
        [data-testid="stMetricValue"] {
            font-size: 2rem;
            color: #1E3A5F;
        }
        /* Sidebar */
        .css-1d391kg {
            background-color: #f8fafc;
        }
        /* DataFrames */
        .stDataFrame {
            border: 1px solid #e9ecef;
            border-radius: 8px;
        }
        /* Expanders */
        .streamlit-expanderHeader {
            background-color: #f8fafc;
            border-radius: 8px;
            border: 1px solid #dee2e6;
        }
        /* Success/Info/Warning boxes */
        .stAlert {
            border-radius: 8px;
            border-left: 4px solid;
        }
        </style>
    """, unsafe_allow_html=True)

# Optional Prophet import
try:
    from prophet import Prophet
    prophet_available = True
except ImportError:
    prophet_available = False

from sklearn.linear_model import LinearRegression
import warnings
warnings.filterwarnings('ignore')

# -----------------------------------------------------------------------------
# Database Helpers (using absolute paths)
# -----------------------------------------------------------------------------
@contextmanager
def get_user_db():
    conn = sqlite3.connect(USER_DB, timeout=10)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()

@contextmanager
def get_business_db():
    conn = sqlite3.connect(BUSINESS_DB, timeout=10)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()

# -----------------------------------------------------------------------------
# Database Initialization
# -----------------------------------------------------------------------------
def init_user_db():
    with get_user_db() as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'Owner',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')

def init_business_db():
    with get_business_db() as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS businesses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            business_name TEXT NOT NULL,
            business_type TEXT,
            address TEXT,
            phone TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        conn.execute('''CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            business_id INTEGER NOT NULL,
            type TEXT NOT NULL,
            amount REAL NOT NULL,
            category TEXT,
            description TEXT,
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        conn.execute('''CREATE TABLE IF NOT EXISTS user_preferences (
            user_id INTEGER PRIMARY KEY,
            active_business_id INTEGER
        )''')

def init_inventory_tables():
    with get_business_db() as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            business_id INTEGER NOT NULL,
            product_name TEXT NOT NULL,
            sku TEXT UNIQUE,
            quantity REAL DEFAULT 0,
            cost_price REAL DEFAULT 0,
            selling_price REAL DEFAULT 0,
            reorder_level REAL DEFAULT 5,
            category TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        conn.execute('''CREATE TABLE IF NOT EXISTS stock_movements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            movement_type TEXT NOT NULL,
            quantity REAL NOT NULL,
            unit_cost REAL,
            unit_price REAL,
            reference_id INTEGER,
            movement_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            notes TEXT,
            FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
        )''')

# -----------------------------------------------------------------------------
# Authentication Helpers
# -----------------------------------------------------------------------------
def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def check_password(password, hashed):
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def create_jwt_token(user_id, username, role):
    payload = {
        'user_id': user_id,
        'username': username,
        'role': role,
        'exp': datetime.utcnow() + timedelta(days=1)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=JWT_ALGORITHM)

def verify_jwt_token(token):
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError:
        return None

# -----------------------------------------------------------------------------
# Session Management
# -----------------------------------------------------------------------------
def init_session_state():
    defaults = {
        'token': None,
        'logged_in': False,
        'username': None,
        'user_id': None,
        'role': None,
        'page': "Home",
        'uploaded_df': None,
        'active_business_id': None
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val

def change_page(page):
    st.session_state.page = page

def login_user(username, password):
    with get_user_db() as conn:
        user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        if user and check_password(password, user['password']):
            st.session_state.token = create_jwt_token(user['id'], user['username'], user['role'])
            st.session_state.logged_in = True
            st.session_state.username = user['username']
            st.session_state.user_id = user['id']
            st.session_state.role = user['role']
            with get_business_db() as b_conn:
                pref = b_conn.execute(
                    "SELECT active_business_id FROM user_preferences WHERE user_id = ?",
                    (user['id'],)
                ).fetchone()
                if pref:
                    st.session_state.active_business_id = pref['active_business_id']
            st.session_state.page = "Dashboard"
            return True, "Login successful!"
    return False, "Invalid username or password!"

def logout_user():
    for key in ['token', 'logged_in', 'username', 'user_id', 'role', 'uploaded_df', 'active_business_id']:
        st.session_state[key] = None
    st.session_state.page = "Home"

def authenticate():
    token = st.session_state.get('token')
    if not token:
        return None
    payload = verify_jwt_token(token)
    if not payload:
        logout_user()
    return payload

# -----------------------------------------------------------------------------
# Role Based Access
# -----------------------------------------------------------------------------
def can_edit_transactions():
    return st.session_state.role in ['Owner', 'Accountant']

def can_delete_transactions():
    return st.session_state.role == 'Owner'

# -----------------------------------------------------------------------------
# Profit Calculation Functions
# -----------------------------------------------------------------------------
def calculate_profit_metrics(user_id, business_id, period='monthly'):
    with get_business_db() as conn:
        df = pd.read_sql("""
            SELECT date, type, amount, category FROM transactions
            WHERE user_id = ? AND business_id = ? ORDER BY date
        """, conn, params=(user_id, business_id))
    if df.empty:
        return None
    df['date'] = pd.to_datetime(df['date'])
    sales = df[df['type'] == 'Sales']
    expenses = df[df['type'] == 'Expense']
    total_revenue = sales['amount'].sum() if not sales.empty else 0
    total_expenses = expenses['amount'].sum() if not expenses.empty else 0

    with get_business_db() as conn:
        cogs_data = pd.read_sql("""
            SELECT sm.quantity, sm.unit_cost FROM stock_movements sm
            JOIN products p ON sm.product_id = p.id
            WHERE p.user_id = ? AND p.business_id = ? AND sm.movement_type = 'sale'
        """, conn, params=(user_id, business_id))
    total_cogs = (cogs_data['quantity'] * cogs_data['unit_cost']).sum() if not cogs_data.empty else 0

    gross_profit = total_revenue - total_cogs
    net_profit = gross_profit - total_expenses

    today = datetime.now()
    if period == 'daily':
        mask = df['date'].dt.date == today.date()
    elif period == 'weekly':
        mask = df['date'] >= (today - timedelta(days=today.weekday()))
    else:
        mask = (df['date'].dt.year == today.year) & (df['date'].dt.month == today.month)

    period_sales = sales.loc[mask, 'amount'].sum() if not sales.empty else 0
    period_expenses = expenses.loc[mask, 'amount'].sum() if not expenses.empty else 0
    period_profit = period_sales - period_expenses

    gross_margin = (gross_profit / total_revenue * 100) if total_revenue else 0
    net_margin = (net_profit / total_revenue * 100) if total_revenue else 0

    return {
        'total_revenue': total_revenue, 'total_cogs': total_cogs,
        'total_expenses': total_expenses, 'gross_profit': gross_profit,
        'net_profit': net_profit, 'gross_margin': gross_margin,
        'net_margin': net_margin, 'period_profit': period_profit,
        'period_sales': period_sales, 'transaction_count': len(df)
    }

def get_monthly_profit_trend(user_id, business_id, months=6):
    with get_business_db() as conn:
        df = pd.read_sql("""
            SELECT strftime('%Y-%m', date) as month,
                   SUM(CASE WHEN type = 'Sales' THEN amount ELSE 0 END) as revenue,
                   SUM(CASE WHEN type = 'Expense' THEN amount ELSE 0 END) as expenses
            FROM transactions
            WHERE user_id = ? AND business_id = ? AND date >= date('now', ?)
            GROUP BY month ORDER BY month
        """, conn, params=(user_id, business_id, f'-{months} months'))
    if not df.empty:
        df['profit'] = df['revenue'] - df['expenses']
        df['margin'] = (df['profit'] / df['revenue'] * 100).round(1)
        df['month_dt'] = pd.to_datetime(df['month'] + '-01')
    return df

# -----------------------------------------------------------------------------
# Inventory Management Functions
# -----------------------------------------------------------------------------
def add_product(user_id, business_id, name, sku, qty, cost, price, reorder, category):
    with get_business_db() as conn:
        try:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO products (user_id, business_id, product_name, sku, quantity,
                cost_price, selling_price, reorder_level, category)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (user_id, business_id, name, sku, qty, cost, price, reorder, category))
            pid = cur.lastrowid
            if qty > 0:
                cur.execute("""
                    INSERT INTO stock_movements (product_id, movement_type, quantity, unit_cost, notes)
                    VALUES (?, 'purchase', ?, ?, 'Initial stock')
                """, (pid, qty, cost))
            return True, "Product added."
        except sqlite3.IntegrityError:
            return False, "SKU already exists."
        except Exception as e:
            return False, str(e)

def record_stock_movement(pid, move_type, qty, unit_cost=None, unit_price=None, ref=None, notes=""):
    with get_business_db() as conn:
        cur = conn.cursor()
        prod = cur.execute("SELECT quantity, cost_price FROM products WHERE id = ?", (pid,)).fetchone()
        if not prod:
            return False, "Product not found."
        curr_qty, curr_cost = prod['quantity'], prod['cost_price']

        if move_type == 'purchase':
            new_qty = curr_qty + qty
            if unit_cost and unit_cost > 0:
                new_cost = (curr_qty * curr_cost + qty * unit_cost) / new_qty
                cur.execute("UPDATE products SET quantity = ?, cost_price = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                            (new_qty, new_cost, pid))
            else:
                cur.execute("UPDATE products SET quantity = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (new_qty, pid))
        elif move_type == 'sale':
            if qty > curr_qty:
                return False, "Insufficient stock."
            new_qty = curr_qty - qty
            cur.execute("UPDATE products SET quantity = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (new_qty, pid))
        elif move_type == 'adjustment':
            cur.execute("UPDATE products SET quantity = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (qty, pid))
        else:
            return False, "Invalid movement type."

        cur.execute("""
            INSERT INTO stock_movements (product_id, movement_type, quantity, unit_cost, unit_price, reference_id, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (pid, move_type, qty, unit_cost, unit_price, ref, notes))
        return True, "Movement recorded."

def get_low_stock_items(user_id, business_id):
    with get_business_db() as conn:
        return pd.read_sql("""
            SELECT product_name, sku, quantity, reorder_level, (reorder_level - quantity) as needed
            FROM products WHERE user_id = ? AND business_id = ? AND quantity <= reorder_level
            ORDER BY needed DESC
        """, conn, params=(user_id, business_id))

def get_inventory_value(user_id, business_id):
    with get_business_db() as conn:
        res = pd.read_sql("""
            SELECT COUNT(*) as product_count, SUM(quantity) as total_units,
                   SUM(quantity * cost_price) as total_value
            FROM products WHERE user_id = ? AND business_id = ?
        """, conn, params=(user_id, business_id)).iloc[0]
    return {k: res[k] or 0 for k in ['product_count', 'total_units', 'total_value']}

# -----------------------------------------------------------------------------
# Page Functions – Milestones 1 & 2
# -----------------------------------------------------------------------------
def home_page():
    st.title("Business Analyzer")
    st.markdown("""
    ### Milestone 1 – Authentication & Basic Transaction Logging
    **Features:** Secure registration/login, business profiles, transaction logging, sales dashboard, file analyzer.

    ### Milestone 2 – Profit & Inventory Tracking
    **Features:** Profit metrics, inventory management, COGS analysis, low stock alerts.

    ### Milestone 3 – Advanced Analytics
    **Features:** Interactive trends, profit margins, category breakdowns, AI forecasting.
    """)

def login_page():
    st.title("Login")
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.form_submit_button("Login", use_container_width=True):
            if username and password:
                ok, msg = login_user(username, password)
                if ok:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)
            else:
                st.error("Enter both fields")

def signup_page():
    st.title("Sign Up")
    with st.form("signup_form"):
        nu, em, pw, cf = st.text_input("Username"), st.text_input("Email"), st.text_input("Password", type="password"), st.text_input("Confirm Password", type="password")
        role = st.selectbox("Role", ["Owner", "Accountant", "Staff"])
        if st.form_submit_button("Sign Up", use_container_width=True):
            if not nu or not em or not pw:
                st.error("All fields required")
            elif pw != cf:
                st.error("Passwords do not match")
            else:
                try:
                    hashed = hash_password(pw)
                    with get_user_db() as conn:
                        cur = conn.cursor()
                        cur.execute("INSERT INTO users (username, email, password, role) VALUES (?,?,?,?)",
                                    (nu, em, hashed, role))
                        uid = cur.lastrowid
                    with get_business_db() as b_conn:
                        b_conn.execute("INSERT OR IGNORE INTO user_preferences (user_id) VALUES (?)", (uid,))
                    st.success("Account created! Please login.")
                    st.session_state.page = "Login"
                    st.rerun()
                except sqlite3.IntegrityError:
                    st.error("Username or email already exists")

def dashboard_page():
    st.title("Dashboard")
    with get_business_db() as conn:
        aid = st.session_state.active_business_id
        if not aid:
            pref = conn.execute("SELECT active_business_id FROM user_preferences WHERE user_id = ?",
                                (st.session_state.user_id,)).fetchone()
            aid = st.session_state.active_business_id = pref['active_business_id'] if pref else None
        if aid:
            cnt = conn.execute("SELECT COUNT(*) FROM transactions WHERE user_id = ? AND business_id = ?",
                               (st.session_state.user_id, aid)).fetchone()[0]
            sales = conn.execute("SELECT SUM(amount) FROM transactions WHERE user_id = ? AND business_id = ? AND type = 'Sales'",
                                 (st.session_state.user_id, aid)).fetchone()[0] or 0
            exp = conn.execute("SELECT SUM(amount) FROM transactions WHERE user_id = ? AND business_id = ? AND type = 'Expense'",
                               (st.session_state.user_id, aid)).fetchone()[0] or 0
        else:
            cnt = sales = exp = 0
    profit = sales - exp
    col1, col2, col3 = st.columns(3)
    col1.metric("Transactions", cnt)
    col2.metric("Total Sales", f"₹{sales:,.2f}")
    col3.metric("Net Profit", f"₹{profit:,.2f}")
    if cnt == 0:
        st.info("No transactions yet. Use 'Add Transaction' or 'Import CSV'.")

    st.divider()
    st.subheader("Active Business")
    with get_business_db() as conn:
        biz = pd.read_sql("SELECT id, business_name FROM businesses WHERE user_id = ?", conn, params=(st.session_state.user_id,))
    if not biz.empty:
        opts = biz.set_index('id')['business_name'].to_dict()
        cur = st.session_state.active_business_id
        sel = st.selectbox("Select business", options=list(opts.keys()), format_func=lambda x: opts[x],
                           index=list(opts.keys()).index(cur) if cur in opts else 0)
        if sel != cur:
            st.session_state.active_business_id = sel
            with get_business_db() as conn:
                conn.execute("UPDATE user_preferences SET active_business_id = ? WHERE user_id = ?",
                             (sel, st.session_state.user_id))
            st.rerun()
    else:
        st.warning("Create a business in 'My Businesses'.")

def businesses_page():
    st.title("My Businesses")
    with st.expander("Add New Business"):
        with st.form("add_business_form"):
            name, typ, addr, phone = st.text_input("Business Name *"), st.text_input("Type"), st.text_area("Address"), st.text_input("Phone")
            if st.form_submit_button("Create", use_container_width=True) and name:
                with get_business_db() as conn:
                    cur = conn.cursor()
                    cur.execute("INSERT INTO businesses (user_id, business_name, business_type, address, phone) VALUES (?,?,?,?,?)",
                                (st.session_state.user_id, name, typ, addr, phone))
                    bid = cur.lastrowid
                    if cur.execute("SELECT COUNT(*) FROM businesses WHERE user_id = ?", (st.session_state.user_id,)).fetchone()[0] == 1:
                        conn.execute("UPDATE user_preferences SET active_business_id = ? WHERE user_id = ?", (bid, st.session_state.user_id))
                        st.session_state.active_business_id = bid
                st.success(f"Business '{name}' created!")
                st.rerun()

    with get_business_db() as conn:
        df = pd.read_sql("SELECT id, business_name, business_type, address, phone, created_at FROM businesses WHERE user_id = ? ORDER BY created_at DESC",
                         conn, params=(st.session_state.user_id,))
    if df.empty:
        st.info("No businesses yet.")
        return

    for _, row in df.iterrows():
        bid, active = row['id'], st.session_state.active_business_id == row['id']
        cols = st.columns([3,1,1,1])
        # Replace checkmark emoji with [ACTIVE]
        active_tag = " [ACTIVE]" if active else ""
        cols[0].write(f"**{row['business_name']}**{active_tag}")
        cols[0].caption(f"{row['business_type'] or 'N/A'} | {row['phone'] or 'N/A'}")
        if not active and cols[1].button("Set Active", key=f"set_{bid}"):
            with get_business_db() as conn:
                conn.execute("UPDATE user_preferences SET active_business_id = ? WHERE user_id = ?", (bid, st.session_state.user_id))
            st.session_state.active_business_id = bid
            st.rerun()
        if cols[2].button("Edit", key=f"edit_{bid}"):
            st.session_state[f"edit_{bid}"] = True
        if not active and cols[3].button("Delete", key=f"del_{bid}"):
            with get_business_db() as conn:
                conn.execute("DELETE FROM transactions WHERE business_id = ?", (bid,))
                conn.execute("DELETE FROM businesses WHERE id = ?", (bid,))
            st.success(f"Deleted {row['business_name']}")
            st.rerun()

        if st.session_state.get(f"edit_{bid}", False):
            with st.expander(f"Edit {row['business_name']}", expanded=True):
                with st.form(key=f"edit_form_{bid}"):
                    nn = st.text_input("Name", row['business_name'])
                    nt = st.text_input("Type", row['business_type'] or '')
                    na = st.text_area("Address", row['address'] or '')
                    np_ = st.text_input("Phone", row['phone'] or '')
                    if st.form_submit_button("Update"):
                        with get_business_db() as conn:
                            conn.execute("UPDATE businesses SET business_name=?, business_type=?, address=?, phone=? WHERE id=?",
                                         (nn, nt, na, np_, bid))
                        st.success("Updated")
                        st.session_state[f"edit_{bid}"] = False
                        st.rerun()
                if st.button("Cancel", key=f"cancel_{bid}"):
                    st.session_state[f"edit_{bid}"] = False
                    st.rerun()
        st.divider()

def add_transaction_page():
    st.title("Add Transaction")
    if not st.session_state.active_business_id:
        st.warning("Select an active business first.")
        if st.button("Go to Businesses"):
            st.session_state.page = "Businesses"
            st.rerun()
        return
    with st.form("transaction_form"):
        typ = st.selectbox("Type", ["Sales", "Expense"])
        amt = st.number_input("Amount (₹)", min_value=0.01, step=10.0)
        cat = st.text_input("Category")
        desc = st.text_area("Description")
        tdate = st.date_input("Date", datetime.now().date())
        if st.form_submit_button("Add", use_container_width=True, type="primary"):
            if amt <= 0:
                st.error("Amount must be >0")
            else:
                dt = datetime.combine(tdate, datetime.min.time())
                with get_business_db() as conn:
                    conn.execute("INSERT INTO transactions (user_id, business_id, type, amount, category, description, date) VALUES (?,?,?,?,?,?,?)",
                                 (st.session_state.user_id, st.session_state.active_business_id, typ, amt, cat, desc, dt))
                st.success("Transaction added!")
                st.rerun()

def view_transactions_page():
    st.title("Transactions")
    if not st.session_state.active_business_id:
        st.warning("No active business.")
        return
    with get_business_db() as conn:
        df = pd.read_sql("SELECT id, type, amount, category, description, date FROM transactions WHERE user_id=? AND business_id=? ORDER BY date DESC",
                         conn, params=(st.session_state.user_id, st.session_state.active_business_id))
    if df.empty:
        st.info("No transactions.")
        return
    disabled = ["id", "date"] if can_edit_transactions() else ["id","type","amount","category","description","date"]
    if not can_edit_transactions():
        st.info("Read-only access")
    edited = st.data_editor(df,
        column_config={
            "id": st.column_config.NumberColumn("ID", disabled=True),
            "type": st.column_config.SelectboxColumn("Type", options=["Sales","Expense"], required=True),
            "amount": st.column_config.NumberColumn("Amount", min_value=0.01, format="₹%.2f", required=True),
            "category": st.column_config.TextColumn("Category"),
            "description": st.column_config.TextColumn("Description"),
            "date": st.column_config.DatetimeColumn("Date", disabled=True),
        },
        disabled=disabled, hide_index=True,
        num_rows="dynamic" if can_delete_transactions() else "fixed",
        key="tx_editor"
    )
    if can_edit_transactions() and st.button("Save Changes"):
        with get_business_db() as conn:
            for _, r in edited.iterrows():
                conn.execute("UPDATE transactions SET type=?, amount=?, category=?, description=? WHERE id=? AND user_id=?",
                             (r['type'], r['amount'], r['category'], r['description'], r['id'], st.session_state.user_id))
        st.success("Saved")
        st.rerun()
    st.download_button("Download CSV", df.to_csv(index=False), "transactions.csv")

def import_transactions_page():
    st.title("Import CSV")
    if not st.session_state.active_business_id:
        st.warning("Select active business first")
        return
    file = st.file_uploader("Choose CSV", type=['csv'])
    if not file:
        return
    df = pd.read_csv(file)
    st.success(f"Loaded {file.name}")
    st.dataframe(df.head())
    st.divider()
    st.subheader("Map Columns")
    cols = df.columns.tolist()
    amt_col = st.selectbox("Amount column", ["None"]+cols, key="amt")
    typ_col = st.selectbox("Type column", ["None"]+cols, key="typ")
    cat_col = st.selectbox("Category column", ["None"]+cols, key="cat")
    desc_col = st.selectbox("Description column", ["None"]+cols, key="desc")
    default_type = st.selectbox("Default type", ["Sales","Expense"])
    if amt_col != "None" and st.button("IMPORT", type="primary"):
        success = 0
        errors = 0
        prog = st.progress(0)
        status = st.empty()
        for idx, row in df.iterrows():
            try:
                if pd.isna(row[amt_col]):
                    errors += 1
                    continue
                amt = float(row[amt_col])
                if amt <= 0:
                    errors += 1
                    continue
                ttype = default_type
                if typ_col != "None" and pd.notna(row[typ_col]):
                    val = str(row[typ_col]).lower()
                    if 'sale' in val or 'income' in val:
                        ttype = 'Sales'
                    elif 'expense' in val or 'cost' in val:
                        ttype = 'Expense'
                cat = str(row[cat_col])[:50] if cat_col != "None" and pd.notna(row[cat_col]) else "Uncategorized"
                desc = str(row[desc_col])[:200] if desc_col != "None" and pd.notna(row[desc_col]) else f"Row {idx+1}"
                with get_business_db() as conn:
                    conn.execute("INSERT INTO transactions (user_id, business_id, type, amount, category, description) VALUES (?,?,?,?,?,?)",
                                 (st.session_state.user_id, st.session_state.active_business_id, ttype, amt, cat, desc))
                success += 1
            except:
                errors += 1
            prog.progress((idx+1)/len(df))
            status.text(f"Processed {idx+1}/{len(df)}")
        prog.empty()
        status.empty()
        st.success(f"Imported {success} transactions, {errors} errors.")
        if success and st.button("View Transactions"):
            st.session_state.page = "View Transactions"
            st.rerun()

def sales_dashboard_page():
    st.title("Sales Dashboard")
    if not st.session_state.active_business_id:
        st.warning("No active business")
        return
    with get_business_db() as conn:
        df = pd.read_sql("SELECT type, amount, category, date FROM transactions WHERE user_id=? AND business_id=?",
                         conn, params=(st.session_state.user_id, st.session_state.active_business_id))
    if df.empty:
        st.info("No data")
        return
    sales = df[df['type']=='Sales']
    exps = df[df['type']=='Expense']
    if not sales.empty:
        fig = px.bar(sales.groupby('category')['amount'].sum().reset_index(), x='category', y='amount', title="Sales by Category")
        st.plotly_chart(fig)
    if not exps.empty:
        fig = px.bar(exps.groupby('category')['amount'].sum().reset_index(), x='category', y='amount', title="Expenses by Category")
        st.plotly_chart(fig)
    df['date'] = pd.to_datetime(df['date'])
    df['month'] = df['date'].dt.to_period('M').astype(str)
    monthly = df.groupby(['month','type'])['amount'].sum().unstack().fillna(0)
    if not monthly.empty:
        fig = px.line(monthly.reset_index().melt(id_vars='month'), x='month', y='value', color='type', title="Monthly Trend")
        st.plotly_chart(fig)
    total_sales = sales['amount'].sum() if not sales.empty else 0
    total_exp = exps['amount'].sum() if not exps.empty else 0
    profit = total_sales - total_exp
    avg = sales['amount'].mean() if not sales.empty else 0
    cols = st.columns(4)
    cols[0].metric("Total Sales", f"₹{total_sales:,.2f}")
    cols[1].metric("Total Expenses", f"₹{total_exp:,.2f}")
    cols[2].metric("Net Profit", f"₹{profit:,.2f}")
    cols[3].metric("Avg Sale", f"₹{avg:,.2f}")

def analyze_data_page():
    st.title("Analyze File")
    file = st.file_uploader("Upload CSV/Excel", type=['csv','xlsx','xls'])
    if file:
        df = pd.read_csv(file) if file.name.endswith('.csv') else pd.read_excel(file)
        st.session_state.uploaded_df = df
        st.success(f"Loaded {file.name}")
    if st.session_state.uploaded_df is not None:
        df = st.session_state.uploaded_df
        tabs = st.tabs(["Preview","Stats","Visualize"])
        with tabs[0]:
            st.dataframe(df.head(100))
        with tabs[1]:
            st.dataframe(df.describe(include='all').T)
        with tabs[2]:
            num_cols = df.select_dtypes(include='number').columns.tolist()
            if not num_cols:
                st.warning("No numeric columns")
            else:
                chart = st.selectbox("Chart type", ["Bar","Line","Scatter","Histogram"])
                if chart == "Bar":
                    x = st.selectbox("X", df.columns)
                    y = st.selectbox("Y", num_cols)
                    if x and y:
                        st.bar_chart(df.groupby(x)[y].sum())
                elif chart == "Line":
                    x = st.selectbox("X", df.columns)
                    y = st.selectbox("Y", num_cols)
                    if x and y:
                        if df[x].dtype == 'object':
                            try:
                                df_sorted = df.copy()
                                df_sorted[x] = pd.to_datetime(df_sorted[x])
                                df_sorted = df_sorted.sort_values(x)
                                st.line_chart(df_sorted.set_index(x)[y])
                            except:
                                st.line_chart(df.groupby(x)[y].sum().sort_index())
                        else:
                            st.line_chart(df.groupby(x)[y].sum().sort_index())
                elif chart == "Scatter" and len(num_cols)>=2:
                    x = st.selectbox("X", num_cols)
                    y = st.selectbox("Y", num_cols)
                    if x and y:
                        st.scatter_chart(df[[x,y]].dropna())
                elif chart == "Histogram":
                    col = st.selectbox("Column", num_cols)
                    if col:
                        st.bar_chart(df[col].value_counts().sort_index())
        if st.button("Clear"):
            st.session_state.uploaded_df = None
            st.rerun()

def profile_page():
    st.title("Profile")
    with get_user_db() as conn:
        user = conn.execute("SELECT * FROM users WHERE id = ?", (st.session_state.user_id,)).fetchone()
    if not user:
        return
    col1, col2 = st.columns(2)
    col1.write(f"**Username:** {user['username']}\n**Email:** {user['email']}\n**Role:** {user['role']}")
    if user['created_at']:
        col2.write(f"**Member since:** {user['created_at']}")
    st.divider()
    with st.form("update_profile"):
        new_email = st.text_input("New Email", user['email'])
        new_pw = st.text_input("New Password", type="password")
        confirm = st.text_input("Confirm", type="password")
        if st.form_submit_button("Update"):
            if new_pw and new_pw != confirm:
                st.error("Passwords don't match")
            else:
                with get_user_db() as conn:
                    if new_pw:
                        hashed = hash_password(new_pw)
                        conn.execute("UPDATE users SET email=?, password=? WHERE id=?", (new_email, hashed, st.session_state.user_id))
                    else:
                        conn.execute("UPDATE users SET email=? WHERE id=?", (new_email, st.session_state.user_id))
                st.success("Updated")
                st.rerun()
    st.divider()
    with st.form("delete_account"):
        st.warning("This is irreversible")
        confirm = st.checkbox("I understand")
        if st.form_submit_button("Delete Account") and confirm:
            with get_business_db() as b_conn:
                b_conn.execute("DELETE FROM transactions WHERE user_id = ?", (st.session_state.user_id,))
                b_conn.execute("DELETE FROM businesses WHERE user_id = ?", (st.session_state.user_id,))
                b_conn.execute("DELETE FROM user_preferences WHERE user_id = ?", (st.session_state.user_id,))
            with get_user_db() as conn:
                conn.execute("DELETE FROM users WHERE id = ?", (st.session_state.user_id,))
            logout_user()
            st.rerun()

def profit_dashboard_page():
    st.title("Profit Dashboard")
    if not st.session_state.active_business_id:
        st.warning("Select active business")
        return
    m = calculate_profit_metrics(st.session_state.user_id, st.session_state.active_business_id)
    if not m:
        st.info("No data")
        return
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Gross Profit", f"₹{m['gross_profit']:,.2f}", f"{m['gross_margin']:.1f}%")
    col2.metric("Net Profit", f"₹{m['net_profit']:,.2f}", f"{m['net_margin']:.1f}%")
    col3.metric("Revenue", f"₹{m['total_revenue']:,.2f}")
    col4.metric("COGS", f"₹{m['total_cogs']:,.2f}")
    st.divider()
    c1, c2 = st.columns(2)
    c1.metric("This Month Profit", f"₹{m['period_profit']:,.2f}", f"₹{m['period_sales']:,.2f} revenue")
    fig = go.Figure(data=[
        go.Bar(name='Revenue', x=['Current'], y=[m['period_sales']]),
        go.Bar(name='Expenses', x=['Current'], y=[m['total_expenses']]),
        go.Bar(name='Profit', x=['Current'], y=[m['period_profit']])
    ])
    fig.update_layout(barmode='group', height=300)
    c2.plotly_chart(fig)
    st.divider()
    trend = get_monthly_profit_trend(st.session_state.user_id, st.session_state.active_business_id)
    if not trend.empty:
        fig = px.line(trend, x='month_dt', y=['revenue','expenses','profit'], markers=True,
                      title="6‑Month Trend", labels={'value':'Amount'})
        fig.update_xaxes(tickformat='%b %Y')
        st.plotly_chart(fig)
        fig2 = px.bar(trend, x='month_dt', y='margin', title="Margin %", color='margin',
                      color_continuous_scale='RdYlGn')
        fig2.update_xaxes(tickformat='%b %Y')
        st.plotly_chart(fig2)

def inventory_management_page():
    st.title("Inventory")
    if not st.session_state.active_business_id:
        st.warning("Select active business")
        return
    inv = get_inventory_value(st.session_state.user_id, st.session_state.active_business_id)
    col1, col2, col3 = st.columns(3)
    col1.metric("Products", inv['product_count'])
    col2.metric("Total Units", f"{inv['total_units']:,.0f}")
    col3.metric("Inventory Value", f"₹{inv['total_value']:,.2f}")

    low = get_low_stock_items(st.session_state.user_id, st.session_state.active_business_id)
    if not low.empty:
        st.error(f"**{len(low)} low‑stock items**")
        with st.expander("View"):
            st.dataframe(low)

    tabs = st.tabs(["Products","Add Product","Movement","History"])
    with tabs[0]:
        with get_business_db() as conn:
            prods = pd.read_sql("SELECT product_name, sku, quantity, cost_price, selling_price, reorder_level, category, (quantity*cost_price) as stock_value FROM products WHERE user_id=? AND business_id=? ORDER BY product_name",
                                conn, params=(st.session_state.user_id, st.session_state.active_business_id))
        if prods.empty:
            st.info("No products")
        else:
            prods['cost_price'] = prods['cost_price'].apply(lambda x: f"₹{x:,.2f}")
            prods['selling_price'] = prods['selling_price'].apply(lambda x: f"₹{x:,.2f}")
            prods['stock_value'] = prods['stock_value'].apply(lambda x: f"₹{x:,.2f}")
            st.dataframe(prods)
    with tabs[1]:
        with st.form("add_product"):
            name = st.text_input("Name *")
            sku = st.text_input("SKU")
            qty = st.number_input("Initial Qty", 0.0, step=1.0)
            cost = st.number_input("Cost Price *", 0.0, step=1.0)
            price = st.number_input("Selling Price *", 0.0, step=1.0)
            reorder = st.number_input("Reorder Level", 0.0, step=1.0, value=5.0)
            cat = st.selectbox("Category", ["Electronics","Clothing","Food","Furniture","Other"])
            if st.form_submit_button("Add") and name and cost>0 and price>0:
                ok, msg = add_product(st.session_state.user_id, st.session_state.active_business_id,
                                      name, sku, qty, cost, price, reorder, cat)
                st.success(msg) if ok else st.error(msg)
                if ok: st.rerun()
    with tabs[2]:
        with get_business_db() as conn:
            plist = pd.read_sql("SELECT id, product_name, quantity FROM products WHERE user_id=? AND business_id=?",
                                conn, params=(st.session_state.user_id, st.session_state.active_business_id))
        if plist.empty:
            st.warning("Add products first")
        else:
            with st.form("movement"):
                pid = st.selectbox("Product", plist['id'].tolist(),
                                   format_func=lambda x: plist[plist['id']==x]['product_name'].iloc[0])
                cur_qty = plist[plist['id']==pid]['quantity'].iloc[0]
                st.info(f"Current stock: {cur_qty:,.2f}")
                move = st.selectbox("Type", ["purchase","sale","adjustment"])
                mqty = st.number_input("Quantity", 0.0, step=1.0)
                unit_cost = st.number_input("Unit Cost (if purchase)", 0.0, step=1.0)
                unit_price = st.number_input("Unit Price (if sale)", 0.0, step=1.0)
                ref = st.text_input("Reference")
                notes = st.text_area("Notes")
                if st.form_submit_button("Record") and mqty>0:
                    ok, msg = record_stock_movement(pid, move, mqty,
                                                    unit_cost or None,
                                                    unit_price or None,
                                                    ref or None, notes)
                    st.success(msg) if ok else st.error(msg)
                    if ok: st.rerun()
    with tabs[3]:
        with get_business_db() as conn:
            hist = pd.read_sql("""
                SELECT sm.movement_date, p.product_name, sm.movement_type, sm.quantity,
                       sm.unit_cost, sm.unit_price, sm.notes
                FROM stock_movements sm JOIN products p ON sm.product_id = p.id
                WHERE p.user_id = ? AND p.business_id = ?
                ORDER BY sm.movement_date DESC LIMIT 100
            """, conn, params=(st.session_state.user_id, st.session_state.active_business_id))
        if hist.empty:
            st.info("No movements")
        else:
            hist['movement_date'] = pd.to_datetime(hist['movement_date']).dt.strftime('%Y-%m-%d %H:%M')
            for c in ['unit_cost','unit_price']:
                hist[c] = hist[c].apply(lambda x: f"₹{x:,.2f}" if x else '-')
            st.dataframe(hist)

def cogs_analysis_page():
    st.title("COGS Analysis")
    if not st.session_state.active_business_id:
        st.warning("Select active business")
        return
    with get_business_db() as conn:
        df = pd.read_sql("""
            SELECT strftime('%Y-%m', t.date) as month,
                   COUNT(DISTINCT t.id) as sales,
                   SUM(t.amount) as revenue,
                   COALESCE(SUM(sm.quantity * sm.unit_cost), 0) as cogs
            FROM transactions t
            LEFT JOIN stock_movements sm ON t.id = sm.reference_id AND sm.movement_type = 'sale'
            WHERE t.user_id = ? AND t.business_id = ? AND t.type = 'Sales'
            GROUP BY month ORDER BY month DESC
        """, conn, params=(st.session_state.user_id, st.session_state.active_business_id))
    if df.empty:
        st.info("No COGS data")
        return
    df['gross_profit'] = df['revenue'] - df['cogs']
    df['margin'] = (df['gross_profit'] / df['revenue'] * 100).round(1)
    df['month_dt'] = pd.to_datetime(df['month'] + '-01')
    df = df.sort_values('month_dt')
    tot_rev, tot_cogs = df['revenue'].sum(), df['cogs'].sum()
    tot_profit = tot_rev - tot_cogs
    avg_margin = (tot_profit/tot_rev*100) if tot_rev else 0
    cols = st.columns(4)
    cols[0].metric("Total Revenue", f"₹{tot_rev:,.2f}")
    cols[1].metric("Total COGS", f"₹{tot_cogs:,.2f}")
    cols[2].metric("Gross Profit", f"₹{tot_profit:,.2f}")
    cols[3].metric("Avg Margin", f"{avg_margin:.1f}%")
    fig = go.Figure()
    fig.add_trace(go.Bar(name='Revenue', x=df['month_dt'], y=df['revenue']))
    fig.add_trace(go.Bar(name='COGS', x=df['month_dt'], y=df['cogs']))
    fig.add_trace(go.Scatter(name='Margin %', x=df['month_dt'], y=df['margin'],
                              yaxis='y2', line=dict(color='red', width=3)))
    fig.update_layout(yaxis=dict(title='Amount'), yaxis2=dict(title='Margin %', overlaying='y', side='right', range=[0,100]))
    fig.update_xaxes(tickformat='%b %Y')
    st.plotly_chart(fig)
    st.dataframe(df)

# -----------------------------------------------------------------------------
# Milestone 3 – Advanced Analytics Functions
# -----------------------------------------------------------------------------
def prepare_time_series(user_id, business_id, value_type='sales', freq='M'):
    with get_business_db() as conn:
        df = pd.read_sql("SELECT date, type, amount FROM transactions WHERE user_id=? AND business_id=? ORDER BY date",
                         conn, params=(user_id, business_id))
    if df.empty:
        return pd.DataFrame()
    df['date'] = pd.to_datetime(df['date'])
    if value_type == 'sales':
        ts = df[df['type']=='Sales'].groupby('date')['amount'].sum().reset_index()
    elif value_type == 'profit':
        sales = df[df['type']=='Sales'].groupby('date')['amount'].sum()
        exp = df[df['type']=='Expense'].groupby('date')['amount'].sum()
        profit = (sales - exp).fillna(0).reset_index()
        profit.columns = ['date','amount']
        ts = profit
    else:
        return pd.DataFrame()
    if ts.empty:
        return ts
    ts = ts.set_index('date').resample(freq).sum().reset_index()
    ts.columns = ['ds','y']
    return ts.dropna()

def forecast_with_prophet(df, periods, freq):
    if not prophet_available:
        return None
    try:
        model = Prophet(yearly_seasonality=True, weekly_seasonality=(freq=='W'), daily_seasonality=False,
                        seasonality_mode='multiplicative')
        model.fit(df)
        future = model.make_future_dataframe(periods=periods, freq=freq)
        return model.predict(future)[['ds','yhat','yhat_lower','yhat_upper']]
    except Exception as e:
        st.error(f"Prophet error: {e}")
        return None

def forecast_with_linear_regression(df, periods, freq):
    try:
        df = df.copy()
        df['days'] = (df['ds'] - df['ds'].min()).dt.days
        X = df['days'].values.reshape(-1,1)
        y = df['y'].values
        model = LinearRegression().fit(X, y)
        last = df['days'].max()
        step = 30 if freq=='M' else (7 if freq=='W' else 1)
        fut = np.arange(last+step, last+step*periods+step, step).reshape(-1,1)
        pred = model.predict(fut)
        dates = [df['ds'].min() + timedelta(days=int(d)) for d in fut.flatten()]
        return pd.DataFrame({'ds':dates, 'yhat':pred, 'yhat_lower':pred*0.9, 'yhat_upper':pred*1.1})
    except Exception as e:
        st.error(f"LinReg error: {e}")
        return None

def get_forecast(user_id, business_id, target, periods, freq, method='auto'):
    ts = prepare_time_series(user_id, business_id, target, freq)
    if ts.empty or len(ts) < 3:
        return None
    if method == 'auto':
        method = 'prophet' if prophet_available else 'linear'
    if method == 'prophet' and prophet_available:
        return forecast_with_prophet(ts, periods, freq)
    return forecast_with_linear_regression(ts, periods, freq)

def get_expense_by_category(user_id, business_id, period):
    with get_business_db() as conn:
        q = "SELECT category, SUM(amount) as total FROM transactions WHERE user_id=? AND business_id=? AND type='Expense'"
        params = [user_id, business_id]
        if period == 'week':
            q += " AND date >= date('now','-7 days')"
        elif period == 'month':
            q += " AND date >= date('now','-30 days')"
        elif period == 'year':
            q += " AND date >= date('now','-1 year')"
        q += " GROUP BY category ORDER BY total DESC"
        return pd.read_sql(q, conn, params=params)

def get_sales_by_category(user_id, business_id, period):
    with get_business_db() as conn:
        q = "SELECT category, SUM(amount) as total FROM transactions WHERE user_id=? AND business_id=? AND type='Sales'"
        params = [user_id, business_id]
        if period == 'week':
            q += " AND date >= date('now','-7 days')"
        elif period == 'month':
            q += " AND date >= date('now','-30 days')"
        elif period == 'year':
            q += " AND date >= date('now','-1 year')"
        q += " GROUP BY category ORDER BY total DESC"
        return pd.read_sql(q, conn, params=params)

def sales_trends_page():
    st.title("Sales Trends")
    if not st.session_state.active_business_id:
        st.warning("Select active business")
        return
    with get_business_db() as conn:
        df = pd.read_sql("SELECT date, amount FROM transactions WHERE user_id=? AND business_id=? AND type='Sales' ORDER BY date",
                         conn, params=(st.session_state.user_id, st.session_state.active_business_id))
    if df.empty:
        st.info("No sales")
        return
    df['date'] = pd.to_datetime(df['date'])
    st.info(f"Records: {len(df)} from {df['date'].min().date()} to {df['date'].max().date()}")
    period = st.radio("View", ["Daily","Weekly","Monthly"], horizontal=True)
    freq = {"Daily":"D","Weekly":"W","Monthly":"M"}[period]
    grouped = df.set_index('date').resample(freq).sum().reset_index()
    fig = px.line(grouped, x='date', y='amount', title=f"Sales ({period})", markers=True)
    fig.update_xaxes(tickformat='%b %d, %Y' if period=='Daily' else '%b %Y')
    st.plotly_chart(fig)
    cols = st.columns(3)
    cols[0].metric("Total", f"₹{grouped['amount'].sum():,.2f}")
    cols[1].metric("Avg/period", f"₹{grouped['amount'].mean():,.2f}")
    cols[2].metric("Periods", len(grouped))

def profit_margins_page():
    st.title("Profit Margins")
    if not st.session_state.active_business_id:
        st.warning("Select active business")
        return
    with get_business_db() as conn:
        df = pd.read_sql("SELECT date, type, amount FROM transactions WHERE user_id=? AND business_id=? ORDER BY date",
                         conn, params=(st.session_state.user_id, st.session_state.active_business_id))
    if df.empty:
        st.info("No data")
        return
    df['date'] = pd.to_datetime(df['date'])
    pivot = df.pivot_table(index='date', columns='type', values='amount', aggfunc='sum').fillna(0)
    if 'Sales' not in pivot:
        pivot['Sales'] = 0
    if 'Expense' not in pivot:
        pivot['Expense'] = 0
    pivot['Profit'] = pivot['Sales'] - pivot['Expense']
    pivot['Margin'] = (pivot['Profit'] / pivot['Sales'] * 100).replace([np.inf,-np.inf],0).fillna(0)
    period = st.radio("Resample", ["Daily","Weekly","Monthly"], horizontal=True)
    freq = {"Daily":"D","Weekly":"W","Monthly":"M"}[period]
    res = pivot.resample(freq).sum().reset_index()
    fig = go.Figure()
    fig.add_trace(go.Bar(name='Sales', x=res['date'], y=res['Sales']))
    fig.add_trace(go.Bar(name='Expenses', x=res['date'], y=res['Expense']))
    fig.add_trace(go.Scatter(name='Margin %', x=res['date'], y=res['Margin'],
                              yaxis='y2', line=dict(color='red', width=3)))
    fig.update_layout(yaxis=dict(title='Amount'), yaxis2=dict(title='Margin %', overlaying='y', side='right', range=[0,100]))
    fig.update_xaxes(tickformat='%b %d, %Y' if period=='Daily' else '%b %Y')
    st.plotly_chart(fig)
    cols = st.columns(3)
    cols[0].metric("Total Profit", f"₹{res['Profit'].sum():,.2f}")
    cols[1].metric("Avg Margin", f"{res['Margin'].mean():.1f}%")
    cols[2].metric("Best Margin", f"{res['Margin'].max():.1f}%")

def expense_categories_page():
    st.title("Expense Categories")
    if not st.session_state.active_business_id:
        st.warning("Select active business")
        return
    period = st.selectbox("Period", ["All time","Last 30 days","Last 7 days","This year"])
    pmap = {"All time":None, "Last 30 days":"month", "Last 7 days":"week", "This year":"year"}
    df_exp = get_expense_by_category(st.session_state.user_id, st.session_state.active_business_id, pmap[period])
    if df_exp.empty:
        st.info("No expenses")
    else:
        fig = px.pie(df_exp, values='total', names='category', title=f"Expenses {period}")
        st.plotly_chart(fig)
        df_exp['total'] = df_exp['total'].apply(lambda x: f"₹{x:,.2f}")
        st.dataframe(df_exp)
    st.divider()
    st.subheader("Sales by Category")
    df_sales = get_sales_by_category(st.session_state.user_id, st.session_state.active_business_id, pmap[period])
    if df_sales.empty:
        st.info("No sales")
    else:
        fig = px.bar(df_sales, x='category', y='total', title=f"Sales {period}")
        st.plotly_chart(fig)
        df_sales['total'] = df_sales['total'].apply(lambda x: f"₹{x:,.2f}")
        st.dataframe(df_sales)

def forecasting_page():
    st.title("AI Forecasting")
    if not st.session_state.active_business_id:
        st.warning("Select active business")
        return
    with get_business_db() as conn:
        s = conn.execute("SELECT COUNT(*), MIN(date), MAX(date) FROM transactions WHERE user_id=? AND business_id=? AND type='Sales'",
                         (st.session_state.user_id, st.session_state.active_business_id)).fetchone()
        e = conn.execute("SELECT COUNT(*) FROM transactions WHERE user_id=? AND business_id=? AND type='Expense'",
                         (st.session_state.user_id, st.session_state.active_business_id)).fetchone()[0]
        distinct = conn.execute("SELECT COUNT(DISTINCT date) FROM transactions WHERE user_id=? AND business_id=? AND type='Sales'",
                                (st.session_state.user_id, st.session_state.active_business_id)).fetchone()[0]
    sales_cnt, min_dt, max_dt = s
    col1, col2 = st.columns(2)
    col1.metric("Sales Records", sales_cnt)
    if min_dt:
        col1.caption(f"From {min_dt} to {max_dt}  |  Distinct days: {distinct}")
    col2.metric("Expense Records", e)

    if sales_cnt == 0:
        st.warning("No sales data")
        return

    # frequency availability
    freq_labels = ["Daily","Weekly","Monthly"]
    freq_codes = ["D","W","M"]
    counts = []
    for code in freq_codes:
        ts = prepare_time_series(st.session_state.user_id, st.session_state.active_business_id, 'sales', code)
        counts.append(len(ts) if not ts.empty else 0)
    st.subheader("Data availability")
    cols = st.columns(3)
    for i, (lab, cnt) in enumerate(zip(freq_labels, counts)):
        with cols[i]:
            if cnt >= 3:
                st.success(f"**{lab}**: {cnt} ✓")
            else:
                # replace ✗ with 'X'
                st.error(f"**{lab}**: {cnt} X (need ≥3)")

    target = st.radio("Forecast", ["Sales","Profit"], horizontal=True)
    freq_opt = st.selectbox("Frequency", freq_labels, index=2)
    freq = freq_codes[freq_labels.index(freq_opt)]
    if freq == 'D':
        periods = st.slider("Horizon (days)", 7, 90, 30)
        unit = "days"
    elif freq == 'W':
        periods = st.slider("Horizon (weeks)", 1, 12, 4)
        unit = "weeks"
    else:
        periods = st.slider("Horizon (months)", 1, 12, 6)
        unit = "months"

    idx = freq_labels.index(freq_opt)
    if counts[idx] < 3:
        st.error(f"❌ Not enough data at {freq_opt} frequency ({counts[idx]} point(s)).")
        viable = [lab for lab, cnt in zip(freq_labels, counts) if cnt >= 3]
        if viable:
            st.info(f"✅ Try: {', '.join(viable)}")
        elif distinct == 1:
            st.error("All sales on same day. Add transactions on different dates.")
        else:
            st.info("Add more transactions spread over time.")
        st.button("Generate Forecast", disabled=True)
        return

    if st.button("Generate Forecast", type="primary"):
        with st.spinner("Calculating..."):
            fc = get_forecast(st.session_state.user_id, st.session_state.active_business_id,
                              target.lower(), periods, freq)
        if fc is None:
            st.error("Forecast failed")
            return
        hist = prepare_time_series(st.session_state.user_id, st.session_state.active_business_id,
                                   target.lower(), freq)
        hist = hist[hist['y']>0]
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=hist['ds'], y=hist['y'], mode='lines+markers', name='Historical', line=dict(color='blue')))
        fig.add_trace(go.Scatter(x=fc['ds'], y=fc['yhat'], mode='lines+markers', name='Forecast', line=dict(color='orange', dash='dash')))
        fig.add_trace(go.Scatter(x=fc['ds'], y=fc['yhat_upper'], mode='lines', line=dict(width=0), showlegend=False))
        fig.add_trace(go.Scatter(x=fc['ds'], y=fc['yhat_lower'], mode='lines', fill='tonexty', fillcolor='rgba(255,165,0,0.2)',
                                  line=dict(width=0), name='Confidence'))
        fmt = '%b %d' if freq=='D' else ('%b %d, %Y' if freq=='W' else '%b %Y')
        fig.update_layout(title=f"{target} Forecast ({freq_opt})", xaxis_title="Date", yaxis_title="Amount (₹)",
                          hovermode='x unified', xaxis=dict(tickformat=fmt))
        st.plotly_chart(fig)
        if not fc.empty:
            st.metric(f"Next {unit.capitalize()} Prediction", f"₹{fc.iloc[0]['yhat']:,.2f}")
        with st.expander("Forecast Table"):
            disp = fc[['ds','yhat','yhat_lower','yhat_upper']].copy()
            disp['ds'] = disp['ds'].dt.strftime('%Y-%m-%d' if freq in ('D','W') else '%Y-%m')
            for c in ['yhat','yhat_lower','yhat_upper']:
                disp[c] = disp[c].apply(lambda x: f"₹{x:,.2f}")
            st.dataframe(disp)

# -----------------------------------------------------------------------------
# Sidebar & Routing
# -----------------------------------------------------------------------------
def render_sidebar():
    with st.sidebar:
        st.title("Business Analyzer")
        user = authenticate()
        if not user and st.session_state.get('logged_in'):
            logout_user()
            st.rerun()
        if st.session_state.get('logged_in'):
            st.write(f"**Welcome,** {st.session_state.username}  \nRole: {st.session_state.role}")
            st.divider()
            # Core
            st.subheader("Core")
            cols = st.columns(2)
            with cols[0]: st.button("Dashboard", use_container_width=True, on_click=change_page, args=("Dashboard",))
            with cols[1]: st.button("Sales", use_container_width=True, on_click=change_page, args=("Sales Dashboard",))
            cols = st.columns(2)
            with cols[0]: st.button("Transactions", use_container_width=True, on_click=change_page, args=("View Transactions",))
            with cols[1]: st.button("Add Tx", use_container_width=True, on_click=change_page, args=("Add Transaction",))
            st.divider()
            # Profit & Inventory
            st.subheader("Business Intelligence")
            cols = st.columns(2)
            with cols[0]: st.button("Profit", use_container_width=True, on_click=change_page, args=("Profit Dashboard",))
            with cols[1]: st.button("Inventory", use_container_width=True, on_click=change_page, args=("Inventory",))
            cols = st.columns(2)
            with cols[0]: st.button("COGS", use_container_width=True, on_click=change_page, args=("COGS Analysis",))
            with cols[1]: st.button("Businesses", use_container_width=True, on_click=change_page, args=("Businesses",))
            st.divider()
            # Advanced Analytics
            st.subheader("Advanced")
            cols = st.columns(2)
            with cols[0]: st.button("Trends", use_container_width=True, on_click=change_page, args=("Sales Trends",))
            with cols[1]: st.button("Forecast", use_container_width=True, on_click=change_page, args=("Forecasting",))
            cols = st.columns(2)
            with cols[0]: st.button("Margins", use_container_width=True, on_click=change_page, args=("Profit Margins",))
            with cols[1]: st.button("Categories", use_container_width=True, on_click=change_page, args=("Expense Categories",))
            st.divider()
            # Data & Profile
            st.subheader("Data")
            cols = st.columns(2)
            with cols[0]: st.button("Import", use_container_width=True, on_click=change_page, args=("Import Transactions",))
            with cols[1]: st.button("Analyze", use_container_width=True, on_click=change_page, args=("Analyze Data",))
            st.divider()
            st.subheader("Account")
            cols = st.columns(2)
            with cols[0]: st.button("Profile", use_container_width=True, on_click=change_page, args=("Profile",))
            with cols[1]: st.button("Logout", use_container_width=True, on_click=logout_user)
        else:
            st.button("Home", use_container_width=True, on_click=change_page, args=("Home",))
            st.button("Login", use_container_width=True, on_click=change_page, args=("Login",))
            st.button("Sign Up", use_container_width=True, on_click=change_page, args=("Sign Up",))

def main():
    st.set_page_config(layout="wide", page_title="Business Analyzer")
    apply_custom_css()          # Apply custom styling
    init_user_db()
    init_business_db()
    init_inventory_tables()
    init_session_state()
    render_sidebar()
    page = st.session_state.page
    logged = st.session_state.logged_in

    # Route pages
    if page == "Home" and not logged: home_page()
    elif page == "Login" and not logged: login_page()
    elif page == "Sign Up" and not logged: signup_page()
    elif page == "Dashboard" and logged: dashboard_page()
    elif page == "Sales Dashboard" and logged: sales_dashboard_page()
    elif page == "Add Transaction" and logged: add_transaction_page()
    elif page == "View Transactions" and logged: view_transactions_page()
    elif page == "Import Transactions" and logged: import_transactions_page()
    elif page == "Analyze Data" and logged: analyze_data_page()
    elif page == "Businesses" and logged: businesses_page()
    elif page == "Profile" and logged: profile_page()
    elif page == "Profit Dashboard" and logged: profit_dashboard_page()
    elif page == "Inventory" and logged: inventory_management_page()
    elif page == "COGS Analysis" and logged: cogs_analysis_page()
    elif page == "Sales Trends" and logged: sales_trends_page()
    elif page == "Profit Margins" and logged: profit_margins_page()
    elif page == "Expense Categories" and logged: expense_categories_page()
    elif page == "Forecasting" and logged: forecasting_page()
    else:
        st.session_state.page = "Home" if not logged else "Dashboard"
        st.rerun()

if __name__ == "__main__":
    # Test database connection before starting
    try:
        with get_business_db() as conn:
            conn.execute("SELECT 1")
        main()
    except sqlite3.Error as e:
        st.error(f"Database connection failed. Ensure BUSINESS.db exists at: {BUSINESS_DB}\nError: {e}")
