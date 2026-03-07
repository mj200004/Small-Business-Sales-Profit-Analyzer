# Business Analyzer - Complete Business Management System

A comprehensive web-based business management tool built with Streamlit that provides authentication, transaction tracking, inventory management, advanced analytics, and AI-powered forecasting for small to medium businesses.

## 📚 Documentation

- **[Quick Start](QUICK_START.md)** - Get started in 5 minutes! ⚡
- **[Setup Guide](SETUP_GUIDE.md)** - Complete installation and configuration instructions
- **[Docker Deployment](DOCKER_DEPLOYMENT.md)** - Containerization and cloud deployment guide 🐳
- **[User Guide](USER_GUIDE.md)** - Detailed guide for using all features
- **[Features](FEATURES.md)** - Complete feature list across all milestones
- **[Architecture](ARCHITECTURE.md)** - Technical architecture and design documentation
- **[Changelog](CHANGELOG.md)** - Version history and milestone details

## 🚀 Quick Start

### Option 1: Local Python Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Run the application
streamlit run streamlit_app.py
```

Then open `http://localhost:8501` in your browser and follow the [Quick Start Guide](QUICK_START.md)!

### Option 2: Docker Deployment (Recommended for Production)

```bash
# Quick deployment with script
./deploy.sh deploy          # Linux/macOS
deploy.bat deploy           # Windows

# Or manually with Docker
docker build -t business-analyzer .
docker run -p 8501:8501 -v $(pwd)/data:/app/data business-analyzer

# Or with Docker Compose
docker-compose up -d
```

See the complete [Docker Deployment Guide](DOCKER_DEPLOYMENT.md) for cloud deployment options!

## Features Overview

### Authentication & Transaction Logging
- Secure user registration and login with JWT tokens and bcrypt password hashing
- Role-based access control (Owner, Accountant, Staff)
- Multi-business profile management
- Transaction logging (Sales & Expenses)
- Interactive sales dashboard with category breakdowns
- CSV/Excel file import and analysis

### Profit & Inventory Tracking
- Real-time profit metrics calculation (Gross Profit, Net Profit, Margins)
- Complete inventory management system with SKU tracking
- Cost of Goods Sold (COGS) analysis
- Stock movement tracking (purchases, sales, adjustments)
- Low stock alerts and reorder level management
- Inventory valuation reports

### Advanced Analytics & Visualization
- Interactive sales trend analysis (Daily/Weekly/Monthly)
- Profit margin visualization over time
- Expense and sales category breakdowns
- AI-based forecasting using Facebook Prophet (with linear regression fallback)
- Multi-frequency forecasting (Daily, Weekly, Monthly)
- Confidence interval predictions

### Reports & Administration
- PDF and Excel report generation
- Email report delivery (SMTP integration)
- Admin dashboard with system statistics
- User management and monitoring
- System health metrics
- Data quality tracking

## Technology Stack

- **Frontend/Backend**: Streamlit
- **Database**: SQLite (USER.db, BUSINESS.db)
- **Authentication**: JWT + bcrypt
- **Data Processing**: Pandas, NumPy
- **Visualization**: Plotly Express & Graph Objects
- **Forecasting**: Facebook Prophet, scikit-learn
- **Reports**: FPDF2, OpenPyXL
- **Email**: smtplib

## Installation

### Prerequisites
- Python 3.8 or higher
- pip package manager

### Setup Instructions

1. Clone or download this repository

2. Install required dependencies:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
streamlit run streamlit_app.py
```

4. Access the application in your browser at `http://localhost:8501`

## Quick Start Guide

### First Time Setup

1. **Sign Up**: Create an account with username, email, password, and select your role
2. **Create Business**: Navigate to "Businesses" and add your first business profile
3. **Add Transactions**: Use "Add Tx" to manually add sales or expenses
4. **Import Data**: Use "Import" to bulk upload transactions from CSV files

### Daily Usage

1. **Dashboard**: View key metrics and transaction counts
2. **Add Transactions**: Record daily sales and expenses
3. **Check Inventory**: Monitor stock levels and receive low-stock alerts
4. **View Analytics**: Analyze trends, margins, and forecasts
5. **Generate Reports**: Create PDF/Excel reports for stakeholders

## User Roles & Permissions

| Feature | Owner | Accountant | Staff |
|---------|-------|------------|-------|
| View Transactions | ✓ | ✓ | ✓ |
| Add Transactions | ✓ | ✓ | ✗ |
| Edit Transactions | ✓ | ✓ | ✗ |
| Delete Transactions | ✓ | ✗ | ✗ |
| Manage Inventory | ✓ | ✓ | ✗ |
| View Analytics | ✓ | ✓ | ✓ |
| Generate Reports | ✓ | ✓ | ✗ |
| Admin Dashboard | ✓ | ✗ | ✗ |
| User Management | ✓ | ✗ | ✗ |

## Database Schema

### USER.db
- **users**: User accounts with authentication credentials

### BUSINESS.db
- **businesses**: Business profiles
- **transactions**: Sales and expense records
- **products**: Inventory items with pricing
- **stock_movements**: Inventory change history
- **user_preferences**: User settings and active business
- **admin_logs**: System administration audit trail

## CSV Import Format

The application accepts CSV files with the following columns (flexible mapping):

| Column | Description | Required |
|--------|-------------|----------|
| Amount | Transaction amount | Yes |
| Type | "Sales" or "Expense" | Optional (uses default) |
| Category | Transaction category | Optional |
| Description | Transaction details | Optional |

Example CSV:
```csv
Amount,Type,Category,Description
1500.00,Sales,Electronics,Laptop sale
250.50,Expense,Utilities,Monthly electricity
```

## Forecasting

The application uses two forecasting methods:

1. **Facebook Prophet** (Primary): Advanced time-series forecasting with seasonality detection
2. **Linear Regression** (Fallback): Simple trend-based forecasting when Prophet is unavailable

### Forecasting Requirements
- Minimum 3 data points at selected frequency
- Data spread across multiple dates
- Supports Daily, Weekly, and Monthly forecasting

## Report Generation

### Excel Reports Include:
- Summary sheet with transaction totals by type
- Detailed transaction list
- Current inventory snapshot
- Report metadata (period, generation date)

### PDF Reports Include:
- Executive summary
- Transaction breakdown (first 20 shown)
- Inventory listing
- Professional formatting

## Configuration

### Currency Symbol
Change in Admin Dashboard → System Settings or Profile settings

### Default Reorder Level
Set default inventory reorder threshold in System Settings

### Email Configuration
Requires local SMTP server on port 25 for email delivery
- Configure your SMTP server (e.g., sendmail, postfix)
- Or modify `send_email_simple()` function for external SMTP

## Security Features

- Password hashing with bcrypt
- JWT token-based authentication
- Session management
- SQL injection prevention with parameterized queries
- Role-based access control
- Secure database connections

## Troubleshooting

### Database Connection Issues
- Ensure USER.db and BUSINESS.db exist in the application directory
- Check file permissions
- Verify SQLite is properly installed

### Prophet Installation Issues
```bash
# If Prophet fails to install, the app will use linear regression fallback
pip install prophet --no-cache-dir
```

### Import Errors
- Verify CSV format matches expected structure
- Check for empty or invalid amount values
- Ensure proper encoding (UTF-8 recommended)

## Development

### Project Structure
```
.
├── streamlit_app.py          # Main application file
├── Milestone3 (1).py          # Advanced analytics module
├── requirements.txt           # Python dependencies
├── USER.db                    # User authentication database
├── BUSINESS.db                # Business data database
├── README.md                  # This file
└── LICENSE.txt                # License information
```

### Adding New Features
1. Define page function in streamlit_app.py
2. Add navigation button in `render_sidebar()`
3. Add route in `main()` function
4. Update database schema if needed in `init_business_db()`

## Performance Optimization

- Database queries use indexed columns
- Transactions are batched during CSV import
- Progress indicators for long operations
- Efficient data aggregation with SQL
- Lazy loading of large datasets

## Browser Compatibility

Tested and optimized for:
- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

## License

See LICENSE.txt for details.

## Support

For issues, questions, or feature requests, please refer to the project documentation or contact the development team.

## Acknowledgments

- Built with Streamlit framework
- Forecasting powered by Facebook Prophet
- Visualization by Plotly
- PDF generation by FPDF2

---

LIVE PAGE
```
small-business-sales-profit-analyzer ∙ main ∙ streamlit_app.py
```
**Last Updated**: 2026 
**Author**: Moupriyo Jana (Infosys Springboard Intern)
