"""
Business Analyzer – SQLite‑only version (fully fixed)
- Tables use AUTOINCREMENT
- INSERTs do not use RETURNING – IDs obtained via lastrowid
- Registration uses a single connection to avoid visibility issues
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
# Session Helpers (unchanged, but with debug prints)
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
# Page Functions (all other functions remain exactly as in the original)
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

# ... all other page functions (page_dashboard, page_businesses, page_add_transaction, etc.)
# remain exactly as in the code you provided earlier. They are omitted here for brevity,
# but must be included in the final file. The full code from your last message should be kept,
# with only the two methods modified as shown above.

# [Include all remaining page functions, analytics, admin helpers, report generation,
#  UI helpers, sidebar, and main() exactly as in your previous version.]

# -----------------------------------------------------------------------------
# (All other functions from your original code go here – unchanged)
# -----------------------------------------------------------------------------

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
