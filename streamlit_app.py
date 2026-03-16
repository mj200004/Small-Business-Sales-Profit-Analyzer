"""
Business Analyzer – Full Production Code (SQLite)
- Tables use AUTOINCREMENT
- No RETURNING clauses – IDs obtained via lastrowid
- Registration uses a single connection to avoid visibility issues
- All Milestone features included
"""

import streamlit as st
import pandas as pd
import sqlalchemy as sa
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool
import numpy as np
import bcrypt
import jwt
from datetime import datetime, timedelta
from contextlib import contextmanager
import os
from pathlib import Path
import plotly.express as px
import plotly.graph_objects as go
from plotly.colors import qualitative
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import io
from fpdf import FPDF
import warnings
warnings.filterwarnings('ignore')
import sys
import traceback

# Optional imports
try:
    from prophet import Prophet
    PROPHET_AVAILABLE = True
except ImportError:
    PROPHET_AVAILABLE = False

from sklearn.linear_model import LinearRegression

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------
class Config:
    DATABASE_URL = os.environ.get('DATABASE_URL')
    SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'your-secret-key-change-in-production')
    JWT_ALGORITHM = 'HS256'
    ADMIN_PASSWORD = "Project@123"

    @classmethod
    def get_engine(cls):
        if cls.DATABASE_URL:
            return create_engine(cls.DATABASE_URL, poolclass=NullPool)
        else:
            data_dir = Path.home() / ".business_analyzer"
            data_dir.mkdir(exist_ok=True)
            db_path = data_dir / "app.db"
            return create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})

# -----------------------------------------------------------------------------
# Database Manager – SQLite specific
# -----------------------------------------------------------------------------
class DBManager:
    _engine = None

    @classmethod
    def get_engine(cls):
        if cls._engine is None:
            cls._engine = Config.get_engine()
            print(f"DEBUG: Database engine created. URL: {Config.DATABASE_URL or 'sqlite local'}", file=sys.stderr)
        return cls._engine

    @classmethod
    @contextmanager
    def get_connection(cls):
        engine = cls.get_engine()
        with engine.connect() as conn:
            print(f"DEBUG: Opened database connection", file=sys.stderr)
            yield conn
            conn.commit()
            print(f"DEBUG: Committed transaction", file=sys.stderr)

    @classmethod
    def init_db(cls):
        """Create tables with SQLite AUTOINCREMENT."""
        with cls.get_connection() as conn:
            # Users table
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username VARCHAR(255) UNIQUE NOT NULL,
                    email VARCHAR(255) UNIQUE NOT NULL,
                    password VARCHAR(255) NOT NULL,
                    role VARCHAR(50) NOT NULL DEFAULT 'Owner',
                    dob DATE,
                    gender VARCHAR(50),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            print("DEBUG: Ensured users table exists", file=sys.stderr)

            # Login history
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS login_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    login_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    logout_time TIMESTAMP,
                    session_duration INTEGER
                )
            """))

            # Admin access logs
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS admin_access_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    access_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))

            # Businesses
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS businesses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    business_name VARCHAR(255) NOT NULL,
                    business_type VARCHAR(255),
                    address TEXT,
                    phone VARCHAR(50),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))

            # Transactions
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    business_id INTEGER NOT NULL,
                    type VARCHAR(50) NOT NULL,
                    amount REAL NOT NULL,
                    category VARCHAR(255),
                    description TEXT,
                    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))

            # User preferences
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS user_preferences (
                    user_id INTEGER PRIMARY KEY,
                    active_business_id INTEGER,
                    currency_symbol VARCHAR(10) DEFAULT '₹',
                    default_reorder_level REAL DEFAULT 5.0
                )
            """))

            # Products
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    business_id INTEGER NOT NULL,
                    product_name VARCHAR(255) NOT NULL,
                    sku VARCHAR(255) UNIQUE,
                    quantity REAL DEFAULT 0,
                    cost_price REAL DEFAULT 0,
                    selling_price REAL DEFAULT 0,
                    reorder_level REAL DEFAULT 5,
                    category VARCHAR(255),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))

            # Stock movements
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS stock_movements (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_id INTEGER NOT NULL,
                    movement_type VARCHAR(50) NOT NULL,
                    quantity REAL NOT NULL,
                    unit_cost REAL,
                    unit_price REAL,
                    reference_id INTEGER,
                    movement_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    notes TEXT
                )
            """))
            print("DEBUG: All tables ensured", file=sys.stderr)

    @classmethod
    def execute(cls, query, params=None):
        print(f"DEBUG: Executing query: {query} with params: {params}", file=sys.stderr)
        with cls.get_connection() as conn:
            result = conn.execute(text(query), params or {})
            if result.returns_rows:
                rows = result.fetchall()
                print(f"DEBUG: Query returned {len(rows)} rows", file=sys.stderr)
                return rows
            print(f"DEBUG: Query executed (no rows returned)", file=sys.stderr)
            return result

    @classmethod
    def fetch_one(cls, query, params=None):
        print(f"DEBUG: Fetch one: {query} with params: {params}", file=sys.stderr)
        with cls.get_connection() as conn:
            result = conn.execute(text(query), params or {})
            row = result.fetchone()
            print(f"DEBUG: Fetched row: {row}", file=sys.stderr)
            return row

    @classmethod
    def fetch_all(cls, query, params=None):
        print(f"DEBUG: Fetch all: {query} with params: {params}", file=sys.stderr)
        with cls.get_connection() as conn:
            result = conn.execute(text(query), params or {})
            rows = result.fetchall()
            print(f"DEBUG: Fetched {len(rows)} rows", file=sys.stderr)
            return rows

    @classmethod
    def insert_and_get_id(cls, query, params=None, conn=None):
        """
        Execute an INSERT and return the generated primary key.
        If a connection is provided, use it; otherwise open a new one.
        """
        print(f"DEBUG: Insert and get ID: {query} with params: {params}", file=sys.stderr)
        if conn is not None:
            result = conn.execute(text(query), params or {})
            id_val = result.lastrowid
            print(f"DEBUG: Insert lastrowid (reused conn): {id_val}", file=sys.stderr)
            return id_val
        else:
            with cls.get_connection() as conn:
                result = conn.execute(text(query), params or {})
                id_val = result.lastrowid
                print(f"DEBUG: Insert lastrowid: {id_val}", file=sys.stderr)
                return id_val

# -----------------------------------------------------------------------------
# Authentication
# -----------------------------------------------------------------------------
class AuthManager:
    @staticmethod
    def hash_password(password):
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    @staticmethod
    def check_password(password, hashed):
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

    @staticmethod
    def create_jwt_token(user_id, username, role):
        payload = {
            'user_id': user_id,
            'username': username,
            'role': role,
            'exp': datetime.utcnow() + timedelta(days=1)
        }
        return jwt.encode(payload, Config.SECRET_KEY, algorithm=Config.JWT_ALGORITHM)

    @staticmethod
    def verify_jwt_token(token):
        try:
            return jwt.decode(token, Config.SECRET_KEY, algorithms=[Config.JWT_ALGORITHM])
        except jwt.PyJWTError:
            return None

    @staticmethod
    def login(username_or_email, password):
        """
        Login using either username or email.
        """
        print(f"DEBUG: Login attempt for: {username_or_email}", file=sys.stderr)
        row = DBManager.fetch_one(
            "SELECT id, username, email, password, role FROM users WHERE username = :login OR email = :login",
            {"login": username_or_email}
        )

        if not row:
            print(f"DEBUG: No user found for {username_or_email}", file=sys.stderr)
            return {'success': False, 'message': 'Invalid username/email or password'}

        # Extract user_id (handles different row types)
        try:
            user_id = row[0]
        except (IndexError, TypeError):
            user_id = row._mapping['id']

        username = row[1]
        email = row[2]
        password_hash = row[3]
        role = row[4]

        if not AuthManager.check_password(password, password_hash):
            print(f"DEBUG: Password check failed for {username_or_email}", file=sys.stderr)
            return {'success': False, 'message': 'Invalid username/email or password'}

        print(f"DEBUG: Login successful for user {username} (ID: {user_id})", file=sys.stderr)

        # Log login – no RETURNING
        try:
            login_id = DBManager.insert_and_get_id(
                "INSERT INTO login_history (user_id) VALUES (:uid)",
                {"uid": user_id}
            )
            st.session_state.current_login_id = login_id
            print(f"DEBUG: Login history recorded with ID {login_id}", file=sys.stderr)
        except Exception as e:
            print(f"DEBUG: Login tracking failed: {e}", file=sys.stderr)
            st.warning(f"Login tracking failed: {e}")
            st.session_state.current_login_id = None

        # Load preferences
        pref = DBManager.fetch_one(
            "SELECT active_business_id, currency_symbol, default_reorder_level FROM user_preferences WHERE user_id = :uid",
            {"uid": user_id}
        )
        if not pref:
            print(f"DEBUG: No preferences found for user {user_id}, creating default", file=sys.stderr)
            DBManager.execute(
                "INSERT INTO user_preferences (user_id) VALUES (:uid)",
                {"uid": user_id}
            )
            pref = (None, '₹', 5.0)
        else:
            print(f"DEBUG: Preferences loaded: {pref}", file=sys.stderr)

        return {
            'success': True,
            'token': AuthManager.create_jwt_token(user_id, username, role),
            'user_id': user_id,
            'username': username,
            'role': role,
            'active_business_id': pref[0],
            'currency_symbol': pref[1],
            'default_reorder_level': pref[2]
        }

    @staticmethod
    def register(username, email, password, role, dob, gender):
        print(f"DEBUG: Registration attempt: username={username}, email={email}, role={role}", file=sys.stderr)
        # Use a single connection for the whole operation
        with DBManager.get_connection() as conn:
            try:
                hashed = AuthManager.hash_password(password)
                # Insert user – reuse the connection
                user_id = DBManager.insert_and_get_id(
                    """
                    INSERT INTO users (username, email, password, role, dob, gender)
                    VALUES (:un, :em, :pw, :role, :dob, :gender)
                    """,
                    {"un": username, "em": email, "pw": hashed,
                     "role": role, "dob": dob, "gender": gender},
                    conn=conn
                )
                print(f"DEBUG: Registration returned user_id: {user_id}", file=sys.stderr)

                if user_id is None:
                    raise Exception("User creation failed: no ID returned from database")

                # Verify the user was actually inserted – still inside the same transaction
                check = conn.execute(
                    text("SELECT id FROM users WHERE id = :uid"),
                    {"uid": user_id}
                ).fetchone()
                if not check:
                    raise Exception("User creation failed: cannot find newly created user")

                print(f"DEBUG: User {username} created successfully with ID {user_id}", file=sys.stderr)

                # Insert preferences (using the same connection)
                conn.execute(
                    text("INSERT INTO user_preferences (user_id) VALUES (:uid)"),
                    {"uid": user_id}
                )
                print(f"DEBUG: Preferences created for user {user_id}", file=sys.stderr)

                # Commit happens automatically when the context manager exits without exception
                return {'success': True, 'message': 'Account created'}

            except Exception as e:
                print(f"DEBUG: Registration exception: {e}", file=sys.stderr)
                traceback.print_exc(file=sys.stderr)
                # The context manager will roll back automatically on exception
                if 'unique constraint' in str(e).lower():
                    return {'success': False, 'message': 'Username or email already exists'}
                return {'success': False, 'message': str(e)}

# -----------------------------------------------------------------------------
# Session Helpers
# -----------------------------------------------------------------------------
def init_session():
    defaults = {
        'token': None,
        'logged_in': False,
        'username': None,
        'user_id': None,
        'role': None,
        'page': 'Home',
        'uploaded_df': None,
        'active_business_id': None,
        'currency_symbol': '₹',
        'default_reorder_level': 5.0,
        'admin_authenticated': False,
        'current_login_id': None
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v
    print(f"DEBUG: Session initialized: logged_in={st.session_state.logged_in}, user_id={st.session_state.user_id}", file=sys.stderr)

def set_page(page):
    print(f"DEBUG: Setting page to {page}", file=sys.stderr)
    st.session_state.page = page

def logout():
    print(f"DEBUG: Logging out user {st.session_state.username}", file=sys.stderr)
    if st.session_state.current_login_id:
        # SQLite version: compute session duration in seconds
        DBManager.execute(
            """
            UPDATE login_history
            SET logout_time = CURRENT_TIMESTAMP,
                session_duration = CAST((julianday('now') - julianday(login_time)) * 86400 AS INTEGER)
            WHERE id = :lid
            """,
            {"lid": st.session_state.current_login_id}
        )
        print(f"DEBUG: Logout time updated for login ID {st.session_state.current_login_id}", file=sys.stderr)
    keys_to_clear = ['token', 'logged_in', 'username', 'user_id', 'role', 'uploaded_df',
                     'active_business_id', 'currency_symbol', 'default_reorder_level',
                     'current_login_id', 'admin_authenticated']
    for k in keys_to_clear:
        st.session_state.pop(k, None)
    st.session_state.page = 'Home'
    print(f"DEBUG: User logged out, session cleared", file=sys.stderr)

def authenticate():
    token = st.session_state.get('token')
    if not token:
        return None
    payload = AuthManager.verify_jwt_token(token)
    if not payload:
        logout()
    return payload

def is_owner():
    return st.session_state.role == 'Owner'

def can_edit_transactions():
    return st.session_state.role in ['Owner', 'Accountant']

def can_delete_transactions():
    return st.session_state.role == 'Owner'

# -----------------------------------------------------------------------------
# Page Functions
# -----------------------------------------------------------------------------

def page_home():
    st.title("Business Analyzer")
    st.markdown("""
    ### Milestone 1 – Authentication & Basic Transaction Logging
    **Features:** Secure registration/login, business profiles, transaction logging, sales dashboard, file analyzer.

    ### Milestone 2 – Profit & Inventory Tracking
    **Features:** Profit metrics, inventory management, COGS analysis, low stock alerts.

    ### Milestone 3 – Advanced Analytics
    **Features:** Interactive trends, profit margins, category breakdowns, AI forecasting.

    ### Milestone 4 – Reports, Admin, and Deployment
    **Features:** PDF/Excel report generation, admin dashboard.
    """)

def page_login():
    if st.session_state.get('logged_in', False):
        print(f"DEBUG: Already logged in, redirecting to Dashboard", file=sys.stderr)
        set_page('Dashboard')
        st.rerun()
        return

    st.title("Login")
    with st.form("login_form"):
        login_field = st.text_input("Username or Email")
        password = st.text_input("Password", type="password")
        if st.form_submit_button("Login", use_container_width=True):
            if login_field and password:
                res = AuthManager.login(login_field, password)
                if res['success']:
                    st.session_state.update({
                        'token': res['token'],
                        'logged_in': True,
                        'username': res['username'],
                        'user_id': res['user_id'],
                        'role': res['role'],
                        'active_business_id': res['active_business_id'],
                        'currency_symbol': res['currency_symbol'],
                        'default_reorder_level': res['default_reorder_level'],
                        'page': 'Dashboard'
                    })
                    print(f"DEBUG: Login successful, session updated, redirecting to Dashboard", file=sys.stderr)
                    st.rerun()
                else:
                    st.error(res['message'])
            else:
                st.error("Enter both fields")

def page_signup():
    st.title("Sign Up")
    with st.form("signup_form"):
        nu = st.text_input("Username")
        em = st.text_input("Email")
        pw = st.text_input("Password", type="password")
        cf = st.text_input("Confirm Password", type="password")
        dob = st.date_input("Date of Birth", min_value=datetime(1900,1,1), max_value=datetime.now().date())
        gender = st.selectbox("Gender", ["Male", "Female", "Other"])
        role = st.selectbox("Role", ["Owner", "Accountant", "Staff", "Manager"])
        if st.form_submit_button("Sign Up", use_container_width=True):
            if not nu or not em or not pw:
                st.error("Please fill all required fields.")
            elif pw != cf:
                st.error("Passwords do not match.")
            else:
                res = AuthManager.register(nu, em, pw, role, dob, gender)
                if res['success']:
                    st.success("Account created! Please login.")
                    set_page("Login")
                    st.rerun()
                else:
                    st.error(res['message'])

def page_dashboard():
    if st.session_state.user_id is None:
        st.warning("Please log in first.")
        set_page("Login")
        st.rerun()

    st.title("Dashboard")
    aid = st.session_state.active_business_id
    if aid:
        cnt = DBManager.fetch_one(
            "SELECT COUNT(*) FROM transactions WHERE user_id = :uid AND business_id = :bid",
            {"uid": st.session_state.user_id, "bid": aid}
        )[0]
        sales = DBManager.fetch_one(
            "SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE user_id = :uid AND business_id = :bid AND type = 'Sales'",
            {"uid": st.session_state.user_id, "bid": aid}
        )[0]
        exp = DBManager.fetch_one(
            "SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE user_id = :uid AND business_id = :bid AND type = 'Expense'",
            {"uid": st.session_state.user_id, "bid": aid}
        )[0]
    else:
        cnt = sales = exp = 0
    profit = sales - exp
    show_metric_row([
        ("Transactions", cnt, None),
        ("Total Sales", f"{st.session_state.currency_symbol}{sales:,.2f}", None),
        ("Net Profit", f"{st.session_state.currency_symbol}{profit:,.2f}", None)
    ])
    if cnt == 0:
        st.info("No transactions yet. Use 'Add Transaction' or 'Import CSV'.")

    st.divider()
    st.subheader("Active Business")
    biz_rows = DBManager.fetch_all(
        "SELECT id, business_name FROM businesses WHERE user_id = :uid",
        {"uid": st.session_state.user_id}
    )
    biz = pd.DataFrame(biz_rows, columns=['id', 'business_name'])
    if not biz.empty:
        opts = biz.set_index('id')['business_name'].to_dict()
        cur = st.session_state.active_business_id
        sel = st.selectbox("Select business", options=list(opts.keys()), format_func=lambda x: opts[x],
                           index=list(opts.keys()).index(cur) if cur in opts else 0)
        if sel != cur:
            st.session_state.active_business_id = sel
            DBManager.execute(
                "UPDATE user_preferences SET active_business_id = :bid WHERE user_id = :uid",
                {"bid": sel, "uid": st.session_state.user_id}
            )
            st.rerun()
    else:
        st.warning("Create a business in 'My Businesses'.")

def page_businesses():
    if st.session_state.user_id is None:
        st.warning("Please log in first.")
        set_page("Login")
        st.rerun()

    st.title("My Businesses")
    with st.expander("Add New Business"):
        with st.form("add_business_form"):
            name = st.text_input("Business Name *")
            typ = st.text_input("Type")
            addr = st.text_area("Address")
            phone = st.text_input("Phone")
            if st.form_submit_button("Create", use_container_width=True) and name:
                if st.session_state.user_id is None:
                    st.error("Session error. Please log in again.")
                    set_page("Login")
                    st.rerun()
                # No RETURNING
                bid = DBManager.insert_and_get_id(
                    """
                    INSERT INTO businesses (user_id, business_name, business_type, address, phone)
                    VALUES (:uid, :name, :typ, :addr, :phone)
                    """,
                    {"uid": st.session_state.user_id, "name": name, "typ": typ, "addr": addr, "phone": phone}
                )
                count = DBManager.fetch_one(
                    "SELECT COUNT(*) FROM businesses WHERE user_id = :uid",
                    {"uid": st.session_state.user_id}
                )[0]
                if count == 1:
                    DBManager.execute(
                        "UPDATE user_preferences SET active_business_id = :bid WHERE user_id = :uid",
                        {"bid": bid, "uid": st.session_state.user_id}
                    )
                    st.session_state.active_business_id = bid
                st.success(f"Business '{name}' created!")
                st.rerun()

    biz_rows = DBManager.fetch_all(
        "SELECT id, business_name, business_type, address, phone, created_at FROM businesses WHERE user_id = :uid ORDER BY created_at DESC",
        {"uid": st.session_state.user_id}
    )
    df = pd.DataFrame(biz_rows, columns=['id','business_name','business_type','address','phone','created_at'])
    if df.empty:
        st.info("No businesses yet.")
        return

    for _, row in df.iterrows():
        bid, active = row['id'], st.session_state.active_business_id == row['id']
        cols = st.columns([3,1,1,1])
        active_tag = " [ACTIVE]" if active else ""
        cols[0].write(f"**{row['business_name']}**{active_tag}")
        cols[0].caption(f"{row['business_type'] or 'N/A'} | {row['phone'] or 'N/A'}")
        if not active and cols[1].button("Set Active", key=f"set_{bid}"):
            DBManager.execute(
                "UPDATE user_preferences SET active_business_id = :bid WHERE user_id = :uid",
                {"bid": bid, "uid": st.session_state.user_id}
            )
            st.session_state.active_business_id = bid
            st.rerun()
        if cols[2].button("Edit", key=f"edit_{bid}"):
            st.session_state[f"edit_{bid}"] = True
        if not active and cols[3].button("Delete", key=f"del_{bid}"):
            DBManager.execute("DELETE FROM transactions WHERE business_id = :bid", {"bid": bid})
            DBManager.execute("DELETE FROM businesses WHERE id = :bid", {"bid": bid})
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
                        DBManager.execute(
                            """
                            UPDATE businesses SET business_name=:name, business_type=:typ, address=:addr, phone=:phone WHERE id=:bid
                            """,
                            {"name": nn, "typ": nt, "addr": na, "phone": np_, "bid": bid}
                        )
                        st.success("Updated")
                        st.session_state[f"edit_{bid}"] = False
                        st.rerun()
                if st.button("Cancel", key=f"cancel_{bid}"):
                    st.session_state[f"edit_{bid}"] = False
                    st.rerun()
        st.divider()

def page_add_transaction():
    if st.session_state.user_id is None:
        st.warning("Please log in first.")
        set_page("Login")
        st.rerun()

    st.title("Add Transaction")
    if not st.session_state.active_business_id:
        st.warning("Select an active business first.")
        if st.button("Go to Businesses"):
            set_page("Businesses")
            st.rerun()
        return
    with st.form("transaction_form"):
        typ = st.selectbox("Type", ["Sales", "Expense"])
        amt = st.number_input(f"Amount ({st.session_state.currency_symbol})", min_value=0.01, value=1.0, step=1.0, format="%.2f")
        cat = st.text_input("Category")
        desc = st.text_area("Description")
        tdate = st.date_input("Date", datetime.now().date())
        if st.form_submit_button("Add", use_container_width=True, type="primary"):
            if amt <= 0:
                st.error("Amount must be >0")
            else:
                dt = datetime.combine(tdate, datetime.min.time())
                DBManager.execute(
                    """
                    INSERT INTO transactions (user_id, business_id, type, amount, category, description, date)
                    VALUES (:uid, :bid, :typ, :amt, :cat, :desc, :dt)
                    """,
                    {"uid": st.session_state.user_id, "bid": st.session_state.active_business_id,
                     "typ": typ, "amt": amt, "cat": cat, "desc": desc, "dt": dt}
                )
                st.success("Transaction added!")
                st.rerun()

def page_view_transactions():
    if st.session_state.user_id is None:
        st.warning("Please log in first.")
        set_page("Login")
        st.rerun()

    st.title("Transactions")
    if not st.session_state.active_business_id:
        st.warning("No active business.")
        return
    rows = DBManager.fetch_all(
        "SELECT id, type, amount, category, description, date FROM transactions WHERE user_id = :uid AND business_id = :bid ORDER BY date DESC",
        {"uid": st.session_state.user_id, "bid": st.session_state.active_business_id}
    )
    df = pd.DataFrame(rows, columns=['id', 'type', 'amount', 'category', 'description', 'date'])
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
            "amount": st.column_config.NumberColumn("Amount", min_value=0.01, format=f"{st.session_state.currency_symbol}%.2f", required=True),
            "category": st.column_config.TextColumn("Category"),
            "description": st.column_config.TextColumn("Description"),
            "date": st.column_config.DatetimeColumn("Date", disabled=True),
        },
        disabled=disabled, hide_index=True,
        num_rows="dynamic" if can_delete_transactions() else "fixed"
    )
    if can_edit_transactions() and st.button("Save Changes"):
        for _, r in edited.iterrows():
            DBManager.execute(
                "UPDATE transactions SET type = :typ, amount = :amt, category = :cat, description = :desc WHERE id = :id AND user_id = :uid",
                {"typ": r['type'], "amt": r['amount'], "cat": r['category'], "desc": r['description'],
                 "id": r['id'], "uid": st.session_state.user_id}
            )
        st.success("Saved")
        st.rerun()
    st.download_button("Download CSV", df.to_csv(index=False), "transactions.csv")

def page_import_transactions():
    if st.session_state.user_id is None:
        st.warning("Please log in first.")
        set_page("Login")
        st.rerun()

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
    amt_col = st.selectbox("Amount column", ["None"]+cols)
    typ_col = st.selectbox("Type column", ["None"]+cols)
    cat_col = st.selectbox("Category column", ["None"]+cols)
    desc_col = st.selectbox("Description column", ["None"]+cols)
    default_type = st.selectbox("Default type", ["Sales","Expense"])

    if amt_col != "None" and st.button("IMPORT", type="primary"):
        success = 0
        errors = 0
        error_details = []
        prog = st.progress(0)
        status = st.empty()

        for idx, row in df.iterrows():
            try:
                raw_amt = row[amt_col]
                if pd.isna(raw_amt):
                    errors += 1
                    error_details.append(f"Row {idx+2}: Amount is empty")
                    continue

                amt_str = str(raw_amt).replace('₹', '').replace(',', '').strip()
                amt_str = ''.join(c for c in amt_str if c.isdigit() or c in '.-')
                if not amt_str:
                    errors += 1
                    error_details.append(f"Row {idx+2}: Amount contains no valid number")
                    continue

                amt = float(amt_str)
                if amt <= 0:
                    errors += 1
                    error_details.append(f"Row {idx+2}: Amount is not positive ({amt})")
                    continue

                ttype = default_type
                if typ_col != "None" and pd.notna(row[typ_col]):
                    val = str(row[typ_col]).lower()
                    if 'sale' in val or 'income' in val:
                        ttype = 'Sales'
                    elif 'expense' in val or 'cost' in val:
                        ttype = 'Expense'

                cat = "Uncategorized"
                if cat_col != "None" and pd.notna(row[cat_col]):
                    cat = str(row[cat_col])[:50]

                desc = f"Row {idx+1}"
                if desc_col != "None" and pd.notna(row[desc_col]):
                    desc = str(row[desc_col])[:200]

                DBManager.execute(
                    """
                    INSERT INTO transactions (user_id, business_id, type, amount, category, description)
                    VALUES (:uid, :bid, :typ, :amt, :cat, :desc)
                    """,
                    {"uid": st.session_state.user_id, "bid": st.session_state.active_business_id,
                     "typ": ttype, "amt": amt, "cat": cat, "desc": desc}
                )
                success += 1

            except Exception as e:
                errors += 1
                error_details.append(f"Row {idx+2}: {str(e)[:100]}")

            prog.progress((idx+1)/len(df))
            status.text(f"Processed {idx+1}/{len(df)}")

        prog.empty()
        status.empty()
        st.success(f"Imported {success} transactions, {errors} errors.")

        if errors > 0:
            with st.expander("Show sample errors (first 20)"):
                for err in error_details[:20]:
                    st.write(err)

        if success and st.button("View Transactions"):
            set_page("View Transactions")
            st.rerun()

def page_sales_dashboard():
    if st.session_state.user_id is None:
        st.warning("Please log in first.")
        set_page("Login")
        st.rerun()

    st.title("Sales Dashboard")
    if not st.session_state.active_business_id:
        st.warning("No active business")
        return
    rows = DBManager.fetch_all(
        "SELECT type, amount, category, date FROM transactions WHERE user_id = :uid AND business_id = :bid",
        {"uid": st.session_state.user_id, "bid": st.session_state.active_business_id}
    )
    df = pd.DataFrame(rows, columns=['type', 'amount', 'category', 'date'])
    if df.empty:
        st.info("No data")
        return
    df['date'] = pd.to_datetime(df['date'])
    sales = df[df['type'] == 'Sales']
    exps = df[df['type'] == 'Expense']

    if not sales.empty:
        sales_cat = sales.groupby('category')['amount'].sum().reset_index()
        colors = get_color_sequence(len(sales_cat), 'Bold')
        fig_sales = px.bar(sales_cat, x='category', y='amount', title="Sales by Category",
                           color='category', color_discrete_sequence=colors)
        st.plotly_chart(fig_sales, use_container_width=True)

    if not exps.empty:
        exp_cat = exps.groupby('category')['amount'].sum().reset_index()
        colors = get_color_sequence(len(exp_cat), 'Pastel')
        fig_exp = px.bar(exp_cat, x='category', y='amount', title="Expenses by Category",
                         color='category', color_discrete_sequence=colors)
        st.plotly_chart(fig_exp, use_container_width=True)

    df['month'] = df['date'].dt.to_period('M').astype(str)
    monthly = df.groupby(['month','type'])['amount'].sum().reset_index()
    if not monthly.empty:
        colors = {'Sales': '#1f77b4', 'Expense': '#d62728'}
        fig_trend = px.line(monthly, x='month', y='amount', color='type',
                            title="Monthly Trend", color_discrete_map=colors,
                            markers=True)
        st.plotly_chart(fig_trend, use_container_width=True)

    total_sales = sales['amount'].sum() if not sales.empty else 0
    total_exp = exps['amount'].sum() if not exps.empty else 0
    profit = total_sales - total_exp
    avg = sales['amount'].mean() if not sales.empty else 0
    show_metric_row([
        ("Total Sales", f"{st.session_state.currency_symbol}{total_sales:,.2f}", None),
        ("Total Expenses", f"{st.session_state.currency_symbol}{total_exp:,.2f}", None),
        ("Net Profit", f"{st.session_state.currency_symbol}{profit:,.2f}", None),
        ("Avg Sale", f"{st.session_state.currency_symbol}{avg:,.2f}", None)
    ])

def page_analyze_data():
    st.title("Analyze File")
    file = st.file_uploader("Upload CSV/Excel", type=['csv','xlsx','xls'])
    if file:
        if file.name.endswith('.csv'):
            df = pd.read_csv(file)
        else:
            df = pd.read_excel(file)
        st.session_state.uploaded_df = df
        st.success(f"Loaded {file.name}")

    if st.session_state.uploaded_df is not None:
        df = st.session_state.uploaded_df
        tabs = st.tabs(["Preview", "Stats", "Visualize"])

        with tabs[0]:
            st.dataframe(df.head(100))

        with tabs[1]:
            st.dataframe(df.describe(include='all').T)

        with tabs[2]:
            num_cols = df.select_dtypes(include='number').columns.tolist()
            if not num_cols:
                st.warning("No numeric columns to visualize.")
            else:
                chart_type = st.selectbox("Chart type", ["Bar", "Line", "Scatter", "Histogram", "Pie"])
                if chart_type == "Bar":
                    x_col = st.selectbox("X-axis (categorical)", df.columns)
                    y_col = st.selectbox("Y-axis (numeric)", num_cols)
                    if x_col and y_col:
                        agg_df = df.groupby(x_col)[y_col].sum().reset_index()
                        colors = get_color_sequence(len(agg_df), 'Set2')
                        fig = px.bar(agg_df, x=x_col, y=y_col, color=x_col,
                                     color_discrete_sequence=colors,
                                     title=f"{y_col} by {x_col}")
                        st.plotly_chart(fig, use_container_width=True)

                elif chart_type == "Line":
                    x_col = st.selectbox("X-axis (date/numeric)", df.columns)
                    y_col = st.selectbox("Y-axis (numeric)", num_cols)
                    if x_col and y_col:
                        plot_df = df[[x_col, y_col]].dropna().copy()
                        try:
                            plot_df[x_col] = pd.to_datetime(plot_df[x_col])
                            plot_df = plot_df.sort_values(x_col)
                        except:
                            pass
                        fig = px.line(plot_df, x=x_col, y=y_col, markers=True,
                                      title=f"{y_col} over {x_col}")
                        st.plotly_chart(fig, use_container_width=True)

                elif chart_type == "Scatter":
                    if len(num_cols) >= 2:
                        x_col = st.selectbox("X-axis", num_cols)
                        y_col = st.selectbox("Y-axis", num_cols)
                        color_col = st.selectbox("Color by (optional)", ["None"] + df.columns.tolist())
                        if x_col and y_col:
                            if color_col != "None":
                                fig = px.scatter(df, x=x_col, y=y_col, color=color_col,
                                                 title=f"{y_col} vs {x_col}")
                            else:
                                fig = px.scatter(df, x=x_col, y=y_col,
                                                 title=f"{y_col} vs {x_col}")
                            st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.warning("Need at least two numeric columns for scatter plot.")

                elif chart_type == "Histogram":
                    col = st.selectbox("Column", num_cols)
                    if col:
                        fig = px.histogram(df, x=col, nbins=20,
                                           title=f"Distribution of {col}")
                        st.plotly_chart(fig, use_container_width=True)

                elif chart_type == "Pie":
                    cat_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
                    if cat_cols:
                        cat = st.selectbox("Category column", cat_cols)
                        num = st.selectbox("Numeric column (sum)", num_cols)
                        if cat and num:
                            pie_df = df.groupby(cat)[num].sum().reset_index()
                            colors = get_color_sequence(len(pie_df), 'Pastel')
                            fig = px.pie(pie_df, values=num, names=cat,
                                         title=f"{num} by {cat}",
                                         color_discrete_sequence=colors)
                            st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.warning("No categorical column found for pie chart.")

        if st.button("Clear Uploaded Data"):
            st.session_state.uploaded_df = None
            st.rerun()

def page_profile():
    if st.session_state.user_id is None:
        st.warning("Please log in first.")
        set_page("Login")
        st.rerun()

    st.title("Profile")
    user_row = DBManager.fetch_one(
        "SELECT id, username, email, role, dob, gender, created_at FROM users WHERE id = :uid",
        {"uid": st.session_state.user_id}
    )
    if not user_row:
        st.error("User not found")
        return

    # Use fallback access
    try:
        user_id = user_row[0]
        username = user_row[1]
        email = user_row[2]
        role = user_row[3]
        dob = user_row[4]
        gender = user_row[5]
        created_at = user_row[6]
    except (IndexError, TypeError):
        u = dict(user_row._mapping)
        user_id = u['id']
        username = u['username']
        email = u['email']
        role = u['role']
        dob = u['dob']
        gender = u['gender']
        created_at = u['created_at']

    col1, col2 = st.columns(2)
    with col1:
        st.write(f"**Username:** {username}")
        st.write(f"**Email:** {email}")
        st.write(f"**Role:** {role}")
        st.write(f"**Date of Birth:** {dob}")
        st.write(f"**Gender:** {gender}")
    with col2:
        st.write(f"**Member since:** {created_at}")

    st.divider()
    with st.form("update_profile"):
        new_email = st.text_input("New Email", email)
        new_pw = st.text_input("New Password", type="password")
        confirm = st.text_input("Confirm Password", type="password")
        if st.form_submit_button("Update Profile", use_container_width=True):
            if new_pw and new_pw != confirm:
                st.error("Passwords do not match. Please re-enter.")
            else:
                if new_pw:
                    hashed = AuthManager.hash_password(new_pw)
                    DBManager.execute(
                        "UPDATE users SET email = :email, password = :pw WHERE id = :uid",
                        {"email": new_email, "pw": hashed, "uid": st.session_state.user_id}
                    )
                else:
                    DBManager.execute(
                        "UPDATE users SET email = :email WHERE id = :uid",
                        {"email": new_email, "uid": st.session_state.user_id}
                    )
                st.success("Profile updated successfully")
                st.rerun()

    st.divider()
    with st.form("delete_account"):
        st.warning("Deleting your account is irreversible. All your data will be permanently removed.")
        confirm = st.checkbox("I understand the consequences")
        if st.form_submit_button("Delete My Account", use_container_width=True) and confirm:
            Admin.delete_user(st.session_state.user_id)
            logout()
            st.success("Account deleted. Redirecting...")
            st.rerun()

def page_profit_dashboard():
    if st.session_state.user_id is None:
        st.warning("Please log in first.")
        set_page("Login")
        st.rerun()

    st.title("Profit Dashboard")
    if not st.session_state.active_business_id:
        st.warning("Select active business")
        return
    m = Analytics.calculate_profit_metrics(st.session_state.user_id, st.session_state.active_business_id)
    if not m:
        st.info("No data")
        return
    show_metric_row([
        ("Gross Profit", f"{st.session_state.currency_symbol}{m['gross_profit']:,.2f}", f"{m['gross_margin']:.1f}%"),
        ("Net Profit", f"{st.session_state.currency_symbol}{m['net_profit']:,.2f}", f"{m['net_margin']:.1f}%"),
        ("Revenue", f"{st.session_state.currency_symbol}{m['total_revenue']:,.2f}", None),
        ("COGS", f"{st.session_state.currency_symbol}{m['total_cogs']:,.2f}", None)
    ])
    st.divider()
    c1, c2 = st.columns(2)
    c1.metric("This Month Profit", f"{st.session_state.currency_symbol}{m['period_profit']:,.2f}", f"{st.session_state.currency_symbol}{m['period_sales']:,.2f} revenue")

    fig = go.Figure(data=[
        go.Bar(name='Revenue', x=['Current'], y=[m['period_sales']], marker_color='#1f77b4'),
        go.Bar(name='Expenses', x=['Current'], y=[m['total_expenses']], marker_color='#d62728'),
        go.Bar(name='Profit', x=['Current'], y=[m['period_profit']], marker_color='#ff7f0e')
    ])
    fig.update_layout(barmode='group', height=300, showlegend=True, title="Current Period Overview")
    c2.plotly_chart(fig, use_container_width=True)

    st.divider()
    trend = Analytics.get_monthly_profit_trend(st.session_state.user_id, st.session_state.active_business_id)
    if not trend.empty:
        fig_trend = px.line(trend, x='month_dt', y=['revenue', 'expenses', 'profit'],
                            markers=True, title="6‑Month Trend",
                            labels={'value': 'Amount', 'month_dt': 'Month'},
                            color_discrete_map={'revenue': '#1f77b4',
                                                'expenses': '#d62728',
                                                'profit': '#ff7f0e'})
        fig_trend.update_xaxes(tickformat='%b %Y')
        st.plotly_chart(fig_trend, use_container_width=True)

        fig_margin = px.bar(trend, x='month_dt', y='margin',
                            title="Margin %", color='margin',
                            color_continuous_scale='RdYlGn',
                            labels={'margin': 'Margin %', 'month_dt': 'Month'})
        fig_margin.update_xaxes(tickformat='%b %Y')
        st.plotly_chart(fig_margin, use_container_width=True)

def page_inventory():
    if st.session_state.user_id is None:
        st.warning("Please log in first.")
        set_page("Login")
        st.rerun()

    st.title("Inventory")
    if not st.session_state.active_business_id:
        st.warning("Select active business")
        return
    inv = Analytics.get_inventory_value(st.session_state.user_id, st.session_state.active_business_id)
    show_metric_row([
        ("Products", inv['product_count'], None),
        ("Total Units", f"{inv['total_units']:,.0f}", None),
        ("Inventory Value", f"{st.session_state.currency_symbol}{inv['total_value']:,.2f}", None)
    ])

    low = Analytics.get_low_stock_items(st.session_state.user_id, st.session_state.active_business_id)
    if not low.empty:
        st.error(f"**{len(low)} low‑stock items**")
        with st.expander("View"):
            st.dataframe(low)

    tabs = st.tabs(["Products", "Add Product", "Movement", "History"])
    with tabs[0]:
        prods_rows = DBManager.fetch_all(
            """
            SELECT product_name, sku, quantity, cost_price, selling_price, reorder_level, category,
                   (quantity * cost_price) as stock_value
            FROM products WHERE user_id = :uid AND business_id = :bid ORDER BY product_name
            """,
            {"uid": st.session_state.user_id, "bid": st.session_state.active_business_id}
        )
        prods = pd.DataFrame(prods_rows, columns=['product_name','sku','quantity','cost_price','selling_price','reorder_level','category','stock_value'])
        if prods.empty:
            st.info("No products")
        else:
            for col in ['cost_price', 'selling_price', 'stock_value']:
                prods[col] = prods[col].apply(lambda x: f"{st.session_state.currency_symbol}{x:,.2f}")
            st.dataframe(prods)
    with tabs[1]:
        with st.form("add_product"):
            name = st.text_input("Product Name *")
            sku = st.text_input("SKU (unique identifier)")
            qty = st.number_input("Initial Quantity", 0.0, step=1.0)
            cost = st.number_input("Cost Price *", 0.0, step=1.0)
            price = st.number_input("Selling Price *", 0.0, step=1.0)
            reorder = st.number_input("Reorder Level", 0.0, step=1.0, value=st.session_state.default_reorder_level)
            cat = st.selectbox("Category", ["Electronics", "Clothing", "Food", "Furniture", "Other"])
            if st.form_submit_button("Add Product", use_container_width=True):
                if name and cost > 0 and price > 0:
                    ok, msg = Analytics.add_product(st.session_state.user_id, st.session_state.active_business_id,
                                                    name, sku, qty, cost, price, reorder, cat)
                    if ok:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)
                else:
                    st.error("Please fill all required fields.")
    with tabs[2]:
        plist_rows = DBManager.fetch_all(
            "SELECT id, product_name, quantity FROM products WHERE user_id = :uid AND business_id = :bid",
            {"uid": st.session_state.user_id, "bid": st.session_state.active_business_id}
        )
        plist = pd.DataFrame(plist_rows, columns=['id','product_name','quantity'])
        if plist.empty:
            st.warning("Add products first")
        else:
            with st.form("movement"):
                pid = st.selectbox("Product", plist['id'].tolist(),
                                   format_func=lambda x: plist[plist['id']==x]['product_name'].iloc[0])
                cur_qty = plist[plist['id']==pid]['quantity'].iloc[0]
                st.info(f"Current stock: {cur_qty:,.2f}")
                move = st.selectbox("Movement Type", ["purchase", "sale", "adjustment"])
                mqty = st.number_input("Quantity", 0.0, step=1.0)
                unit_cost = st.number_input("Unit Cost (if purchase)", 0.0, step=1.0)
                unit_price = st.number_input("Unit Price (if sale)", 0.0, step=1.0)
                ref = st.text_input("Reference (optional)")
                notes = st.text_area("Notes")
                if st.form_submit_button("Record Movement", use_container_width=True):
                    if mqty > 0:
                        ok, msg = Analytics.record_stock_movement(pid, move, mqty,
                                                                   unit_cost or None,
                                                                   unit_price or None,
                                                                   ref or None, notes)
                        if ok:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)
                    else:
                        st.error("Quantity must be positive.")
    with tabs[3]:
        hist_rows = DBManager.fetch_all(
            """
            SELECT sm.movement_date, p.product_name, sm.movement_type, sm.quantity,
                   sm.unit_cost, sm.unit_price, sm.notes
            FROM stock_movements sm JOIN products p ON sm.product_id = p.id
            WHERE p.user_id = :uid AND p.business_id = :bid
            ORDER BY sm.movement_date DESC LIMIT 100
            """,
            {"uid": st.session_state.user_id, "bid": st.session_state.active_business_id}
        )
        hist = pd.DataFrame(hist_rows, columns=['movement_date','product_name','movement_type','quantity','unit_cost','unit_price','notes'])
        if hist.empty:
            st.info("No movements")
        else:
            hist['movement_date'] = pd.to_datetime(hist['movement_date']).dt.strftime('%Y-%m-%d %H:%M')
            for c in ['unit_cost', 'unit_price']:
                hist[c] = hist[c].apply(lambda x: f"{st.session_state.currency_symbol}{x:,.2f}" if x else '-')
            st.dataframe(hist)

def page_cogs():
    if st.session_state.user_id is None:
        st.warning("Please log in first.")
        set_page("Login")
        st.rerun()

    st.title("COGS Analysis")
    if not st.session_state.active_business_id:
        st.warning("Select active business")
        return
    rows = DBManager.fetch_all(
        """
        SELECT strftime('%Y-%m', t.date) as month,
               COUNT(DISTINCT t.id) as sales,
               SUM(t.amount) as revenue,
               COALESCE(SUM(sm.quantity * sm.unit_cost), 0) as cogs
        FROM transactions t
        LEFT JOIN stock_movements sm ON t.id = sm.reference_id AND sm.movement_type = 'sale'
        WHERE t.user_id = :uid AND t.business_id = :bid AND t.type = 'Sales'
        GROUP BY month ORDER BY month DESC
        """,
        {"uid": st.session_state.user_id, "bid": st.session_state.active_business_id}
    )
    df = pd.DataFrame(rows, columns=['month','sales','revenue','cogs'])
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
    show_metric_row([
        ("Total Revenue", f"{st.session_state.currency_symbol}{tot_rev:,.2f}", None),
        ("Total COGS", f"{st.session_state.currency_symbol}{tot_cogs:,.2f}", None),
        ("Gross Profit", f"{st.session_state.currency_symbol}{tot_profit:,.2f}", None),
        ("Avg Margin", f"{avg_margin:.1f}%", None)
    ])

    fig = go.Figure()
    fig.add_trace(go.Bar(name='Revenue', x=df['month_dt'], y=df['revenue'], marker_color='#1f77b4'))
    fig.add_trace(go.Bar(name='COGS', x=df['month_dt'], y=df['cogs'], marker_color='#d62728'))
    fig.add_trace(go.Scatter(name='Margin %', x=df['month_dt'], y=df['margin'],
                              yaxis='y2', line=dict(color='#ff7f0e', width=3),
                              mode='lines+markers'))
    fig.update_layout(
        yaxis=dict(title='Amount', side='left'),
        yaxis2=dict(title='Margin %', overlaying='y', side='right', range=[0, 100]),
        hovermode='x unified',
        barmode='group'
    )
    fig.update_xaxes(tickformat='%b %Y')
    st.plotly_chart(fig, use_container_width=True)

    st.dataframe(df)

def page_sales_trends():
    if st.session_state.user_id is None:
        st.warning("Please log in first.")
        set_page("Login")
        st.rerun()

    st.title("Sales Trends")
    if not st.session_state.active_business_id:
        st.warning("Select active business")
        return
    rows = DBManager.fetch_all(
        "SELECT date, amount FROM transactions WHERE user_id = :uid AND business_id = :bid AND type='Sales' ORDER BY date",
        {"uid": st.session_state.user_id, "bid": st.session_state.active_business_id}
    )
    df = pd.DataFrame(rows, columns=['date', 'amount'])
    if df.empty:
        st.info("No sales")
        return
    df['date'] = pd.to_datetime(df['date'])
    st.info(f"Records: {len(df)} from {df['date'].min().date()} to {df['date'].max().date()}")
    period = st.radio("View", ["Daily", "Weekly", "Monthly"], horizontal=True)
    freq = {"Daily": "D", "Weekly": "W", "Monthly": "M"}[period]
    grouped = df.set_index('date').resample(freq).sum().reset_index()
    fig = px.line(grouped, x='date', y='amount', title=f"Sales ({period})", markers=True,
                  line_shape='linear')
    fig.update_xaxes(tickformat='%b %d, %Y' if period == 'Daily' else '%b %Y')
    st.plotly_chart(fig, use_container_width=True)
    show_metric_row([
        ("Total", f"{st.session_state.currency_symbol}{grouped['amount'].sum():,.2f}", None),
        ("Avg/period", f"{st.session_state.currency_symbol}{grouped['amount'].mean():,.2f}", None),
        ("Periods", len(grouped), None)
    ])

def page_profit_margins():
    if st.session_state.user_id is None:
        st.warning("Please log in first.")
        set_page("Login")
        st.rerun()

    st.title("Profit Margins")
    if not st.session_state.active_business_id:
        st.warning("Select active business")
        return
    rows = DBManager.fetch_all(
        "SELECT date, type, amount FROM transactions WHERE user_id = :uid AND business_id = :bid ORDER BY date",
        {"uid": st.session_state.user_id, "bid": st.session_state.active_business_id}
    )
    df = pd.DataFrame(rows, columns=['date', 'type', 'amount'])
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
    pivot['Margin'] = (pivot['Profit'] / pivot['Sales'] * 100).replace([np.inf, -np.inf], 0).fillna(0)

    period = st.radio("Resample", ["Daily", "Weekly", "Monthly"], horizontal=True)
    freq = {"Daily": "D", "Weekly": "W", "Monthly": "M"}[period]
    res = pivot.resample(freq).sum().reset_index()

    fig = go.Figure()
    fig.add_trace(go.Bar(name='Sales', x=res['date'], y=res['Sales'], marker_color='#1f77b4'))
    fig.add_trace(go.Bar(name='Expenses', x=res['date'], y=res['Expense'], marker_color='#d62728'))
    fig.add_trace(go.Scatter(name='Margin %', x=res['date'], y=res['Margin'],
                              yaxis='y2', line=dict(color='#ff7f0e', width=3),
                              mode='lines+markers'))
    fig.update_layout(
        yaxis=dict(title='Amount', side='left'),
        yaxis2=dict(title='Margin %', overlaying='y', side='right', range=[0, 100]),
        hovermode='x unified',
        barmode='group',
        title=f"Profit Margins ({period})"
    )
    fig.update_xaxes(tickformat='%b %d, %Y' if period == 'Daily' else '%b %Y')
    st.plotly_chart(fig, use_container_width=True)

    show_metric_row([
        ("Total Profit", f"{st.session_state.currency_symbol}{res['Profit'].sum():,.2f}", None),
        ("Avg Margin", f"{res['Margin'].mean():.1f}%", None),
        ("Best Margin", f"{res['Margin'].max():.1f}%", None)
    ])

def page_expense_categories():
    if st.session_state.user_id is None:
        st.warning("Please log in first.")
        set_page("Login")
        st.rerun()

    st.title("Expense Categories")
    if not st.session_state.active_business_id:
        st.warning("Select active business")
        return
    period = st.selectbox("Period", ["All time", "Last 30 days", "Last 7 days", "This year"])
    pmap = {"All time": None, "Last 30 days": "month", "Last 7 days": "week", "This year": "year"}

    df_exp = Analytics.get_expense_by_category(st.session_state.user_id, st.session_state.active_business_id, pmap[period])
    if df_exp.empty:
        st.info("No expenses")
    else:
        colors = get_color_sequence(len(df_exp), 'Pastel')
        fig_exp = px.pie(df_exp, values='amount', names='category',
                         title=f"Expenses {period}", color_discrete_sequence=colors)
        st.plotly_chart(fig_exp, use_container_width=True)
        df_exp['amount'] = df_exp['amount'].apply(lambda x: f"{st.session_state.currency_symbol}{x:,.2f}")
        st.dataframe(df_exp)

    st.divider()
    st.subheader("Sales by Category")
    df_sales = Analytics.get_sales_by_category(st.session_state.user_id, st.session_state.active_business_id, pmap[period])
    if df_sales.empty:
        st.info("No sales")
    else:
        colors = get_color_sequence(len(df_sales), 'Bold')
        fig_sales = px.bar(df_sales, x='category', y='amount',
                           title=f"Sales {period}", color='category',
                           color_discrete_sequence=colors)
        st.plotly_chart(fig_sales, use_container_width=True)
        df_sales['amount'] = df_sales['amount'].apply(lambda x: f"{st.session_state.currency_symbol}{x:,.2f}")
        st.dataframe(df_sales)

def page_forecasting():
    if st.session_state.user_id is None:
        st.warning("Please log in first.")
        set_page("Login")
        st.rerun()

    st.title("AI Forecasting")
    if not st.session_state.active_business_id:
        st.warning("Select active business")
        return
    s = DBManager.fetch_one(
        "SELECT COUNT(*), MIN(date), MAX(date) FROM transactions WHERE user_id = :uid AND business_id = :bid AND type='Sales'",
        {"uid": st.session_state.user_id, "bid": st.session_state.active_business_id}
    )
    e = DBManager.fetch_one(
        "SELECT COUNT(*) FROM transactions WHERE user_id = :uid AND business_id = :bid AND type='Expense'",
        {"uid": st.session_state.user_id, "bid": st.session_state.active_business_id}
    )[0]
    distinct = DBManager.fetch_one(
        "SELECT COUNT(DISTINCT date) FROM transactions WHERE user_id = :uid AND business_id = :bid AND type='Sales'",
        {"uid": st.session_state.user_id, "bid": st.session_state.active_business_id}
    )[0]
    sales_cnt, min_dt, max_dt = s
    col1, col2 = st.columns(2)
    col1.metric("Sales Records", sales_cnt)
    if min_dt:
        col1.caption(f"From {min_dt} to {max_dt}  |  Distinct days: {distinct}")
    col2.metric("Expense Records", e)

    if sales_cnt == 0:
        st.warning("No sales data")
        return

    freq_labels = ["Daily", "Weekly", "Monthly"]
    freq_codes = ["D", "W", "M"]
    counts = []
    for code in freq_codes:
        ts = Analytics.prepare_time_series(st.session_state.user_id, st.session_state.active_business_id, 'sales', code)
        counts.append(len(ts) if not ts.empty else 0)
    st.subheader("Data availability")
    cols = st.columns(3)
    for i, (lab, cnt) in enumerate(zip(freq_labels, counts)):
        with cols[i]:
            if cnt >= 3:
                st.success(f"**{lab}**: {cnt} ✓")
            else:
                st.error(f"**{lab}**: {cnt} X (need ≥3)")

    target = st.radio("Forecast", ["Sales", "Profit"], horizontal=True)
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
            fc = Analytics.get_forecast(st.session_state.user_id, st.session_state.active_business_id,
                                        target.lower(), periods, freq)
        if fc is None:
            st.error("Forecast failed")
            return
        hist = Analytics.prepare_time_series(st.session_state.user_id, st.session_state.active_business_id,
                                             target.lower(), freq)
        hist = hist[hist['y'] > 0]
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=hist['ds'], y=hist['y'], mode='lines+markers',
                                  name='Historical', line=dict(color='#1f77b4', width=2)))
        fig.add_trace(go.Scatter(x=fc['ds'], y=fc['yhat'], mode='lines+markers',
                                  name='Forecast', line=dict(color='#ff7f0e', dash='dash', width=2)))
        fig.add_trace(go.Scatter(x=fc['ds'], y=fc['yhat_upper'], mode='lines',
                                  line=dict(width=0), showlegend=False))
        fig.add_trace(go.Scatter(x=fc['ds'], y=fc['yhat_lower'], mode='lines',
                                  fill='tonexty', fillcolor='rgba(255,127,14,0.2)',
                                  line=dict(width=0), name='Confidence Interval'))
        fmt = '%b %d' if freq == 'D' else ('%b %d, %Y' if freq == 'W' else '%b %Y')
        fig.update_layout(title=f"{target} Forecast ({freq_opt})",
                          xaxis_title="Date", yaxis_title=f"Amount ({st.session_state.currency_symbol})",
                          hovermode='x unified', xaxis=dict(tickformat=fmt))
        st.plotly_chart(fig, use_container_width=True)
        if not fc.empty:
            st.metric(f"Next {unit.capitalize()} Prediction", f"{st.session_state.currency_symbol}{fc.iloc[0]['yhat']:,.2f}")
        with st.expander("Forecast Table"):
            disp = fc[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].copy()
            disp['ds'] = disp['ds'].dt.strftime('%Y-%m-%d' if freq in ('D', 'W') else '%Y-%m')
            for c in ['yhat', 'yhat_lower', 'yhat_upper']:
                disp[c] = disp[c].apply(lambda x: f"{st.session_state.currency_symbol}{x:,.2f}")
            st.dataframe(disp)

def page_report_generation():
    if st.session_state.user_id is None:
        st.warning("Please log in first.")
        set_page("Login")
        st.rerun()

    st.title("Generate Report")
    if not st.session_state.active_business_id:
        st.warning("Select an active business first.")
        return

    with st.form("report_form"):
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("Start Date", datetime.now().date() - timedelta(days=30))
        with col2:
            end_date = st.date_input("End Date", datetime.now().date())

        report_type = st.radio("Report Format", ["Excel", "PDF"], horizontal=True)

        submitted = st.form_submit_button("Generate Report", type="primary")

    if submitted:
        if start_date > end_date:
            st.error("Start date must be before end date.")
            return

        data = Analytics.get_report_data(st.session_state.user_id, st.session_state.active_business_id,
                                         start_date, end_date)
        if data['transactions'].empty and data['inventory'].empty:
            st.warning("No data for the selected period.")
            return

        try:
            if report_type == "Excel":
                excel_bytes = generate_excel_report(data, start_date, end_date)
                st.download_button(
                    label="Download Excel Report",
                    data=excel_bytes,
                    file_name=f"report_{start_date}_to_{end_date}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            else:
                pdf_bytes = generate_pdf_report(data, start_date, end_date)
                st.download_button(
                    label="Download PDF Report",
                    data=pdf_bytes,
                    file_name=f"report_{start_date}_to_{end_date}.pdf",
                    mime="application/pdf"
                )
        except Exception as e:
            st.error(f"Report generation failed: {str(e)}")

def page_admin_dashboard():
    if st.session_state.user_id is None:
        st.warning("Please log in first.")
        set_page("Login")
        st.rerun()

    st.title("Admin Dashboard")

    if st.session_state.role != "Manager":
        st.error("Only managers can access the Admin Dashboard.")
        return

    if not st.session_state.get('admin_authenticated', False):
        with st.form("admin_password_form"):
            password = st.text_input("Enter Admin Password", type="password")
            if st.form_submit_button("Access Dashboard"):
                if password == Config.ADMIN_PASSWORD:
                    st.session_state.admin_authenticated = True
                    DBManager.execute(
                        "INSERT INTO admin_access_logs (user_id) VALUES (:uid)",
                        {"uid": st.session_state.user_id}
                    )
                    st.rerun()
                else:
                    st.error("Incorrect password.")
        return

    stats = Admin.get_system_stats()
    show_metric_row([
        ("Total Users", stats['users'], None),
        ("Total Businesses", stats['businesses'], None),
        ("Total Transactions", stats['transactions'], None),
        ("Total Products", stats['products'], None)
    ])

    st.divider()
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["User Management", "Login History", "Admin Access Logs", "Change Passwords", "System Settings"])

    with tab1:
        st.subheader("User Management")
        users_df = Admin.get_all_users_with_stats()
        if users_df.empty:
            st.info("No users found.")
        else:
            st.dataframe(users_df[['username','email','role','dob','gender','business_count','transaction_count']])
            for idx, row in users_df.iterrows():
                cols = st.columns([2,2,1,1,1,1])
                cols[0].write(f"**{row['username']}**")
                cols[1].write(row['email'])
                cols[2].write(row['role'])
                cols[3].write(f"Biz: {row['business_count']}")
                cols[4].write(f"Tx: {row['transaction_count']}")
                if row['id'] != st.session_state.user_id:
                    delete_key = f"del_user_{row['id']}"
                    confirm_key = f"confirm_{row['id']}"
                    if cols[5].button("Delete", key=delete_key):
                        st.session_state[confirm_key] = True
                    if st.session_state.get(confirm_key, False):
                        st.warning(f"Are you sure you want to delete user {row['username']}? This action is irreversible.")
                        col_yes, col_no = st.columns(2)
                        if col_yes.button("Yes, delete", key=f"yes_{row['id']}"):
                            Admin.delete_user(row['id'])
                            st.success(f"User {row['username']} deleted.")
                            st.session_state[confirm_key] = False
                            st.rerun()
                        if col_no.button("Cancel", key=f"no_{row['id']}"):
                            st.session_state[confirm_key] = False
                            st.rerun()
                else:
                    cols[5].write("(You)")

    with tab2:
        st.subheader("User Login History")
        role_filter = st.selectbox("Filter by role", ["All", "Owner", "Accountant", "Staff", "Manager"])
        rows = DBManager.fetch_all(
            """
            SELECT u.username, u.role, lh.login_time, lh.logout_time, lh.session_duration
            FROM login_history lh
            JOIN users u ON lh.user_id = u.id
            WHERE (:role = 'All' OR u.role = :role)
            ORDER BY lh.login_time DESC
            """,
            {"role": role_filter}
        )
        df_logins = pd.DataFrame(rows, columns=['username','role','login_time','logout_time','session_duration'])
        if df_logins.empty:
            st.info("No login records.")
        else:
            df_logins['login_time'] = pd.to_datetime(df_logins['login_time']).dt.strftime('%Y-%m-%d %H:%M:%S')
            df_logins['logout_time'] = pd.to_datetime(df_logins['logout_time']).dt.strftime('%Y-%m-%d %H:%M:%S') if df_logins['logout_time'].notna().any() else None
            df_logins['session_duration'] = df_logins['session_duration'].apply(lambda x: f"{x} sec" if pd.notna(x) else "Active")
            st.dataframe(df_logins)

    with tab3:
        st.subheader("Manager Admin Access Logs")
        rows = DBManager.fetch_all(
            """
            SELECT a.access_time, u.username, u.role
            FROM admin_access_logs a
            JOIN users u ON a.user_id = u.id
            ORDER BY a.access_time DESC
            """
        )
        df_admin = pd.DataFrame(rows, columns=['access_time','username','role'])
        if df_admin.empty:
            st.info("No admin access records.")
        else:
            df_admin['access_time'] = pd.to_datetime(df_admin['access_time']).dt.strftime('%Y-%m-%d %H:%M:%S')
            st.dataframe(df_admin)

    with tab4:
        st.subheader("Change User Password")
        users = DBManager.fetch_all("SELECT id, username FROM users")
        user_options = {u[0]: u[1] for u in users}
        selected_user_id = st.selectbox("Select User", options=list(user_options.keys()), format_func=lambda x: user_options[x])
        new_password = st.text_input("New Password", type="password")
        confirm_password = st.text_input("Confirm New Password", type="password")
        if st.button("Update Password"):
            if new_password != confirm_password:
                st.error("Passwords do not match.")
            elif not new_password:
                st.error("Password cannot be empty.")
            else:
                Admin.change_user_password(selected_user_id, new_password)
                st.success(f"Password updated for user {user_options[selected_user_id]}.")

    with tab5:
        st.subheader("System Settings")
        with st.form("system_settings_form"):
            currency = st.text_input("Currency Symbol", value=st.session_state.currency_symbol,
                                     help="Symbol used for monetary values (e.g., ₹, $, €)")
            default_reorder = st.number_input("Default Reorder Level", value=st.session_state.default_reorder_level,
                                              step=0.5, help="Default reorder threshold for new products")
            if st.form_submit_button("Save Settings", use_container_width=True):
                DBManager.execute(
                    "UPDATE user_preferences SET currency_symbol = :cur, default_reorder_level = :reorder WHERE user_id = :uid",
                    {"cur": currency, "reorder": default_reorder, "uid": st.session_state.user_id}
                )
                st.session_state.currency_symbol = currency
                st.session_state.default_reorder_level = default_reorder
                st.success("Settings saved.")
                st.rerun()

# -----------------------------------------------------------------------------
# Analytics Helpers
# -----------------------------------------------------------------------------
class Analytics:
    @staticmethod
    def calculate_profit_metrics(user_id, business_id, period='monthly'):
        rows = DBManager.fetch_all(
            "SELECT date, type, amount, category FROM transactions WHERE user_id = :uid AND business_id = :bid ORDER BY date",
            {"uid": user_id, "bid": business_id}
        )
        df = pd.DataFrame(rows, columns=['date', 'type', 'amount', 'category'])
        if df.empty:
            return None
        df['date'] = pd.to_datetime(df['date'])
        sales = df[df['type'] == 'Sales']
        expenses = df[df['type'] == 'Expense']
        total_revenue = sales['amount'].sum() if not sales.empty else 0
        total_expenses = expenses['amount'].sum() if not expenses.empty else 0

        cogs_rows = DBManager.fetch_all(
            """
            SELECT sm.quantity, sm.unit_cost FROM stock_movements sm
            JOIN products p ON sm.product_id = p.id
            WHERE p.user_id = :uid AND p.business_id = :bid AND sm.movement_type = 'sale'
            """,
            {"uid": user_id, "bid": business_id}
        )
        cogs_df = pd.DataFrame(cogs_rows, columns=['quantity', 'unit_cost'])
        total_cogs = (cogs_df['quantity'] * cogs_df['unit_cost']).sum() if not cogs_df.empty else 0

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

    @staticmethod
    def get_monthly_profit_trend(user_id, business_id, months=6):
        rows = DBManager.fetch_all(
            "SELECT date, type, amount FROM transactions WHERE user_id = :uid AND business_id = :bid",
            {"uid": user_id, "bid": business_id}
        )
        df = pd.DataFrame(rows, columns=['date', 'type', 'amount'])
        if df.empty:
            return pd.DataFrame()
        df['date'] = pd.to_datetime(df['date'])
        cutoff = datetime.now() - timedelta(days=30*months)
        df = df[df['date'] >= cutoff]
        if df.empty:
            return pd.DataFrame()
        df['month'] = df['date'].dt.to_period('M').astype(str)
        pivot = df.pivot_table(index='month', columns='type', values='amount', aggfunc='sum', fill_value=0)
        if 'Sales' not in pivot.columns:
            pivot['Sales'] = 0
        if 'Expense' not in pivot.columns:
            pivot['Expense'] = 0
        pivot['profit'] = pivot['Sales'] - pivot['Expense']
        pivot['margin'] = (pivot['profit'] / pivot['Sales'] * 100).round(1).replace([np.inf, -np.inf], 0).fillna(0)
        pivot = pivot.reset_index()
        pivot['month_dt'] = pd.to_datetime(pivot['month'] + '-01')
        return pivot[['month_dt', 'Sales', 'Expense', 'profit', 'margin']].rename(
            columns={'Sales': 'revenue', 'Expense': 'expenses'})

    @staticmethod
    def add_product(user_id, business_id, name, sku, qty, cost, price, reorder, category):
        try:
            # No RETURNING
            pid = DBManager.insert_and_get_id(
                """
                INSERT INTO products (user_id, business_id, product_name, sku, quantity,
                    cost_price, selling_price, reorder_level, category)
                VALUES (:uid, :bid, :name, :sku, :qty, :cost, :price, :reorder, :cat)
                """,
                {"uid": user_id, "bid": business_id, "name": name, "sku": sku,
                 "qty": qty, "cost": cost, "price": price, "reorder": reorder, "cat": category}
            )
            if qty > 0:
                DBManager.execute(
                    """
                    INSERT INTO stock_movements (product_id, movement_type, quantity, unit_cost, notes)
                    VALUES (:pid, 'purchase', :qty, :cost, 'Initial stock')
                    """,
                    {"pid": pid, "qty": qty, "cost": cost}
                )
            return True, "Product added."
        except Exception as e:
            if 'unique constraint' in str(e).lower():
                return False, "SKU already exists."
            return False, str(e)

    @staticmethod
    def record_stock_movement(pid, move_type, qty, unit_cost=None, unit_price=None, ref=None, notes=""):
        try:
            prod = DBManager.fetch_one(
                "SELECT quantity, cost_price FROM products WHERE id = :pid",
                {"pid": pid}
            )
            if not prod:
                return False, "Product not found."
            # Use fallback access
            try:
                curr_qty = prod[0]
                curr_cost = prod[1]
            except (IndexError, TypeError):
                prod_dict = dict(prod._mapping)
                curr_qty = prod_dict['quantity']
                curr_cost = prod_dict['cost_price']

            if move_type == 'purchase':
                new_qty = curr_qty + qty
                if unit_cost and unit_cost > 0:
                    new_cost = (curr_qty * curr_cost + qty * unit_cost) / new_qty
                    DBManager.execute(
                        "UPDATE products SET quantity = :qty, cost_price = :cost, updated_at = CURRENT_TIMESTAMP WHERE id = :pid",
                        {"qty": new_qty, "cost": new_cost, "pid": pid}
                    )
                else:
                    DBManager.execute(
                        "UPDATE products SET quantity = :qty, updated_at = CURRENT_TIMESTAMP WHERE id = :pid",
                        {"qty": new_qty, "pid": pid}
                    )
            elif move_type == 'sale':
                if qty > curr_qty:
                    return False, f"Insufficient stock. Available: {curr_qty}"
                new_qty = curr_qty - qty
                DBManager.execute(
                    "UPDATE products SET quantity = :qty, updated_at = CURRENT_TIMESTAMP WHERE id = :pid",
                    {"qty": new_qty, "pid": pid}
                )
            elif move_type == 'adjustment':
                DBManager.execute(
                    "UPDATE products SET quantity = :qty, updated_at = CURRENT_TIMESTAMP WHERE id = :pid",
                    {"qty": qty, "pid": pid}
                )
            else:
                return False, "Invalid movement type."

            DBManager.execute(
                """
                INSERT INTO stock_movements (product_id, movement_type, quantity, unit_cost, unit_price, reference_id, notes)
                VALUES (:pid, :mtype, :qty, :ucost, :uprice, :ref, :notes)
                """,
                {"pid": pid, "mtype": move_type, "qty": qty,
                 "ucost": unit_cost, "uprice": unit_price, "ref": ref, "notes": notes}
            )
            return True, "Movement recorded."
        except Exception as e:
            return False, str(e)

    @staticmethod
    def get_low_stock_items(user_id, business_id):
        rows = DBManager.fetch_all(
            """
            SELECT product_name, sku, quantity, reorder_level, (reorder_level - quantity) as needed
            FROM products WHERE user_id = :uid AND business_id = :bid AND quantity <= reorder_level
            ORDER BY needed DESC
            """,
            {"uid": user_id, "bid": business_id}
        )
        return pd.DataFrame(rows, columns=['product_name', 'sku', 'quantity', 'reorder_level', 'needed'])

    @staticmethod
    def get_inventory_value(user_id, business_id):
        row = DBManager.fetch_one(
            """
            SELECT COUNT(*) as product_count, COALESCE(SUM(quantity), 0) as total_units,
                   COALESCE(SUM(quantity * cost_price), 0) as total_value
            FROM products WHERE user_id = :uid AND business_id = :bid
            """,
            {"uid": user_id, "bid": business_id}
        )
        if not row:
            return {'product_count': 0, 'total_units': 0, 'total_value': 0}
        # Fallback access
        try:
            product_count = row[0]
            total_units = row[1]
            total_value = row[2]
        except (IndexError, TypeError):
            r = dict(row._mapping)
            product_count = r['product_count']
            total_units = r['total_units']
            total_value = r['total_value']
        return {'product_count': product_count, 'total_units': total_units, 'total_value': total_value}

    @staticmethod
    def prepare_time_series(user_id, business_id, value_type='sales', freq='M'):
        rows = DBManager.fetch_all(
            "SELECT date, type, amount FROM transactions WHERE user_id = :uid AND business_id = :bid ORDER BY date",
            {"uid": user_id, "bid": business_id}
        )
        df = pd.DataFrame(rows, columns=['date', 'type', 'amount'])
        if df.empty:
            return pd.DataFrame()
        df['date'] = pd.to_datetime(df['date'])
        if value_type == 'sales':
            ts = df[df['type'] == 'Sales'].groupby('date')['amount'].sum().reset_index()
        elif value_type == 'profit':
            sales = df[df['type'] == 'Sales'].groupby('date')['amount'].sum()
            exp = df[df['type'] == 'Expense'].groupby('date')['amount'].sum()
            profit = (sales - exp).fillna(0).reset_index()
            profit.columns = ['date', 'amount']
            ts = profit
        else:
            return pd.DataFrame()
        if ts.empty:
            return ts
        ts = ts.set_index('date').resample(freq).sum().reset_index()
        ts.columns = ['ds', 'y']
        return ts.dropna()

    @staticmethod
    def forecast_with_prophet(df, periods, freq):
        if not PROPHET_AVAILABLE:
            return None
        try:
            model = Prophet(yearly_seasonality=True, weekly_seasonality=(freq=='W'), daily_seasonality=False,
                            seasonality_mode='multiplicative')
            model.fit(df)
            future = model.make_future_dataframe(periods=periods, freq=freq)
            return model.predict(future)[['ds','yhat','yhat_lower','yhat_upper']]
        except Exception:
            return None

    @staticmethod
    def forecast_with_linear(df, periods, freq):
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
        except Exception:
            return None

    @staticmethod
    def get_forecast(user_id, business_id, target, periods, freq, method='auto'):
        ts = Analytics.prepare_time_series(user_id, business_id, target, freq)
        if ts.empty or len(ts) < 3:
            return None
        if method == 'auto':
            method = 'prophet' if PROPHET_AVAILABLE else 'linear'
        if method == 'prophet' and PROPHET_AVAILABLE:
            return Analytics.forecast_with_prophet(ts, periods, freq)
        return Analytics.forecast_with_linear(ts, periods, freq)

    @staticmethod
    def get_expense_by_category(user_id, business_id, period):
        rows = DBManager.fetch_all(
            "SELECT category, amount, date FROM transactions WHERE user_id = :uid AND business_id = :bid AND type = 'Expense'",
            {"uid": user_id, "bid": business_id}
        )
        df = pd.DataFrame(rows, columns=['category', 'amount', 'date'])
        if df.empty:
            return pd.DataFrame()
        df['date'] = pd.to_datetime(df['date'])
        if period == 'week':
            cutoff = datetime.now() - timedelta(days=7)
        elif period == 'month':
            cutoff = datetime.now() - timedelta(days=30)
        elif period == 'year':
            cutoff = datetime.now() - timedelta(days=365)
        else:
            cutoff = datetime(1900,1,1)
        df = df[df['date'] >= cutoff]
        return df.groupby('category')['amount'].sum().reset_index().sort_values('amount', ascending=False)

    @staticmethod
    def get_sales_by_category(user_id, business_id, period):
        rows = DBManager.fetch_all(
            "SELECT category, amount, date FROM transactions WHERE user_id = :uid AND business_id = :bid AND type = 'Sales'",
            {"uid": user_id, "bid": business_id}
        )
        df = pd.DataFrame(rows, columns=['category', 'amount', 'date'])
        if df.empty:
            return pd.DataFrame()
        df['date'] = pd.to_datetime(df['date'])
        if period == 'week':
            cutoff = datetime.now() - timedelta(days=7)
        elif period == 'month':
            cutoff = datetime.now() - timedelta(days=30)
        elif period == 'year':
            cutoff = datetime.now() - timedelta(days=365)
        else:
            cutoff = datetime(1900,1,1)
        df = df[df['date'] >= cutoff]
        return df.groupby('category')['amount'].sum().reset_index().sort_values('amount', ascending=False)

    @staticmethod
    def get_report_data(user_id, business_id, start_date, end_date):
        start = start_date.strftime('%Y-%m-%d')
        end = end_date.strftime('%Y-%m-%d')
        tx_rows = DBManager.fetch_all(
            """
            SELECT date, type, amount, category, description
            FROM transactions
            WHERE user_id = :uid AND business_id = :bid
              AND date BETWEEN :start AND :end
            ORDER BY date
            """,
            {"uid": user_id, "bid": business_id, "start": start, "end": end}
        )
        tx_df = pd.DataFrame(tx_rows, columns=['date', 'type', 'amount', 'category', 'description'])
        sum_rows = DBManager.fetch_all(
            """
            SELECT type, COUNT(*) as count, SUM(amount) as total
            FROM transactions
            WHERE user_id = :uid AND business_id = :bid
              AND date BETWEEN :start AND :end
            GROUP BY type
            """,
            {"uid": user_id, "bid": business_id, "start": start, "end": end}
        )
        sum_df = pd.DataFrame(sum_rows, columns=['type', 'count', 'total'])
        inv_rows = DBManager.fetch_all(
            """
            SELECT product_name, sku, quantity, cost_price, selling_price
            FROM products
            WHERE user_id = :uid AND business_id = :bid
            """,
            {"uid": user_id, "bid": business_id}
        )
        inv_df = pd.DataFrame(inv_rows, columns=['product_name', 'sku', 'quantity', 'cost_price', 'selling_price'])
        return {'transactions': tx_df, 'summary': sum_df, 'inventory': inv_df}

# -----------------------------------------------------------------------------
# Admin Helpers
# -----------------------------------------------------------------------------
class Admin:
    @staticmethod
    def get_system_stats():
        users = DBManager.fetch_one("SELECT COUNT(*) FROM users")[0]
        businesses = DBManager.fetch_one("SELECT COUNT(*) FROM businesses")[0]
        transactions = DBManager.fetch_one("SELECT COUNT(*) FROM transactions")[0]
        products = DBManager.fetch_one("SELECT COUNT(*) FROM products")[0]
        return {'users': users, 'businesses': businesses, 'transactions': transactions, 'products': products}

    @staticmethod
    def get_all_users_with_stats():
        users = DBManager.fetch_all("SELECT id, username, email, role, dob, gender FROM users")
        users_df = pd.DataFrame(users, columns=['id','username','email','role','dob','gender'])
        biz_counts = DBManager.fetch_all("SELECT user_id, COUNT(*) as cnt FROM businesses GROUP BY user_id")
        biz_df = pd.DataFrame(biz_counts, columns=['user_id','business_count'])
        tx_counts = DBManager.fetch_all("SELECT user_id, COUNT(*) as cnt FROM transactions GROUP BY user_id")
        tx_df = pd.DataFrame(tx_counts, columns=['user_id','transaction_count'])
        users_df = users_df.merge(biz_df, left_on='id', right_on='user_id', how='left').drop('user_id', axis=1)
        users_df = users_df.merge(tx_df, left_on='id', right_on='user_id', how='left').drop('user_id', axis=1)
        users_df['business_count'] = users_df['business_count'].fillna(0).astype(int)
        users_df['transaction_count'] = users_df['transaction_count'].fillna(0).astype(int)
        return users_df

    @staticmethod
    def delete_user(user_id):
        DBManager.execute("DELETE FROM users WHERE id = :uid", {"uid": user_id})
        DBManager.execute("DELETE FROM businesses WHERE user_id = :uid", {"uid": user_id})
        DBManager.execute("DELETE FROM transactions WHERE user_id = :uid", {"uid": user_id})
        DBManager.execute("DELETE FROM products WHERE user_id = :uid", {"uid": user_id})
        DBManager.execute("DELETE FROM user_preferences WHERE user_id = :uid", {"uid": user_id})
        DBManager.execute("DELETE FROM login_history WHERE user_id = :uid", {"uid": user_id})
        DBManager.execute("DELETE FROM admin_access_logs WHERE user_id = :uid", {"uid": user_id})

    @staticmethod
    def change_user_password(user_id, new_password):
        hashed = AuthManager.hash_password(new_password)
        DBManager.execute(
            "UPDATE users SET password = :pw WHERE id = :uid",
            {"pw": hashed, "uid": user_id}
        )

    @staticmethod
    def get_daily_transaction_volume(days=30):
        # SQLite version: use date('now', '-30 days')
        rows = DBManager.fetch_all(
            f"""
            SELECT date(date) as day, COUNT(*) as count
            FROM transactions
            WHERE date >= date('now', '-{days} days')
            GROUP BY day
            ORDER BY day
            """
        )
        return pd.DataFrame(rows, columns=['day', 'count'])

    @staticmethod
    def get_category_completeness():
        total = DBManager.fetch_one("SELECT COUNT(*) FROM transactions")[0]
        missing = DBManager.fetch_one("SELECT COUNT(*) FROM transactions WHERE category IS NULL OR category = ''")[0]
        return total, missing

    @staticmethod
    def get_top_users_by_transactions(limit=5):
        rows = DBManager.fetch_all(
            """
            SELECT u.username, COUNT(t.id) as tx_count
            FROM users u
            LEFT JOIN transactions t ON u.id = t.user_id
            GROUP BY u.id, u.username
            ORDER BY tx_count DESC
            LIMIT :lim
            """,
            {"lim": limit}
        )
        return pd.DataFrame(rows, columns=['username', 'tx_count'])

# -----------------------------------------------------------------------------
# Report Generation Helpers
# -----------------------------------------------------------------------------
def generate_excel_report(data_dict, start_date, end_date):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        summary_df = data_dict['summary']
        if not summary_df.empty:
            summary_df.to_excel(writer, sheet_name='Summary', index=False)
        else:
            pd.DataFrame({'Message': ['No data for this period']}).to_excel(writer, sheet_name='Summary', index=False)
        data_dict['transactions'].to_excel(writer, sheet_name='Transactions', index=False)
        inv_df = data_dict['inventory']
        if not inv_df.empty:
            inv_df.to_excel(writer, sheet_name='Inventory', index=False)
        info = pd.DataFrame({
            'Report Period': [f"{start_date} to {end_date}"],
            'Generated On': [datetime.now().strftime('%Y-%m-%d %H:%M:%S')]
        })
        info.to_excel(writer, sheet_name='Report Info', index=False)
    output.seek(0)
    return output

class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, 'Business Analyzer Report', 0, 1, 'C')
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

def generate_pdf_report(data_dict, start_date, end_date):
    pdf = PDF()
    pdf.add_page()
    pdf.set_font('Arial', 'B', 10)

    pdf.cell(0, 10, f"Period: {start_date} to {end_date}", 0, 1)
    pdf.cell(0, 10, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", 0, 1)
    pdf.ln(5)

    pdf.set_font('Arial', 'B', 10)
    pdf.cell(0, 10, 'Summary', 0, 1)
    pdf.set_font('Arial', '', 9)
    summary = data_dict['summary']
    if not summary.empty:
        for _, row in summary.iterrows():
            pdf.cell(40, 8, row['type'], 1)
            pdf.cell(30, 8, str(row['count']), 1)
            pdf.cell(40, 8, f"${row['total']:,.2f}", 1)
            pdf.ln(8)
    else:
        pdf.cell(0, 8, "No summary data", 0, 1)
    pdf.ln(5)

    pdf.set_font('Arial', 'B', 10)
    pdf.cell(0, 10, 'Transactions (first 20 shown)', 0, 1)
    pdf.set_font('Arial', '', 8)
    tx = data_dict['transactions'].head(20)
    if not tx.empty:
        pdf.cell(25, 8, 'Date', 1)
        pdf.cell(20, 8, 'Type', 1)
        pdf.cell(25, 8, 'Amount', 1)
        pdf.cell(30, 8, 'Category', 1)
        pdf.cell(0, 8, 'Description', 1)
        pdf.ln(8)
        for _, row in tx.iterrows():
            pdf.cell(25, 8, str(row['date'])[:10], 1)
            pdf.cell(20, 8, row['type'][:10], 1)
            pdf.cell(25, 8, f"${row['amount']:,.2f}", 1)
            pdf.cell(30, 8, (row['category'] or '')[:15], 1)
            pdf.cell(0, 8, (row['description'] or '')[:30], 1)
            pdf.ln(8)
    else:
        pdf.cell(0, 8, "No transactions", 0, 1)
    pdf.ln(5)

    pdf.set_font('Arial', 'B', 10)
    pdf.cell(0, 10, 'Inventory', 0, 1)
    pdf.set_font('Arial', '', 8)
    inv = data_dict['inventory']
    if not inv.empty:
        pdf.cell(40, 8, 'Product', 1)
        pdf.cell(25, 8, 'SKU', 1)
        pdf.cell(20, 8, 'Qty', 1)
        pdf.cell(25, 8, 'Cost', 1)
        pdf.cell(25, 8, 'Price', 1)
        pdf.ln(8)
        for _, row in inv.iterrows():
            pdf.cell(40, 8, row['product_name'][:20], 1)
            pdf.cell(25, 8, row['sku'][:10], 1)
            pdf.cell(20, 8, str(row['quantity']), 1)
            pdf.cell(25, 8, f"${row['cost_price']:,.2f}", 1)
            pdf.cell(25, 8, f"${row['selling_price']:,.2f}", 1)
            pdf.ln(8)
    else:
        pdf.cell(0, 8, "No inventory data", 0, 1)

    out = pdf.output(dest='S')
    return out.encode('latin-1', errors='replace') if isinstance(out, str) else bytes(out)

def send_email_simple(to_email, subject, body, attachment_bytes, attachment_filename, from_email):
    msg = MIMEMultipart()
    msg['From'] = from_email
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    part = MIMEBase('application', 'octet-stream')
    part.set_payload(attachment_bytes)
    encoders.encode_base64(part)
    part.add_header('Content-Disposition', f'attachment; filename={attachment_filename}')
    msg.attach(part)

    try:
        server = smtplib.SMTP('localhost', 25)
        server.send_message(msg)
        server.quit()
        return True, "Email sent via local SMTP."
    except Exception as e:
        return False, str(e)

# -----------------------------------------------------------------------------
# UI Helpers
# -----------------------------------------------------------------------------
def get_color_sequence(n, palette='Plotly'):
    palettes = {
        'Set2': qualitative.Set2,
        'Pastel': qualitative.Pastel,
        'Plotly': qualitative.Plotly,
        'Dark2': qualitative.Dark2,
        'Bold': ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']
    }
    colors = palettes.get(palette, qualitative.Plotly)
    return [colors[i % len(colors)] for i in range(n)]

def show_metric_row(metrics):
    cols = st.columns(len(metrics))
    for col, (label, value, delta) in zip(cols, metrics):
        col.metric(label, value, delta)

# -----------------------------------------------------------------------------
# Sidebar Navigation
# -----------------------------------------------------------------------------
def render_sidebar():
    with st.sidebar:
        st.title("Business Analyzer")
        user = authenticate()
        if not user and st.session_state.get('logged_in'):
            logout()
            st.rerun()
        if st.session_state.get('logged_in'):
            st.write(f"**Welcome,** {st.session_state.username}  \nRole: {st.session_state.role}")
            st.divider()

            nav = {
                "Core": ["Dashboard", "Sales Dashboard", "View Transactions", "Add Transaction"],
                "Business Intelligence": ["Profit Dashboard", "Inventory", "COGS Analysis", "Businesses"],
                "Advanced": ["Sales Trends", "Forecasting", "Profit Margins", "Expense Categories"],
                "Reports & Admin": ["Generate Report"] + (["Admin Dashboard"] if st.session_state.role == 'Manager' else []),
                "Data": ["Import Transactions", "Analyze Data"],
                "Account": ["Profile", "Logout"]
            }

            for group, pages in nav.items():
                st.subheader(group)
                cols = st.columns(2)
                for i, page in enumerate(pages):
                    with cols[i % 2]:
                        if page == "Logout":
                            if st.button(page, use_container_width=True, key=f"nav_{page}"):
                                logout()
                                st.rerun()
                        else:
                            if st.button(page, use_container_width=True, key=f"nav_{page}"):
                                set_page(page)
                st.divider()
        else:
            for page in ["Home", "Login", "Sign Up"]:
                if st.button(page, use_container_width=True):
                    set_page(page)

# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------
def main():
    st.set_page_config(
        layout="wide",
        page_title="Business Analyzer",
        page_icon="📊",
        initial_sidebar_state="expanded"
    )
    DBManager.init_db()
    init_session()
    render_sidebar()

    # Safety redirect: if logged in but page is Login, go to Dashboard
    if st.session_state.get('logged_in', False) and st.session_state.page == 'Login':
        set_page('Dashboard')
        st.rerun()

    pages = {
        "Home": page_home,
        "Login": page_login,
        "Sign Up": page_signup,
        "Dashboard": page_dashboard,
        "Sales Dashboard": page_sales_dashboard,
        "Add Transaction": page_add_transaction,
        "View Transactions": page_view_transactions,
        "Import Transactions": page_import_transactions,
        "Analyze Data": page_analyze_data,
        "Businesses": page_businesses,
        "Profile": page_profile,
        "Profit Dashboard": page_profit_dashboard,
        "Inventory": page_inventory,
        "COGS Analysis": page_cogs,
        "Sales Trends": page_sales_trends,
        "Profit Margins": page_profit_margins,
        "Expense Categories": page_expense_categories,
        "Forecasting": page_forecasting,
        "Generate Report": page_report_generation,
        "Admin Dashboard": page_admin_dashboard
    }

    page_name = st.session_state.page
    if page_name in pages and (st.session_state.logged_in or page_name in ["Home", "Login", "Sign Up"]):
        pages[page_name]()
    else:
        set_page("Home" if not st.session_state.logged_in else "Dashboard")
        st.rerun()

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        st.error(f"Application error: {e}")
        traceback.print_exc(file=sys.stderr)
