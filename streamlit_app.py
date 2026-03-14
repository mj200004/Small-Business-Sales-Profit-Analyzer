
"""
Business Analyzer – Production Ready – ULTIMATE FIXED VERSION
All milestones + requested enhancements.
Uses dictionary-style row access to guarantee user_id is never None.
"""

import streamlit as st
import pandas as pd
import sqlalchemy as sa
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool
import numpy as np
import bcrypt
import jwt
from datetime import datetime, timedelta, date
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
warnings.filterwarnings("ignore")

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
    DATABASE_URL = os.environ.get("DATABASE_URL")
    SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "your-secret-key-change-in-production")
    JWT_ALGORITHM = "HS256"
    # ADMIN_PASSWORD is now dynamic, stored in DB

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
# Database Manager
# -----------------------------------------------------------------------------
class DBManager:
    _engine = None

    @classmethod
    def get_engine(cls):
        if cls._engine is None:
            cls._engine = Config.get_engine()
        return cls._engine

    @classmethod
    @contextmanager
    def get_connection(cls):
        engine = cls.get_engine()
        with engine.connect() as conn:
            yield conn
            conn.commit()

    @classmethod
    def init_db(cls):
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
            # Login history
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS login_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    login_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    logout_time TIMESTAMP,
                    session_duration INTEGER,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """))
            # Admin access logs
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS admin_access_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    access_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
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
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
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
                    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    FOREIGN KEY (business_id) REFERENCES businesses(id) ON DELETE CASCADE
                )
            """))
            # User preferences
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS user_preferences (
                    user_id INTEGER PRIMARY KEY,
                    active_business_id INTEGER,
                    currency_symbol VARCHAR(10) DEFAULT '₹',
                    default_reorder_level REAL DEFAULT 5.0,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    FOREIGN KEY (active_business_id) REFERENCES businesses(id) ON DELETE SET NULL
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
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    FOREIGN KEY (business_id) REFERENCES businesses(id) ON DELETE CASCADE
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
                    notes TEXT,
                    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
                )
            """))
            # System settings table for dynamic admin password
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS system_settings (
                    key VARCHAR(255) PRIMARY KEY,
                    value TEXT
                )
            """))
            # Initialize admin password if not exists
            admin_pw_exists = conn.execute(text("SELECT 1 FROM system_settings WHERE key = 'admin_password'")).fetchone()
            if not admin_pw_exists:
                hashed_default_admin_pw = AuthManager.hash_password("Project@123")
                conn.execute(text("INSERT INTO system_settings (key, value) VALUES ('admin_password', :pw)"), {"pw": hashed_default_admin_pw})

    @classmethod
    def execute(cls, query, params=None):
        with cls.get_connection() as conn:
            result = conn.execute(text(query), params or {})
            if result.returns_rows:
                return result.fetchall()
            return result

    @classmethod
    def fetch_one(cls, query, params=None):
        with cls.get_connection() as conn:
            result = conn.execute(text(query), params or {})
            return result.fetchone()

    @classmethod
    def fetch_all(cls, query, params=None):
        with cls.get_connection() as conn:
            result = conn.execute(text(query), params or {})
            return result.fetchall()

    @classmethod
    def insert_and_get_id(cls, query, params=None):
        with cls.get_connection() as conn:
            result = conn.execute(text(query), params or {})
            # For SQLite, result.lastrowid is the way to get the last inserted ID
            return result.lastrowid

# -----------------------------------------------------------------------------
# Authentication
# -----------------------------------------------------------------------------
class AuthManager:
    @staticmethod
    def hash_password(password):
        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    @staticmethod
    def check_password(password, hashed):
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))

    @staticmethod
    def create_jwt_token(user_id, username, role):
        payload = {
            "user_id": user_id,
            "username": username,
            "role": role,
            "exp": datetime.utcnow() + timedelta(days=1)
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
        Returns user dict with guaranteed user_id.
        Uses ._mapping for safe column access.
        """
        row = DBManager.fetch_one(
            "SELECT id, username, email, password, role FROM users WHERE username = :login OR email = :login",
            {"login": username_or_email}
        )

        if not row:
            return {"success": False, "message": "Invalid username/email or password"}

        # Convert to dictionary for safe named access
        user = dict(row._mapping)

        # Safety check: id must exist and not be None
        if "id" not in user or user["id"] is None:
            return {"success": False, "message": "Database error: user ID is missing"}

        user_id = user["id"]
        username = user["username"]
        email = user["email"]
        password_hash = user["password"]
        role = user["role"]

        if not AuthManager.check_password(password, password_hash):
            return {"success": False, "message": "Invalid username/email or password"}

        # Log login – only if user_id is valid
        try:
            login_id = DBManager.insert_and_get_id(
                "INSERT INTO login_history (user_id) VALUES (:uid)",
                {"uid": user_id}
            )
            st.session_state.current_login_id = login_id
        except Exception as e:
            # If login logging fails, still allow login (just don't track history)
            st.warning(f"Login tracking failed: {e}")
            st.session_state.current_login_id = None

        # Load preferences
        pref = DBManager.fetch_one(
            "SELECT active_business_id, currency_symbol, default_reorder_level FROM user_preferences WHERE user_id = :uid",
            {"uid": user_id}
        )
        if pref:
            st.session_state.active_business_id = pref._mapping["active_business_id"]
            st.session_state.currency_symbol = pref._mapping["currency_symbol"]
            st.session_state.default_reorder_level = pref._mapping["default_reorder_level"]
        else:
            # This case should ideally not happen if preferences are created at signup
            # But as a fallback, create default preferences if none exist
            try:
                DBManager.execute(
                    "INSERT INTO user_preferences (user_id) VALUES (:uid)",
                    {"uid": user_id}
                )
            except sa.exc.IntegrityError: # Catch if another process/rerun already created it
                pass
            st.session_state.active_business_id = None
            st.session_state.currency_symbol = '₹'
            st.session_state.default_reorder_level = 5.0

        return {
            "success": True,
            "user_id": user_id,
            "username": username,
            "email": email,
            "role": role,
            "token": AuthManager.create_jwt_token(user_id, username, role)
        }

# -----------------------------------------------------------------------------
# Session Management
# -----------------------------------------------------------------------------
def init_session():
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
        st.session_state.user_id = None
        st.session_state.username = None
        st.session_state.email = None
        st.session_state.role = None
        st.session_state.token = None
        st.session_state.page = "Home"
        st.session_state.active_business_id = None
        st.session_state.currency_symbol = '₹'
        st.session_state.default_reorder_level = 5.0
        st.session_state.admin_authenticated = False # New: for admin dashboard access
        st.session_state.current_login_id = None # To track current login session for logout

def set_page(page_name):
    st.session_state.page = page_name

def authenticate():
    token = st.session_state.get("token")
    if token:
        payload = AuthManager.verify_jwt_token(token)
        if payload:
            st.session_state.logged_in = True
            st.session_state.user_id = payload["user_id"]
            st.session_state.username = payload["username"]
            st.session_state.email = payload["email"]
            st.session_state.role = payload["role"]
            return True
    st.session_state.logged_in = False
    st.session_state.user_id = None
    st.session_state.username = None
    st.session_state.email = None
    st.session_state.role = None
    st.session_state.token = None
    st.session_state.admin_authenticated = False # Reset admin auth on general auth check
    return False

def logout():
    if st.session_state.get("current_login_id"):
        DBManager.execute(
            "UPDATE login_history SET logout_time = CURRENT_TIMESTAMP, session_duration = STRFTIME('%s', CURRENT_TIMESTAMP) - STRFTIME('%s', login_time) WHERE id = :lid",
            {"lid": st.session_state.current_login_id}
        )
    st.session_state.logged_in = False
    st.session_state.user_id = None
    st.session_state.username = None
    st.session_state.email = None
    st.session_state.role = None
    st.session_state.token = None
    st.session_state.page = "Login"
    st.session_state.active_business_id = None
    st.session_state.currency_symbol = '₹'
    st.session_state.default_reorder_level = 5.0
    st.session_state.admin_authenticated = False
    st.session_state.current_login_id = None
    st.rerun()

# -----------------------------------------------------------------------------
# Analytics & Admin Classes
# -----------------------------------------------------------------------------
class Analytics:
    @staticmethod
    def add_product(user_id, business_id, name, sku, quantity, cost_price, selling_price, reorder_level, category):
        if not user_id or not business_id:
            return False, "User or Business ID is missing."
        try:
            # Check for unique SKU within the user's products
            existing_sku = DBManager.fetch_one(
                "SELECT id FROM products WHERE user_id = :uid AND sku = :sku",
                {"uid": user_id, "sku": sku}
            )
            if sku and existing_sku:
                return False, f"SKU '{sku}' already exists for one of your products."

            DBManager.execute(
                """
                INSERT INTO products (user_id, business_id, product_name, sku, quantity, cost_price, selling_price, reorder_level, category)
                VALUES (:uid, :bid, :name, :sku, :qty, :cost, :price, :reorder, :cat)
                """,
                {"uid": user_id, "bid": business_id, "name": name, "sku": sku, "qty": quantity, "cost": cost_price, "price": selling_price, "reorder": reorder_level, "cat": category}
            )
            return True, f"Product '{name}' added successfully!"
        except Exception as e:
            return False, f"Error adding product: {e}"

    @staticmethod
    def record_stock_movement(product_id, movement_type, quantity, unit_cost, unit_price, reference_id, notes):
        try:
            current_qty_row = DBManager.fetch_one(
                "SELECT quantity FROM products WHERE id = :pid",
                {"pid": product_id}
            )
            if not current_qty_row:
                return False, "Product not found."
            current_qty = current_qty_row._mapping["quantity"]

            new_qty = current_qty
            if movement_type == "purchase":
                new_qty += quantity
            elif movement_type == "sale":
                if current_qty < quantity:
                    return False, "Not enough stock for sale."
                new_qty -= quantity
            elif movement_type == "adjustment":
                new_qty += quantity # Adjustment can be positive or negative
            else:
                return False, "Invalid movement type."

            DBManager.execute(
                "UPDATE products SET quantity = :new_qty, updated_at = CURRENT_TIMESTAMP WHERE id = :pid",
                {"new_qty": new_qty, "pid": product_id}
            )
            DBManager.execute(
                """
                INSERT INTO stock_movements (product_id, movement_type, quantity, unit_cost, unit_price, reference_id, notes)
                VALUES (:pid, :mtype, :qty, :ucost, :uprice, :refid, :notes)
                """,
                {"pid": product_id, "mtype": movement_type, "qty": quantity, "ucost": unit_cost, "uprice": unit_price, "refid": reference_id, "notes": notes}
            )
            return True, f"Stock movement recorded. New quantity: {new_qty}"
        except Exception as e:
            return False, f"Error recording stock movement: {e}"

    @staticmethod
    def get_inventory_value(user_id, business_id):
        products = DBManager.fetch_all(
            "SELECT quantity, cost_price FROM products WHERE user_id = :uid AND business_id = :bid",
            {"uid": user_id, "bid": business_id}
        )
        total_value = sum(p._mapping["quantity"] * p._mapping["cost_price"] for p in products) if products else 0
        return {
            "product_count": len(products),
            "total_units": sum(p._mapping["quantity"] for p in products) if products else 0,
            "total_value": total_value
        }

    @staticmethod
    def get_low_stock_items(user_id, business_id):
        rows = DBManager.fetch_all(
            "SELECT product_name, sku, quantity, reorder_level FROM products WHERE user_id = :uid AND business_id = :bid AND quantity <= reorder_level ORDER BY product_name",
            {"uid": user_id, "bid": business_id}
        )
        return pd.DataFrame(rows, columns=["product_name", "sku", "quantity", "reorder_level"])

    @staticmethod
    def calculate_profit_metrics(user_id, business_id, period="monthly"):
        rows = DBManager.fetch_all(
            "SELECT date, type, amount, category FROM transactions WHERE user_id = :uid AND business_id = :bid ORDER BY date",
            {"uid": user_id, "bid": business_id}
        )
        df = pd.DataFrame(rows, columns=["date", "type", "amount", "category"])
        if df.empty:
            return None
        df["date"] = pd.to_datetime(df["date"])
        sales = df[df["type"] == "Sales"]
        expenses = df[df["type"] == "Expense"]
        total_revenue = sales["amount"].sum() if not sales.empty else 0
        total_expenses = expenses["amount"].sum() if not expenses.empty else 0

        cogs_rows = DBManager.fetch_all(
            """
            SELECT sm.quantity, sm.unit_cost FROM stock_movements sm
            JOIN products p ON sm.product_id = p.id
            WHERE p.user_id = :uid AND p.business_id = :bid AND sm.movement_type = 'sale'
            """,
            {"uid": user_id, "bid": business_id}
        )
        cogs_df = pd.DataFrame(cogs_rows, columns=["quantity", "unit_cost"])
        total_cogs = (cogs_df["quantity"] * cogs_df["unit_cost"]).sum() if not cogs_df.empty else 0

        gross_profit = total_revenue - total_cogs
        net_profit = gross_profit - total_expenses

        today = datetime.now()
        if period == "daily":
            mask = df["date"].dt.date == today.date()
        elif period == "weekly":
            mask = df["date"] >= (today - timedelta(days=today.weekday()))
        else:
            mask = (df["date"].dt.year == today.year) & (df["date"].dt.month == today.month)

        period_sales = sales.loc[mask, "amount"].sum() if not sales.empty else 0
        period_expenses = expenses.loc[mask, "amount"].sum() if not expenses.empty else 0
        period_profit = period_sales - period_expenses

        gross_margin = (gross_profit / total_revenue * 100) if total_revenue else 0
        net_margin = (net_profit / total_revenue * 100) if total_revenue else 0

        return {
            "total_revenue": total_revenue, "total_cogs": total_cogs,
            "total_expenses": total_expenses, "gross_profit": gross_profit,
            "net_profit": net_profit, "gross_margin": gross_margin,
            "net_margin": net_margin, "period_profit": period_profit,
            "period_sales": period_sales, "transaction_count": len(df)
        }

    @staticmethod
    def get_monthly_profit_trend(user_id, business_id, months=6):
        rows = DBManager.fetch_all(
            "SELECT date, type, amount FROM transactions WHERE user_id = :uid AND business_id = :bid",
            {"uid": user_id, "bid": business_id}
        )
        df = pd.DataFrame(rows, columns=["date", "type", "amount"])
        if df.empty:
            return pd.DataFrame()
        df["date"] = pd.to_datetime(df["date"])
        cutoff = datetime.now() - timedelta(days=30*months)
        df = df[df["date"] >= cutoff]
        if df.empty:
            return pd.DataFrame()
        df["month"] = df["date"].dt.to_period("M").astype(str)
        pivot = df.pivot_table(index="month", columns="type", values="amount", aggfunc="sum", fill_value=0)
        if "Sales" not in pivot.columns:
            pivot["Sales"] = 0
        if "Expense" not in pivot.columns:
            pivot["Expense"] = 0
        pivot["profit"] = pivot["Sales"] - pivot["Expense"]
        pivot["margin"] = (pivot["profit"] / pivot["Sales"] * 100).replace([np.inf, -np.inf], 0).fillna(0).round(1)
        pivot = pivot.reset_index()
        pivot["month_dt"] = pd.to_datetime(pivot["month"])
        pivot = pivot.sort_values("month_dt")
        return pivot.rename(columns={"Sales": "revenue", "Expense": "expenses"})

    @staticmethod
    def get_sales_data(user_id, business_id):
        rows = DBManager.fetch_all(
            "SELECT date, amount, category FROM transactions WHERE user_id = :uid AND business_id = :bid AND type = 'Sales'",
            {"uid": user_id, "bid": business_id}
        )
        df = pd.DataFrame(rows, columns=["date", "amount", "category"])
        if df.empty:
            return pd.DataFrame()
        df["date"] = pd.to_datetime(df["date"])
        return df

    @staticmethod
    def get_expense_data(user_id, business_id):
        rows = DBManager.fetch_all(
            "SELECT date, amount, category FROM transactions WHERE user_id = :uid AND business_id = :bid AND type = 'Expense'",
            {"uid": user_id, "bid": business_id}
        )
        df = pd.DataFrame(rows, columns=["date", "amount", "category"])
        if df.empty:
            return pd.DataFrame()
        df["date"] = pd.to_datetime(df["date"])
        return df

    @staticmethod
    def get_all_transactions(user_id, business_id, start_date=None, end_date=None):
        query = "SELECT id, date, type, amount, category, description FROM transactions WHERE user_id = :uid AND business_id = :bid"
        params = {"uid": user_id, "bid": business_id}
        if start_date:
            query += " AND date >= :start_date"
            params["start_date"] = start_date
        if end_date:
            query += " AND date <= :end_date"
            params["end_date"] = end_date
        query += " ORDER BY date DESC"
        rows = DBManager.fetch_all(query, params)
        return pd.DataFrame(rows, columns=["id", "date", "type", "amount", "category", "description"])


class Admin:
    @staticmethod
    def get_system_stats():
        users = DBManager.fetch_one("SELECT COUNT(*) FROM users")[0]
        businesses = DBManager.fetch_one("SELECT COUNT(*) FROM businesses")[0]
        transactions = DBManager.fetch_one("SELECT COUNT(*) FROM transactions")[0]
        products = DBManager.fetch_one("SELECT COUNT(*) FROM products")[0]
        return {"users": users, "businesses": businesses, "transactions": transactions, "products": products}

    @staticmethod
    def get_all_users_with_stats():
        users_rows = DBManager.fetch_all("SELECT id, username, email, role, dob, gender FROM users ORDER BY created_at DESC")
        users_df = pd.DataFrame(users_rows, columns=["id", "username", "email", "role", "dob", "gender"])
        if users_df.empty:
            return users_df

        biz_counts = DBManager.fetch_all("SELECT user_id, COUNT(*) as cnt FROM businesses GROUP BY user_id")
        biz_df = pd.DataFrame(biz_counts, columns=["user_id","business_count"])
        tx_counts = DBManager.fetch_all("SELECT user_id, COUNT(*) as cnt FROM transactions GROUP BY user_id")
        tx_df = pd.DataFrame(tx_counts, columns=["user_id","transaction_count"])

        users_df = users_df.merge(biz_df, left_on="id", right_on="user_id", how="left").drop("user_id", axis=1)
        users_df = users_df.merge(tx_df, left_on="id", right_on="user_id", how="left").drop("user_id", axis=1)

        users_df["business_count"] = users_df["business_count"].fillna(0).astype(int)
        users_df["transaction_count"] = users_df["transaction_count"].fillna(0).astype(int)
        return users_df

    @staticmethod
    def delete_user(user_id):
        # All related data will be deleted due to FOREIGN KEY ON DELETE CASCADE
        DBManager.execute("DELETE FROM users WHERE id = :uid", {"uid": user_id})

    @staticmethod
    def change_user_password(user_id, new_password):
        hashed = AuthManager.hash_password(new_password)
        DBManager.execute(
            "UPDATE users SET password = :pw WHERE id = :uid",
            {"pw": hashed, "uid": user_id}
        )

    @staticmethod
    def get_admin_password_hash():
        row = DBManager.fetch_one("SELECT value FROM system_settings WHERE key = 'admin_password'")
        return row._mapping["value"] if row else None

    @staticmethod
    def set_admin_password(new_password):
        hashed = AuthManager.hash_password(new_password)
        DBManager.execute("UPDATE system_settings SET value = :pw WHERE key = 'admin_password'", {"pw": hashed})

    @staticmethod
    def get_daily_transaction_volume(days=30):
        rows = DBManager.fetch_all(
            f"""
            SELECT date(date) as day, COUNT(*) as count
            FROM transactions
            WHERE date >= DATE('now', '-{days} days')
            GROUP BY day
            ORDER BY day
            """
        )
        return pd.DataFrame(rows, columns=["day", "count"])

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
        return pd.DataFrame(rows, columns=["username", "tx_count"])

# -----------------------------------------------------------------------------
# UI Pages
# -----------------------------------------------------------------------------
def page_home():
    st.title("Welcome to Business Analyzer")
    st.write("Your all-in-one solution for managing business finances, inventory, and analytics.")
    st.info("Please log in or sign up to continue.")

def page_login():
    st.title("Login")
    with st.form("login_form"):
        username_or_email = st.text_input("Username or Email")
        password = st.text_input("Password", type="password")
        if st.form_submit_button("Login", use_container_width=True):
            if username_or_email and password:
                result = AuthManager.login(username_or_email, password)
                if result["success"]:
                    st.session_state.logged_in = True
                    st.session_state.user_id = result["user_id"]
                    st.session_state.username = result["username"]
                    st.session_state.email = result["email"]
                    st.session_state.role = result["role"]
                    st.session_state.token = result["token"]
                    st.session_state.page = "Dashboard"
                    st.success(f"Welcome back, {st.session_state.username}!")
                    st.rerun()
                else:
                    st.error(result["message"])
            else:
                st.error("Please enter both username/email and password.")

def page_signup():
    st.title("Sign Up")
    with st.form("signup_form"):
        username = st.text_input("Username")
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        confirm_password = st.text_input("Confirm Password", type="password")
        dob = st.date_input("Date of Birth", min_value=date(1900, 1, 1), max_value=date.today())
        gender = st.selectbox("Gender", ["Male", "Female", "Other", "Prefer not to say"])
        role = st.selectbox("Role", ["Owner", "Accountant", "Staff", "Manager"])

        if st.form_submit_button("Sign Up", use_container_width=True):
            if not (username and email and password and confirm_password):
                st.error("Please fill in all fields.")
            elif password != confirm_password:
                st.error("Passwords do not match.")
            else:
                hashed_password = AuthManager.hash_password(password)
                try:
                    # Insert user and get the ID
                    user_id = DBManager.insert_and_get_id(
                        "INSERT INTO users (username, email, password, role, dob, gender) VALUES (:uname, :email, :pw, :role, :dob, :gender)",
                        {"uname": username, "email": email, "pw": hashed_password, "role": role, "dob": dob, "gender": gender}
                    )

                    if user_id:
                        # Explicitly fetch the user to ensure the ID is correct and committed
                        new_user_row = DBManager.fetch_one(
                            "SELECT id, username, email, role FROM users WHERE id = :uid",
                            {"uid": user_id}
                        )
                        if new_user_row:
                            new_user = dict(new_user_row._mapping)
                            # Create user preferences if they don't exist
                            existing_pref = DBManager.fetch_one("SELECT user_id FROM user_preferences WHERE user_id = :uid", {"uid": user_id})
                            if not existing_pref:
                                DBManager.execute(
                                    "INSERT INTO user_preferences (user_id) VALUES (:uid)",
                                    {"uid": user_id}
                                )

                            st.success("Account created successfully! You can now log in.")
                            set_page("Login")
                            st.rerun()
                        else:
                            st.error("Failed to retrieve new user data after signup. Please try logging in.")
                    else:
                        st.error("Failed to create account. Please try again.")
                except sa.exc.IntegrityError as e:
                    if "UNIQUE constraint failed: users.username" in str(e):
                        st.error("Username already exists. Please choose a different one.")
                    elif "UNIQUE constraint failed: users.email" in str(e):
                        st.error("Email already exists. Please use a different one.")
                    else:
                        st.error(f"Database error during signup: {e}")
                except Exception as e:
                    st.error(f"An unexpected error occurred during signup: {e}")

def page_dashboard():
    if st.session_state.user_id is None:
        st.warning("Please log in first.")
        set_page("Login")
        st.rerun()

    st.title(f"Dashboard for {st.session_state.username}")
    st.write(f"Role: {st.session_state.role}")

    # Display active business selector
    biz_rows = DBManager.fetch_all(
        "SELECT id, business_name FROM businesses WHERE user_id = :uid ORDER BY business_name",
        {"uid": st.session_state.user_id}
    )
    biz = pd.DataFrame(biz_rows, columns=["id", "business_name"])

    if not biz.empty:
        opts = biz.set_index("id")["business_name"].to_dict()
        # Ensure active_business_id is valid for the current user
        if st.session_state.active_business_id not in opts and opts:
            st.session_state.active_business_id = list(opts.keys())[0]
            DBManager.execute(
                "UPDATE user_preferences SET active_business_id = :bid WHERE user_id = :uid",
                {"bid": st.session_state.active_business_id, "uid": st.session_state.user_id}
            )
            st.rerun()

        cur = st.session_state.active_business_id
        sel = st.selectbox("Select active business", options=list(opts.keys()), format_func=lambda x: opts[x],
                           index=list(opts.keys()).index(cur) if cur in opts else 0)
        if sel != cur:
            st.session_state.active_business_id = sel
            DBManager.execute(
                "UPDATE user_preferences SET active_business_id = :bid WHERE user_id = :uid",
                {"bid": sel, "uid": st.session_state.user_id}
            )
            st.rerun()
    else:
        st.info("No businesses found. Please add a business in the 'My Businesses' section.")
        st.session_state.active_business_id = None

    if st.session_state.active_business_id:
        st.subheader(f"Overview for {opts[st.session_state.active_business_id]}")
        metrics = Analytics.calculate_profit_metrics(st.session_state.user_id, st.session_state.active_business_id)
        if metrics:
            show_metric_row([
                ("Total Revenue", f"{st.session_state.currency_symbol}{metrics['total_revenue']:,.2f}", None),
                ("Total Expenses", f"{st.session_state.currency_symbol}{metrics['total_expenses']:,.2f}", None),
                ("Net Profit", f"{st.session_state.currency_symbol}{metrics['net_profit']:,.2f}", f"{metrics['net_margin']:.1f}%"),
                ("Transactions", metrics['transaction_count'], None)
            ])

            st.divider()
            st.subheader("Recent Transactions")
            recent_tx = Analytics.get_all_transactions(st.session_state.user_id, st.session_state.active_business_id)
            if not recent_tx.empty:
                st.dataframe(recent_tx.head(5))
            else:
                st.info("No recent transactions.")
        else:
            st.info("No financial data for the active business yet.")

def page_sales_dashboard():
    if st.session_state.user_id is None:
        st.warning("Please log in first.")
        set_page("Login")
        st.rerun()

    st.title("Sales Dashboard")
    if not st.session_state.active_business_id:
        st.warning("Select active business")
        return

    sales_df = Analytics.get_sales_data(st.session_state.user_id, st.session_state.active_business_id)
    if sales_df.empty:
        st.info("No sales data available for this business.")
        return

    total_sales = sales_df["amount"].sum()
    st.metric("Total Sales", f"{st.session_state.currency_symbol}{total_sales:,.2f}")

    st.subheader("Sales by Category")
    sales_by_category = sales_df.groupby("category")["amount"].sum().sort_values(ascending=False).reset_index()
    fig_cat = px.pie(sales_by_category, values="amount", names="category", title="Sales Distribution by Category")
    st.plotly_chart(fig_cat, use_container_width=True)

    st.subheader("Daily Sales Trend")
    sales_daily = sales_df.set_index("date").resample("D")["amount"].sum().reset_index()
    fig_daily = px.line(sales_daily, x="date", y="amount", title="Daily Sales Over Time")
    st.plotly_chart(fig_daily, use_container_width=True)

def page_sales_trends():
    if st.session_state.user_id is None:
        st.warning("Please log in first.")
        set_page("Login")
        st.rerun()

    st.title("Sales Trends")
    if not st.session_state.active_business_id:
        st.warning("Select active business")
        return

    sales_df = Analytics.get_sales_data(st.session_state.user_id, st.session_state.active_business_id)
    if sales_df.empty:
        st.info("No sales data available for this business.")
        return

    sales_df["month"] = sales_df["date"].dt.to_period("M").astype(str)
    monthly_sales = sales_df.groupby("month")["amount"].sum().reset_index()
    monthly_sales["month_dt"] = pd.to_datetime(monthly_sales["month"])
    monthly_sales = monthly_sales.sort_values("month_dt")

    st.subheader("Monthly Sales Over Time")
    fig = px.line(monthly_sales, x="month_dt", y="amount", markers=True, title="Monthly Sales Trend")
    fig.update_xaxes(tickformat="%b %Y")
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Sales Forecasting (Experimental)")
    if PROPHET_AVAILABLE and len(monthly_sales) > 5:
        prophet_df = monthly_sales[["month_dt", "amount"]].rename(columns={"month_dt": "ds", "amount": "y"})
        m = Prophet()
        m.fit(prophet_df)
        future = m.make_future_dataframe(periods=3, freq="M")
        forecast = m.predict(future)

        fig_forecast = go.Figure()
        fig_forecast.add_trace(go.Scatter(x=prophet_df["ds"], y=prophet_df["y"], mode="lines+markers", name="Actual Sales"))
        fig_forecast.add_trace(go.Scatter(x=forecast["ds"], y=forecast["yhat"], mode="lines", name="Forecast", line=dict(dash="dash")))
        fig_forecast.add_trace(go.Scatter(x=forecast["ds"], y=forecast["yhat_lower"], fill="tonexty", fillcolor="rgba(0,100,80,0.2)", line=dict(color="transparent"), name="Lower Bound"))
        fig_forecast.add_trace(go.Scatter(x=forecast["ds"], y=forecast["yhat_upper"], fill="tonexty", fillcolor="rgba(0,100,80,0.2)", line=dict(color="transparent"), name="Upper Bound"))
        fig_forecast.update_layout(title="Sales Forecast for Next 3 Months", xaxis_title="Date", yaxis_title="Sales Amount")
        st.plotly_chart(fig_forecast, use_container_width=True)
    else:
        st.info("Not enough data points (min 5 months) or Prophet library not installed for forecasting.")

def page_forecasting():
    if st.session_state.user_id is None:
        st.warning("Please log in first.")
        set_page("Login")
        st.rerun()

    st.title("Forecasting")
    if not st.session_state.active_business_id:
        st.warning("Select active business")
        return

    st.subheader("Sales Forecasting")
    sales_df = Analytics.get_sales_data(st.session_state.user_id, st.session_state.active_business_id)
    if sales_df.empty:
        st.info("No sales data available for this business to forecast.")
        return

    sales_df["month"] = sales_df["date"].dt.to_period("M").astype(str)
    monthly_sales = sales_df.groupby("month")["amount"].sum().reset_index()
    monthly_sales["month_dt"] = pd.to_datetime(monthly_sales["month"])
    monthly_sales = monthly_sales.sort_values("month_dt")

    if PROPHET_AVAILABLE and len(monthly_sales) > 5:
        periods = st.slider("Number of months to forecast", 1, 12, 3)
        prophet_df = monthly_sales[["month_dt", "amount"]].rename(columns={"month_dt": "ds", "amount": "y"})
        m = Prophet()
        m.fit(prophet_df)
        future = m.make_future_dataframe(periods=periods, freq="M")
        forecast = m.predict(future)

        fig_forecast = go.Figure()
        fig_forecast.add_trace(go.Scatter(x=prophet_df["ds"], y=prophet_df["y"], mode="lines+markers", name="Actual Sales"))
        fig_forecast.add_trace(go.Scatter(x=forecast["ds"], y=forecast["yhat"], mode="lines", name="Forecast", line=dict(dash="dash")))
        fig_forecast.add_trace(go.Scatter(x=forecast["ds"], y=forecast["yhat_lower"], fill="tonexty", fillcolor="rgba(0,100,80,0.2)", line=dict(color="transparent"), name="Lower Bound"))
        fig_forecast.add_trace(go.Scatter(x=forecast["ds"], y=forecast["yhat_upper"], fill="tonexty", fillcolor="rgba(0,100,80,0.2)", line=dict(color="transparent"), name="Upper Bound"))
        fig_forecast.update_layout(title=f"Sales Forecast for Next {periods} Months", xaxis_title="Date", yaxis_title="Sales Amount")
        st.plotly_chart(fig_forecast, use_container_width=True)

        st.subheader("Forecast Data")
        st.dataframe(forecast[["ds", "yhat", "yhat_lower", "yhat_upper"]].tail(periods).rename(columns={"ds": "Date", "yhat": "Forecast", "yhat_lower": "Lower Bound", "yhat_upper": "Upper Bound"}))

    else:
        st.info("Not enough data points (min 5 months) or Prophet library not installed for forecasting.")
        if st.button("Install Prophet (requires restart)"):
            st.code("pip install prophet")
            st.warning("Please restart the app after installation.")

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
                            markers=True, title="6-Month Trend",
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

def page_profit_margins():
    if st.session_state.user_id is None:
        st.warning("Please log in first.")
        set_page("Login")
        st.rerun()

    st.title("Profit Margins Analysis")
    if not st.session_state.active_business_id:
        st.warning("Select active business")
        return

    trend = Analytics.get_monthly_profit_trend(st.session_state.user_id, st.session_state.active_business_id, months=12)
    if trend.empty:
        st.info("No data to analyze profit margins.")
        return

    st.subheader("Monthly Profit Margin Trend")
    fig_margin_line = px.line(trend, x='month_dt', y='margin', markers=True, title='Monthly Profit Margin %')
    fig_margin_line.update_xaxes(tickformat='%b %Y')
    st.plotly_chart(fig_margin_line, use_container_width=True)

    st.subheader("Profit Margin Distribution")
    fig_margin_hist = px.histogram(trend, x='margin', nbins=20, title='Distribution of Monthly Profit Margins')
    st.plotly_chart(fig_margin_hist, use_container_width=True)

    st.subheader("Key Margin Statistics")
    st.write(f"Average Margin: {trend['margin'].mean():.2f}%")
    st.write(f"Highest Margin: {trend['margin'].max():.2f}% (in {trend.loc[trend['margin'].idxmax(), 'month']})")
    st.write(f"Lowest Margin: {trend['margin'].min():.2f}% (in {trend.loc[trend['margin'].idxmin(), 'month']})")

def page_expense_categories():
    if st.session_state.user_id is None:
        st.warning("Please log in first.")
        set_page("Login")
        st.rerun()

    st.title("Expense Categories Analysis")
    if not st.session_state.active_business_id:
        st.warning("Select active business")
        return

    expense_df = Analytics.get_expense_data(st.session_state.user_id, st.session_state.active_business_id)
    if expense_df.empty:
        st.info("No expense data available for this business.")
        return

    st.subheader("Expenses by Category")
    expenses_by_category = expense_df.groupby("category")["amount"].sum().sort_values(ascending=False).reset_index()
    fig_exp_cat = px.pie(expenses_by_category, values="amount", names="category", title="Expense Distribution by Category")
    st.plotly_chart(fig_exp_cat, use_container_width=True)

    st.subheader("Monthly Expense Trend by Category")
    expense_df["month"] = expense_df["date"].dt.to_period("M").astype(str)
    monthly_expenses_cat = expense_df.groupby(["month", "category"])["amount"].sum().reset_index()
    monthly_expenses_cat["month_dt"] = pd.to_datetime(monthly_expenses_cat["month"])
    monthly_expenses_cat = monthly_expenses_cat.sort_values("month_dt")

    fig_exp_trend = px.line(monthly_expenses_cat, x="month_dt", y="amount", color="category", markers=True, title="Monthly Expenses by Category")
    fig_exp_trend.update_xaxes(tickformat="%b %Y")
    st.plotly_chart(fig_exp_trend, use_container_width=True)

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
        ("Products", inv["product_count"], None),
        ("Total Units", f"{inv['total_units']:,.0f}", None),
        ("Inventory Value", f"{st.session_state.currency_symbol}{inv['total_value']:,.2f}", None)
    ])

    low = Analytics.get_low_stock_items(st.session_state.user_id, st.session_state.active_business_id)
    if not low.empty:
        st.error(f"**{len(low)} low-stock items**")
        with st.expander("View"):
            st.dataframe(low)

    tabs = st.tabs(["Products", "Add Product", "Movement", "History"])
    with tabs[0]:
        prods_rows = DBManager.fetch_all(
            """
            SELECT id, product_name, sku, quantity, cost_price, selling_price, reorder_level, category,
                   (quantity * cost_price) as stock_value
            FROM products WHERE user_id = :uid AND business_id = :bid ORDER BY product_name
            """,
            {"uid": st.session_state.user_id, "bid": st.session_state.active_business_id}
        )
        prods = pd.DataFrame(prods_rows, columns=["id", "product_name","sku","quantity","cost_price","selling_price","reorder_level","category","stock_value"])
        if prods.empty:
            st.info("No products")
        else:
            # Make product names clickable for editing
            edited_prods = st.data_editor(
                prods,
                column_config={
                    "id": None, # Hide ID column
                    "product_name": st.column_config.TextColumn("Product Name", help="Name of the product", required=True),
                    "sku": st.column_config.TextColumn("SKU", help="Unique Stock Keeping Unit"),
                    "quantity": st.column_config.NumberColumn("Quantity", format="%.2f"),
                    "cost_price": st.column_config.NumberColumn("Cost Price", format=f"{st.session_state.currency_symbol}%.2f"),
                    "selling_price": st.column_config.NumberColumn("Selling Price", format=f"{st.session_state.currency_symbol}%.2f"),
                    "reorder_level": st.column_config.NumberColumn("Reorder Level", format="%.2f"),
                    "category": st.column_config.SelectboxColumn("Category", options=["Electronics", "Clothing", "Food", "Furniture", "Other"]),
                    "stock_value": st.column_config.NumberColumn("Stock Value", format=f"{st.session_state.currency_symbol}%.2f", disabled=True)
                },
                hide_index=True,
                num_rows="dynamic",
                key="product_data_editor"
            )

            if st.button("Save Product Changes", key="save_product_changes"):
                for _, r in edited_prods.iterrows():
                    # Check if SKU is unique for other products
                    existing_sku_id = DBManager.fetch_one(
                        "SELECT id FROM products WHERE user_id = :uid AND sku = :sku AND id != :pid",
                        {"uid": st.session_state.user_id, "sku": r["sku"], "pid": r["id"]}
                    )
                    if r["sku"] and existing_sku_id:
                        st.error(f"SKU '{r['sku']}' already exists for another product. Cannot save changes for {r['product_name']}.")
                        continue

                    DBManager.execute(
                        """
                        UPDATE products SET product_name = :name, sku = :sku, quantity = :qty, cost_price = :cost, selling_price = :price, reorder_level = :reorder, category = :cat, updated_at = CURRENT_TIMESTAMP
                        WHERE id = :pid AND user_id = :uid
                        """,
                        {"name": r["product_name"], "sku": r["sku"], "qty": r["quantity"], "cost": r["cost_price"], "price": r["selling_price"], "reorder": r["reorder_level"], "cat": r["category"], "pid": r["id"], "uid": st.session_state.user_id}
                    )
                st.success("Product changes saved!")
                st.rerun()

            # Add delete functionality for products
            st.subheader("Delete Products")
            product_to_delete_id = st.selectbox("Select product to delete", options=[None] + prods["id"].tolist(), format_func=lambda x: prods[prods["id"]==x]["product_name"].iloc[0] if x else "Select a product")
            if product_to_delete_id and st.button("Delete Selected Product", key="delete_product_btn"):
                product_name_to_delete = prods[prods["id"]==product_to_delete_id]["product_name"].iloc[0]
                # Added confirmation step
                confirm_delete = st.warning(f"Are you sure you want to delete '{product_name_to_delete}' and all its stock movements?")
                if confirm_delete:
                    if st.button("Confirm Delete", key="confirm_delete_product"):
                        DBManager.execute("DELETE FROM products WHERE id = :pid AND user_id = :uid", {"pid": product_to_delete_id, "uid": st.session_state.user_id})
                        st.success(f"Product '{product_name_to_delete}' deleted.")
                        st.rerun()

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
                    st.error("Please fill all required fields and ensure prices are positive.")
    with tabs[2]:
        plist_rows = DBManager.fetch_all(
            "SELECT id, product_name, quantity FROM products WHERE user_id = :uid AND business_id = :bid",
            {"uid": st.session_state.user_id, "bid": st.session_state.active_business_id}
        )
        plist = pd.DataFrame(plist_rows, columns=["id","product_name","quantity"])
        if plist.empty:
            st.warning("Add products first")
        else:
            with st.form("movement"):
                pid = st.selectbox("Product", plist["id"].tolist(),
                                   format_func=lambda x: plist[plist["id"]==x]["product_name"].iloc[0])
                cur_qty = plist[plist["id"]==pid]["quantity"].iloc[0]
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
        hist = pd.DataFrame(hist_rows, columns=["movement_date","product_name","movement_type","quantity","unit_cost","unit_price","notes"])
        if hist.empty:
            st.info("No movements")
        else:
            hist["movement_date"] = pd.to_datetime(hist["movement_date"]).dt.strftime("%Y-%m-%d %H:%M")
            for c in ["unit_cost", "unit_price"]:
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
    df = pd.DataFrame(rows, columns=["month","sales","revenue","cogs"])
    if df.empty:
        st.info("No COGS data")
        return
    df["gross_profit"] = df["revenue"] - df["cogs"]
    df["margin"] = (df["gross_profit"] / df["revenue"] * 100).round(1)
    df["month_dt"] = pd.to_datetime(df["month"] + '-01')
    df = df.sort_values("month_dt")
    tot_rev, tot_cogs = df["revenue"].sum(), df["cogs"].sum()
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
        title='Monthly Revenue, COGS, and Gross Margin',
        xaxis_title='Month',
        legend=dict(x=0, y=1.1, orientation='h')
    )
    st.plotly_chart(fig, use_container_width=True)

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
                # Ensure user_id is not None
                if st.session_state.user_id is None:
                    st.error("Session error. Please log in again.")
                    set_page("Login")
                    st.rerun()
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
    df = pd.DataFrame(biz_rows, columns=["id","business_name","business_type","address","phone","created_at"])
    if df.empty:
        st.info("No businesses yet.")
        return

    for _, row in df.iterrows():
        bid, active = row["id"], st.session_state.active_business_id == row["id"]
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
            # Confirm deletion
            confirm_delete = st.warning(f"Are you sure you want to delete business '{row['business_name']}' and all its transactions/products?")
            if confirm_delete:
                if st.button("Confirm Delete", key=f"confirm_del_{bid}"):
                    DBManager.execute("DELETE FROM businesses WHERE id = :bid AND user_id = :uid", {"bid": bid, "uid": st.session_state.user_id})
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
                            UPDATE businesses SET business_name=:name, business_type=:typ, address=:addr, phone=:phone WHERE id=:bid AND user_id = :uid
                            """,
                            {"name": nn, "typ": nt, "addr": na, "phone": np_, "bid": bid, "uid": st.session_state.user_id}
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
    df = pd.DataFrame(rows, columns=["id", "type", "amount", "category", "description", "date"])
    if df.empty:
        st.info("No transactions.")
        return

    # Permissions for editing/deleting transactions
    can_edit = st.session_state.role in ["Owner", "Manager", "Accountant"]
    can_delete = st.session_state.role in ["Owner", "Manager"]

    disabled_cols = ["id", "date"]
    if not can_edit:
        disabled_cols.extend(["type","amount","category","description"])

    edited = st.data_editor(df,
        column_config={
            "id": st.column_config.NumberColumn("ID", disabled=True),
            "type": st.column_config.SelectboxColumn("Type", options=["Sales","Expense"], required=True),
            "amount": st.column_config.NumberColumn("Amount", min_value=0.01, format=f"{st.session_state.currency_symbol}%.2f", required=True),
            "category": st.column_config.TextColumn("Category"),
            "description": st.column_config.TextColumn("Description"),
            "date": st.column_config.DatetimeColumn("Date", disabled=True),
        },
        disabled=disabled_cols, hide_index=True,
        num_rows="dynamic" if can_delete else "fixed"
    )
    if can_edit and st.button("Save Changes"):
        for _, r in edited.iterrows():
            DBManager.execute(
                "UPDATE transactions SET type = :typ, amount = :amt, category = :cat, description = :desc WHERE id = :id AND user_id = :uid",
                {"typ": r["type"], "amt": r["amount"], "cat": r["category"], "desc": r["description"],
                 "id": r["id"], "uid": st.session_state.user_id}
            )
        st.success("Saved")
        st.rerun()

    if can_delete:
        st.subheader("Delete Transactions")
        tx_to_delete_id = st.selectbox("Select transaction to delete", options=[None] + df["id"].tolist(), format_func=lambda x: f"ID: {x} - {df[df["id"]==x]['description'].iloc[0]}" if x else "Select a transaction")
        if tx_to_delete_id and st.button("Delete Selected Transaction", key="delete_tx_btn"):
            # Added confirmation step
            confirm_delete = st.warning(f"Are you sure you want to delete transaction ID {tx_to_delete_id}?")
            if confirm_delete:
                if st.button("Confirm Delete", key="confirm_delete_tx"):
                    DBManager.execute("DELETE FROM transactions WHERE id = :tid AND user_id = :uid", {"tid": tx_to_delete_id, "uid": st.session_state.user_id})
                    st.success(f"Transaction ID {tx_to_delete_id} deleted.")
                    st.rerun()

    st.download_button("Download CSV", df.to_csv(index=False).encode("utf-8"), "transactions.csv", mime="text/csv")

def page_import_transactions():
    if st.session_state.user_id is None:
        st.warning("Please log in first.")
        set_page("Login")
        st.rerun()

    st.title("Import CSV")
    if not st.session_state.active_business_id:
        st.warning("Select active business first")
        return
    file = st.file_uploader("Choose CSV", type=["csv"])
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
    date_col = st.selectbox("Date column", ["None"]+cols, index=0) # Added date column mapping
    default_type = st.selectbox("Default type for unmapped rows", ["Sales","Expense"])

    if amt_col != "None" and st.button("IMPORT", type="primary"):
        success = 0
        errors = 0
        error_details = []
        prog = st.progress(0)
        status = st.empty()

        for idx, row in df.iterrows():
            prog.progress((idx + 1) / len(df))
            try:
                raw_amt = row[amt_col]
                if pd.isna(raw_amt):
                    errors += 1
                    error_details.append(f"Row {idx+2}: Amount is empty")
                    continue

                amt_str = str(raw_amt).replace('₹', '').replace('$', '').replace('€', '').replace(',', '').strip()
                # Ensure only valid numeric characters remain
                amt_str = ''.join(c for c in amt_str if c.isdigit() or c in '.-')
                if not amt_str:
                    errors += 1
                    error_details.append(f"Row {idx+2}: Amount contains no valid number")
                    continue
                amount = float(amt_str)

                transaction_type = row[typ_col] if typ_col != "None" and pd.notna(row[typ_col]) else default_type
                category = row[cat_col] if cat_col != "None" and pd.notna(row[cat_col]) else None
                description = row[desc_col] if desc_col != "None" and pd.notna(row[desc_col]) else None

                # Handle date column
                transaction_date = datetime.now()
                if date_col != "None" and pd.notna(row[date_col]):
                    try:
                        transaction_date = pd.to_datetime(row[date_col])
                    except Exception:
                        error_details.append(f"Row {idx+2}: Invalid date format for '{row[date_col]}'. Using current date.")

                DBManager.execute(
                    """
                    INSERT INTO transactions (user_id, business_id, type, amount, category, description, date)
                    VALUES (:uid, :bid, :typ, :amt, :cat, :desc, :dt)
                    """,
                    {"uid": st.session_state.user_id, "bid": st.session_state.active_business_id,
                     "typ": transaction_type, "amt": amount, "cat": category, "desc": description, "dt": transaction_date}
                )
                success += 1
            except Exception as e:
                errors += 1
                error_details.append(f"Row {idx+2}: {e}")
        status.empty()
        st.success(f"Import complete! {success} transactions added, {errors} errors.")
        if errors > 0:
            with st.expander("View Errors"):
                for err in error_details:
                    st.error(err)
        st.rerun()

def page_analyze_data():
    if st.session_state.user_id is None:
        st.warning("Please log in first.")
        set_page("Login")
        st.rerun()

    st.title("Analyze Data")
    if not st.session_state.active_business_id:
        st.warning("Select active business")
        return

    st.write("This section provides advanced data analysis capabilities.")
    st.info("Coming soon: Custom queries, predictive modeling, and more!")

def page_profile():
    if st.session_state.user_id is None:
        st.warning("Please log in first.")
        set_page("Login")
        st.rerun()

    st.title("User Profile")
    user_data = DBManager.fetch_one(
        "SELECT username, email, role, dob, gender, created_at FROM users WHERE id = :uid",
        {"uid": st.session_state.user_id}
    )

    if user_data:
        user_dict = dict(user_data._mapping)
        st.write(f"**Username:** {user_dict['username']}")
        st.write(f"**Email:** {user_dict['email']}")
        st.write(f"**Role:** {user_dict['role']}")
        st.write(f"**Date of Birth:** {user_dict['dob']}")
        st.write(f"**Gender:** {user_dict['gender']}")
        st.write(f"**Member Since:** {user_dict['created_at']}")

        st.subheader("Change Password")
        with st.form("change_password_form"):
            current_password = st.text_input("Current Password", type="password")
            new_password = st.text_input("New Password", type="password")
            confirm_new_password = st.text_input("Confirm New Password", type="password")
            if st.form_submit_button("Change Password"):
                # Verify current password
                user_auth_data = DBManager.fetch_one(
                    "SELECT password FROM users WHERE id = :uid",
                    {"uid": st.session_state.user_id}
                )
                if user_auth_data and AuthManager.check_password(current_password, user_auth_data._mapping["password"]):
                    if new_password == confirm_new_password:
                        if new_password:
                            Admin.change_user_password(st.session_state.user_id, new_password)
                            st.success("Password changed successfully!")
                            # Force re-login for security
                            logout()
                        else:
                            st.error("New password cannot be empty.")
                    else:
                        st.error("New passwords do not match.")
                else:
                    st.error("Incorrect current password.")
    else:
        st.error("User data not found.")

def page_report_generation():
    if st.session_state.user_id is None:
        st.warning("Please log in first.")
        set_page("Login")
        st.rerun()

    st.title("Generate Reports")
    if not st.session_state.active_business_id:
        st.warning("Select active business")
        return

    report_type = st.selectbox("Select Report Type", ["Financial Summary (Excel)", "Detailed Transactions (PDF)"])
    start_date = st.date_input("Start Date", value=datetime.now().date() - timedelta(days=30))
    end_date = st.date_input("End Date", value=datetime.now().date())

    if st.button("Generate Report", type="primary"):
        transactions_df = Analytics.get_all_transactions(st.session_state.user_id, st.session_state.active_business_id, start_date, end_date)
        inventory_df = DBManager.fetch_all(
            "SELECT product_name, sku, quantity, cost_price, selling_price FROM products WHERE user_id = :uid AND business_id = :bid",
            {"uid": st.session_state.user_id, "bid": st.session_state.active_business_id}
        )
        inventory_df = pd.DataFrame(inventory_df, columns=["product_name", "sku", "quantity", "cost_price", "selling_price"])

        summary_data = []
        if not transactions_df.empty:
            sales_sum = transactions_df[transactions_df["type"] == "Sales"]["amount"].sum()
            expense_sum = transactions_df[transactions_df["type"] == "Expense"]["amount"].sum()
            summary_data.append({"type": "Sales", "count": len(transactions_df[transactions_df["type"] == "Sales"]), "total": sales_sum})
            summary_data.append({"type": "Expenses", "count": len(transactions_df[transactions_df["type"] == "Expense"]), "total": expense_sum})
            summary_data.append({"type": "Net Profit", "count": '-', "total": sales_sum - expense_sum})
        summary_df = pd.DataFrame(summary_data)

        report_data = {
            "summary": summary_df,
            "transactions": transactions_df,
            "inventory": inventory_df
        }

        try:
            if report_type == "Financial Summary (Excel)":
                excel_output = generate_excel_report(report_data, start_date, end_date)
                st.download_button(
                    label="Download Excel Report",
                    data=excel_output,
                    file_name=f"financial_report_{start_date}_{end_date}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            elif report_type == "Detailed Transactions (PDF)":
                pdf_output = generate_pdf_report(report_data, start_date, end_date)
                st.download_button(
                    label="Download PDF Report",
                    data=pdf_output,
                    file_name=f"transactions_report_{start_date}_{end_date}.pdf",
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

    # Admin password authentication
    if not st.session_state.get("admin_authenticated", False):
        with st.form("admin_password_form"):
            password = st.text_input("Enter Admin Password", type="password")
            if st.form_submit_button("Access Dashboard"):
                stored_admin_pw_hash = Admin.get_admin_password_hash()
                if stored_admin_pw_hash and AuthManager.check_password(password, stored_admin_pw_hash):
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
        ("Total Users", stats["users"], None),
        ("Total Businesses", stats["businesses"], None),
        ("Total Transactions", stats["transactions"], None),
        ("Total Products", stats["products"], None)
    ])

    st.divider()
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["User Management", "Login History", "Admin Access Logs", "Change Passwords", "System Settings"])

    with tab1:
        st.subheader("User Management")
        users_df = Admin.get_all_users_with_stats()
        if users_df.empty:
            st.info("No users found.")
        else:
            st.dataframe(users_df[["username","email","role","dob","gender","business_count","transaction_count"]])
            st.markdown("--- User Actions ---")
            for idx, row in users_df.iterrows():
                cols = st.columns([2,2,1,1,1,1])
                cols[0].write(f"**{row['username']}**")
                cols[1].write(row['email'])
                cols[2].write(row['role'])
                cols[3].write(f"Biz: {row['business_count']}")
                cols[4].write(f"Tx: {row['transaction_count']}")
                if row["id"] != st.session_state.user_id:
                    delete_key = f"del_user_{row['id']}"
                    # Using a unique key for the button to avoid Streamlit issues
                    if cols[5].button("Delete", key=delete_key):
                        # Confirmation step
                        confirm_delete = st.warning(f"Are you sure you want to delete user {row['username']}? This action is irreversible and will delete all associated data.")
                        if confirm_delete:
                            if st.button("Confirm Delete", key=f"confirm_del_user_{row['id']}"):
                                Admin.delete_user(row['id'])
                                st.success(f"User {row['username']} deleted.")
                                st.rerun()
                else:
                    cols[5].write("(You)")
                st.markdown("--- ")

    with tab2:
        st.subheader("User Login History")
        role_filter = st.selectbox("Filter by role", ["All", "Owner", "Accountant", "Staff", "Manager"], key="login_history_role_filter")
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
        df_logins = pd.DataFrame(rows, columns=["username","role","login_time","logout_time","session_duration"])
        if df_logins.empty:
            st.info("No login records.")
        else:
            df_logins["login_time"] = pd.to_datetime(df_logins["login_time"]).dt.strftime("%Y-%m-%d %H:%M:%S")
            # Apply to_datetime only if there are non-null values to avoid error on all-null column
            if df_logins["logout_time"].notna().any():
                df_logins["logout_time"] = pd.to_datetime(df_logins["logout_time"]).dt.strftime("%Y-%m-%d %H:%M:%S")
            else:
                df_logins["logout_time"] = None # Ensure column type consistency
            df_logins["session_duration"] = df_logins["session_duration"].apply(lambda x: f"{int(x)} sec" if pd.notna(x) else "Active")
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
        df_admin = pd.DataFrame(rows, columns=["access_time","username","role"])
        if df_admin.empty:
            st.info("No admin access records.")
        else:
            df_admin["access_time"] = pd.to_datetime(df_admin["access_time"]).dt.strftime("%Y-%m-%d %H:%M:%S")
            st.dataframe(df_admin)

    with tab4:
        st.subheader("Change User Password")
        users = DBManager.fetch_all("SELECT id, username FROM users")
        user_options = {u._mapping["id"]: u._mapping["username"] for u in users}
        selected_user_id = st.selectbox("Select User", options=list(user_options.keys()), format_func=lambda x: user_options[x], key="admin_change_user_pw_select")
        new_password = st.text_input("New Password", type="password", key="admin_new_pw")
        confirm_password = st.text_input("Confirm New Password", type="password", key="admin_confirm_pw")
        if st.button("Update Password", key="admin_update_pw_btn"):
            if new_password != confirm_password:
                st.error("Passwords do not match.")
            elif not new_password:
                st.error("Password cannot be empty.")
            else:
                Admin.change_user_password(selected_user_id, new_password)
                st.success(f"Password updated for user {user_options[selected_user_id]}.")

        st.subheader("Change Admin Dashboard Password")
        with st.form("change_admin_password_form"):
            current_admin_password = st.text_input("Current Admin Password", type="password", key="current_admin_pw")
            new_admin_password = st.text_input("New Admin Password", type="password", key="new_admin_pw")
            confirm_new_admin_password = st.text_input("Confirm New Admin Password", type="password", key="confirm_new_admin_pw")
            if st.form_submit_button("Change Admin Password", key="change_admin_pw_btn"):
                stored_admin_pw_hash = Admin.get_admin_password_hash()
                if stored_admin_pw_hash and AuthManager.check_password(current_admin_password, stored_admin_pw_hash):
                    if new_admin_password == confirm_new_admin_password:
                        if new_admin_password:
                            Admin.set_admin_password(new_admin_password)
                            st.success("Admin password changed successfully!")
                            st.session_state.admin_authenticated = False # Force re-auth with new password
                            st.rerun()
                        else:
                            st.error("New admin password cannot be empty.")
                    else:
                        st.error("New admin passwords do not match.")
                else:
                    st.error("Incorrect current admin password.")

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
        # Headers
        pdf.cell(40, 8, 'Type', 1)
        pdf.cell(30, 8, 'Count', 1)
        pdf.cell(40, 8, 'Total', 1)
        pdf.ln(8)
        for _, row in summary.iterrows():
            pdf.cell(40, 8, str(row['type']), 1)
            pdf.cell(30, 8, str(row['count']), 1)
            pdf.cell(40, 8, f"{st.session_state.currency_symbol}{row['total']:,.2f}", 1)
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
            pdf.cell(25, 8, f"{st.session_state.currency_symbol}{row['amount']:,.2f}", 1)
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
            pdf.cell(25, 8, (row['sku'] or '')[:10], 1)
            pdf.cell(20, 8, str(row['quantity']), 1)
            pdf.cell(25, 8, f"{st.session_state.currency_symbol}{row['cost_price']:,.2f}", 1)
            pdf.cell(25, 8, f"{st.session_state.currency_symbol}{row['selling_price']:,.2f}", 1)
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
        if not user and st.session_state.get("logged_in"):
            logout()
            st.rerun()
        if st.session_state.get("logged_in"):
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
                                # st.rerun() # logout already calls rerun
                        else:
                            if st.button(page, use_container_width=True, key=f"nav_{page}"):
                                set_page(page)
                                st.rerun() # Add rerun here to ensure page change takes effect
                st.divider()
        else:
            for page in ["Home", "Login", "Sign Up"]:
                if st.button(page, use_container_width=True):
                    set_page(page)
                    st.rerun()

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
    if st.session_state.get("logged_in", False) and st.session_state.page == 'Login':
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
        # Default to Home if not logged in, or Dashboard if logged in but on an invalid page
        set_page("Home" if not st.session_state.logged_in else "Dashboard")
        st.rerun()

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        st.error(f"Application error: {e}")
