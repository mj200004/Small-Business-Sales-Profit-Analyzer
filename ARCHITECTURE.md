# Business Analyzer - Technical Architecture

Complete technical documentation of the Business Analyzer application architecture, design patterns, and implementation details.

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Technology Stack](#technology-stack)
3. [Application Architecture](#application-architecture)
4. [Database Design](#database-design)
5. [Authentication & Security](#authentication--security)
6. [Data Flow](#data-flow)
7. [Module Structure](#module-structure)
8. [Design Patterns](#design-patterns)
9. [API Reference](#api-reference)
10. [Deployment Architecture](#deployment-architecture)

---

## System Overview

### Architecture Type
**Monolithic Web Application** with client-server architecture

### Components
- **Frontend**: Streamlit (Python-based reactive UI)
- **Backend**: Python application logic
- **Database**: SQLite (embedded database)
- **Authentication**: JWT + bcrypt
- **Visualization**: Plotly
- **ML/Forecasting**: Prophet + scikit-learn

### Deployment Model
- Single-process application
- Embedded database (no separate DB server)
- Local or cloud deployment
- Horizontal scaling via load balancer (optional)

---

## Technology Stack

### Core Framework
```
Streamlit 1.x
├── Python 3.8+
├── Reactive UI components
├── Session state management
└── Built-in routing
```

### Data Processing
```
Pandas 1.x
├── DataFrame operations
├── Time series analysis
├── Data aggregation
└── CSV/Excel I/O

NumPy 1.x
├── Numerical computations
├── Array operations
└── Statistical functions
```

### Database
```
SQLite 3.x
├── Embedded database
├── ACID compliance
├── Zero configuration
└── File-based storage
```

### Authentication
```
PyJWT 2.x
├── Token generation
├── Token verification
└── Expiration handling

bcrypt 4.x
├── Password hashing
├── Salt generation
└── Secure comparison
```

### Visualization
```
Plotly 5.x
├── Express (high-level API)
├── Graph Objects (low-level API)
├── Interactive charts
└── Export capabilities
```

### Machine Learning
```
Prophet 1.x (optional)
├── Time series forecasting
├── Seasonality detection
└── Trend analysis

scikit-learn 1.x
├── Linear regression
├── Model training
└── Predictions
```

### Reporting
```
FPDF2 2.x
├── PDF generation
├── Custom layouts
└── Multi-page support

OpenPyXL 3.x
├── Excel file creation
├── Multi-sheet workbooks
└── Cell formatting
```

---

## Application Architecture

### Layered Architecture

```
┌─────────────────────────────────────┐
│     Presentation Layer              │
│  (Streamlit UI Components)          │
├─────────────────────────────────────┤
│     Application Layer               │
│  (Business Logic & Controllers)     │
├─────────────────────────────────────┤
│     Data Access Layer               │
│  (Database Operations)              │
├─────────────────────────────────────┤
│     Data Layer                      │
│  (SQLite Databases)                 │
└─────────────────────────────────────┘
```

### Component Diagram

```
┌──────────────┐
│   Browser    │
└──────┬───────┘
       │ HTTP
       ▼
┌──────────────────────────────────────┐
│      Streamlit Server                │
│  ┌────────────────────────────────┐  │
│  │   Session State Manager        │  │
│  └────────────────────────────────┘  │
│  ┌────────────────────────────────┐  │
│  │   Page Router                  │  │
│  └────────────────────────────────┘  │
│  ┌────────────────────────────────┐  │
│  │   Authentication Middleware    │  │
│  └────────────────────────────────┘  │
└──────────────┬───────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│      Business Logic Layer            │
│  ┌────────────────────────────────┐  │
│  │   Transaction Manager          │  │
│  │   Inventory Manager            │  │
│  │   Analytics Engine             │  │
│  │   Forecasting Engine           │  │
│  │   Report Generator             │  │
│  └────────────────────────────────┘  │
└──────────────┬───────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│      Data Access Layer               │
│  ┌────────────────────────────────┐  │
│  │   Database Context Managers    │  │
│  │   Query Builders               │  │
│  │   Connection Pool              │  │
│  └────────────────────────────────┘  │
└──────────────┬───────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│      SQLite Databases                │
│  ┌─────────────┐  ┌──────────────┐  │
│  │  USER.db    │  │ BUSINESS.db  │  │
│  └─────────────┘  └──────────────┘  │
└──────────────────────────────────────┘
```

---

## Database Design

### Entity-Relationship Diagram

```
┌─────────────┐
│    users    │
└──────┬──────┘
       │ 1
       │
       │ N
┌──────┴──────────────┐
│                     │
│ ┌─────────────┐    │ ┌──────────────────┐
│ │ businesses  │    │ │ user_preferences │
│ └──────┬──────┘    │ └──────────────────┘
│        │ 1         │
│        │           │
│        │ N         │
│ ┌──────┴──────┐    │
│ │transactions │    │
│ └─────────────┘    │
│                    │
│ ┌─────────────┐    │
│ │  products   │    │
│ └──────┬──────┘    │
│        │ 1         │
│        │           │
│        │ N         │
│ ┌──────┴──────────┐│
│ │stock_movements  ││
│ └─────────────────┘│
└────────────────────┘
```

### Database Schema Details

#### USER.db

**users table**
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,  -- bcrypt hashed
    role TEXT NOT NULL DEFAULT 'Owner',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE UNIQUE INDEX idx_users_username ON users(username);
CREATE UNIQUE INDEX idx_users_email ON users(email);
```

#### BUSINESS.db

**businesses table**
```sql
CREATE TABLE businesses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    business_name TEXT NOT NULL,
    business_type TEXT,
    address TEXT,
    phone TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Indexes
CREATE INDEX idx_businesses_user_id ON businesses(user_id);
```

**transactions table**
```sql
CREATE TABLE transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    business_id INTEGER NOT NULL,
    type TEXT NOT NULL CHECK(type IN ('Sales', 'Expense')),
    amount REAL NOT NULL CHECK(amount > 0),
    category TEXT,
    description TEXT,
    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (business_id) REFERENCES businesses(id)
);

-- Indexes
CREATE INDEX idx_transactions_user_business ON transactions(user_id, business_id);
CREATE INDEX idx_transactions_date ON transactions(date);
CREATE INDEX idx_transactions_type ON transactions(type);
```

**products table**
```sql
CREATE TABLE products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    business_id INTEGER NOT NULL,
    product_name TEXT NOT NULL,
    sku TEXT UNIQUE,
    quantity REAL DEFAULT 0 CHECK(quantity >= 0),
    cost_price REAL DEFAULT 0 CHECK(cost_price >= 0),
    selling_price REAL DEFAULT 0 CHECK(selling_price >= 0),
    reorder_level REAL DEFAULT 5 CHECK(reorder_level >= 0),
    category TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (business_id) REFERENCES businesses(id)
);

-- Indexes
CREATE UNIQUE INDEX idx_products_sku ON products(sku);
CREATE INDEX idx_products_user_business ON products(user_id, business_id);
```

**stock_movements table**
```sql
CREATE TABLE stock_movements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,
    movement_type TEXT NOT NULL CHECK(movement_type IN ('purchase', 'sale', 'adjustment')),
    quantity REAL NOT NULL CHECK(quantity > 0),
    unit_cost REAL,
    unit_price REAL,
    reference_id INTEGER,
    movement_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes TEXT,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
);

-- Indexes
CREATE INDEX idx_stock_movements_product ON stock_movements(product_id);
CREATE INDEX idx_stock_movements_date ON stock_movements(movement_date);
```

**user_preferences table**
```sql
CREATE TABLE user_preferences (
    user_id INTEGER PRIMARY KEY,
    active_business_id INTEGER,
    currency_symbol TEXT DEFAULT '₹',
    default_reorder_level REAL DEFAULT 5.0,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (active_business_id) REFERENCES businesses(id)
);
```

**admin_logs table**
```sql
CREATE TABLE admin_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    admin_user_id INTEGER,
    action TEXT,
    target_user_id INTEGER,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (admin_user_id) REFERENCES users(id),
    FOREIGN KEY (target_user_id) REFERENCES users(id)
);

-- Indexes
CREATE INDEX idx_admin_logs_admin ON admin_logs(admin_user_id);
CREATE INDEX idx_admin_logs_timestamp ON admin_logs(timestamp);
```

---

## Authentication & Security

### Authentication Flow

```
┌─────────┐
│  User   │
└────┬────┘
     │ 1. Enter credentials
     ▼
┌─────────────────┐
│  Login Page     │
└────┬────────────┘
     │ 2. Submit
     ▼
┌─────────────────────────┐
│  login_user()           │
│  - Query user           │
│  - Verify password      │
│  - Generate JWT token   │
└────┬────────────────────┘
     │ 3. Token + Session
     ▼
┌─────────────────────────┐
│  Session State          │
│  - token                │
│  - logged_in = True     │
│  - user_id              │
│  - username             │
│  - role                 │
└────┬────────────────────┘
     │ 4. Redirect
     ▼
┌─────────────────┐
│  Dashboard      │
└─────────────────┘
```

### JWT Token Structure

```json
{
  "header": {
    "alg": "HS256",
    "typ": "JWT"
  },
  "payload": {
    "user_id": 1,
    "username": "john_doe",
    "role": "Owner",
    "exp": 1234567890
  },
  "signature": "..."
}
```

### Password Security

**Hashing Process:**
```python
# Registration
plain_password = "user_password"
salt = bcrypt.gensalt()  # Random salt
hashed = bcrypt.hashpw(plain_password.encode(), salt)
# Store hashed in database

# Login
stored_hash = get_from_database()
input_password = "user_password"
is_valid = bcrypt.checkpw(input_password.encode(), stored_hash.encode())
```

### Security Measures

1. **Password Hashing**: bcrypt with automatic salt
2. **SQL Injection Prevention**: Parameterized queries
3. **XSS Prevention**: Streamlit's built-in escaping
4. **CSRF Protection**: Streamlit's session tokens
5. **Session Management**: Server-side session state
6. **Token Expiration**: 24-hour JWT expiration
7. **Role-Based Access**: Function-level permission checks

---

## Data Flow

### Transaction Creation Flow

```
User Input
    │
    ▼
┌─────────────────────┐
│ add_transaction_    │
│ page()              │
│ - Validate input    │
│ - Check permissions │
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│ get_business_db()   │
│ - Open connection   │
│ - Begin transaction │
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│ INSERT INTO         │
│ transactions        │
│ - Execute query     │
│ - Get last_row_id   │
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│ Commit & Close      │
│ - conn.commit()     │
│ - conn.close()      │
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│ Update UI           │
│ - st.success()      │
│ - st.rerun()        │
└─────────────────────┘
```

### Forecasting Data Flow

```
User Request
    │
    ▼
┌──────────────────────┐
│ forecasting_page()   │
│ - Get parameters     │
│ - Validate data      │
└──────┬───────────────┘
       │
       ▼
┌──────────────────────┐
│ prepare_time_series()│
│ - Query transactions │
│ - Aggregate by freq  │
│ - Format for Prophet │
└──────┬───────────────┘
       │
       ▼
┌──────────────────────┐
│ get_forecast()       │
│ - Choose method      │
│ - Train model        │
│ - Generate forecast  │
└──────┬───────────────┘
       │
       ▼
┌──────────────────────┐
│ Visualization        │
│ - Create Plotly fig  │
│ - Add traces         │
│ - Display chart      │
└──────────────────────┘
```

---

## Module Structure

### File Organization

```
BusinessAnalyzer/
├── streamlit_app.py          # Main application (2000+ lines)
│   ├── CSS styling
│   ├── Database functions
│   ├── Authentication
│   ├── Business logic
│   ├── Page functions
│   ├── Sidebar & routing
│   └── Main entry point
│
├── Milestone3 (1).py          # Advanced analytics module
│   ├── Forecasting functions
│   ├── Category analysis
│   └── Trend analysis pages
│
├── requirements.txt           # Python dependencies
├── USER.db                    # User database (created at runtime)
├── BUSINESS.db                # Business database (created at runtime)
│
└── Documentation/
    ├── README.md
    ├── SETUP_GUIDE.md
    ├── USER_GUIDE.md
    ├── FEATURES.md
    └── ARCHITECTURE.md
```

### Function Categories

**Authentication Functions:**
- `hash_password()`
- `check_password()`
- `create_jwt_token()`
- `verify_jwt_token()`
- `login_user()`
- `logout_user()`
- `authenticate()`

**Database Functions:**
- `get_user_db()` - Context manager
- `get_business_db()` - Context manager
- `init_user_db()`
- `init_business_db()`

**Business Logic Functions:**
- `calculate_profit_metrics()`
- `get_monthly_profit_trend()`
- `add_product()`
- `record_stock_movement()`
- `get_low_stock_items()`
- `get_inventory_value()`

**Analytics Functions:**
- `prepare_time_series()`
- `forecast_with_prophet()`
- `forecast_with_linear_regression()`
- `get_forecast()`
- `get_expense_by_category()`
- `get_sales_by_category()`

**Report Functions:**
- `get_report_data()`
- `generate_excel_report()`
- `generate_pdf_report()`
- `send_email_simple()`

**Admin Functions:**
- `get_system_stats()`
- `get_all_users_with_stats()`
- `delete_user()`
- `get_daily_transaction_volume()`
- `get_category_completeness()`
- `get_top_users_by_transactions()`

**Page Functions:**
- `home_page()`
- `login_page()`
- `signup_page()`
- `dashboard_page()`
- `add_transaction_page()`
- `view_transactions_page()`
- `import_transactions_page()`
- `businesses_page()`
- `inventory_management_page()`
- `profit_dashboard_page()`
- `sales_trends_page()`
- `forecasting_page()`
- `report_generation_page()`
- `admin_dashboard_page()`

**UI Functions:**
- `apply_custom_css()`
- `get_color_sequence()`
- `render_sidebar()`
- `change_page()`

---

## Design Patterns

### 1. Context Manager Pattern

**Usage**: Database connections

```python
@contextmanager
def get_business_db():
    conn = sqlite3.connect(BUSINESS_DB, timeout=10)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()

# Usage
with get_business_db() as conn:
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM transactions")
    # Automatic commit and close
```

**Benefits:**
- Automatic resource cleanup
- Exception safety
- Consistent connection handling

### 2. Session State Pattern

**Usage**: User session management

```python
def init_session_state():
    defaults = {
        'token': None,
        'logged_in': False,
        'username': None,
        'user_id': None,
        'role': None,
        'page': "Home"
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val
```

**Benefits:**
- Persistent state across reruns
- User-specific data isolation
- Simple state management

### 3. Factory Pattern

**Usage**: Chart creation

```python
def get_color_sequence(n, palette='Plotly'):
    palettes = {
        'Set2': qualitative.Set2,
        'Pastel': qualitative.Pastel,
        'Plotly': qualitative.Plotly
    }
    colors = palettes.get(palette, qualitative.Plotly)
    return [colors[i % len(colors)] for i in range(n)]
```

**Benefits:**
- Flexible color scheme selection
- Easy to extend
- Consistent styling

### 4. Strategy Pattern

**Usage**: Forecasting methods

```python
def get_forecast(user_id, business_id, target, periods, freq, method='auto'):
    ts = prepare_time_series(user_id, business_id, target, freq)
    
    if method == 'auto':
        method = 'prophet' if prophet_available else 'linear'
    
    if method == 'prophet':
        return forecast_with_prophet(ts, periods, freq)
    else:
        return forecast_with_linear_regression(ts, periods, freq)
```

**Benefits:**
- Interchangeable algorithms
- Fallback mechanism
- Easy to add new methods

### 5. Decorator Pattern

**Usage**: Permission checking

```python
def can_edit_transactions():
    return st.session_state.role in ['Owner', 'Accountant']

def can_delete_transactions():
    return st.session_state.role == 'Owner'

def is_admin():
    return st.session_state.role == 'Owner'

# Usage in pages
if can_edit_transactions():
    # Show edit UI
else:
    st.info("Read-only access")
```

**Benefits:**
- Centralized permission logic
- Reusable checks
- Easy to modify

---

## API Reference

### Core Functions

#### Authentication

```python
def login_user(username: str, password: str) -> Tuple[bool, str]:
    """
    Authenticate user and create session.
    
    Args:
        username: User's username
        password: Plain text password
    
    Returns:
        (success: bool, message: str)
    """
```

```python
def create_jwt_token(user_id: int, username: str, role: str) -> str:
    """
    Generate JWT token for authenticated user.
    
    Args:
        user_id: User's database ID
        username: User's username
        role: User's role (Owner/Accountant/Staff)
    
    Returns:
        JWT token string
    """
```

#### Transaction Management

```python
def calculate_profit_metrics(
    user_id: int,
    business_id: int,
    period: str = 'monthly'
) -> Dict[str, float]:
    """
    Calculate comprehensive profit metrics.
    
    Args:
        user_id: User ID
        business_id: Business ID
        period: 'daily', 'weekly', or 'monthly'
    
    Returns:
        Dictionary with metrics:
        - total_revenue
        - total_cogs
        - total_expenses
        - gross_profit
        - net_profit
        - gross_margin
        - net_margin
        - period_profit
        - period_sales
        - transaction_count
    """
```

#### Inventory Management

```python
def add_product(
    user_id: int,
    business_id: int,
    name: str,
    sku: str,
    qty: float,
    cost: float,
    price: float,
    reorder: float,
    category: str
) -> Tuple[bool, str]:
    """
    Add new product to inventory.
    
    Args:
        user_id: User ID
        business_id: Business ID
        name: Product name
        sku: Stock keeping unit (unique)
        qty: Initial quantity
        cost: Cost price per unit
        price: Selling price per unit
        reorder: Reorder level threshold
        category: Product category
    
    Returns:
        (success: bool, message: str)
    """
```

```python
def record_stock_movement(
    pid: int,
    move_type: str,
    qty: float,
    unit_cost: Optional[float] = None,
    unit_price: Optional[float] = None,
    ref: Optional[int] = None,
    notes: str = ""
) -> Tuple[bool, str]:
    """
    Record inventory movement.
    
    Args:
        pid: Product ID
        move_type: 'purchase', 'sale', or 'adjustment'
        qty: Quantity (positive)
        unit_cost: Cost per unit (for purchases)
        unit_price: Price per unit (for sales)
        ref: Reference ID (e.g., transaction ID)
        notes: Additional notes
    
    Returns:
        (success: bool, message: str)
    """
```

#### Forecasting

```python
def get_forecast(
    user_id: int,
    business_id: int,
    target: str = 'sales',
    periods: int = 30,
    freq: str = 'D',
    method: str = 'auto'
) -> Optional[pd.DataFrame]:
    """
    Generate forecast for sales or profit.
    
    Args:
        user_id: User ID
        business_id: Business ID
        target: 'sales' or 'profit'
        periods: Number of periods to forecast
        freq: 'D' (daily), 'W' (weekly), or 'M' (monthly)
        method: 'auto', 'prophet', or 'linear'
    
    Returns:
        DataFrame with columns:
        - ds: Date
        - yhat: Predicted value
        - yhat_lower: Lower confidence bound
        - yhat_upper: Upper confidence bound
        
        Returns None if insufficient data
    """
```

#### Report Generation

```python
def generate_excel_report(
    data_dict: Dict[str, pd.DataFrame],
    start_date: str,
    end_date: str
) -> io.BytesIO:
    """
    Generate Excel report.
    
    Args:
        data_dict: Dictionary with keys:
            - 'transactions': Transaction DataFrame
            - 'summary': Summary DataFrame
            - 'inventory': Inventory DataFrame
        start_date: Report start date
        end_date: Report end date
    
    Returns:
        BytesIO object containing Excel file
    """
```

---

## Deployment Architecture

### Local Deployment

```
┌─────────────────────────────────┐
│   User's Computer               │
│                                 │
│  ┌──────────────────────────┐   │
│  │  Streamlit Process       │   │
│  │  Port: 8501              │   │
│  └──────────┬───────────────┘   │
│             │                   │
│  ┌──────────▼───────────────┐   │
│  │  SQLite Databases        │   │
│  │  - USER.db               │   │
│  │  - BUSINESS.db           │   │
│  └──────────────────────────┘   │
└─────────────────────────────────┘
```

### Cloud Deployment (Example: AWS)

```
┌─────────────────────────────────────────┐
│   AWS Cloud                             │
│                                         │
│  ┌───────────────────────────────────┐  │
│  │  Application Load Balancer        │  │
│  │  (HTTPS/SSL)                      │  │
│  └──────────┬────────────────────────┘  │
│             │                           │
│  ┌──────────▼────────────┐              │
│  │  EC2 Instance(s)      │              │
│  │  - Streamlit App      │              │
│  │  - Python 3.10        │              │
│  │  - Nginx (reverse     │              │
│  │    proxy)             │              │
│  └──────────┬────────────┘              │
│             │                           │
│  ┌──────────▼────────────┐              │
│  │  EBS Volume           │              │
│  │  - SQLite databases   │              │
│  │  - Persistent storage │              │
│  └───────────────────────┘              │
│                                         │
│  ┌───────────────────────┐              │
│  │  S3 Bucket            │              │
│  │  - Database backups   │              │
│  │  - Report archives    │              │
│  └───────────────────────┘              │
└─────────────────────────────────────────┘
```

### Docker Deployment

```dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8501

CMD ["streamlit", "run", "streamlit_app.py", \
     "--server.port=8501", \
     "--server.address=0.0.0.0"]
```

### Scaling Considerations

**Vertical Scaling:**
- Increase CPU/RAM for single instance
- Suitable for up to 100 concurrent users

**Horizontal Scaling:**
- Multiple app instances behind load balancer
- Shared database on network storage
- Session affinity required (sticky sessions)

**Database Scaling:**
- Migrate from SQLite to PostgreSQL/MySQL
- Separate database server
- Connection pooling
- Read replicas for analytics

---

## Performance Considerations

### Database Optimization

1. **Indexes**: Created on frequently queried columns
2. **Query Optimization**: Use of aggregations in SQL
3. **Connection Pooling**: Context managers for efficient connections
4. **Batch Operations**: Bulk inserts during CSV import

### Application Optimization

1. **Lazy Loading**: Data loaded on-demand
2. **Caching**: Streamlit's built-in caching for expensive operations
3. **Pagination**: Limit results for large datasets
4. **Efficient Data Structures**: Pandas for vectorized operations

### UI Optimization

1. **Minimal Reruns**: Strategic use of st.rerun()
2. **Progress Indicators**: For long-running operations
3. **Responsive Design**: Efficient CSS
4. **Chart Optimization**: Plotly's WebGL rendering for large datasets

---

## Testing Strategy

### Unit Testing (Recommended)

```python
import pytest
from streamlit_app import calculate_profit_metrics

def test_profit_calculation():
    # Mock database
    # Test calculation logic
    pass
```

### Integration Testing

```python
def test_transaction_flow():
    # Test complete transaction creation flow
    pass
```

### End-to-End Testing

```python
from selenium import webdriver

def test_user_journey():
    # Test complete user workflow
    pass
```

---

## Maintenance & Monitoring

### Logging

```python
import logging

logging.basicConfig(
    filename='app.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
```

### Health Checks

```python
def health_check():
    try:
        with get_business_db() as conn:
            conn.execute("SELECT 1")
        return True
    except:
        return False
```

### Backup Strategy

```bash
#!/bin/bash
# Daily backup script
DATE=$(date +%Y%m%d)
cp USER.db backups/USER_$DATE.db
cp BUSINESS.db backups/BUSINESS_$DATE.db
```

---

**Last Updated**: 2026

