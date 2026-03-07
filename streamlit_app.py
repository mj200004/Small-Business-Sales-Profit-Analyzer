"""
Business Analyzer – All Milestones (1, 2, 3, 4)
-----------------------------------------------
A comprehensive business management tool with:
- Authentication & user management (JWT + bcrypt)
- Business profiles & transaction logging
- Inventory tracking & COGS calculation
- Advanced analytics: interactive charts, category breakdowns,
  AI-based forecasting using Prophet (with linear regression fallback)
- Report generation (PDF/Excel) with email delivery
- Admin dashboard for system monitoring

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

# Optional Prophet import
try:
    from prophet import Prophet
    prophet_available = True
except ImportError:
    prophet_available = False

from sklearn.linear_model import LinearRegression

# -----------------------------------------------------------------------------
# Database paths
# -----------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
USER_DB = os.path.join(BASE_DIR, 'USER.db')
BUSINESS_DB = os.path.join(BASE_DIR, 'BUSINESS.db')
SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'your-secret-key-change-in-production')
JWT_ALGORITHM = 'HS256'

# -----------------------------------------------------------------------------
# Clean and modern CSS – clearly visible input fields and select boxes
# -----------------------------------------------------------------------------
def apply_custom_css():
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
        html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
        .stApp { background: linear-gradient(135deg, #f5f7fa 0%, #e9ecf5 100%); }

        [data-testid="stSidebar"] {
            background: rgba(255, 255, 255, 0.7) !important;
            backdrop-filter: blur(10px);
            border-right: 1px solid rgba(255, 255, 255, 0.3);
        }

        h1, h2, h3 {
            color: #1E3A5F;
            font-weight: 600;
            border-bottom: 2px solid rgba(30,58,95,0.1);
            padding-bottom: 0.5rem;
        }

        .stButton > button {
            border-radius: 12px;
            border: none;
            background: linear-gradient(135deg, #1E3A5F 0%, #2B4C7C 100%);
            color: white;
            padding: 0.6rem 1.2rem;
            font-weight: 500;
            transition: all 0.3s ease;
            box-shadow: 0 4px 15px rgba(30,58,95,0.2);
        }
        .stButton > button:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(30,58,95,0.3);
        }

        [data-testid="stSidebar"] {
            background: rgba(255, 255, 255, 0.98) !important;
            backdrop-filter: blur(20px);
            border-right: 3px solid rgba(102, 126, 234, 0.5);
            box-shadow: 4px 0 20px rgba(0,0,0,0.15);
        }
        
        .stButton > button {
            border-radius: 12px !important;
            border: 2px solid transparent !important;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
            color: white !important;
            padding: 0.75rem 1.5rem !important;
            font-weight: 600 !important;
            font-size: 1rem !important;
            transition: all 0.3s ease !important;
            box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4) !important;
        }
        
        .stButton > button:hover {
            transform: translateY(-3px) !important;
            box-shadow: 0 10px 30px rgba(102, 126, 234, 0.6) !important;
            border-color: #ffffff !important;
        }
        
        .stTextInput > div > div > input,
        .stNumberInput > div > div > input,
        .stTextArea > div > div > textarea {
            background-color: #ffffff !important;
            border: 3px solid #667eea !important;
            border-radius: 10px !important;
            padding: 0.75rem 1rem !important;
            font-size: 1rem !important;
            font-weight: 500 !important;
            color: #2d3748 !important;
        }
        
        .stTextInput > div > div > input:focus,
        .stNumberInput > div > div > input:focus {
            border-color: #764ba2 !important;
            box-shadow: 0 0 0 3px rgba(118, 75, 162, 0.2) !important;
        }
        
        .stSelectbox > div > div {
            background-color: #ffffff !important;
            border: 3px solid #667eea !important;
            border-radius: 10px !important;
            padding: 0.5rem 1rem !important;
            font-weight: 600 !important;
            min-height: 50px !important;
        }
        
        .stSelectbox > div > div > div {
            color: #2d3748 !important;
            font-weight: 600 !important;
        }


        div[data-testid="stMetric"] {
            background: rgba(255, 255, 255, 0.6);
            backdrop-filter: blur(8px);
            border-radius: 20px;
            padding: 1.5rem 1rem;
            box-shadow: 0 8px 32px rgba(0,0,0,0.05);
            border: 1px solid rgba(255,255,255,0.5);
        }
        [data-testid="stMetricValue"] {
            font-size: 2.2rem !important;
            font-weight: 700;
            color: #1E3A5F;
        }

        .stDataFrame { border: none; border-radius: 16px; overflow: hidden; }

        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
            background: rgba(255,255,255,0.4);
            backdrop-filter: blur(4px);
            padding: 6px;
            border-radius: 30px;
        }
        .stTabs [data-baseweb="tab"] {
            border-radius: 30px;
            padding: 8px 20px;
            background: transparent;
            font-weight: 500;
        }
        .stTabs [aria-selected="true"] {
            background: white !important;
            color: #1E3A5F !important;
            box-shadow: 0 4px 10px rgba(0,0,0,0.05);
        }

        .admin-card {
            background: rgba(255, 255, 255, 0.7);
            backdrop-filter: blur(10px);
            border-radius: 24px;
            padding: 1.8rem 1.2rem;
            box-shadow: 0 15px 35px rgba(0,0,0,0.05);
            border: 1px solid rgba(255,255,255,0.6);
            text-align: center;
        }
        .admin-card .value { font-size: 2.5rem; font-weight: 700; color: #1E3A5F; }

        .js-plotly-plot {
            background: rgba(255,255,255,0.3);
            backdrop-filter: blur(4px);
            border-radius: 20px;
            padding: 10px;
        }

        /* Enhanced input fields */
        .stTextInput label, .stNumberInput label, .stSelectbox label,
        .stDateInput label, .stTextArea label {
            font-weight: 600;
            color: #1E3A5F;
            font-size: 0.95rem;
        }

        .stTextInput input, .stNumberInput input,
        .stSelectbox div[data-baseweb="select"] > div,
        .stDateInput input, .stTextArea textarea {
            background-color: #ffffff !important;
            border: 2px solid #a0b8cc !important;
            border-radius: 10px !important;
            padding: 0.6rem 1rem !important;
            box-shadow: 0 2px 6px rgba(0,0,0,0.05) !important;
            transition: all 0.2s ease;
        }

        .stTextInput input:focus, .stNumberInput input:focus,
        .stSelectbox div[data-baseweb="select"] > div:focus,
        .stDateInput input:focus, .stTextArea textarea:focus {
            border-color: #1E3A5F !important;
            box-shadow: 0 0 0 3px rgba(30,58,95,0.2) !important;
        }

        /* Ensure selectbox container has consistent styling */
        .stSelectbox div[data-baseweb="select"] > div {
            background-color: white;
            min-height: 45px;
        }

        /* Make the dropdown arrow visible */
        .stSelectbox svg {
            fill: #1E3A5F !important;
        }

        /* Dropdown menu styling */
        div[data-baseweb="popover"] {
            border-radius: 10px !important;
            border: 2px solid #a0b8cc !important;
            background-color: white !important;
        }

        .stCheckbox label {
            font-weight: 500;
            color: #1E3A5F;
        }

        .stAlert { border-radius: 12px; }
        </style>
    """, unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# Color helper
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

# -----------------------------------------------------------------------------
# Database Helpers
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
            active_business_id INTEGER,
            currency_symbol TEXT DEFAULT '₹',
            default_reorder_level REAL DEFAULT 5.0
        )''')
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
        conn.execute('''CREATE TABLE IF NOT EXISTS admin_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_user_id INTEGER,
            action TEXT,
            target_user_id INTEGER,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        # Ensure user_preferences has new columns
        try:
            conn.execute("ALTER TABLE user_preferences ADD COLUMN currency_symbol TEXT DEFAULT '₹'")
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute("ALTER TABLE user_preferences ADD COLUMN default_reorder_level REAL DEFAULT 5.0")
        except sqlite3.OperationalError:
            pass

# -----------------------------------------------------------------------------
# Authentication
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

def init_session_state():
    defaults = {
        'token': None,
        'logged_in': False,
        'username': None,
        'user_id': None,
        'role': None,
        'page': "Home",
        'uploaded_df': None,
        'active_business_id': None,
        'currency_symbol': '₹',
        'default_reorder_level': 5.0
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
                    "SELECT active_business_id, currency_symbol, default_reorder_level FROM user_preferences WHERE user_id = ?",
                    (user['id'],)
                ).fetchone()
                if pref:
                    st.session_state.active_business_id = pref['active_business_id']
                    st.session_state.currency_symbol = pref['currency_symbol']
                    st.session_state.default_reorder_level = pref['default_reorder_level']
                else:
                    b_conn.execute("INSERT INTO user_preferences (user_id, currency_symbol, default_reorder_level) VALUES (?, '₹', 5.0)", (user['id'],))
                    st.session_state.currency_symbol = '₹'
                    st.session_state.default_reorder_level = 5.0
            st.session_state.page = "Dashboard"
            return True, "Login successful!"
    return False, "Invalid username or password!"

def logout_user():
    for key in ['token', 'logged_in', 'username', 'user_id', 'role', 'uploaded_df', 'active_business_id', 'currency_symbol', 'default_reorder_level']:
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

def can_edit_transactions():
    return st.session_state.role in ['Owner', 'Accountant']

def can_delete_transactions():
    return st.session_state.role == 'Owner'

def is_admin():
    return st.session_state.role == 'Owner'

# -----------------------------------------------------------------------------
# Profit & Inventory functions
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
            return False, "SKU already exists. Please use a different SKU."
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
                return False, f"Insufficient stock. Available: {curr_qty}, requested: {qty}"
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
# Advanced Analytics
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

# -----------------------------------------------------------------------------
# Report Generation
# -----------------------------------------------------------------------------
def get_report_data(user_id, business_id, start_date, end_date):
    with get_business_db() as conn:
        df = pd.read_sql("""
            SELECT date, type, amount, category, description
            FROM transactions
            WHERE user_id=? AND business_id=?
              AND date BETWEEN ? AND ?
            ORDER BY date
        """, conn, params=(user_id, business_id, start_date, end_date))
        summary = pd.read_sql("""
            SELECT type, COUNT(*) as count, SUM(amount) as total
            FROM transactions
            WHERE user_id=? AND business_id=?
              AND date BETWEEN ? AND ?
            GROUP BY type
        """, conn, params=(user_id, business_id, start_date, end_date))
        inventory = pd.read_sql("""
            SELECT product_name, sku, quantity, cost_price, selling_price
            FROM products
            WHERE user_id=? AND business_id=?
        """, conn, params=(user_id, business_id))
    return {
        'transactions': df,
        'summary': summary,
        'inventory': inventory
    }

def generate_excel_report(data_dict, start_date, end_date):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        summary_df = data_dict['summary']
        if not summary_df.empty:
            summary_df.to_excel(writer, sheet_name='Summary', index=False)
        else:
            pd.DataFrame({'Message': ['No data for this period']}).to_excel(writer, sheet_name='Summary', index=False)
        tx_df = data_dict['transactions']
        tx_df.to_excel(writer, sheet_name='Transactions', index=False)
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

    # Summary
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

    # Transactions (first 20)
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

    # Inventory
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
    if isinstance(out, str):
        return out.encode('latin-1', errors='replace')
    else:
        return bytes(out)

# -----------------------------------------------------------------------------
# Simplified Email Sending (no configuration, local SMTP)
# -----------------------------------------------------------------------------
def send_email_simple(to_email, subject, body, attachment_bytes, attachment_filename, from_email):
    """
    Send email using local SMTP server (no authentication).
    Assumes a local mail server (e.g., sendmail) is running on port 25.
    """
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
        server = smtplib.SMTP('localhost', 25)  # local SMTP server, no auth
        server.send_message(msg)
        server.quit()
        return True, "Email sent successfully via local SMTP."
    except Exception as e:
        return False, str(e)

# -----------------------------------------------------------------------------
# Admin Functions
# -----------------------------------------------------------------------------
def get_system_stats():
    with get_user_db() as u_conn:
        total_users = u_conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    with get_business_db() as b_conn:
        total_businesses = b_conn.execute("SELECT COUNT(*) FROM businesses").fetchone()[0]
        total_transactions = b_conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
        total_products = b_conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    return {
        'users': total_users,
        'businesses': total_businesses,
        'transactions': total_transactions,
        'products': total_products
    }

def get_all_users_with_stats():
    with get_user_db() as u_conn:
        users = pd.read_sql("SELECT id, username, email, role, created_at FROM users", u_conn)
    with get_business_db() as b_conn:
        biz_counts = pd.read_sql("SELECT user_id, COUNT(*) as business_count FROM businesses GROUP BY user_id", b_conn)
        tx_counts = pd.read_sql("SELECT user_id, COUNT(*) as transaction_count FROM transactions GROUP BY user_id", b_conn)
    users = users.merge(biz_counts, left_on='id', right_on='user_id', how='left').drop('user_id', axis=1, errors='ignore')
    users = users.merge(tx_counts, left_on='id', right_on='user_id', how='left').drop('user_id', axis=1, errors='ignore')
    users['business_count'] = users['business_count'].fillna(0).astype(int)
    users['transaction_count'] = users['transaction_count'].fillna(0).astype(int)
    return users

def delete_user(user_id):
    with get_user_db() as u_conn:
        u_conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
    with get_business_db() as b_conn:
        b_conn.execute("DELETE FROM transactions WHERE user_id = ?", (user_id,))
        b_conn.execute("DELETE FROM businesses WHERE user_id = ?", (user_id,))
        b_conn.execute("DELETE FROM products WHERE user_id = ?", (user_id,))
        b_conn.execute("DELETE FROM user_preferences WHERE user_id = ?", (user_id,))

def get_daily_transaction_volume(days=30):
    with get_business_db() as conn:
        df = pd.read_sql(f"""
            SELECT date(date) as day, COUNT(*) as count
            FROM transactions
            WHERE date >= date('now', '-{days} days')
            GROUP BY day
            ORDER BY day
        """, conn)
    return df

def get_category_completeness():
    with get_business_db() as conn:
        total = conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
        missing = conn.execute("SELECT COUNT(*) FROM transactions WHERE category IS NULL OR category = ''").fetchone()[0]
    if total == 0:
        return 0, 0
    return total, missing

def get_top_users_by_transactions(limit=5):
    with get_user_db() as u_conn:
        users = pd.read_sql("SELECT id, username FROM users", u_conn)
    with get_business_db() as b_conn:
        tx_counts = pd.read_sql("SELECT user_id, COUNT(*) as tx_count FROM transactions GROUP BY user_id", b_conn)
    merged = users.merge(tx_counts, left_on='id', right_on='user_id', how='left')
    merged['tx_count'] = merged['tx_count'].fillna(0).astype(int)
    merged = merged.sort_values('tx_count', ascending=False).head(limit)
    return merged[['username', 'tx_count']]

# -----------------------------------------------------------------------------
# Page Functions
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

    ### Milestone 4 – Reports, Admin, and Deployment
    **Features:** PDF/Excel report generation, email reports, admin dashboard.
    """)

def login_page():
    st.title("Login")
    # Image removed as requested
    with st.form("login_form", clear_on_submit=False):
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
    with st.form("signup_form", clear_on_submit=False):
        nu = st.text_input("Username")
        em = st.text_input("Email")
        pw = st.text_input("Password", type="password")
        cf = st.text_input("Confirm Password", type="password")
        # Role selectbox – clearly visible due to enhanced CSS
        role = st.selectbox("Role", ["Owner", "Accountant", "Staff"], key="selectbox_1")
        if st.form_submit_button("Sign Up", use_container_width=True):
            if not nu or not em or not pw:
                st.error("Please fill in all required fields.")
            elif pw != cf:
                st.error("Passwords do not match. Please re-enter.")
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
    col2.metric("Total Sales", f"{st.session_state.currency_symbol}{sales:,.2f}")
    col3.metric("Net Profit", f"{st.session_state.currency_symbol}{profit:,.2f}")
    if cnt == 0:
        st.info("No transactions yet. Use 'Add Transaction' or 'Import CSV'.")

    st.divider()
    st.subheader("Active Business")
    with get_business_db() as conn:
        biz = pd.read_sql("SELECT id, business_name FROM businesses WHERE user_id = ?", conn, params=(st.session_state.user_id,))
    if not biz.empty:
        opts = biz.set_index('id')['business_name'].to_dict()
        cur = st.session_state.active_business_id
        sel = st.selectbox("Select business", options=list(opts.keys(, key="selectbox_2")), format_func=lambda x: opts[x],
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
        with st.form("add_business_form", clear_on_submit=False):
            name = st.text_input("Business Name *")
            typ = st.text_input("Type")
            addr = st.text_area("Address")
            phone = st.text_input("Phone")
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
    with st.form("transaction_form", clear_on_submit=False):
        typ = st.selectbox("Type", ["Sales", "Expense"], key="trans_type")
        # FIXED: amount starts at 0.0, step 1.0, format allows decimals
        amt = st.number_input(f"Amount ({st.session_state.currency_symbol})", min_value=0.01, value=1.01, value=0.01, step=1.0, format="%.2f", key="amount_input")
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
            "amount": st.column_config.NumberColumn("Amount", min_value=0.01, format=f"{st.session_state.currency_symbol}%.2f", required=True),
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
    default_type = st.selectbox("Default type", ["Sales","Expense"], key="selectbox_8")

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

                with get_business_db() as conn:
                    conn.execute("""
                        INSERT INTO transactions (user_id, business_id, type, amount, category, description)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (st.session_state.user_id, st.session_state.active_business_id,
                          ttype, amt, cat, desc))
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

    df['date'] = pd.to_datetime(df['date'])
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
    cols = st.columns(4)
    cols[0].metric("Total Sales", f"{st.session_state.currency_symbol}{total_sales:,.2f}")
    cols[1].metric("Total Expenses", f"{st.session_state.currency_symbol}{total_exp:,.2f}")
    cols[2].metric("Net Profit", f"{st.session_state.currency_symbol}{profit:,.2f}")
    cols[3].metric("Avg Sale", f"{st.session_state.currency_symbol}{avg:,.2f}")

def analyze_data_page():
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
                chart_type = st.selectbox("Chart type", ["Bar", "Line", "Scatter", "Histogram", "Pie"], key="selectbox_9")
                if chart_type == "Bar":
                    x_col = st.selectbox("X-axis (categorical, key="selectbox_10")", df.columns)
                    y_col = st.selectbox("Y-axis (numeric, key="selectbox_11")", num_cols)
                    if x_col and y_col:
                        agg_df = df.groupby(x_col)[y_col].sum().reset_index()
                        colors = get_color_sequence(len(agg_df), 'Set2')
                        fig = px.bar(agg_df, x=x_col, y=y_col, color=x_col,
                                     color_discrete_sequence=colors,
                                     title=f"{y_col} by {x_col}")
                        st.plotly_chart(fig, use_container_width=True)

                elif chart_type == "Line":
                    x_col = st.selectbox("X-axis (date/numeric, key="selectbox_12")", df.columns)
                    y_col = st.selectbox("Y-axis (numeric, key="selectbox_13")", num_cols)
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
                        x_col = st.selectbox("X-axis", num_cols, key="selectbox_14")
                        y_col = st.selectbox("Y-axis", num_cols, key="selectbox_15")
                        color_col = st.selectbox("Color by (optional, key="selectbox_16")", ["None"] + df.columns.tolist())
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
                    col = st.selectbox("Column", num_cols, key="selectbox_17")
                    if col:
                        fig = px.histogram(df, x=col, nbins=20,
                                           title=f"Distribution of {col}")
                        st.plotly_chart(fig, use_container_width=True)

                elif chart_type == "Pie":
                    cat_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
                    if cat_cols:
                        cat = st.selectbox("Category column", cat_cols, key="selectbox_18")
                        num = st.selectbox("Numeric column (sum, key="selectbox_19")", num_cols)
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

def profile_page():
    st.title("Profile")
    with get_user_db() as conn:
        user = conn.execute("SELECT * FROM users WHERE id = ?", (st.session_state.user_id,)).fetchone()
    if not user:
        st.error("User not found")
        return

    col1, col2 = st.columns(2)
    with col1:
        st.write(f"**Username:** {user['username']}")
        st.write(f"**Email:** {user['email']}")
        st.write(f"**Role:** {user['role']}")
    with col2:
        if user['created_at']:
            st.write(f"**Member since:** {user['created_at']}")

    st.divider()
    with st.form("update_profile", clear_on_submit=False):
        new_email = st.text_input("New Email", user['email'])
        new_pw = st.text_input("New Password", type="password")
        confirm = st.text_input("Confirm Password", type="password")
        if st.form_submit_button("Update Profile", use_container_width=True):
            if new_pw and new_pw != confirm:
                st.error("Passwords do not match. Please re-enter.")
            else:
                with get_user_db() as conn:
                    if new_pw:
                        hashed = hash_password(new_pw)
                        conn.execute("UPDATE users SET email=?, password=? WHERE id=?", (new_email, hashed, st.session_state.user_id))
                    else:
                        conn.execute("UPDATE users SET email=? WHERE id=?", (new_email, st.session_state.user_id))
                st.success("Profile updated successfully")
                st.rerun()

    st.divider()
    with st.form("delete_account", clear_on_submit=False):
        st.warning("Deleting your account is irreversible. All your data will be permanently removed.")
        confirm = st.checkbox("I understand the consequences")
        if st.form_submit_button("Delete My Account", use_container_width=True) and confirm:
            with get_business_db() as b_conn:
                b_conn.execute("DELETE FROM transactions WHERE user_id = ?", (st.session_state.user_id,))
                b_conn.execute("DELETE FROM businesses WHERE user_id = ?", (st.session_state.user_id,))
                b_conn.execute("DELETE FROM products WHERE user_id = ?", (st.session_state.user_id,))
                b_conn.execute("DELETE FROM user_preferences WHERE user_id = ?", (st.session_state.user_id,))
            with get_user_db() as conn:
                conn.execute("DELETE FROM users WHERE id = ?", (st.session_state.user_id,))
            logout_user()
            st.success("Account deleted. Redirecting...")
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
    col1.metric("Gross Profit", f"{st.session_state.currency_symbol}{m['gross_profit']:,.2f}", f"{m['gross_margin']:.1f}%")
    col2.metric("Net Profit", f"{st.session_state.currency_symbol}{m['net_profit']:,.2f}", f"{m['net_margin']:.1f}%")
    col3.metric("Revenue", f"{st.session_state.currency_symbol}{m['total_revenue']:,.2f}")
    col4.metric("COGS", f"{st.session_state.currency_symbol}{m['total_cogs']:,.2f}")
    st.divider()
    c1, c2 = st.columns(2)
    c1.metric("This Month Profit", f"{st.session_state.currency_symbol}{m['period_profit']:,.2f}", f"{st.session_state.currency_symbol}{m['period_sales']:,.2f} revenue")

    fig = go.Figure(data=[
        go.Bar(name='Revenue', x=['Current'], y=[m['period_sales']],
               marker_color='#1f77b4'),
        go.Bar(name='Expenses', x=['Current'], y=[m['total_expenses']],
               marker_color='#d62728'),
        go.Bar(name='Profit', x=['Current'], y=[m['period_profit']],
               marker_color='#ff7f0e')
    ])
    fig.update_layout(barmode='group', height=300, showlegend=True,
                      title="Current Period Overview")
    c2.plotly_chart(fig, use_container_width=True)

    st.divider()
    trend = get_monthly_profit_trend(st.session_state.user_id, st.session_state.active_business_id)
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

def inventory_management_page():
    st.title("Inventory")
    if not st.session_state.active_business_id:
        st.warning("Select active business")
        return
    inv = get_inventory_value(st.session_state.user_id, st.session_state.active_business_id)
    col1, col2, col3 = st.columns(3)
    col1.metric("Products", inv['product_count'])
    col2.metric("Total Units", f"{inv['total_units']:,.0f}")
    col3.metric("Inventory Value", f"{st.session_state.currency_symbol}{inv['total_value']:,.2f}")

    low = get_low_stock_items(st.session_state.user_id, st.session_state.active_business_id)
    if not low.empty:
        st.error(f"**{len(low)} low‑stock items**")
        with st.expander("View"):
            st.dataframe(low)

    tabs = st.tabs(["Products", "Add Product", "Movement", "History"])
    with tabs[0]:
        with get_business_db() as conn:
            prods = pd.read_sql("SELECT product_name, sku, quantity, cost_price, selling_price, reorder_level, category, (quantity*cost_price) as stock_value FROM products WHERE user_id=? AND business_id=? ORDER BY product_name",
                                conn, params=(st.session_state.user_id, st.session_state.active_business_id))
        if prods.empty:
            st.info("No products")
        else:
            prods['cost_price'] = prods['cost_price'].apply(lambda x: f"{st.session_state.currency_symbol}{x:,.2f}")
            prods['selling_price'] = prods['selling_price'].apply(lambda x: f"{st.session_state.currency_symbol}{x:,.2f}")
            prods['stock_value'] = prods['stock_value'].apply(lambda x: f"{st.session_state.currency_symbol}{x:,.2f}")
            st.dataframe(prods)
    with tabs[1]:
        with st.form("add_product", clear_on_submit=False):
            name = st.text_input("Product Name *")
            sku = st.text_input("SKU (unique identifier)")
            qty = st.number_input("Initial Quantity", 0.0, step=1.0)
            cost = st.number_input("Cost Price *", 0.0, step=1.0)
            price = st.number_input("Selling Price *", 0.0, step=1.0)
            reorder = st.number_input("Reorder Level", 0.0, step=1.0, value=st.session_state.default_reorder_level)
            cat = st.selectbox("Category", ["Electronics", "Clothing", "Food", "Furniture", "Other"], key="selectbox_20")
            if st.form_submit_button("Add Product", use_container_width=True):
                if name and cost > 0 and price > 0:
                    ok, msg = add_product(st.session_state.user_id, st.session_state.active_business_id,
                                          name, sku, qty, cost, price, reorder, cat)
                    if ok:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)
                else:
                    st.error("Please fill all required fields.")
    with tabs[2]:
        with get_business_db() as conn:
            plist = pd.read_sql("SELECT id, product_name, quantity FROM products WHERE user_id=? AND business_id=?",
                                conn, params=(st.session_state.user_id, st.session_state.active_business_id))
        if plist.empty:
            st.warning("Add products first")
        else:
            with st.form("movement", clear_on_submit=False):
                pid = st.selectbox("Product", plist['id'].tolist(, key="selectbox_21"),
                                   format_func=lambda x: plist[plist['id']==x]['product_name'].iloc[0])
                cur_qty = plist[plist['id']==pid]['quantity'].iloc[0]
                st.info(f"Current stock: {cur_qty:,.2f}")
                move = st.selectbox("Movement Type", ["purchase", "sale", "adjustment"], key="selectbox_22")
                mqty = st.number_input("Quantity", 0.0, step=1.0)
                unit_cost = st.number_input("Unit Cost (if purchase)", 0.0, step=1.0)
                unit_price = st.number_input("Unit Price (if sale)", 0.0, step=1.0)
                ref = st.text_input("Reference (optional)")
                notes = st.text_area("Notes")
                if st.form_submit_button("Record Movement", use_container_width=True):
                    if mqty > 0:
                        ok, msg = record_stock_movement(pid, move, mqty,
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
            for c in ['unit_cost', 'unit_price']:
                hist[c] = hist[c].apply(lambda x: f"{st.session_state.currency_symbol}{x:,.2f}" if x else '-')
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
    cols[0].metric("Total Revenue", f"{st.session_state.currency_symbol}{tot_rev:,.2f}")
    cols[1].metric("Total COGS", f"{st.session_state.currency_symbol}{tot_cogs:,.2f}")
    cols[2].metric("Gross Profit", f"{st.session_state.currency_symbol}{tot_profit:,.2f}")
    cols[3].metric("Avg Margin", f"{avg_margin:.1f}%")

    fig = go.Figure()
    fig.add_trace(go.Bar(name='Revenue', x=df['month_dt'], y=df['revenue'],
                         marker_color='#1f77b4'))
    fig.add_trace(go.Bar(name='COGS', x=df['month_dt'], y=df['cogs'],
                         marker_color='#d62728'))
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
    period = st.radio("View", ["Daily", "Weekly", "Monthly"], horizontal=True, key="view_period")
    freq = {"Daily": "D", "Weekly": "W", "Monthly": "M"}[period]
    grouped = df.set_index('date').resample(freq).sum().reset_index()
    fig = px.line(grouped, x='date', y='amount', title=f"Sales ({period})", markers=True,
                  line_shape='linear')
    fig.update_xaxes(tickformat='%b %d, %Y' if period == 'Daily' else '%b %Y')
    st.plotly_chart(fig, use_container_width=True)
    cols = st.columns(3)
    cols[0].metric("Total", f"{st.session_state.currency_symbol}{grouped['amount'].sum():,.2f}")
    cols[1].metric("Avg/period", f"{st.session_state.currency_symbol}{grouped['amount'].mean():,.2f}")
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
    pivot['Margin'] = (pivot['Profit'] / pivot['Sales'] * 100).replace([np.inf, -np.inf], 0).fillna(0)

    period = st.radio("Resample", ["Daily", "Weekly", "Monthly"], horizontal=True, key="radio_2")
    freq = {"Daily": "D", "Weekly": "W", "Monthly": "M"}[period]
    res = pivot.resample(freq).sum().reset_index()

    fig = go.Figure()
    fig.add_trace(go.Bar(name='Sales', x=res['date'], y=res['Sales'],
                         marker_color='#1f77b4'))
    fig.add_trace(go.Bar(name='Expenses', x=res['date'], y=res['Expense'],
                         marker_color='#d62728'))
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

    cols = st.columns(3)
    cols[0].metric("Total Profit", f"{st.session_state.currency_symbol}{res['Profit'].sum():,.2f}")
    cols[1].metric("Avg Margin", f"{res['Margin'].mean():.1f}%")
    cols[2].metric("Best Margin", f"{res['Margin'].max():.1f}%")

def expense_categories_page():
    st.title("Expense Categories")
    if not st.session_state.active_business_id:
        st.warning("Select active business")
        return
    period = st.selectbox("Period", ["All time", "Last 30 days", "Last 7 days", "This year"], key="selectbox_23")
    pmap = {"All time": None, "Last 30 days": "month", "Last 7 days": "week", "This year": "year"}

    df_exp = get_expense_by_category(st.session_state.user_id, st.session_state.active_business_id, pmap[period])
    if df_exp.empty:
        st.info("No expenses")
    else:
        colors = get_color_sequence(len(df_exp), 'Pastel')
        fig_exp = px.pie(df_exp, values='total', names='category',
                         title=f"Expenses {period}", color_discrete_sequence=colors)
        st.plotly_chart(fig_exp, use_container_width=True)
        df_exp['total'] = df_exp['total'].apply(lambda x: f"{st.session_state.currency_symbol}{x:,.2f}")
        st.dataframe(df_exp)

    st.divider()
    st.subheader("Sales by Category")
    df_sales = get_sales_by_category(st.session_state.user_id, st.session_state.active_business_id, pmap[period])
    if df_sales.empty:
        st.info("No sales")
    else:
        colors = get_color_sequence(len(df_sales), 'Bold')
        fig_sales = px.bar(df_sales, x='category', y='total',
                           title=f"Sales {period}", color='category',
                           color_discrete_sequence=colors)
        st.plotly_chart(fig_sales, use_container_width=True)
        df_sales['total'] = df_sales['total'].apply(lambda x: f"{st.session_state.currency_symbol}{x:,.2f}")
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

    freq_labels = ["Daily", "Weekly", "Monthly"]
    freq_codes = ["D", "W", "M"]
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
                st.error(f"**{lab}**: {cnt} X (need ≥3)")

    target = st.radio("Forecast", ["Sales", "Profit"], horizontal=True, key="radio_3")
    freq_opt = st.selectbox("Frequency", freq_labels, index=2, key="selectbox_24")
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

# -----------------------------------------------------------------------------
# Milestone 4 Pages: Report Generation & Admin Dashboard
# -----------------------------------------------------------------------------
def report_generation_page():
    st.title("Generate Report")
    if not st.session_state.active_business_id:
        st.warning("Select an active business first.")
        return

    with st.form("report_form", clear_on_submit=False):
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("Start Date", datetime.now().date() - timedelta(days=30))
        with col2:
            end_date = st.date_input("End Date", datetime.now().date())

        report_type = st.radio("Report Format", ["Excel", "PDF"], horizontal=True, key="radio_4")
        include_inventory = st.checkbox("Include Inventory Data", value=True)

        send_email = st.checkbox("Send report via email")
        if send_email:
            email_to = st.text_input("Recipient Email")
            # Get owner's email from user database
            with get_user_db() as conn:
                user = conn.execute("SELECT email FROM users WHERE id = ?", (st.session_state.user_id,)).fetchone()
            owner_email = user['email'] if user else ""
            st.info(f"Report will be sent from your registered email: {owner_email}")
        else:
            email_to = None

        submitted = st.form_submit_button("Generate Report", type="primary")

    if submitted:
        if start_date > end_date:
            st.error("Start date must be before end date.")
            return

        data = get_report_data(st.session_state.user_id, st.session_state.active_business_id,
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
                attachment = excel_bytes.getvalue()
                filename = f"report_{start_date}_to_{end_date}.xlsx"
            else:  # PDF
                pdf_bytes = generate_pdf_report(data, start_date, end_date)
                st.download_button(
                    label="Download PDF Report",
                    data=pdf_bytes,
                    file_name=f"report_{start_date}_to_{end_date}.pdf",
                    mime="application/pdf"
                )
                attachment = pdf_bytes
                filename = f"report_{start_date}_to_{end_date}.pdf"

            if send_email and email_to:
                with get_user_db() as conn:
                    user = conn.execute("SELECT email FROM users WHERE id = ?", (st.session_state.user_id,)).fetchone()
                from_email = user['email'] if user else "business-analyzer@localhost"
                subject = f"Business Report {start_date} to {end_date}"
                body = f"Please find attached your business report for period {start_date} to {end_date}."
                ok, msg = send_email_simple(email_to, subject, body, attachment, filename, from_email)
                if ok:
                    st.success(msg)
                else:
                    st.error(f"Email failed: {msg}. Ensure a local SMTP server is running on port 25.")
        except Exception as e:
            st.error(f"Report generation failed: {str(e)}")

def admin_dashboard_page():
    st.title("Admin Dashboard")
    if not is_admin():
        st.error("Access denied. This page is for Owners only.")
        return

    stats = get_system_stats()
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"""
        <div class="admin-card">
            <h3>Total Users</h3>
            <div class="value">{stats['users']}</div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="admin-card">
            <h3>Total Businesses</h3>
            <div class="value">{stats['businesses']}</div>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
        <div class="admin-card">
            <h3>Total Transactions</h3>
            <div class="value">{stats['transactions']}</div>
        </div>
        """, unsafe_allow_html=True)
    with col4:
        st.markdown(f"""
        <div class="admin-card">
            <h3>Total Products</h3>
            <div class="value">{stats['products']}</div>
        </div>
        """, unsafe_allow_html=True)

    st.divider()

    tab1, tab2, tab3 = st.tabs(["User Management", "System Health", "System Settings"])

    with tab1:
        st.subheader("User Management")
        users_df = get_all_users_with_stats()
        if users_df.empty:
            st.info("No users found.")
        else:
            for idx, row in users_df.iterrows():
                cols = st.columns([2, 2, 1, 1, 1, 1])
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
                            delete_user(row['id'])
                            st.success(f"User {row['username']} deleted.")
                            st.session_state[confirm_key] = False
                            st.rerun()
                        if col_no.button("Cancel", key=f"no_{row['id']}"):
                            st.session_state[confirm_key] = False
                            st.rerun()
                else:
                    cols[5].write("(You)")

    with tab2:
        st.subheader("System Health & Data Quality")

        daily_df = get_daily_transaction_volume(30)
        if not daily_df.empty:
            fig = px.bar(daily_df, x='day', y='count', title="Daily Transaction Volume (Last 30 Days)",
                         labels={'day': 'Date', 'count': 'Transactions'})
            st.plotly_chart(fig, use_container_width=True)

        total_tx, missing_cat = get_category_completeness()
        if total_tx > 0:
            completeness = ((total_tx - missing_cat) / total_tx) * 100
            st.metric("Category Completeness", f"{completeness:.1f}%", f"{missing_cat} missing")
        else:
            st.info("No transaction data yet.")

        top_users = get_top_users_by_transactions()
        if not top_users.empty:
            fig = px.bar(top_users, x='username', y='tx_count', title="Top Users by Transactions",
                         labels={'username': 'User', 'tx_count': 'Transactions'})
            st.plotly_chart(fig, use_container_width=True)

    with tab3:
        st.subheader("System Settings")

        with st.form("system_settings_form", clear_on_submit=False):
            currency = st.text_input("Currency Symbol", value=st.session_state.currency_symbol,
                                     help="Symbol used for monetary values (e.g., ₹, $, €)")
            default_reorder = st.number_input("Default Reorder Level", value=st.session_state.default_reorder_level,
                                              step=0.5, help="Default reorder threshold for new products")
            if st.form_submit_button("Save Settings", use_container_width=True):
                with get_business_db() as conn:
                    conn.execute("UPDATE user_preferences SET currency_symbol = ?, default_reorder_level = ? WHERE user_id = ?",
                                 (currency, default_reorder, st.session_state.user_id))
                st.session_state.currency_symbol = currency
                st.session_state.default_reorder_level = default_reorder
                st.success("Settings saved.")
                st.rerun()

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
            # Milestone 4 – Reports & Admin
            st.subheader("Reports & Admin")
            cols = st.columns(2)
            with cols[0]: st.button("Generate Report", use_container_width=True, on_click=change_page, args=("Generate Report",))
            if is_admin():
                with cols[1]: st.button("Admin Dashboard", use_container_width=True, on_click=change_page, args=("Admin Dashboard",))
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
    apply_custom_css()
    init_user_db()
    init_business_db()
    init_session_state()
    render_sidebar()

    page = st.session_state.page
    logged = st.session_state.logged_in

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
    elif page == "Generate Report" and logged: report_generation_page()
    elif page == "Admin Dashboard" and logged: admin_dashboard_page()
    else:
        st.session_state.page = "Home" if not logged else "Dashboard"
        st.rerun()

if __name__ == "__main__":
    try:
        with get_business_db() as conn:
            conn.execute("SELECT 1")
        main()
    except sqlite3.Error as e:
        st.error(f"Database connection failed. Ensure BUSINESS.db exists at: {BUSINESS_DB}\nError: {e}")
