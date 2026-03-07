# Business Analyzer - Quick Start Guide

Get up and running with Business Analyzer in 5 minutes!

---

## Installation (2 minutes)

### Step 1: Install Python
Make sure you have Python 3.8 or higher installed:
```bash
python --version
```

### Step 2: Install Dependencies
```bash
cd path/to/BusinessAnalyzer
pip install -r requirements.txt
```

### Step 3: Run the Application
```bash
streamlit run streamlit_app.py
```

The app will open in your browser at `http://localhost:8501`

---

## First-Time Setup (3 minutes)

### 1. Create Your Account
1. Click **Sign Up**
2. Enter:
   - Username: `your_username`
   - Email: `your@email.com`
   - Password: `secure_password`
   - Role: Select **Owner** for full access
3. Click **Sign Up**

### 2. Login
1. Click **Login**
2. Enter your username and password
3. Click **Login**

### 3. Create Your Business
1. Click **Businesses** in the sidebar
2. Expand "Add New Business"
3. Enter:
   - Business Name: `My Business` (required)
   - Type: `Retail` (optional)
4. Click **Create**

### 4. Add Your First Transaction
1. Click **Add Tx** in the sidebar
2. Fill in:
   - Type: **Sales**
   - Amount: `1000`
   - Category: `Electronics`
   - Description: `First sale`
3. Click **Add**

🎉 **Congratulations!** You're all set up!

---

## Common Tasks

### Add a Transaction
**Sidebar → Add Tx**
1. Select Type (Sales/Expense)
2. Enter Amount
3. Add Category
4. Click Add

### View Transactions
**Sidebar → Transactions**
- View all transactions
- Edit amounts, categories
- Download as CSV

### Import CSV Data
**Sidebar → Import**
1. Click "Choose CSV"
2. Select your file
3. Map columns
4. Click IMPORT

### Check Inventory
**Sidebar → Inventory**
- View all products
- Add new products
- Record stock movements
- Check low stock alerts

### View Analytics
**Sidebar → Trends**
- Sales trends (Daily/Weekly/Monthly)
- Profit margins
- Category breakdowns

### Generate Forecast
**Sidebar → Forecast**
1. Select Sales or Profit
2. Choose frequency (Daily/Weekly/Monthly)
3. Set horizon (how far ahead)
4. Click Generate Forecast

### Create Report
**Sidebar → Generate Report**
1. Select date range
2. Choose format (Excel/PDF)
3. Click Generate Report
4. Download

---

## Sample CSV for Testing

Create a file called `test_data.csv`:

```csv
Amount,Type,Category,Description
1500.00,Sales,Electronics,Laptop sale
2500.00,Sales,Electronics,Desktop sale
250.50,Expense,Utilities,Electricity bill
180.00,Expense,Supplies,Office supplies
3200.00,Sales,Services,Consulting service
450.00,Expense,Marketing,Social media ads
1200.00,Sales,Electronics,Tablet sale
320.00,Expense,Rent,Office rent
890.00,Sales,Services,Web development
150.00,Expense,Utilities,Internet bill
```

Import this file to get started with sample data!

---

## Keyboard Shortcuts

- **Tab** - Navigate between fields
- **Enter** - Submit forms
- **Ctrl/Cmd + R** - Refresh page
- **Ctrl/Cmd + F** - Find in page

---

## Navigation Guide

### Sidebar Sections

**Core**
- Dashboard - Overview and metrics
- Sales - Sales dashboard with charts
- Transactions - View all transactions
- Add Tx - Add new transaction

**Business Intelligence**
- Profit - Profit metrics and trends
- Inventory - Product and stock management
- COGS - Cost of goods sold analysis
- Businesses - Manage business profiles

**Advanced**
- Trends - Sales trend analysis
- Forecast - AI-powered predictions
- Margins - Profit margin analysis
- Categories - Expense/sales by category

**Reports & Admin**
- Generate Report - Create PDF/Excel reports
- Admin Dashboard - System management (Owner only)

**Data**
- Import - Bulk import from CSV
- Analyze - Analyze uploaded files

**Account**
- Profile - Update account settings
- Logout - Sign out

---

## Tips for Success

### Data Entry
✓ Enter transactions daily for accurate analytics
✓ Use consistent category names
✓ Add descriptions for large transactions
✓ Set realistic reorder levels for inventory

### Analytics
✓ Review trends weekly
✓ Use forecasting for planning
✓ Monitor profit margins regularly
✓ Check low stock alerts daily

### Reports
✓ Generate monthly reports for review
✓ Export data before making bulk changes
✓ Keep report archives for reference

### Security
✓ Use a strong password
✓ Log out on shared computers
✓ Backup databases weekly
✓ Assign appropriate roles to team members

---

## Troubleshooting

### App won't start
```bash
# Check Python version
python --version

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall

# Try different port
streamlit run streamlit_app.py --server.port 8502
```

### Can't import CSV
- Remove currency symbols (₹, $) from amounts
- Ensure Amount column has valid numbers
- Save CSV as UTF-8 encoding
- Check for empty rows

### Forecast not working
- Need at least 3 data points at selected frequency
- Add more transactions on different dates
- Try a different frequency (Monthly usually works best)

### Charts not showing
- Refresh the page (Ctrl/Cmd + R)
- Clear browser cache
- Try a different browser

---

## Next Steps

1. **Import Your Data**: Use the Import feature to load existing data
2. **Add Products**: Set up your inventory in the Inventory section
3. **Explore Analytics**: Check out Trends, Margins, and Forecasting
4. **Generate Reports**: Create your first report
5. **Read Full Docs**: Check out [USER_GUIDE.md](USER_GUIDE.md) for detailed instructions

---

## Getting Help

- **Setup Issues**: See [SETUP_GUIDE.md](SETUP_GUIDE.md)
- **Feature Details**: See [USER_GUIDE.md](USER_GUIDE.md)
- **Technical Info**: See [ARCHITECTURE.md](ARCHITECTURE.md)
- **Feature List**: See [FEATURES.md](FEATURES.md)

---

## Quick Reference Card

| Task | Location | Key Steps |
|------|----------|-----------|
| Add Transaction | Add Tx | Type → Amount → Category → Add |
| View Sales | Sales | Auto-displays charts |
| Check Profit | Profit | View metrics and trends |
| Add Product | Inventory → Add Product | Name → SKU → Prices → Add |
| Record Sale | Inventory → Movement | Product → sale → Quantity → Record |
| Import Data | Import | Upload CSV → Map → Import |
| View Trends | Trends | Select period → View chart |
| Forecast | Forecast | Target → Frequency → Generate |
| Create Report | Generate Report | Date range → Format → Generate |
| Manage Users | Admin Dashboard | User Management tab |

---

**Ready to go!** Start managing your business with Business Analyzer.

For detailed documentation, see the [complete User Guide](USER_GUIDE.md).
